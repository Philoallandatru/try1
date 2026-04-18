from __future__ import annotations

import sys
import time
import types
import unittest
from pathlib import Path
from time import sleep
from unittest.mock import patch

from apps.portal_runner.auth import PortalRunnerAuthError, verify_bearer_token
from apps.portal_runner.config import load_config, validate_bind_security
from apps.portal_runner.pipeline_registry import get_pipeline_definition, list_pipeline_definitions
from apps.portal_runner.schemas import PipelineInput
from apps.portal_runner.storage import PortalRunnerStorage
from services.workspace import init_workspace
from tests.temp_utils import temporary_directory


class PortalRunnerTest(unittest.TestCase):
    def test_auth_requires_matching_bearer_token(self) -> None:
        verify_bearer_token("Bearer runner-secret", "runner-secret")
        with self.assertRaises(PortalRunnerAuthError):
            verify_bearer_token("Bearer wrong", "runner-secret")

    def test_config_loads_yaml_without_exposing_secrets_in_status(self) -> None:
        fake_yaml = types.SimpleNamespace(
            safe_load=lambda _: {
                "server": {"runner_token": "runner-secret", "max_upload_mb": 25},
                "jira": {"base_url": "https://jira.example.com", "token": "jira-secret"},
                "confluence": {"base_url": "https://conf.example.com", "token": "conf-secret"},
                "workspace": {
                    "root": ".tmp/test-workspaces",
                    "uploads_root": ".tmp/test-uploads",
                    "runs_root": ".tmp/test-runs",
                },
                "pipelines": {
                    "full_real_data_smoke": {
                        "enabled": True,
                        "preferred_parser": "pypdf",
                        "publish_wiki": False,
                    }
                },
            }
        )
        original_yaml = sys.modules.get("yaml")
        sys.modules["yaml"] = fake_yaml
        try:
            with temporary_directory("portal-runner-config") as temp_dir:
                config_path = Path(temp_dir) / "config.yaml"
                config_path.write_text("server: {}\n", encoding="utf-8")
                config = load_config(config_path)
        finally:
            if original_yaml is None:
                sys.modules.pop("yaml", None)
            else:
                sys.modules["yaml"] = original_yaml

        status = config.public_status()
        self.assertEqual(status["server"]["max_upload_mb"], 25)
        self.assertTrue(status["jira"]["configured"])
        self.assertNotIn("jira-secret", str(status))
        self.assertNotIn("conf-secret", str(status))
        validate_bind_security(config, "0.0.0.0")

    def test_config_treats_placeholder_source_tokens_as_unconfigured(self) -> None:
        fake_yaml = types.SimpleNamespace(
            safe_load=lambda _: {
                "server": {"runner_token": "runner-secret"},
                "jira": {"base_url": "https://jira.example.com", "token": "change-me"},
                "confluence": {"base_url": "https://conf.example.com", "token": "<token>"},
            }
        )
        original_yaml = sys.modules.get("yaml")
        sys.modules["yaml"] = fake_yaml
        try:
            with temporary_directory("portal-runner-placeholder-config") as temp_dir:
                config_path = Path(temp_dir) / "config.yaml"
                config_path.write_text("server: {}\n", encoding="utf-8")
                config = load_config(config_path)
        finally:
            if original_yaml is None:
                sys.modules.pop("yaml", None)
            else:
                sys.modules["yaml"] = original_yaml

        status = config.public_status()
        self.assertFalse(status["jira"]["configured"])
        self.assertFalse(status["confluence"]["configured"])

    def test_config_accepts_literal_source_tokens(self) -> None:
        fake_yaml = types.SimpleNamespace(
            safe_load=lambda _: {
                "server": {"runner_token": "runner-secret"},
                "jira": {"base_url": "https://jira.example.com", "token": "jira-secret"},
                "confluence": {"base_url": "https://conf.example.com", "token": "conf-secret"},
            }
        )
        original_yaml = sys.modules.get("yaml")
        sys.modules["yaml"] = fake_yaml
        try:
            with temporary_directory("portal-runner-literal-config") as temp_dir:
                config_path = Path(temp_dir) / "config.yaml"
                config_path.write_text("server: {}\n", encoding="utf-8")
                config = load_config(config_path)
        finally:
            if original_yaml is None:
                sys.modules.pop("yaml", None)
            else:
                sys.modules["yaml"] = original_yaml

        status = config.public_status()
        self.assertTrue(status["jira"]["configured"])
        self.assertTrue(status["confluence"]["configured"])
        self.assertNotIn("jira-secret", str(status))
        self.assertNotIn("conf-secret", str(status))

    def test_pipeline_registry_exposes_fixed_whitelist(self) -> None:
        full = get_pipeline_definition("full_real_data_smoke")
        self.assertIn("jira_issue_key", full.required_inputs)
        self.assertTrue(full.accepts_pdf)
        pipeline_ids = {row["pipeline_id"] for row in list_pipeline_definitions()}
        self.assertIn("jira_live_smoke", pipeline_ids)
        self.assertIn("full_real_data_smoke", pipeline_ids)

    def test_storage_validates_pdf_upload_and_redacts_request_shape(self) -> None:
        with temporary_directory("portal-runner-storage") as temp_dir:
            runs_root = Path(temp_dir) / "runs"
            uploads_root = Path(temp_dir) / "uploads"
            storage = PortalRunnerStorage(runs_root=runs_root, uploads_root=uploads_root)
            definition = get_pipeline_definition("pdf_ingest_smoke")
            manifest = storage.create_run(
                definition=definition,
                pipeline_input=PipelineInput(pipeline_id="pdf_ingest_smoke"),
                client_ip="127.0.0.1",
            )
            upload = storage.save_uploaded_pdf(
                manifest["run_id"],
                filename="sample.pdf",
                content=b"%PDF-1.4\nbody",
                max_upload_mb=1,
            )
            self.assertTrue(Path(upload["path"]).exists())
            self.assertEqual(upload["size_bytes"], 13)

            with self.assertRaises(ValueError):
                storage.save_uploaded_pdf(
                    manifest["run_id"],
                    filename="not-pdf.txt",
                    content=b"not pdf",
                    max_upload_mb=1,
                )

    def test_fastapi_app_exposes_authenticated_pipeline_metadata_when_extra_is_installed(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        with temporary_directory("portal-runner-api") as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
                        "jira:",
                        "  base_url: https://jira.example.com",
                        "  token: jira-secret",
                        "confluence:",
                        "  base_url: https://conf.example.com",
                        "  token: conf-secret",
                        "workspace:",
                        f"  root: {Path(temp_dir, 'workspaces').as_posix()}",
                        f"  uploads_root: {Path(temp_dir, 'uploads').as_posix()}",
                        f"  runs_root: {Path(temp_dir, 'runs').as_posix()}",
                        f"  spec_assets_workspace: {Path(temp_dir, 'spec-assets').as_posix()}",
                        "pipelines:",
                        "  full_real_data_smoke:",
                        "    enabled: true",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            from apps.portal_runner.server import create_app

            client = TestClient(create_app(config_path, host="0.0.0.0"))
            unauthorized = client.get("/api/pipelines")
            authorized = client.get("/api/pipelines", headers={"Authorization": "Bearer runner-secret"})

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertTrue(any(row["pipeline_id"] == "full_real_data_smoke" for row in authorized.json()["pipelines"]))

    def test_fastapi_app_can_run_pdf_ingest_smoke_when_extra_is_installed(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        with temporary_directory("portal-runner-pdf-api") as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
                        "  max_upload_mb: 10",
                        "jira:",
                        "  base_url: https://jira.example.com",
                        "  token: jira-secret",
                        "confluence:",
                        "  base_url: https://conf.example.com",
                        "  token: conf-secret",
                        "workspace:",
                        f"  root: {Path(temp_dir, 'workspaces').as_posix()}",
                        f"  uploads_root: {Path(temp_dir, 'uploads').as_posix()}",
                        f"  runs_root: {Path(temp_dir, 'runs').as_posix()}",
                        f"  spec_assets_workspace: {Path(temp_dir, 'spec-assets').as_posix()}",
                        "pipelines:",
                        "  pdf_ingest_smoke:",
                        "    enabled: true",
                        "    preferred_parser: pypdf",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            from apps.portal_runner.server import create_app

            client = TestClient(create_app(config_path, host="127.0.0.1"))
            headers = {"Authorization": "Bearer runner-secret"}
            with Path("fixtures/corpus/pdf/sample.pdf").open("rb") as handle:
                response = client.post(
                    "/api/runs",
                    headers=headers,
                    data={"pipeline_id": "pdf_ingest_smoke", "preferred_parser": "pypdf"},
                    files={"pdf": ("sample.pdf", handle, "application/pdf")},
                )
            self.assertEqual(response.status_code, 200, response.text)
            run_id = response.json()["run_id"]

            detail = {}
            for _ in range(50):
                detail = client.get(f"/api/runs/{run_id}", headers=headers).json()
                if detail["status"] in {"succeeded", "failed", "cancelled"}:
                    break
                sleep(0.1)

        self.assertEqual(detail["status"], "succeeded")
        self.assertTrue(all(step["status"] == "succeeded" for step in detail["steps"]))

    def test_fastapi_app_can_run_full_real_data_smoke_with_mocked_sources(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        from apps.portal_runner.server import create_app
        from services.connectors.confluence.connector import load_confluence_sync
        from services.connectors.jira.connector import load_jira_sync

        jira_payload = load_jira_sync("fixtures/connectors/jira/incremental_sync.json")
        confluence_payload = load_confluence_sync("fixtures/connectors/confluence/page_sync.json")

        def fake_load_source_payload(*, kind: str, **_: object) -> dict:
            if kind == "jira":
                return jira_payload
            if kind == "confluence":
                return confluence_payload
            raise AssertionError(f"Unexpected source kind: {kind}")

        with temporary_directory("portal-runner-full-api") as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
                        "  max_upload_mb: 10",
                        "jira:",
                        "  base_url: https://jira.example.com",
                        "  token: jira-secret",
                        "confluence:",
                        "  base_url: https://conf.example.com",
                        "  token: conf-secret",
                        "workspace:",
                        f"  root: {Path(temp_dir, 'workspaces').as_posix()}",
                        f"  uploads_root: {Path(temp_dir, 'uploads').as_posix()}",
                        f"  runs_root: {Path(temp_dir, 'runs').as_posix()}",
                        f"  spec_assets_workspace: {Path(temp_dir, 'spec-assets').as_posix()}",
                        "pipelines:",
                        "  full_real_data_smoke:",
                        "    enabled: true",
                        "    preferred_parser: pypdf",
                        "    publish_wiki: true",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            client = TestClient(create_app(config_path, host="127.0.0.1"))
            headers = {"Authorization": "Bearer runner-secret"}
            with patch("apps.portal_runner.runner.load_source_payload", side_effect=fake_load_source_payload):
                with Path("fixtures/corpus/pdf/sample.pdf").open("rb") as handle:
                    response = client.post(
                        "/api/runs",
                        headers=headers,
                        data={
                            "pipeline_id": "full_real_data_smoke",
                            "jira_issue_key": "SSD-102",
                            "confluence_page_id": "CONF-201",
                            "preferred_parser": "pypdf",
                            "publish_wiki": "true",
                            "topic_slug": "real-source-smoke",
                            "topic_title": "Real Source Smoke",
                            "mock_response": "Mock full smoke",
                        },
                        files={"pdf": ("sample.pdf", handle, "application/pdf")},
                    )
                self.assertEqual(response.status_code, 200, response.text)
                run_id = response.json()["run_id"]

                detail = {}
                for _ in range(80):
                    detail = client.get(f"/api/runs/{run_id}", headers=headers).json()
                    if detail["status"] in {"succeeded", "failed", "cancelled"}:
                        break
                    sleep(0.1)

        self.assertEqual(detail["status"], "succeeded", detail.get("error"))
        self.assertIn("wiki-publish", detail["artifacts"])
        self.assertTrue(all(step["status"] == "succeeded" for step in detail["steps"]))

    def test_fastapi_app_can_reuse_ingested_spec_asset_for_jira_pdf_qa(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        from apps.portal_runner.server import create_app
        from services.connectors.confluence.connector import load_confluence_sync
        from services.connectors.jira.connector import load_jira_sync

        jira_payload = load_jira_sync("fixtures/connectors/jira/incremental_sync.json")
        confluence_payload = load_confluence_sync("fixtures/connectors/confluence/page_sync.json")

        def fake_load_source_payload(*, kind: str, **_: object) -> dict:
            if kind == "jira":
                return jira_payload
            if kind == "confluence":
                return confluence_payload
            raise AssertionError(f"Unexpected source kind: {kind}")

        with temporary_directory("portal-runner-reuse-api") as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
                        "  max_upload_mb: 10",
                        "jira:",
                        "  base_url: https://jira.example.com",
                        "  token: jira-secret",
                        "confluence:",
                        "  base_url: https://conf.example.com",
                        "  token: conf-secret",
                        "workspace:",
                        f"  root: {Path(temp_dir, 'workspaces').as_posix()}",
                        f"  uploads_root: {Path(temp_dir, 'uploads').as_posix()}",
                        f"  runs_root: {Path(temp_dir, 'runs').as_posix()}",
                        f"  spec_assets_workspace: {Path(temp_dir, 'spec-assets').as_posix()}",
                        "pipelines:",
                        "  pdf_ingest_smoke:",
                        "    enabled: true",
                        "    preferred_parser: pypdf",
                        "  jira_pdf_qa_smoke:",
                        "    enabled: true",
                        "    preferred_parser: pypdf",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            client = TestClient(create_app(config_path, host="127.0.0.1"))
            headers = {"Authorization": "Bearer runner-secret"}
            with Path("fixtures/corpus/pdf/sample.pdf").open("rb") as handle:
                ingest_response = client.post(
                    "/api/runs",
                    headers=headers,
                    data={"pipeline_id": "pdf_ingest_smoke", "preferred_parser": "pypdf", "spec_asset_id": "nvme-shared"},
                    files={"pdf": ("sample.pdf", handle, "application/pdf")},
                )
            self.assertEqual(ingest_response.status_code, 200, ingest_response.text)
            self._wait_for_run(client, headers, ingest_response.json()["run_id"])

            assets = client.get("/api/spec-assets", headers=headers).json()["assets"]
            self.assertTrue(any(asset["asset_id"] == "nvme-shared" for asset in assets))

            with patch("apps.portal_runner.runner.load_source_payload", side_effect=fake_load_source_payload):
                qa_response = client.post(
                    "/api/runs",
                    headers=headers,
                    data={
                        "pipeline_id": "jira_pdf_qa_smoke",
                        "jira_issue_key": "SSD-102",
                        "confluence_scope": "page",
                        "confluence_page_id": "CONF-201",
                        "spec_asset_id": "nvme-shared",
                        "mock_response": "Mock Jira PDF QA",
                    },
                )
                self.assertEqual(qa_response.status_code, 200, qa_response.text)
                qa_detail = self._wait_for_run(client, headers, qa_response.json()["run_id"])

        self.assertEqual(qa_detail["status"], "succeeded", qa_detail.get("error"))
        self.assertIn("selected-spec-asset", qa_detail["artifacts"])

    def test_fastapi_app_can_run_profile_prompt_debug_with_llm(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        from apps.portal_runner.server import create_app
        from services.connectors.confluence.connector import load_confluence_sync
        from services.connectors.jira.connector import load_jira_sync

        jira_payload = load_jira_sync("fixtures/connectors/jira/incremental_sync.json")
        confluence_payload = load_confluence_sync("fixtures/connectors/confluence/page_sync.json")

        def fake_load_source_payload(*, kind: str, **_: object) -> dict:
            if kind == "jira":
                return jira_payload
            if kind == "confluence":
                return confluence_payload
            raise AssertionError(f"Unexpected source kind: {kind}")

        with temporary_directory("portal-runner-profile-prompt") as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
                        "  max_upload_mb: 10",
                        "jira:",
                        "  base_url: https://jira.example.com",
                        "  token: jira-secret",
                        "confluence:",
                        "  base_url: https://conf.example.com",
                        "  token: conf-secret",
                        "workspace:",
                        f"  root: {Path(temp_dir, 'workspaces').as_posix()}",
                        f"  uploads_root: {Path(temp_dir, 'uploads').as_posix()}",
                        f"  runs_root: {Path(temp_dir, 'runs').as_posix()}",
                        f"  spec_assets_workspace: {Path(temp_dir, 'spec-assets').as_posix()}",
                        "pipelines:",
                        "  profile_prompt_debug:",
                        "    enabled: true",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            client = TestClient(create_app(config_path, host="127.0.0.1"))
            headers = {"Authorization": "Bearer runner-secret"}

            with patch("services.workspace.workspace.load_source_payload", side_effect=fake_load_source_payload):
                response = client.post(
                    "/api/runs",
                    headers=headers,
                    data={
                        "pipeline_id": "profile_prompt_debug",
                        "profile": "debug_ssd",
                        "prompt": "Debug this Jira issue using firmware knowledge and cite relevant evidence.",
                        "jira_issue_key": "SSD-102",
                        "confluence_scope": "page",
                        "confluence_page_id": "CONF-201",
                        "mock_response": "Mock profile debug answer",
                    },
                )
                self.assertEqual(response.status_code, 200, response.text)
                detail = self._wait_for_run(client, headers, response.json()["run_id"])

            self.assertEqual(detail["status"], "succeeded", detail.get("error"))
            self.assertIn("profile-registry", detail["artifacts"])
            self.assertIn("profile-prompt-result", detail["artifacts"])
            workspace_dir = Path(config_path.parent, "workspaces", detail["run_id"])
            self.assertTrue((workspace_dir / "workspace.yaml").exists())
            self.assertTrue((workspace_dir / "profiles" / "debug_ssd.yaml").exists())
            self.assertTrue((workspace_dir / "sources" / "portal_jira.yaml").exists())
            self.assertTrue((workspace_dir / "sources" / "portal_confluence.yaml").exists())
            self.assertTrue((workspace_dir / "build" / "index" / "pageindex_v1" / "page_index.json").exists())

    def test_fastapi_app_can_run_workspace_analyze_jira_on_existing_workspace(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        from apps.portal_runner.server import create_app

        with temporary_directory("portal-runner-workspace-analyze") as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            workspace_dir = Path(temp_dir, "workspace")
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
                        "jira:",
                        "  base_url: https://jira.example.com",
                        "  token: jira-secret",
                        "confluence:",
                        "  base_url: https://conf.example.com",
                        "  token: conf-secret",
                        "workspace:",
                        f"  root: {Path(temp_dir, 'workspaces').as_posix()}",
                        f"  uploads_root: {Path(temp_dir, 'uploads').as_posix()}",
                        f"  runs_root: {Path(temp_dir, 'runs').as_posix()}",
                        f"  spec_assets_workspace: {Path(temp_dir, 'spec-assets').as_posix()}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            init_workspace(workspace_dir)
            (workspace_dir / "sources" / "jira_fixture.yaml").write_text(
                "\n".join(
                    [
                        "version: 1",
                        "name: jira_fixture",
                        "kind: jira",
                        "connector_type: jira.atlassian_api",
                        "mode: fixture",
                        "config:",
                        "  path: fixtures/connectors/jira/incremental_sync.json",
                        "defaults: {}",
                        "policies:",
                        "  - team:ssd",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (workspace_dir / "selectors" / "jira_one_issue.yaml").write_text(
                "\n".join(
                    [
                        "version: 1",
                        "name: jira_one_issue",
                        "source: jira_fixture",
                        "selector:",
                        "  type: issue",
                        "  issue_key: SSD-102",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (workspace_dir / "profiles" / "ssd_default.yaml").write_text(
                "\n".join(
                    [
                        "version: 1",
                        "name: ssd_default",
                        "inputs:",
                        "  jira:",
                        "    source: jira_fixture",
                        "    selector_profile: jira_one_issue",
                        "analysis:",
                        "  top_k: 3",
                        "  llm_backend: none",
                        "  llm_prompt_mode: strict",
                        "  policies:",
                        "    - team:ssd",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            client = TestClient(create_app(config_path, host="127.0.0.1"))
            headers = {"Authorization": "Bearer runner-secret"}
            response = client.post(
                "/api/workspace/analyze-jira",
                headers=headers,
                json={
                    "workspace_dir": str(workspace_dir),
                    "profile": "ssd_default",
                    "issue_key": "SSD-102",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["analysis"]["profile"], "ssd_default")
        self.assertEqual(payload["portal_state"]["workspace_dir"], str(workspace_dir))
        self.assertEqual(payload["portal_state"]["task_workbench"]["new_task_entry"]["fields"][0]["value"], "SSD-102")

    def test_fastapi_app_exposes_run_events_and_cancel(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        from apps.portal_runner.runner import PortalPipelineRunner
        from apps.portal_runner.server import create_app

        with temporary_directory("portal-runner-cancel-api") as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
                        "  max_upload_mb: 10",
                        "jira:",
                        "  base_url: https://jira.example.com",
                        "  token: jira-secret",
                        "confluence:",
                        "  base_url: https://conf.example.com",
                        "  token: conf-secret",
                        "workspace:",
                        f"  root: {Path(temp_dir, 'workspaces').as_posix()}",
                        f"  uploads_root: {Path(temp_dir, 'uploads').as_posix()}",
                        f"  runs_root: {Path(temp_dir, 'runs').as_posix()}",
                        f"  spec_assets_workspace: {Path(temp_dir, 'spec-assets').as_posix()}",
                        "pipelines:",
                        "  pdf_ingest_smoke:",
                        "    enabled: true",
                        "    preferred_parser: pypdf",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            client = TestClient(create_app(config_path, host="127.0.0.1"))
            headers = {"Authorization": "Bearer runner-secret"}

            original_workspace_init = PortalPipelineRunner._workspace_init

            def slow_workspace_init(self, run_id: str, context: dict) -> dict:
                time.sleep(0.3)
                return original_workspace_init(self, run_id, context)

            with patch.object(PortalPipelineRunner, "_workspace_init", slow_workspace_init):
                with Path("fixtures/corpus/pdf/sample.pdf").open("rb") as handle:
                    response = client.post(
                        "/api/runs",
                        headers=headers,
                        data={"pipeline_id": "pdf_ingest_smoke", "preferred_parser": "pypdf"},
                        files={"pdf": ("sample.pdf", handle, "application/pdf")},
                    )
                self.assertEqual(response.status_code, 200, response.text)
                run_id = response.json()["run_id"]
                cancel = client.post(f"/api/runs/{run_id}/cancel", headers=headers)
                self.assertEqual(cancel.status_code, 200, cancel.text)

                detail = {}
                for _ in range(80):
                    detail = client.get(f"/api/runs/{run_id}", headers=headers).json()
                    if detail["status"] in {"succeeded", "failed", "cancelled"}:
                        break
                    sleep(0.1)
                events = client.get(f"/api/runs/{run_id}/events", headers=headers).json()["events"]

        self.assertEqual(detail["status"], "cancelled", detail)
        self.assertTrue(any(event["event"] == "cancel-requested" for event in events))
        self.assertTrue(any(event["event"] == "run-created" for event in events))

    def _wait_for_run(self, client, headers: dict, run_id: str) -> dict:
        detail = {}
        for _ in range(80):
            detail = client.get(f"/api/runs/{run_id}", headers=headers).json()
            if detail["status"] in {"succeeded", "failed", "cancelled"}:
                break
            sleep(0.1)
        self.assertEqual(detail["status"], "succeeded", detail.get("error"))
        return detail


if __name__ == "__main__":
    unittest.main()

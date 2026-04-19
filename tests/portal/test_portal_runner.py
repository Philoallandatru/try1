from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys
import time
import types
import unittest
from pathlib import Path
from threading import Thread
from time import sleep
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from apps.portal_runner.auth import PortalRunnerAuthError, verify_bearer_token
from apps.portal_runner.config import load_config, validate_bind_security
from apps.portal_runner.pipeline_registry import get_pipeline_definition, list_pipeline_definitions
from apps.portal_runner.schemas import PipelineInput
from apps.portal_runner.storage import PortalRunnerStorage
from services.workspace import init_workspace
from tests.temp_utils import temporary_directory


class _FakeSourceHandler(BaseHTTPRequestHandler):
    jira_requests = 0
    confluence_requests = 0

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/rest/api/2/search":
            _FakeSourceHandler.jira_requests += 1
            self._send_json(_fake_jira_search_payload())
            return
        if parsed.path == "/rest/api/content":
            _FakeSourceHandler.confluence_requests += 1
            self._send_json(_fake_confluence_content_payload(parse_qs(parsed.query)))
            return
        self.send_error(404)

    def log_message(self, *_: object) -> None:
        return

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _FakeSourceServer:
    def __enter__(self):
        _FakeSourceHandler.jira_requests = 0
        _FakeSourceHandler.confluence_requests = 0
        self.server = HTTPServer(("127.0.0.1", 0), _FakeSourceHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        return self

    def __exit__(self, *_: object) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()


def _fake_jira_search_payload() -> dict:
    return {
        "total": 1,
        "startAt": 0,
        "maxResults": 50,
        "names": {},
        "issues": [
            {
                "key": "SSD-DEMO-A",
                "fields": {
                    "project": {"key": "SSD"},
                    "summary": "[SV][SSD1100][Power][S4 Resume] Resume 后设备枚举成功但首次 I/O 超时",
                    "issuetype": {"name": "FW Bug"},
                    "labels": ["S4", "Resume", "Timeout", "NVMe"],
                    "priority": {"name": "High"},
                    "components": [{"name": "FW"}],
                    "versions": [{"name": "SSD1100"}],
                    "resolution": None,
                    "status": {"name": "In Progress"},
                    "fixVersions": [],
                    "Severity": "Major",
                    "Report Department": "SV",
                    "Root Cause": "Resume 后 controller ready 与 I/O queue recreate 时序重叠",
                    "description": "Device enumerates after S4 resume, but first random read times out once.",
                    "updated": "2026-04-18T10:00:00Z",
                    "comment": {
                        "comments": [
                            {
                                "author": {"displayName": "FW"},
                                "created": "2026-04-18T10:05:00Z",
                                "body": "UART shows queue restore completed after first command submission.",
                            }
                        ]
                    },
                    "attachment": [],
                },
            }
        ],
    }


def _fake_confluence_content_payload(query: dict) -> dict:
    return {
        "results": [
            {
                "id": "CONF-DEMO-1",
                "title": "NVMe Resume Timeout Debug Guide",
                "space": {"key": query.get("space", ["SSDENG"])[0].strip('"')},
                "version": {"number": 3, "when": "2026-04-18T09:00:00Z"},
                "body": {
                    "storage": {
                        "value": (
                            "<h1>Symptom Definition</h1>"
                            "<p>Device enumerates successfully after resume.</p>"
                            "<p>First admin or I/O command times out and retry may succeed.</p>"
                            "<h1>Key Debug Evidence</h1>"
                            "<p>CAP, CC, CSTS timeline and queue recreate completion timestamp.</p>"
                        )
                    }
                },
                "_links": {"webui": "/pages/viewpage.action?pageId=CONF-DEMO-1"},
            }
        ],
        "size": 1,
        "limit": 25,
    }


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

    def test_product_api_supports_zero_start_source_profile_and_analyze_workflow(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        from apps.portal_runner.server import create_app

        with temporary_directory("portal-runner-product-workflow") as temp_dir, _FakeSourceServer() as fake_sources:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
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
            client = TestClient(create_app(config_path, host="127.0.0.1"))
            headers = {"Authorization": "Bearer runner-secret"}

            workspace = client.post(
                "/api/workspaces",
                headers=headers,
                json={"name": "real-user-flow"},
            )
            self.assertEqual(workspace.status_code, 200, workspace.text)
            workspace_dir = workspace.json()["workspace_dir"]

            jira_source = client.post(
                "/api/workspace/sources",
                headers=headers,
                json={
                    "workspace_dir": workspace_dir,
                    "name": "user_jira",
                    "connector_type": "jira.atlassian_api",
                    "base_url": fake_sources.base_url,
                    "token": "jira-secret-token",
                    "defaults": {"fetch_backend": "native", "include_comments": True},
                    "selector": {
                        "name": "user_jira_issue",
                        "type": "issue",
                        "issue_key": "SSD-DEMO-A",
                    },
                },
            )
            self.assertEqual(jira_source.status_code, 200, jira_source.text)
            self.assertNotIn("jira-secret-token", str(jira_source.json()))

            confluence_source = client.post(
                "/api/workspace/sources",
                headers=headers,
                json={
                    "workspace_dir": workspace_dir,
                    "name": "user_confluence",
                    "connector_type": "confluence.atlassian_api",
                    "base_url": fake_sources.base_url,
                    "token": "confluence-secret-token",
                    "defaults": {"fetch_backend": "native", "include_attachments": True},
                    "selector": {
                        "name": "user_confluence_space",
                        "type": "space_slice",
                        "space_key": "SSDENG",
                    },
                },
            )
            self.assertEqual(confluence_source.status_code, 200, confluence_source.text)
            self.assertNotIn("confluence-secret-token", str(confluence_source.json()))

            sources_payload = client.get(
                "/api/workspace/sources",
                headers=headers,
                params={"workspace_dir": workspace_dir},
            )
            self.assertEqual(sources_payload.status_code, 200, sources_payload.text)
            selectors_by_source = {
                selector["source"]: selector["name"]
                for selector in sources_payload.json()["selectors"]
            }
            self.assertEqual(selectors_by_source["user_jira"], "user_jira_issue")
            self.assertEqual(selectors_by_source["user_confluence"], "user_confluence_space")

            extra_selector = client.post(
                "/api/workspace/selectors",
                headers=headers,
                json={
                    "workspace_dir": workspace_dir,
                    "name": "user_jira_project",
                    "source": "user_jira",
                    "selector": {"type": "project_slice", "project_key": "SSD"},
                },
            )
            self.assertEqual(extra_selector.status_code, 200, extra_selector.text)
            self.assertEqual(extra_selector.json()["selector"]["name"], "user_jira_project")

            selector_list = client.get(
                "/api/workspace/selectors",
                headers=headers,
                params={"workspace_dir": workspace_dir},
            )
            self.assertEqual(selector_list.status_code, 200, selector_list.text)
            self.assertIn("user_jira_project", {row["name"] for row in selector_list.json()["selectors"]})

            for source_name, selector_name in [
                ("user_jira", "user_jira_issue"),
                ("user_confluence", "user_confluence_space"),
            ]:
                test_response = client.post(
                    f"/api/workspace/sources/{source_name}/test",
                    headers=headers,
                    json={"workspace_dir": workspace_dir, "selector_profile": selector_name},
                )
                self.assertEqual(test_response.status_code, 200, test_response.text)
                self.assertTrue(test_response.json()["ok"])

                refresh_response = client.post(
                    f"/api/workspace/sources/{source_name}/refresh",
                    headers=headers,
                    json={"workspace_dir": workspace_dir, "selector_profile": selector_name},
                )
                self.assertEqual(refresh_response.status_code, 200, refresh_response.text)
                self.assertGreater(refresh_response.json()["document_count"], 0)

            self.assertEqual(_FakeSourceHandler.jira_requests, 1)
            self.assertEqual(_FakeSourceHandler.confluence_requests, 1)

            refreshed_sources = client.get(
                "/api/workspace/sources",
                headers=headers,
                params={"workspace_dir": workspace_dir},
            )
            self.assertEqual(refreshed_sources.status_code, 200, refreshed_sources.text)
            source_rows = {row["name"]: row for row in refreshed_sources.json()["sources"]}
            self.assertEqual(source_rows["user_jira"]["status"], "fresh")
            self.assertEqual(source_rows["user_jira"]["document_count"], 1)
            self.assertTrue(source_rows["user_jira"]["last_refresh"])
            self.assertEqual(source_rows["user_jira"]["selector"]["name"], "user_jira_issue")
            self.assertTrue(source_rows["user_jira"]["enabled"])

            source_detail = client.get(
                "/api/workspace/sources/user_jira",
                headers=headers,
                params={"workspace_dir": workspace_dir},
            )
            self.assertEqual(source_detail.status_code, 200, source_detail.text)
            self.assertEqual(source_detail.json()["source"]["name"], "user_jira")
            self.assertEqual(source_detail.json()["source"]["status"], "fresh")
            self.assertNotIn("jira-secret-token", str(source_detail.json()))

            registry_path = Path(workspace_dir) / "raw" / "files" / "spec_assets" / "registry.json"
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text(
                json.dumps(
                    {
                        "assets": [
                            {
                                "asset_id": "nvme-spec-mineru",
                                "display_name": "NVMe Spec",
                                "version": "v1",
                                "document_id": "nvme",
                                "parser_used": "mineru",
                                "asset_root": str(registry_path.parent / "nvme-spec-mineru" / "v1"),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            spec_assets = client.get(
                "/api/workspace/spec-assets",
                headers=headers,
                params={"workspace_dir": workspace_dir},
            )
            self.assertEqual(spec_assets.status_code, 200, spec_assets.text)
            self.assertEqual(spec_assets.json()["assets"][0]["asset_id"], "nvme-spec-mineru")

            profile_response = client.post(
                "/api/workspace/profiles",
                headers=headers,
                json={
                    "workspace_dir": workspace_dir,
                    "name": "user_nvme_default",
                    "inputs": {
                        "jira": {"source": "user_jira", "selector_profile": "user_jira_issue"},
                        "evidence": {"source": "user_confluence", "selector_profile": "user_confluence_space"},
                    },
                    "spec_asset_ids": ["nvme-spec-mineru"],
                    "analysis": {
                        "top_k": 5,
                        "llm_backend": "openai-compatible",
                        "llm_model": "qwen-9b",
                        "llm_base_url": "http://127.0.0.1:1234/v1",
                        "llm_prompt_mode": "strict",
                        "policies": ["team:ssd", "public"],
                    },
                },
            )
            self.assertEqual(profile_response.status_code, 200, profile_response.text)

            profile_detail = client.get(
                "/api/workspace/profiles/user_nvme_default",
                headers=headers,
                params={"workspace_dir": workspace_dir},
            )
            self.assertEqual(profile_detail.status_code, 200, profile_detail.text)
            self.assertEqual(profile_detail.json()["profile"]["name"], "user_nvme_default")
            self.assertEqual(profile_detail.json()["profile"]["inputs"]["jira"]["source"], "user_jira")
            self.assertEqual(profile_detail.json()["profile"]["inputs"]["spec_assets"], ["nvme-spec-mineru"])
            self.assertEqual(profile_detail.json()["profile"]["analysis"]["llm_model"], "qwen-9b")

            duplicate_profile = client.post(
                "/api/workspace/profiles/user_nvme_default/duplicate",
                headers=headers,
                json={"workspace_dir": workspace_dir, "name": "user_nvme_copy"},
            )
            self.assertEqual(duplicate_profile.status_code, 200, duplicate_profile.text)
            self.assertEqual(duplicate_profile.json()["profile"]["name"], "user_nvme_copy")
            self.assertEqual(
                duplicate_profile.json()["profile"]["inputs"],
                profile_detail.json()["profile"]["inputs"],
            )

            validate_response = client.post(
                "/api/workspace/profiles/user_nvme_copy/validate",
                headers=headers,
                json={"workspace_dir": workspace_dir},
            )
            self.assertEqual(validate_response.status_code, 200, validate_response.text)
            self.assertTrue(validate_response.json()["ok"])

            test_profile_runtime = client.patch(
                "/api/workspace/profiles/user_nvme_copy",
                headers=headers,
                json={"workspace_dir": workspace_dir, "analysis": {"llm_backend": "none"}},
            )
            self.assertEqual(test_profile_runtime.status_code, 200, test_profile_runtime.text)

            analyze_response = client.post(
                "/api/workspace/analyze-jira",
                headers=headers,
                json={
                    "workspace_dir": workspace_dir,
                    "profile": "user_nvme_copy",
                    "issue_key": "SSD-DEMO-A",
                },
            )
            self.assertEqual(analyze_response.status_code, 200, analyze_response.text)
            payload = analyze_response.json()
            verify_response = client.post(
                f"/api/workspace/runs/{payload['run_id']}/verify-llm",
                headers=headers,
                json={
                    "workspace_dir": workspace_dir,
                    "llm_backend": "mock",
                    "llm_mock_response": "Mock verification",
                },
            )
            self.assertEqual(verify_response.status_code, 200, verify_response.text)
            self.assertEqual(verify_response.json()["verification"]["verification_text"], "Mock verification")
            self.assertEqual(verify_response.json()["verification_count"], 1)
            verify_response_2 = client.post(
                f"/api/workspace/runs/{payload['run_id']}/verify-llm",
                headers=headers,
                json={
                    "workspace_dir": workspace_dir,
                    "llm_backend": "mock",
                    "llm_mock_response": "Second verification",
                },
            )
            self.assertEqual(verify_response_2.status_code, 200, verify_response_2.text)
            self.assertEqual(verify_response_2.json()["verification_count"], 2)
            artifact_response = client.get(
                f"/api/workspace/runs/{payload['run_id']}/artifacts/llm_verification",
                headers=headers,
                params={"workspace_dir": workspace_dir},
            )
            self.assertEqual(artifact_response.status_code, 200, artifact_response.text)
            self.assertEqual(artifact_response.json()["payload"]["backend"], "mock")
            self.assertEqual(artifact_response.json()["payload"]["verification_text"], "Second verification")
            history_response = client.get(
                f"/api/workspace/runs/{payload['run_id']}/artifacts/llm_verification_history",
                headers=headers,
                params={"workspace_dir": workspace_dir},
            )
            self.assertEqual(history_response.status_code, 200, history_response.text)
            self.assertEqual(len(history_response.json()["payload"]["verifications"]), 2)
            run_detail = client.get(
                f"/api/workspace/runs/{payload['run_id']}",
                headers=headers,
                params={"workspace_dir": workspace_dir},
            )
            self.assertEqual(run_detail.status_code, 200, run_detail.text)
            input_config = run_detail.json()["manifest"]["input_config"]
            self.assertEqual(input_config["issue_key"], "SSD-DEMO-A")
            self.assertEqual(input_config["profile"], "user_nvme_copy")
            rerun_response = client.post(
                "/api/workspace/analyze-jira",
                headers=headers,
                json={
                    "workspace_dir": workspace_dir,
                    "profile": input_config["profile"],
                    "issue_key": input_config["issue_key"],
                },
            )
            self.assertEqual(rerun_response.status_code, 200, rerun_response.text)
            self.assertNotEqual(rerun_response.json()["run_id"], payload["run_id"])

        self.assertEqual(payload["issue_key"], "SSD-DEMO-A")
        self.assertEqual(payload["profile"], "user_nvme_copy")
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["run_id"])
        self.assertIn("summary", payload)
        self.assertIn("sections", payload)
        self.assertIn("citations", payload)
        self.assertIn("artifacts", payload)
        self.assertNotIn("pipeline_id", payload)
        self.assertNotIn("jira-secret-token", str(payload))
        self.assertNotIn("confluence-secret-token", str(payload))

    def test_product_api_rejects_non_mineru_nvme_spec_asset(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        from apps.portal_runner.server import create_app

        with temporary_directory("portal-runner-spec-gate") as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            workspace_dir = Path(temp_dir, "workspace")
            registry_path = workspace_dir / "raw" / "files" / "spec_assets" / "registry.json"
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
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
            registry_path.write_text(
                json.dumps(
                    {
                        "assets": [
                            {
                                "asset_id": "nvme-spec-mineru",
                                "display_name": "NVMe Spec",
                                "version": "v1",
                                "document_id": "nvme",
                                "parser_used": "pypdf",
                                "asset_root": str(registry_path.parent / "nvme-spec-mineru" / "v1"),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app(config_path, host="127.0.0.1"))
            response = client.get(
                "/api/workspace/spec-assets/nvme-spec-mineru/require-mineru",
                headers={"Authorization": "Bearer runner-secret"},
                params={"workspace_dir": str(workspace_dir)},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("MinerU", response.text)

    def test_product_api_bootstraps_demo_workspace_without_faking_missing_spec(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        from apps.portal_runner.server import create_app

        with temporary_directory("portal-runner-demo-workspace") as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
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
            client = TestClient(create_app(config_path, host="127.0.0.1"))
            headers = {"Authorization": "Bearer runner-secret"}

            workspaces = client.get("/api/workspaces", headers=headers)
            self.assertEqual(workspaces.status_code, 200, workspaces.text)
            demo = next(row for row in workspaces.json()["workspaces"] if row["name"] == "demo")
            self.assertTrue(demo["setup_required"])
            self.assertEqual(demo["missing_spec_asset"], "nvme-spec-mineru")

            sources = client.get(
                "/api/workspace/sources",
                headers=headers,
                params={"workspace_dir": demo["workspace_dir"]},
            )
            self.assertEqual(sources.status_code, 200, sources.text)
            source_names = {row["name"] for row in sources.json()["sources"]}
            selector_names = {row["name"] for row in sources.json()["selectors"]}

            profiles = client.get(
                "/api/workspace/profiles",
                headers=headers,
                params={"workspace_dir": demo["workspace_dir"]},
            )
            self.assertEqual(profiles.status_code, 200, profiles.text)

        self.assertIn("demo_jira", source_names)
        self.assertIn("demo_confluence", source_names)
        self.assertIn("demo_jira_project", selector_names)
        self.assertIn("demo_confluence_space", selector_names)
        self.assertEqual(profiles.json()["profiles"], [])

    def test_product_api_bootstraps_demo_profile_when_mineru_spec_exists(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("portal-runner extra is not installed")

        from apps.portal_runner.server import create_app

        with temporary_directory("portal-runner-demo-mineru-ready") as temp_dir:
            workspace_root = Path(temp_dir, "workspaces")
            demo_workspace = workspace_root / "demo"
            registry_path = demo_workspace / "raw" / "files" / "spec_assets" / "registry.json"
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text(
                json.dumps(
                    {
                        "assets": [
                            {
                                "asset_id": "nvme-spec-mineru",
                                "display_name": "NVMe Spec",
                                "version": "v1",
                                "document_id": "nvme",
                                "parser_used": "mineru",
                                "asset_root": str(registry_path.parent / "nvme-spec-mineru" / "v1"),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "server:",
                        "  runner_token: runner-secret",
                        "workspace:",
                        f"  root: {workspace_root.as_posix()}",
                        f"  uploads_root: {Path(temp_dir, 'uploads').as_posix()}",
                        f"  runs_root: {Path(temp_dir, 'runs').as_posix()}",
                        f"  spec_assets_workspace: {Path(temp_dir, 'spec-assets').as_posix()}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            client = TestClient(create_app(config_path, host="127.0.0.1"))
            headers = {"Authorization": "Bearer runner-secret"}

            workspaces = client.get("/api/workspaces", headers=headers)
            self.assertEqual(workspaces.status_code, 200, workspaces.text)
            demo = next(row for row in workspaces.json()["workspaces"] if row["name"] == "demo")
            self.assertFalse(demo["setup_required"])
            self.assertEqual(demo["spec_asset"]["parser_used"], "mineru")

            profiles = client.get(
                "/api/workspace/profiles",
                headers=headers,
                params={"workspace_dir": demo["workspace_dir"]},
            )
            self.assertEqual(profiles.status_code, 200, profiles.text)
            profile_names = {profile["name"] for profile in profiles.json()["profiles"]}

        self.assertIn("demo_nvme_default", profile_names)

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
                time.sleep(1.0)
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

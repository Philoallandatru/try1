from __future__ import annotations

import sys
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


if __name__ == "__main__":
    unittest.main()

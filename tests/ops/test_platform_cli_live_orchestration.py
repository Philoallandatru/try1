from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import unittest
from unittest.mock import patch

from scripts import platform_cli
from services.ingest.normalizer import normalize_markdown_text
from tests.temp_utils import temporary_directory as TemporaryDirectory


class PlatformCliLiveOrchestrationTest(unittest.TestCase):
    def _live_jira_payload(self) -> dict:
        jira_document = normalize_markdown_text(
            "# Live Jira Sync\n\nFirmware flush ordering changed.",
            document_id="SSD-401",
            source_type="jira",
            authority_level="supporting",
            version="2026-04-07T08:00:00Z",
            language="en",
            title="Live Jira Sync",
            source_uri="https://jira.example.com/browse/SSD-401",
            ingested_at="2026-04-07T08:00:00Z",
            parser="jira-markdown-normalizer",
            acl_policy="team:ssd",
        )
        jira_document["markdown"] = "# Live Jira Sync\n\nFirmware flush ordering changed."
        jira_document["metadata"] = {
            "issue_fields": {
                "Priority": "Highest",
                "Root Cause": "Firmware flush ordering changed",
            }
        }
        jira_document["comments"] = ["Need spec comparison."]
        return {
            "sync_type": "incremental",
            "cursor": "jira-live-003",
            "documents": [jira_document],
        }

    def _live_confluence_payload(self) -> dict:
        confluence_document = normalize_markdown_text(
            "# Live Confluence Sync\n\nLatency budget updated.",
            document_id="CONF-701",
            source_type="confluence",
            authority_level="supporting",
            version="7",
            language="en",
            title="Live Confluence Sync",
            source_uri="https://confluence.example.com/pages/viewpage.action?pageId=CONF-701",
            ingested_at="2026-04-07T08:05:00Z",
            parser="confluence-markdown-normalizer",
            acl_policy="team:ssd",
        )
        return {
            "sync_type": "incremental",
            "cursor": "conf-live-007",
            "documents": [confluence_document],
        }

    def test_multi_sync_health_supports_live_dual_source_orchestration(self) -> None:
        jira_payload = self._live_jira_payload()
        confluence_payload = self._live_confluence_payload()

        with TemporaryDirectory() as temp_dir:
            stdout = StringIO()
            argv = [
                "platform_cli.py",
                "multi-sync-health",
                "--snapshot-dir",
                temp_dir,
                "--jira-live",
                "--jira-base-url",
                "https://jira.example.com",
                "--jira-token",
                "secret",
                "--confluence-live",
                "--confluence-base-url",
                "https://confluence.example.com",
                "--confluence-token",
                "secret",
                "--reference-time-iso",
                "2026-04-07T09:00:00Z",
            ]
            with patch("services.ops.orchestration.fetch_jira_server_sync", return_value=jira_payload), patch(
                "services.ops.orchestration.fetch_confluence_page_sync",
                return_value=confluence_payload,
            ), patch("sys.argv", argv), redirect_stdout(stdout):
                exit_code = platform_cli.main()

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["sources"][0]["source_name"], "jira")
        self.assertEqual(payload["sources"][1]["source_name"], "confluence")
        self.assertEqual(payload["sources"][0]["sync"]["cursor"], "jira-live-003")
        self.assertEqual(payload["sources"][1]["sync"]["cursor"], "conf-live-007")
        source_types = {entry["source_type"] for entry in payload["ops_health"]["freshness"]["sources"]}
        self.assertEqual(source_types, {"jira", "confluence"})
        self.assertEqual(payload["ops_health"]["backup_restore"]["backup"]["status"], "healthy")
        self.assertEqual(payload["ops_health"]["backup_restore"]["restore"]["status"], "validated")

    def test_sync_export_live_uses_manifest_cursor_when_cli_cursor_is_omitted(self) -> None:
        seen_cursors = []

        def fake_jira_sync(**kwargs) -> dict:
            seen_cursors.append(("jira", kwargs.get("cursor")))
            return self._live_jira_payload()

        def fake_confluence_sync(**kwargs) -> dict:
            seen_cursors.append(("confluence", kwargs.get("cursor")))
            return self._live_confluence_payload()

        with TemporaryDirectory() as temp_dir:
            first_stdout = StringIO()
            first_argv = [
                "platform_cli.py",
                "sync-export",
                "--snapshot-dir",
                temp_dir,
                "--jira-live",
                "--jira-base-url",
                "https://jira.example.com",
                "--jira-token",
                "secret",
                "--jira-cursor",
                "jira-explicit-001",
                "--confluence-live",
                "--confluence-base-url",
                "https://confluence.example.com",
                "--confluence-token",
                "secret",
                "--confluence-cursor",
                "conf-explicit-001",
            ]
            second_stdout = StringIO()
            second_argv = [
                "platform_cli.py",
                "sync-export",
                "--snapshot-dir",
                temp_dir,
                "--jira-live",
                "--jira-base-url",
                "https://jira.example.com",
                "--jira-token",
                "secret",
                "--confluence-live",
                "--confluence-base-url",
                "https://confluence.example.com",
                "--confluence-token",
                "secret",
            ]

            with patch("services.ops.orchestration.fetch_jira_server_sync", side_effect=fake_jira_sync), patch(
                "services.ops.orchestration.fetch_confluence_page_sync",
                side_effect=fake_confluence_sync,
            ):
                with patch("sys.argv", first_argv), redirect_stdout(first_stdout):
                    first_exit_code = platform_cli.main()
                with patch("sys.argv", second_argv), redirect_stdout(second_stdout):
                    second_exit_code = platform_cli.main()

        self.assertEqual(first_exit_code, 0)
        self.assertEqual(second_exit_code, 0)
        self.assertEqual(
            seen_cursors,
            [
                ("jira", "jira-explicit-001"),
                ("confluence", "conf-explicit-001"),
                ("jira", "jira-live-003"),
                ("confluence", "conf-live-007"),
            ],
        )

    def test_jira_report_validates_live_base_url(self) -> None:
        argv = [
            "platform_cli.py",
            "jira-report",
            "--jira-live",
            "--jira-token",
            "secret",
        ]
        stderr = StringIO()
        with patch("sys.argv", argv), patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as raised:
                platform_cli.main()

        self.assertNotEqual(raised.exception.code, 0)
        self.assertIn("--jira-base-url is required when --jira-live is set", stderr.getvalue())

    def test_jira_spec_qa_supports_live_jira_source(self) -> None:
        stdout = StringIO()
        argv = [
            "platform_cli.py",
            "jira-spec-qa",
            "--jira-live",
            "--jira-base-url",
            "https://jira.example.com",
            "--jira-token",
            "secret",
            "--jira-issue-id",
            "SSD-401",
            "--spec-document-id",
            "nvme-spec-v1",
            "--question",
            "Does live Jira mention flush ordering?",
            "--prompt-template",
            "LIVE {jira_issue_id} {question} {evidence}",
        ]
        with patch("services.ops.orchestration.fetch_jira_server_sync", return_value=self._live_jira_payload()), patch(
            "sys.argv",
            argv,
        ), redirect_stdout(stdout):
            exit_code = platform_cli.main()

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["jira_issue_id"], "SSD-401")
        self.assertTrue(payload["retrieval"]["has_jira_evidence"])
        self.assertTrue(payload["retrieval"]["has_spec_evidence"])
        self.assertTrue(payload["ai_prompt"].startswith("LIVE SSD-401"))

    def test_retrieval_consume_supports_live_jira_source(self) -> None:
        stdout = StringIO()
        argv = [
            "platform_cli.py",
            "retrieval-consume",
            "--source-kind",
            "jira-live",
            "--base-url",
            "https://jira.example.com",
            "--token",
            "secret",
            "--question",
            "Does live Jira mention flush ordering?",
        ]
        with patch("services.ops.orchestration.fetch_jira_server_sync", return_value=self._live_jira_payload()), patch(
            "sys.argv",
            argv,
        ), redirect_stdout(stdout):
            exit_code = platform_cli.main()

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["retrieval"]["citations"][0]["document"], "SSD-401")

    def test_retrieval_consume_supports_live_confluence_source(self) -> None:
        stdout = StringIO()
        argv = [
            "platform_cli.py",
            "retrieval-consume",
            "--source-kind",
            "confluence-live",
            "--base-url",
            "https://confluence.example.com",
            "--token",
            "secret",
            "--question",
            "What changed in the live confluence page?",
            "--llm-backend",
            "mock",
            "--llm-mock-response",
            "Mock live confluence answer",
        ]
        with patch("services.ops.orchestration.fetch_confluence_page_sync", return_value=self._live_confluence_payload()), patch(
            "sys.argv",
            argv,
        ), redirect_stdout(stdout):
            exit_code = platform_cli.main()

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["answer"]["text"], "Mock live confluence answer")

    def test_connector_supports_selective_atlassian_api_jira_fetch_args(self) -> None:
        stdout = StringIO()
        argv = [
            "platform_cli.py",
            "connector",
            "jira",
            "--live",
            "--base-url",
            "https://jira.example.com",
            "--token",
            "secret",
            "--fetch-backend",
            "atlassian-api",
            "--issue-key",
            "SSD-777",
        ]
        with patch(
            "scripts.platform_cli.load_source_payload",
            return_value={"sync_type": "full", "cursor": None, "documents": [], "selector_summary": {"issue_key": "SSD-777"}},
        ) as mocked, patch("sys.argv", argv), redirect_stdout(stdout):
            exit_code = platform_cli.main()

        self.assertEqual(exit_code, 0)
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.kwargs["fetch_backend"], "atlassian-api")
        self.assertEqual(mocked.call_args.kwargs["issue_key"], "SSD-777")

    def test_connector_supports_confluence_page_tree_args(self) -> None:
        stdout = StringIO()
        argv = [
            "platform_cli.py",
            "connector",
            "confluence",
            "--live",
            "--base-url",
            "https://confluence.example.com",
            "--token",
            "secret",
            "--fetch-backend",
            "atlassian-api",
            "--root-page-id",
            "CONF-ROOT",
            "--include-descendants",
            "--max-depth",
            "2",
        ]
        with patch(
            "scripts.platform_cli.load_source_payload",
            return_value={"sync_type": "full", "cursor": None, "documents": [], "selector_summary": {"root_page_id": "CONF-ROOT"}},
        ) as mocked, patch("sys.argv", argv), redirect_stdout(stdout):
            exit_code = platform_cli.main()

        self.assertEqual(exit_code, 0)
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.kwargs["fetch_backend"], "atlassian-api")
        self.assertEqual(mocked.call_args.kwargs["root_page_id"], "CONF-ROOT")
        self.assertTrue(mocked.call_args.kwargs["include_descendants"])
        self.assertEqual(mocked.call_args.kwargs["max_depth"], 2)

    def test_connector_rejects_jql_combined_with_jira_helper_filters(self) -> None:
        argv = [
            "platform_cli.py",
            "connector",
            "jira",
            "--live",
            "--base-url",
            "https://jira.example.com",
            "--token",
            "secret",
            "--fetch-backend",
            "atlassian-api",
            "--jql",
            "project = SSD",
            "--issue-key",
            "SSD-777",
        ]
        stderr = StringIO()
        with patch("sys.argv", argv), patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as raised:
                platform_cli.main()

        self.assertNotEqual(raised.exception.code, 0)
        self.assertIn("Jira helper filters cannot be combined with raw JQL", stderr.getvalue())

    def test_connector_rejects_confluence_max_depth_without_include_descendants(self) -> None:
        argv = [
            "platform_cli.py",
            "connector",
            "confluence",
            "--live",
            "--base-url",
            "https://confluence.example.com",
            "--token",
            "secret",
            "--fetch-backend",
            "atlassian-api",
            "--root-page-id",
            "CONF-ROOT",
            "--max-depth",
            "1",
        ]
        stderr = StringIO()
        with patch("sys.argv", argv), patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as raised:
                platform_cli.main()

        self.assertNotEqual(raised.exception.code, 0)
        self.assertIn("--max-depth requires --include-descendants", stderr.getvalue())

    def test_connector_rejects_selective_jira_flags_on_native_backend(self) -> None:
        argv = [
            "platform_cli.py",
            "connector",
            "jira",
            "--live",
            "--base-url",
            "https://jira.example.com",
            "--token",
            "secret",
            "--issue-key",
            "SSD-777",
        ]
        stderr = StringIO()
        with patch("sys.argv", argv), patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as raised:
                platform_cli.main()

        self.assertNotEqual(raised.exception.code, 0)
        self.assertIn("Selective Jira live fetch flags require the atlassian-api backend", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

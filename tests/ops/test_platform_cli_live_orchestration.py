from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from scripts import platform_cli
from services.ingest.normalizer import normalize_markdown_text


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

    def test_multi_sync_health_supports_live_dual_source_orchestration(self) -> None:
        jira_payload = self._live_jira_payload()
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
        confluence_payload = {
            "sync_type": "incremental",
            "cursor": "conf-live-007",
            "documents": [confluence_document],
        }

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


if __name__ == "__main__":
    unittest.main()

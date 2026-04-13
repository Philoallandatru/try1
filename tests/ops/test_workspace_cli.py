import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


class WorkspaceCliTest(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_workspace_cli_init_creates_layout(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(Path(payload["config_path"]).exists())
            self.assertTrue(Path(temp_dir, "raw", "jira", "specs").exists())
            self.assertTrue(Path(temp_dir, "raw", "confluence", "specs").exists())
            self.assertTrue(Path(temp_dir, "snapshots", "current").exists())

    def test_workspace_cli_supports_fetch_build_export_query_and_lint(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/full_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-101"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            confluence_spec = Path(temp_dir, "raw", "confluence", "specs", "fixture-confluence.json")
            confluence_spec.write_text(
                json.dumps(
                    {
                        "kind": "confluence",
                        "mode": "fixture",
                        "path": "fixtures/connectors/confluence/page_sync.json",
                        "scope": {"type": "page", "page_id": "CONF-001"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            jira_fetch = self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec))
            self.assertEqual(jira_fetch.returncode, 0, jira_fetch.stderr)
            confluence_fetch = self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(confluence_spec))
            self.assertEqual(confluence_fetch.returncode, 0, confluence_fetch.stderr)

            build = self._run("scripts/workspace_cli.py", "build", temp_dir)
            self.assertEqual(build.returncode, 0, build.stderr)
            build_payload = json.loads(build.stdout)
            self.assertGreater(build_payload["document_count"], 0)
            self.assertGreater(build_payload["page_index_count"], 0)

            status = self._run("scripts/workspace_cli.py", "status", temp_dir)
            self.assertEqual(status.returncode, 0, status.stderr)
            status_payload = json.loads(status.stdout)
            self.assertEqual(status_payload["payload_counts"]["total"], 2)
            self.assertGreater(status_payload["snapshot"]["document_count"], 0)

            export = self._run("scripts/workspace_cli.py", "export", temp_dir)
            self.assertEqual(export.returncode, 0, export.stderr)
            export_payload = json.loads(export.stdout)
            self.assertGreater(export_payload["tree_document_count"], 0)

            query = self._run("scripts/workspace_cli.py", "query", temp_dir, "black screen")
            self.assertEqual(query.returncode, 0, query.stderr)
            query_payload = json.loads(query.stdout)
            self.assertGreaterEqual(query_payload["result_count"], 1)
            self.assertEqual(query_payload["answer"]["mode"], "extractive")

            lint = self._run("scripts/workspace_cli.py", "lint", temp_dir)
            self.assertEqual(lint.returncode, 0, lint.stderr)
            lint_payload = json.loads(lint.stdout)
            self.assertTrue(lint_payload["ok"], lint_payload)

            llm_query = self._run(
                "scripts/workspace_cli.py",
                "query",
                temp_dir,
                "black screen",
                "--llm-backend",
                "mock",
                "--llm-mock-response",
                "Mock workspace answer",
                "--output-answer-md",
                str(Path(temp_dir) / "answer.md"),
            )
            self.assertEqual(llm_query.returncode, 0, llm_query.stderr)
            llm_query_payload = json.loads(llm_query.stdout)
            self.assertEqual(llm_query_payload["answer"]["mode"], "local-llm")
            self.assertEqual(llm_query_payload["answer"]["backend"], "mock")
            self.assertEqual(llm_query_payload["answer"]["text"], "Mock workspace answer")
            self.assertTrue(Path(llm_query_payload["output_answer_md"]).exists())

    def test_workspace_cli_watch_run_once_fetches_specs_and_builds_snapshot(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            watch = self._run(
                "scripts/workspace_cli.py",
                "watch",
                temp_dir,
                "--run-once",
                "--max-cycles",
                "1",
                "--interval-seconds",
                "0.01",
            )
            self.assertEqual(watch.returncode, 0, watch.stderr)
            payload = json.loads(watch.stdout)
            self.assertTrue(payload["built"])
            self.assertGreater(payload["fetched_spec_count"], 0)
            snapshot_manifest = Path(temp_dir, "snapshots", "current", "manifest.json")
            self.assertTrue(snapshot_manifest.exists())


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
import unittest


class SkillReadyCliTest(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_normalize_cli_outputs_markdown_document(self) -> None:
        result = self._run("scripts/ingest/normalize_cli.py", "markdown", "fixtures/corpus/markdown/sample.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["source_type"], "md")
        self.assertIn("content_blocks", payload)

    def test_normalize_cli_outputs_connector_sync_documents(self) -> None:
        result = self._run("scripts/ingest/normalize_cli.py", "jira-sync", "fixtures/connectors/jira/full_sync.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["documents"][0]["source_type"], "jira")

    def test_retrieval_toolkit_search_outputs_results(self) -> None:
        result = self._run(
            "scripts/retrieval/toolkit_cli.py",
            "search",
            "flush command",
            "--corpus",
            "fixtures/retrieval/pageindex_corpus.json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["document_id"], "nvme-spec-v1")

    def test_retrieval_toolkit_citation_outputs_contract_payload(self) -> None:
        result = self._run(
            "scripts/retrieval/toolkit_cli.py",
            "citation",
            "flush command",
            "--corpus",
            "fixtures/retrieval/pageindex_corpus.json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["citation"]["document"], "nvme-spec-v1")


if __name__ == "__main__":
    unittest.main()

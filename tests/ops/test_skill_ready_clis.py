import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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

    def test_normalize_cli_can_write_four_source_markdown_and_page_index(self) -> None:
        cases = [
            ("jira-sync", "fixtures/connectors/jira/full_sync.json", "SSD-101", "jira"),
            ("confluence-sync", "fixtures/connectors/confluence/page_sync.json", "Telemetry Architecture", "confluence"),
            ("pptx", "fixtures/corpus/office/sample.pptx", "## Slide 1", "pptx"),
            ("pdf", "fixtures/corpus/pdf/sample.pdf", "## Page 1", "pdf"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            for kind, source_path, expected_markdown, expected_source_type in cases:
                with self.subTest(kind=kind):
                    markdown_path = Path(temp_dir) / f"{kind}.md"
                    index_path = Path(temp_dir) / f"{kind}-page-index.json"
                    result = self._run(
                        "scripts/ingest/normalize_cli.py",
                        kind,
                        source_path,
                        "--output-md",
                        str(markdown_path),
                        "--output-page-index",
                        str(index_path),
                    )

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(expected_markdown, markdown_path.read_text(encoding="utf-8"))
                    page_index = json.loads(index_path.read_text(encoding="utf-8"))
                    self.assertIn("entries", page_index)
                    self.assertTrue(page_index["entries"])
                    self.assertEqual(
                        {entry["source_type"] for entry in page_index["entries"]},
                        {expected_source_type},
                    )

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

    def test_retrieval_toolkit_search_can_read_page_index_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "page_index.json"
            index_result = self._run(
                "scripts/retrieval/toolkit_cli.py",
                "index",
                "--corpus",
                "fixtures/retrieval/pageindex_corpus.json",
                "--output-page-index",
                str(index_path),
            )
            self.assertEqual(index_result.returncode, 0, index_result.stderr)

            result = self._run(
                "scripts/retrieval/toolkit_cli.py",
                "search",
                "flush command",
                "--page-index",
                str(index_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload[0]["document_id"], "nvme-spec-v1")

    def test_retrieval_toolkit_search_can_read_snapshot_page_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_result = self._run(
                "scripts/retrieval/snapshot_cli.py",
                "create",
                "--snapshot-dir",
                temp_dir,
                "--corpus",
                "fixtures/retrieval/pageindex_corpus.json",
            )
            self.assertEqual(snapshot_result.returncode, 0, snapshot_result.stderr)

            result = self._run(
                "scripts/retrieval/toolkit_cli.py",
                "search",
                "flush command",
                "--snapshot-dir",
                temp_dir,
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

from pathlib import Path
import unittest

from services.ingest.adapters.markdown.adapter import parse_markdown


class MarkdownAdapterTest(unittest.TestCase):
    def test_markdown_adapter_preserves_headings_and_provenance(self) -> None:
        payload = parse_markdown(Path("fixtures/corpus/markdown/sample.md"))
        self.assertEqual(payload["source_type"], "md")
        self.assertEqual(payload["title"], "SSD Spec Notes")
        self.assertGreaterEqual(len(payload["structure"]["sections"]), 2)
        self.assertEqual(payload["provenance"]["source_uri"], "fixtures/corpus/markdown/sample.md")
        self.assertTrue(any(block["section_heading"] == "Flush Command" for block in payload["content_blocks"]))


if __name__ == "__main__":
    unittest.main()


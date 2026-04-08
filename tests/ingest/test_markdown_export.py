from pathlib import Path
import tempfile
import unittest

from services.ingest.adapters.office.adapter import parse_pptx
from services.ingest.markdown_export import document_to_markdown, ensure_document_markdown
from services.retrieval.indexing.page_index import build_page_index


class MarkdownExportTest(unittest.TestCase):
    def test_pptx_exports_slide_markdown_and_page_index_entries(self) -> None:
        document = ensure_document_markdown(parse_pptx(Path("fixtures/corpus/office/sample.pptx")))
        markdown = document_to_markdown(document)
        page_index = build_page_index([document])

        self.assertIn("#", markdown)
        self.assertIn("## Slide 1", markdown)
        self.assertIn("## Slide 2", markdown)
        self.assertTrue(document["markdown"].startswith("#"))
        self.assertEqual({entry["page"] for entry in page_index}, {1, 2})

    def test_document_with_existing_markdown_is_preserved(self) -> None:
        document = {"markdown": "# Existing\n\nBody", "title": "Ignored"}
        self.assertEqual(document_to_markdown(document), "# Existing\n\nBody")


if __name__ == "__main__":
    unittest.main()

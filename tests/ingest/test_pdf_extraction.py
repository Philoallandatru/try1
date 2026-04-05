from pathlib import Path
import unittest

from services.ingest.adapters.pdf.adapter import extract_pdf_structure


class PdfExtractionTest(unittest.TestCase):
    def test_pdf_adapter_extracts_text_and_pages(self) -> None:
        payload = extract_pdf_structure(Path("fixtures/corpus/pdf/sample.pdf"))
        self.assertEqual(payload["source_type"], "pdf")
        self.assertGreaterEqual(len(payload["content_blocks"]), 5)
        self.assertEqual(payload["structure"]["pages"][0]["page"], 1)
        self.assertEqual(payload["structure"]["pages"][1]["page"], 2)


if __name__ == "__main__":
    unittest.main()


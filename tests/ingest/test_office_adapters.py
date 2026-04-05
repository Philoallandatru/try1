from pathlib import Path
import unittest

from services.ingest.adapters.office.adapter import parse_docx, parse_pptx, parse_xlsx


class OfficeAdapterTest(unittest.TestCase):
    def test_docx_adapter_preserves_paragraph_structure(self) -> None:
        payload = parse_docx(Path("fixtures/corpus/office/sample.docx"))
        self.assertEqual(payload["source_type"], "docx")
        self.assertGreaterEqual(len(payload["content_blocks"]), 2)
        self.assertIn("SSD", payload["title"])

    def test_xlsx_adapter_preserves_worksheet_names(self) -> None:
        payload = parse_xlsx(Path("fixtures/corpus/office/sample.xlsx"))
        self.assertEqual(payload["source_type"], "xlsx")
        self.assertEqual(payload["structure"]["worksheets"][0]["name"], "Telemetry")
        self.assertGreaterEqual(len(payload["structure"]["tables"]), 1)

    def test_pptx_adapter_preserves_slide_boundaries(self) -> None:
        payload = parse_pptx(Path("fixtures/corpus/office/sample.pptx"))
        self.assertEqual(payload["source_type"], "pptx")
        self.assertGreaterEqual(len(payload["structure"]["slides"]), 2)
        self.assertGreaterEqual(len(payload["content_blocks"]), 2)


if __name__ == "__main__":
    unittest.main()


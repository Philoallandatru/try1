from pathlib import Path
import unittest

from services.ingest.adapters.pdf.adapter import extract_pdf_structure


class PdfFidelityTest(unittest.TestCase):
    def test_pdf_adapter_preserves_sections_clauses_tables_and_figures(self) -> None:
        payload = extract_pdf_structure(Path("fixtures/corpus/pdf/sample.pdf"), preferred_parser="pypdf")
        sections = payload["structure"]["sections"]
        tables = payload["structure"]["tables"]
        figures = payload["structure"]["figures"]

        self.assertTrue(any(section["clause"] == "1" for section in sections))
        self.assertTrue(any(section["clause"] == "1.1" for section in sections))
        self.assertTrue(any(table["id"] == "table-1" for table in tables))
        self.assertTrue(any(figure["id"] == "figure-1" for figure in figures))
        self.assertEqual(payload["language"], "en")

    def test_pdf_adapter_records_page_level_structure(self) -> None:
        payload = extract_pdf_structure(Path("fixtures/corpus/pdf/sample.pdf"), preferred_parser="pypdf")
        section_pages = {section["clause"]: section["page"] for section in payload["structure"]["sections"]}
        self.assertEqual(section_pages["1"], 1)
        self.assertEqual(section_pages["1.1"], 2)


if __name__ == "__main__":
    unittest.main()

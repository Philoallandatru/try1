from pathlib import Path
import unittest
from unittest.mock import patch

from services.ingest.adapters.pdf.adapter import _parse_mineru_middle_json, extract_pdf_structure


class PdfExtractionTest(unittest.TestCase):
    def test_pdf_adapter_extracts_text_and_pages_with_pypdf(self) -> None:
        payload = extract_pdf_structure(Path("fixtures/corpus/pdf/sample.pdf"), preferred_parser="pypdf")
        self.assertEqual(payload["source_type"], "pdf")
        self.assertGreaterEqual(len(payload["content_blocks"]), 5)
        self.assertEqual(payload["structure"]["pages"][0]["page"], 1)
        self.assertEqual(payload["structure"]["pages"][1]["page"], 2)

    def test_pdf_adapter_falls_back_when_mineru_is_unavailable(self) -> None:
        with patch(
            "services.ingest.adapters.pdf.adapter._extract_pdf_structure_mineru",
            side_effect=RuntimeError("mineru unavailable"),
        ):
            payload = extract_pdf_structure(Path("fixtures/corpus/pdf/sample.pdf"), preferred_parser="auto")
        self.assertEqual(payload["provenance"]["parser"], "pypdf-fallback")
        self.assertIn("parser_fallback_reason", payload["provenance"])

    def test_pdf_adapter_prefers_mineru_when_requested(self) -> None:
        mineru_payload = {"source_type": "pdf", "provenance": {"parser": "mineru"}, "content_blocks": []}
        with patch(
            "services.ingest.adapters.pdf.adapter._extract_pdf_structure_mineru",
            return_value=mineru_payload,
        ) as mineru_mock, patch(
            "services.ingest.adapters.pdf.adapter._extract_pdf_structure_pypdf",
        ) as pypdf_mock:
            payload = extract_pdf_structure(Path("fixtures/corpus/pdf/sample.pdf"), preferred_parser="mineru")

        self.assertIs(payload, mineru_payload)
        mineru_mock.assert_called_once()
        pypdf_mock.assert_not_called()

    def test_pdf_adapter_auto_fallback_preserves_aggregated_reason(self) -> None:
        with patch(
            "services.ingest.adapters.pdf.adapter._extract_pdf_structure_mineru",
            side_effect=RuntimeError("in-process MinerU failed: missing package; MinerU CLI failed: missing cli"),
        ):
            payload = extract_pdf_structure(Path("fixtures/corpus/pdf/sample.pdf"), preferred_parser="auto")

        self.assertEqual(payload["provenance"]["parser"], "pypdf-fallback")
        self.assertEqual(
            payload["provenance"]["parser_fallback_reason"],
            "in-process MinerU failed: missing package; MinerU CLI failed: missing cli",
        )

    def test_mineru_runner_reports_failures_in_attempt_order(self) -> None:
        with patch(
            "services.ingest.adapters.pdf.adapter._extract_pdf_structure_mineru_in_process",
            side_effect=RuntimeError("in-process unavailable"),
        ), patch(
            "services.ingest.adapters.pdf.adapter._extract_pdf_structure_mineru_via_python",
            side_effect=RuntimeError("external unavailable"),
        ), patch(
            "services.ingest.adapters.pdf.adapter._extract_pdf_structure_mineru_cli",
            side_effect=RuntimeError("cli unavailable"),
        ), patch.dict(
            "os.environ",
            {"MINERU_PYTHON_EXE": "C:/fake/python.exe"},
            clear=False,
        ):
            with self.assertRaises(RuntimeError) as context:
                extract_pdf_structure(Path("fixtures/corpus/pdf/sample.pdf"), preferred_parser="mineru")

        self.assertEqual(
            str(context.exception),
            "in-process MinerU failed: in-process unavailable; external MinerU Python failed: external unavailable; MinerU CLI failed: cli unavailable",
        )

    def test_mineru_middle_json_parser_extracts_span_content(self) -> None:
        payload = _parse_mineru_middle_json(
            Path("fixtures/corpus/pdf/sample.pdf"),
            {
                "pdf_info": [
                    {
                        "page_idx": 0,
                        "para_blocks": [
                            {
                                "type": "title",
                                "level": 1,
                                "lines": [
                                    {
                                        "spans": [
                                            {"content": "NVM Express Base Specification Revision 2.1"}
                                        ]
                                    }
                                ],
                            },
                            {
                                "type": "text",
                                "lines": [
                                    {
                                        "spans": [
                                            {"content": "Ratified requirements for NVMe devices."}
                                        ]
                                    }
                                ],
                            },
                        ],
                    }
                ]
            },
            "mineru",
        )

        self.assertEqual(payload["structure"]["pages"], [{"page": 1}])
        self.assertEqual(payload["title"], "NVM Express Base Specification Revision 2.1")
        self.assertGreaterEqual(len(payload["content_blocks"]), 2)
        self.assertEqual(payload["content_blocks"][0]["text"], "NVM Express Base Specification Revision 2.1")
        self.assertEqual(payload["content_blocks"][0]["block_type"], "title")
        self.assertEqual(payload["content_blocks"][1]["text"], "Ratified requirements for NVMe devices.")

    def test_mineru_middle_json_parser_uses_page_idx_for_page_numbers(self) -> None:
        payload = _parse_mineru_middle_json(
            Path("fixtures/corpus/pdf/sample.pdf"),
            {
                "pdf_info": [
                    {
                        "page_idx": 4,
                        "para_blocks": [
                            {
                                "type": "title",
                                "lines": [
                                    {
                                        "spans": [
                                            {"content": "PCI-SIG Fast Tracks Evolution to 32GT/s"}
                                        ]
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            "mineru",
        )

        self.assertEqual(payload["structure"]["pages"], [{"page": 5}])
        self.assertEqual(payload["content_blocks"][0]["page"], 5)
        self.assertEqual(payload["structure"]["sections"][0]["page"], 5)


if __name__ == "__main__":
    unittest.main()

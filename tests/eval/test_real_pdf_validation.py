from __future__ import annotations

from pathlib import Path
import unittest
from types import SimpleNamespace

from scripts.eval.run_real_pdf_validation import _write_markdown
from services.eval.real_pdf_validation import _normalize_line, _title_from_pdf, build_validation_report
from tests.temp_utils import temporary_directory


def _document(
    document_id: str,
    title: str,
    authority_level: str,
    text: str,
) -> dict:
    return {
        "document_id": document_id,
        "source_type": "pdf",
        "authority_level": authority_level,
        "version": "fixture",
        "language": "en",
        "title": title,
        "provenance": {
            "source_uri": f"fixtures://{document_id}.pdf",
            "parser": "fixture",
        },
        "acl": {
            "policy": "team:ssd",
            "inherits_from": None,
        },
        "structure": {
            "pages": [{"page": 1}],
            "sections": [{"id": "section-1", "clause": "1", "heading": "Overview", "page": 1}],
            "tables": [],
            "figures": [],
            "worksheets": [],
            "slides": [],
        },
        "terminology": {"terms": []},
        "content_blocks": [{"id": "block-1", "page": 1, "text": text}],
    }


class RealPdfValidationTest(unittest.TestCase):
    def test_normalize_line_cleans_common_mojibake(self) -> None:
        self.assertEqual(
            _normalize_line("PCI-SIGÂ® Fast Tracks Evolution 鈥?June 7, 2017"),
            "PCI-SIG® Fast Tracks Evolution –June 7, 2017",
        )

    def test_title_from_pdf_prefers_structured_page_one_title(self) -> None:
        reader = SimpleNamespace(metadata=SimpleNamespace(title=None))
        payload = {
            "structure": {
                "sections": [
                    {
                        "heading": "PCI-SIG Fast Tracks Evolution to 32GT/s with PCI Express 5.0 Architecture",
                        "page": 1,
                    }
                ]
            },
            "content_blocks": [
                {
                    "page": 1,
                    "block_type": "title",
                    "text": "PCI-SIG Fast Tracks Evolution to 32GT/s with PCI Express 5.0 Architecture",
                },
                {
                    "page": 1,
                    "block_type": "text",
                    "text": "proof the PCIe architecture design, thereby accelerating future specification development. This",
                },
            ],
        }

        title = _title_from_pdf(
            Path("fixtures/corpus/pdf/sample.pdf"),
            reader,
            [
                "proof the PCIe architecture design, thereby accelerating future specification development. This",
                "PCI-SIG Fast Tracks Evolution to 32GT/s with PCI Express 5.0 Architecture",
            ],
            payload,
        )

        self.assertEqual(
            title,
            "PCI-SIG Fast Tracks Evolution to 32GT/s with PCI Express 5.0 Architecture",
        )

    def test_title_from_pdf_refines_split_specification_title(self) -> None:
        reader = SimpleNamespace(metadata=SimpleNamespace(title=None))
        payload = {
            "structure": {
                "sections": [
                    {"heading": "Base Specification", "page": 1},
                ]
            },
            "content_blocks": [
                {"page": 1, "block_type": "text", "text": "NVM Express®"},
                {"page": 1, "block_type": "title", "text": "Base Specification"},
                {"page": 1, "block_type": "text", "text": "Revision 2.1 August 5th, 2024"},
            ],
        }

        title = _title_from_pdf(
            Path("fixtures/corpus/pdf/sample.pdf"),
            reader,
            ["Base Specification", "Revision 2.1 August 5th, 2024"],
            payload,
        )

        self.assertEqual(title, "NVM Express® Base Specification, Revision 2.1")

    def test_validation_report_passes_when_retrieval_and_llm_align(self) -> None:
        documents = [
            _document(
                "nvme-spec",
                "NVM Express Base Specification Revision 2.1",
                "canonical",
                "NVM Express Base Specification Revision 2.1 ratified requirements.",
            ),
            _document(
                "pcie-press-release",
                "PCIe 5.0 Press Release",
                "contextual",
                "PCIe 5.0 press release announcement for background context.",
            ),
        ]

        def fake_runner(_: str) -> dict:
            return {
                "normative_lead_document_id": "nvme-spec",
                "contextual_document_id": "pcie-press-release",
                "authority_policy_passed": True,
                "summary": "The ratified NVMe specification is normative and the PCIe press release is contextual.",
                "citations": [
                    {"document_id": "nvme-spec", "page": 1},
                    {"document_id": "pcie-press-release", "page": 1},
                ],
            }

        report = build_validation_report(documents, {"team:ssd"}, fake_runner)
        self.assertTrue(report["overall_pass"])
        self.assertEqual(report["retrieval_checks"][0]["top_results"][0]["document_id"], "nvme-spec")
        self.assertEqual(report["retrieval_checks"][1]["top_results"][0]["document_id"], "pcie-press-release")

    def test_validation_report_fails_when_llm_picks_contextual_doc_as_normative(self) -> None:
        documents = [
            _document(
                "nvme-spec",
                "NVM Express Base Specification Revision 2.1",
                "canonical",
                "NVM Express Base Specification Revision 2.1 ratified requirements.",
            ),
            _document(
                "pcie-press-release",
                "PCIe 5.0 Press Release",
                "contextual",
                "PCIe 5.0 press release announcement for background context.",
            ),
        ]

        def fake_runner(_: str) -> dict:
            return {
                "normative_lead_document_id": "pcie-press-release",
                "contextual_document_id": "nvme-spec",
                "authority_policy_passed": False,
                "summary": "Incorrect authority ordering.",
                "citations": [],
            }

        report = build_validation_report(documents, {"team:ssd"}, fake_runner)
        self.assertFalse(report["overall_pass"])

    def test_validation_report_repairs_contextual_id_when_evidence_supports_it(self) -> None:
        documents = [
            _document(
                "nvme-spec",
                "NVM Express Base Specification Revision 2.1",
                "canonical",
                "NVM Express Base Specification Revision 2.1 ratified requirements.",
            ),
            _document(
                "pcie-press-release",
                "PCIe 5.0 Press Release",
                "contextual",
                "PCIe 5.0 press release announcement for background context.",
            ),
        ]

        def fake_runner(_: str) -> dict:
            return {
                "normative_lead_document_id": "nvme-spec",
                "contextual_document_id": "nvme-spec",
                "authority_policy_passed": True,
                "summary": "The NVMe specification is normative.",
                "citations": [
                    {"document_id": "nvme-spec", "page": 1},
                    {"document_id": "pcie-press-release", "page": 1},
                ],
            }

        report = build_validation_report(documents, {"team:ssd"}, fake_runner)
        self.assertTrue(report["overall_pass"])
        self.assertEqual(report["llm_judgement"]["contextual_document_id"], "pcie-press-release")

    def test_write_markdown_includes_document_and_citation_titles(self) -> None:
        report = {
            "overall_pass": True,
            "documents": [
                {
                    "document_id": "nvme-spec",
                    "authority_level": "canonical",
                    "title": "NVM Express® Base Specification, Revision 2.1",
                    "version": "Revision 2.1 2024.08.05 Ratified",
                    "pages": 707,
                    "source_uri": "fixtures://nvme-spec.pdf",
                },
                {
                    "document_id": "pcie-press-release",
                    "authority_level": "contextual",
                    "title": "PCI-SIG® Fast Tracks Evolution to 32GT/s with PCI Express 5.0 Architecture",
                    "version": "PCIe 5.0 Press Release_June 6_FINAL VERSION",
                    "pages": 4,
                    "source_uri": "fixtures://pcie-press-release.pdf",
                },
            ],
            "retrieval_checks": [
                {
                    "query_id": "contextual-press-release-query",
                    "pass": True,
                    "query": "PCI-SIG Developers Conference 2017 Santa Clara PCIe 5.0 press release announcement",
                    "top_results": [
                        {
                            "document_id": "pcie-press-release",
                            "page": 1,
                            "authority_level": "contextual",
                            "title": "PCI-SIG® Fast Tracks Evolution to 32GT/s with PCI Express 5.0 Architecture",
                            "citation": {
                                "document": "pcie-press-release",
                                "title": "PCI-SIG® Fast Tracks Evolution to 32GT/s with PCI Express 5.0 Architecture",
                                "page": 1,
                            },
                        }
                    ],
                }
            ],
            "llm_judgement": {
                "normative_lead_document_id": "nvme-spec",
                "contextual_document_id": "pcie-press-release",
                "authority_policy_passed": True,
                "summary": "The NVMe specification is normative and the PCIe press release is contextual.",
            },
        }

        with temporary_directory("real-pdf-validation") as tmpdir:
            target = Path(tmpdir) / "report.md"
            _write_markdown(report, target, "qwen2.5:1.5b")
            rendered = target.read_text(encoding="utf-8")

        self.assertIn("title=`NVM Express® Base Specification, Revision 2.1`", rendered)
        self.assertIn(
            "title=`PCI-SIG® Fast Tracks Evolution to 32GT/s with PCI Express 5.0 Architecture`",
            rendered,
        )
        self.assertIn(
            "citation: document=`pcie-press-release` title=`PCI-SIG® Fast Tracks Evolution to 32GT/s with PCI Express 5.0 Architecture` page=`1`",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from services.analysis.image_evidence import build_image_evidence_summary, format_image_evidence_summary


class ImageEvidenceTest(unittest.TestCase):
    def test_image_evidence_summary_tracks_indexed_and_degraded_assets(self) -> None:
        summary = build_image_evidence_summary(
            [
                {
                    "document_id": "SSD-102",
                    "source_type": "jira",
                    "visual_assets": [
                        {
                            "asset_id": "jira-image",
                            "filename": "failure.png",
                            "ocr_text": "FTL assert",
                            "vision_caption": "Failure screenshot.",
                        }
                    ],
                },
                {
                    "document_id": "CONF-201",
                    "source_type": "confluence",
                    "visual_assets": [
                        {
                            "asset_id": "conf-image",
                            "filename": "diagram.png",
                        }
                    ],
                },
            ]
        )

        self.assertEqual(summary["asset_count"], 2)
        self.assertEqual(summary["indexed_asset_count"], 1)
        self.assertEqual(summary["degraded_asset_count"], 1)
        self.assertEqual(summary["source_breakdown"], {"confluence": 1, "jira": 1})
        self.assertEqual(summary["assets"][0]["indexed_text_fields"], ["ocr_text", "vision_caption"])
        self.assertEqual(summary["assets"][1]["gaps"], ["missing_ocr", "missing_caption"])
        self.assertIn("conf-image", format_image_evidence_summary(summary))


if __name__ == "__main__":
    unittest.main()

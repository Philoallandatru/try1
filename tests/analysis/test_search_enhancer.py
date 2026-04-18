from __future__ import annotations

import unittest

from services.analysis.search_enhancer import build_enhanced_search_query


class SearchEnhancerTest(unittest.TestCase):
    def test_enhanced_query_adds_route_fields_and_section_cues(self) -> None:
        payload = build_enhanced_search_query(
            base_query="SSD-102 NAND write telemetry",
            jira_document={
                "document_id": "SSD-102",
                "metadata": {
                    "issue_family": "defect",
                    "issue_route": "root_cause_analysis",
                    "issue_fields": {
                        "Component/s": "FW",
                        "Labels": ["GetLogPage"],
                    },
                },
            },
            section_name="rca",
            scope_hint="failure mechanism, error-code, and root-cause evidence",
        )

        self.assertEqual(payload["base_query"], "SSD-102 NAND write telemetry")
        self.assertIn("defect", payload["query"])
        self.assertIn("root_cause_analysis", payload["query"])
        self.assertIn("root cause", payload["query"])
        self.assertIn("failure mechanism", payload["query"])

    def test_enhanced_query_is_bounded_for_large_jira_metadata_lists(self) -> None:
        payload = build_enhanced_search_query(
            base_query="SSD-999 telemetry",
            jira_document={
                "document_id": "SSD-999",
                "metadata": {
                    "issue_family": "defect",
                    "issue_route": "root_cause_analysis",
                    "issue_fields": {
                        "Component/s": [f"component-{index}" for index in range(20)],
                        "Labels": [f"label-{index}" for index in range(20)],
                        "Fix Version/s": [f"fix-{index}" for index in range(20)],
                        "Affects Version/s": [f"affects-{index}" for index in range(20)],
                    },
                },
            },
            section_name="decision_brief",
            scope_hint="decision, risk, and tradeoff evidence",
        )

        self.assertLessEqual(len(payload["query"]), payload["bounds"]["max_query_chars"])
        self.assertLessEqual(len(payload["additions"]), payload["bounds"]["max_additions"])
        self.assertIn("component-2", payload["query"])
        self.assertNotIn("component-3", payload["query"])
        self.assertIn("label-2", payload["query"])
        self.assertNotIn("label-3", payload["query"])


if __name__ == "__main__":
    unittest.main()

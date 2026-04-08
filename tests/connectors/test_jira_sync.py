from pathlib import Path
import unittest

from services.connectors.jira.connector import load_jira_sync


class JiraSyncTest(unittest.TestCase):
    def test_jira_full_sync_loads_issue_documents(self) -> None:
        payload = load_jira_sync(Path("fixtures/connectors/jira/full_sync.json"))
        self.assertEqual(payload["sync_type"], "full")
        self.assertEqual(payload["documents"][0]["document_id"], "SSD-101")
        self.assertFalse(payload["documents"][0]["metadata"]["incremental"])
        self.assertEqual(payload["documents"][0]["metadata"]["issue_fields"]["Priority"], "Highest")
        self.assertIn("## Issue Fields", payload["documents"][0]["markdown"])
        self.assertIn("admin create queue failed", payload["documents"][0]["markdown"])

    def test_jira_incremental_sync_marks_incremental_metadata(self) -> None:
        payload = load_jira_sync(Path("fixtures/connectors/jira/incremental_sync.json"))
        self.assertEqual(payload["sync_type"], "incremental")
        self.assertTrue(payload["documents"][0]["metadata"]["incremental"])
        self.assertEqual(payload["documents"][0]["metadata"]["issue_type_raw"], "FW Bug")
        self.assertEqual(payload["documents"][0]["metadata"]["issue_family"], "defect")
        self.assertEqual(payload["documents"][0]["metadata"]["issue_route"], "fw_bug_rca")
        self.assertEqual(payload["documents"][0]["version"], "2026-04-05T09:30:00Z")
        self.assertEqual(
            payload["documents"][0]["metadata"]["issue_fields"]["Root Cause"],
            "DFh log的total NAND write没有加上TLC write",
        )
        self.assertIn("## How To Fix", payload["documents"][0]["markdown"])

    def test_jira_issue_type_routing_maps_known_types(self) -> None:
        payload = load_jira_sync(Path("fixtures/connectors/jira/issue_type_routing.json"))
        routes = {
            document["document_id"]: (
                document["metadata"]["issue_type_raw"],
                document["metadata"]["issue_family"],
                document["metadata"]["issue_route"],
            )
            for document in payload["documents"]
        }

        self.assertEqual(routes["SSD-201"], ("FW Bug", "defect", "fw_bug_rca"))
        self.assertEqual(routes["SSD-202"], ("HW Bug", "defect", "hw_bug_rca"))
        self.assertEqual(routes["SSD-203"], ("Test Bug", "defect", "test_bug_rca"))
        self.assertEqual(routes["SSD-204"], ("Misc Bug", "defect", "misc_bug_rca"))
        self.assertEqual(routes["SSD-205"], ("DAS/PRD", "requirement", "prd_review"))
        self.assertEqual(routes["SSD-206"], ("MRD", "requirement", "mrd_review"))
        self.assertEqual(routes["SSD-207"], ("Requirement Change", "requirement_change", "requirement_change_impact"))
        self.assertEqual(routes["SSD-208"], ("Component Change", "change_control", "component_change_impact"))
        self.assertEqual(routes["SSD-209"], ("Epic", "delivery", "delivery_summary"))
        self.assertEqual(routes["SSD-210"], ("Story", "delivery", "story_summary"))
        self.assertEqual(routes["SSD-211"], ("Task", "delivery", "task_summary"))
        self.assertEqual(routes["SSD-212"], ("Release", "release", "release_summary"))
        self.assertEqual(routes["SSD-213"], ("Investigation", "unknown", "generic_jira_summary"))

    def test_requirement_issue_markdown_does_not_require_bug_fields(self) -> None:
        payload = load_jira_sync(Path("fixtures/connectors/jira/issue_type_routing.json"))
        prd_document = next(document for document in payload["documents"] if document["document_id"] == "SSD-205")
        story_document = next(document for document in payload["documents"] if document["document_id"] == "SSD-210")

        self.assertEqual(prd_document["metadata"]["issue_family"], "requirement")
        self.assertIn("## Issue Type", prd_document["markdown"])
        self.assertIn("Product requirement for telemetry capture.", prd_document["markdown"])
        self.assertNotIn("## Root Cause", prd_document["markdown"])

        self.assertEqual(story_document["metadata"]["issue_family"], "delivery")
        self.assertNotEqual(story_document["metadata"]["issue_family"], "requirement")


if __name__ == "__main__":
    unittest.main()

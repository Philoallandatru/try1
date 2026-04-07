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
        self.assertEqual(payload["documents"][0]["version"], "2026-04-05T09:30:00Z")
        self.assertEqual(
            payload["documents"][0]["metadata"]["issue_fields"]["Root Cause"],
            "DFh log的total NAND write没有加上TLC write",
        )
        self.assertIn("## How To Fix", payload["documents"][0]["markdown"])


if __name__ == "__main__":
    unittest.main()

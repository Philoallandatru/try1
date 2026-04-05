from pathlib import Path
import unittest

from services.connectors.confluence.connector import load_confluence_sync


class ConfluenceSyncTest(unittest.TestCase):
    def test_confluence_page_sync_loads_attachment_metadata(self) -> None:
        payload = load_confluence_sync(Path("fixtures/connectors/confluence/page_sync.json"))
        self.assertEqual(payload["sync_type"], "full")
        self.assertEqual(payload["documents"][0]["attachments"][0]["name"], "telemetry-diagram.png")
        self.assertFalse(payload["documents"][0]["metadata"]["incremental"])

    def test_confluence_incremental_sync_marks_incremental_metadata(self) -> None:
        payload = load_confluence_sync(Path("fixtures/connectors/confluence/incremental_sync.json"))
        self.assertEqual(payload["sync_type"], "incremental")
        self.assertTrue(payload["documents"][0]["metadata"]["incremental"])
        self.assertEqual(payload["documents"][0]["version"], "3")


if __name__ == "__main__":
    unittest.main()


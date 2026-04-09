from pathlib import Path
import unittest

from services.connectors.confluence.connector import load_confluence_sync


class ConfluenceSyncTest(unittest.TestCase):
    def test_confluence_page_sync_loads_attachment_metadata(self) -> None:
        payload = load_confluence_sync(Path("fixtures/connectors/confluence/page_sync.json"))
        self.assertEqual(payload["sync_type"], "full")
        self.assertEqual(payload["documents"][0]["attachments"][0]["name"], "telemetry-diagram.png")
        self.assertFalse(payload["documents"][0]["metadata"]["incremental"])
        self.assertEqual(payload["documents"][0]["metadata"]["space"], "SSDENG")
        self.assertEqual(payload["documents"][0]["version"], "7")
        self.assertEqual(payload["documents"][0]["provenance"]["ingested_at"], "2026-04-06T08:30:00Z")
        self.assertEqual(payload["documents"][0]["metadata"]["sync_cursor"], "2026-04-06T08:30:00Z")
        self.assertIn("# Telemetry Architecture", payload["documents"][0]["markdown"])
        self.assertIn("Overview", payload["documents"][0]["markdown"])
        self.assertIn("Telemetry ingest pipeline.", payload["documents"][0]["markdown"])
        self.assertIn("## Attachments", payload["documents"][0]["markdown"])
        self.assertIn("[telemetry-diagram.png](/download/attachments/201/telemetry-diagram.png)", payload["documents"][0]["markdown"])

    def test_confluence_incremental_sync_marks_incremental_metadata(self) -> None:
        payload = load_confluence_sync(Path("fixtures/connectors/confluence/incremental_sync.json"))
        self.assertEqual(payload["sync_type"], "incremental")
        self.assertTrue(payload["documents"][0]["metadata"]["incremental"])
        self.assertEqual(payload["documents"][0]["version"], "3")
        self.assertEqual(payload["documents"][0]["provenance"]["ingested_at"], "2026-04-06T09:45:00Z")
        self.assertEqual(payload["documents"][0]["metadata"]["sync_cursor"], "2026-04-06T09:45:00Z")
        self.assertIn("## Changes", payload["documents"][0]["markdown"])
        self.assertIn("- Reduced queue wait", payload["documents"][0]["markdown"])
        self.assertIn("- Added retry guard", payload["documents"][0]["markdown"])

    def test_confluence_documents_preserve_direct_canonical_sections_and_blocks(self) -> None:
        payload = load_confluence_sync(Path("fixtures/connectors/confluence/incremental_sync.json"))
        document = payload["documents"][0]

        headings = [section["heading"] for section in document["structure"]["sections"]]
        self.assertIn("Changes", headings)
        self.assertIn("Attachments", headings)

        block_texts = [block["text"] for block in document["content_blocks"]]
        self.assertIn("Reduced queue wait", block_texts)
        self.assertIn("Added retry guard", block_texts)


if __name__ == "__main__":
    unittest.main()

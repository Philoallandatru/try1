import unittest

from services.connectors.confluence.connector import _page_to_document


class ConfluenceVisualAssetsTest(unittest.TestCase):
    def test_confluence_inline_images_are_merged_at_page_position(self) -> None:
        document = _page_to_document(
            {
                "id": "CONF-501",
                "space": "SSDENG",
                "title": "Telemetry Diagram",
                "version": {"number": 2, "when": "2026-04-08T09:00:00Z"},
                "body": {
                    "storage": {
                        "value": (
                            "<h1>Overview</h1>"
                            "<p>Pipeline text before diagram.</p>"
                            "<ac:image><ri:attachment ri:filename=\"telemetry-diagram.png\" /></ac:image>"
                            "<p>Pipeline text after diagram.</p>"
                        )
                    }
                },
                "attachments": [
                    {
                        "name": "telemetry-diagram.png",
                        "media_type": "image/png",
                        "_links": {"download": "/download/attachments/501/telemetry-diagram.png"},
                        "ocr_text": "ingest queue retry guard",
                        "vision_caption": "Architecture diagram for telemetry ingestion.",
                    }
                ],
            },
            source_uri="https://confluence.example.com/pages/viewpage.action?pageId=CONF-501",
            incremental=False,
            acl_policy="team:ssd",
        )

        markdown = document["markdown"]
        before = markdown.index("Pipeline text before diagram.")
        image = markdown.index("### Image: telemetry-diagram.png")
        after = markdown.index("Pipeline text after diagram.")
        self.assertLess(before, image)
        self.assertLess(image, after)
        self.assertIn("ingest queue retry guard", markdown)
        self.assertEqual(document["metadata"]["visual_asset_count"], 1)
        self.assertTrue(any("ingest queue retry guard" in block["text"] for block in document["content_blocks"]))

    def test_confluence_tables_are_preserved_in_markdown_and_canonical_structure(self) -> None:
        document = _page_to_document(
            {
                "id": "CONF-502",
                "space": "SSDENG",
                "title": "Latency Table",
                "version": {"number": 1, "when": "2026-04-08T10:00:00Z"},
                "body": {
                    "storage": {
                        "value": (
                            "<h1>Overview</h1>"
                            "<p>Latency budgets are listed below.</p>"
                            "<table>"
                            "<tr><th>Stage</th><th>Budget</th></tr>"
                            "<tr><td>Queue wait</td><td>5us</td></tr>"
                            "<tr><td>Retry guard</td><td>2us</td></tr>"
                            "</table>"
                        )
                    }
                },
                "attachments": [],
            },
            source_uri="https://confluence.example.com/pages/viewpage.action?pageId=CONF-502",
            incremental=False,
            acl_policy="team:ssd",
        )

        self.assertIn("| Stage | Budget |", document["markdown"])
        self.assertIn("| Queue wait | 5us |", document["markdown"])
        self.assertTrue(document["structure"]["tables"])
        self.assertTrue(any("Queue wait" in block["text"] for block in document["content_blocks"]))

    def test_confluence_mixed_content_preserves_section_order(self) -> None:
        document = _page_to_document(
            {
                "id": "CONF-503",
                "space": "SSDENG",
                "title": "Mixed Content",
                "version": {"number": 1, "when": "2026-04-08T11:00:00Z"},
                "body": {
                    "storage": {
                        "value": (
                            "<h1>Overview</h1>"
                            "<p>Intro paragraph.</p>"
                            "<h2>Changes</h2>"
                            "<ul><li>Reduced queue wait</li></ul>"
                            "<table>"
                            "<tr><th>Stage</th><th>Budget</th></tr>"
                            "<tr><td>Queue wait</td><td>5us</td></tr>"
                            "</table>"
                            "<p>Post-table note.</p>"
                        )
                    }
                },
                "attachments": [],
            },
            source_uri="https://confluence.example.com/pages/viewpage.action?pageId=CONF-503",
            incremental=False,
            acl_policy="team:ssd",
        )

        blocks = document["content_blocks"]
        intro = next(block for block in blocks if block["text"] == "Intro paragraph.")
        change = next(block for block in blocks if block["text"] == "Reduced queue wait")
        table = next(block for block in blocks if "| Stage | Budget |" in block["text"])
        note = next(block for block in blocks if block["text"] == "Post-table note.")

        self.assertEqual(intro["section_heading"], "Overview")
        self.assertEqual(change["section_heading"], "Changes")
        self.assertEqual(table["section_heading"], "Changes")
        self.assertEqual(note["section_heading"], "Changes")


if __name__ == "__main__":
    unittest.main()

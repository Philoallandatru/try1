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


if __name__ == "__main__":
    unittest.main()

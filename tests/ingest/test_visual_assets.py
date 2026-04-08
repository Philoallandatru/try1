import unittest

from services.ingest.visual_assets import (
    build_visual_asset_markdown,
    image_asset_from_attachment,
    is_image_media_type,
)


class VisualAssetsTest(unittest.TestCase):
    def test_image_media_type_detection(self) -> None:
        self.assertTrue(is_image_media_type("image/png"))
        self.assertTrue(is_image_media_type("IMAGE/JPEG"))
        self.assertFalse(is_image_media_type("application/pdf"))
        self.assertFalse(is_image_media_type(""))

    def test_attachment_asset_renders_readable_indexable_markdown(self) -> None:
        asset = image_asset_from_attachment(
            {
                "filename": "failure-log.png",
                "mimeType": "image/png",
                "content": "https://jira.example.com/secure/attachment/100/failure-log.png",
                "ocr_text": "FTL assert at block 0x1234",
                "vision_caption": "Screenshot of a firmware failure log.",
            },
            source_type="jira",
            document_id="SSD-123",
            source_uri="https://jira.example.com/browse/SSD-123",
            section="Attachments",
        )

        markdown = build_visual_asset_markdown(asset)

        self.assertEqual(asset["asset_id"], "jira-ssd-123-failure-log-png")
        self.assertIn("### Image: failure-log.png", markdown)
        self.assertIn("![failure-log.png](https://jira.example.com/secure/attachment/100/failure-log.png)", markdown)
        self.assertIn("Image Source: jira SSD-123 Attachments", markdown)
        self.assertIn("FTL assert at block 0x1234", markdown)
        self.assertIn("Screenshot of a firmware failure log.", markdown)


if __name__ == "__main__":
    unittest.main()

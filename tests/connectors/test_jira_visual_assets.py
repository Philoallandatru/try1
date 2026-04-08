import unittest

from services.connectors.jira.connector import _issue_to_document


class JiraVisualAssetsTest(unittest.TestCase):
    def test_jira_image_attachments_are_merged_into_markdown_and_content_blocks(self) -> None:
        document = _issue_to_document(
            {
                "key": "SSD-501",
                "summary": "Failure screenshot",
                "description": "Firmware failure with attached screenshot.",
                "attachments": [
                    {
                        "filename": "failure-log.png",
                        "mimeType": "image/png",
                        "content": "https://jira.example.com/secure/attachment/501/failure-log.png",
                        "ocr_text": "FTL assert during TLC write",
                        "vision_caption": "Screenshot of the failure log.",
                    },
                    {
                        "filename": "trace.zip",
                        "mimeType": "application/zip",
                        "content": "https://jira.example.com/secure/attachment/501/trace.zip",
                    },
                ],
            },
            source_uri="https://jira.example.com/browse/SSD-501",
            incremental=False,
            acl_policy="team:ssd",
        )

        markdown = document["markdown"]
        self.assertIn("### Image: failure-log.png", markdown)
        self.assertIn("OCR Text:", markdown)
        self.assertIn("FTL assert during TLC write", markdown)
        self.assertIn("[trace.zip](https://jira.example.com/secure/attachment/501/trace.zip)", markdown)
        self.assertEqual(document["metadata"]["visual_asset_count"], 1)
        self.assertEqual(document["visual_assets"][0]["asset_id"], "jira-ssd-501-failure-log-png")
        self.assertTrue(
            any("FTL assert during TLC write" in block["text"] for block in document["content_blocks"])
        )


if __name__ == "__main__":
    unittest.main()

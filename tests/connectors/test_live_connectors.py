import unittest
from unittest.mock import patch

from services.connectors.confluence.connector import fetch_confluence_page_sync
from services.connectors.jira.connector import fetch_jira_server_sync
from services.retrieval.indexing.page_index import build_page_index


class LiveConnectorTest(unittest.TestCase):
    def test_jira_live_sync_normalizes_to_canonical_documents(self) -> None:
        with patch(
            "services.connectors.jira.connector._request_json",
            return_value={
                "total": 1,
                "names": {
                    "customfield_10001": "Root Cause",
                    "customfield_10002": "How to fix",
                    "customfield_10003": "Report department",
                },
                "issues": [
                    {
                        "key": "SSD-301",
                        "fields": {
                            "summary": "Live flush issue",
                            "description": "Need to confirm flush ordering.",
                            "updated": "2026-04-06T09:00:00Z",
                            "project": {"key": "SSD"},
                            "priority": {"name": "Highest"},
                            "status": {"name": "In Progress"},
                            "resolution": {"name": "Unresolved"},
                            "labels": ["BSOD"],
                            "customfield_10001": "Max Queue Exceeded after S4",
                            "customfield_10002": "Increase MQES and rerun debug FW",
                            "customfield_10003": {"value": "SV"},
                            "comment": {"comments": [{"body": "Check firmware impact."}]},
                            "attachment": [{"filename": "trace.txt", "mimeType": "text/plain"}],
                        },
                    }
                ],
            },
        ):
            payload = fetch_jira_server_sync(base_url="https://jira.example.com", token="secret")

        self.assertEqual(payload["sync_type"], "full")
        self.assertEqual(payload["documents"][0]["document_id"], "SSD-301")
        self.assertEqual(payload["documents"][0]["source_type"], "jira")
        self.assertIn("content_blocks", payload["documents"][0])
        self.assertIn("markdown", payload["documents"][0])
        self.assertEqual(payload["documents"][0]["metadata"]["issue_fields"]["Priority"], "Highest")
        self.assertEqual(payload["documents"][0]["metadata"]["issue_fields"]["Root Cause"], "Max Queue Exceeded after S4")
        self.assertEqual(payload["documents"][0]["metadata"]["issue_fields"]["How to fix"], "Increase MQES and rerun debug FW")
        self.assertIn("## Issue Fields", payload["documents"][0]["markdown"])
        self.assertGreaterEqual(len(build_page_index(payload["documents"])), 1)

    def test_confluence_live_sync_normalizes_to_canonical_documents(self) -> None:
        with patch(
            "services.connectors.confluence.connector._request_json",
            return_value={
                "results": [
                    {
                        "id": "CONF-501",
                        "title": "Flush Architecture",
                        "space": {"key": "SSDENG"},
                        "version": {"number": 9, "when": "2026-04-06T10:00:00Z"},
                        "body": {"storage": {"value": "<h1>Overview</h1><p>Flush path details.</p>"}},
                        "children": {
                            "attachment": {
                                "results": [
                                    {
                                        "title": "diagram.png",
                                        "metadata": {"mediaType": "image/png"},
                                        "_links": {"download": "/download/attachments/1/diagram.png"},
                                    }
                                ]
                            }
                        },
                        "_links": {"webui": "/pages/viewpage.action?pageId=CONF-501"},
                    }
                ]
            },
        ):
            payload = fetch_confluence_page_sync(base_url="https://confluence.example.com", token="secret")

        self.assertEqual(payload["sync_type"], "full")
        self.assertEqual(payload["documents"][0]["document_id"], "CONF-501")
        self.assertEqual(payload["documents"][0]["source_type"], "confluence")
        self.assertIn("attachments", payload["documents"][0])
        self.assertEqual(payload["documents"][0]["metadata"]["space"], "SSDENG")
        self.assertEqual(payload["documents"][0]["version"], "9")
        self.assertIn("# Flush Architecture", payload["documents"][0]["markdown"])
        self.assertIn("## Attachments", payload["documents"][0]["markdown"])
        self.assertIn("[diagram.png](/download/attachments/1/diagram.png)", payload["documents"][0]["markdown"])
        self.assertGreaterEqual(len(build_page_index(payload["documents"])), 1)


if __name__ == "__main__":
    unittest.main()

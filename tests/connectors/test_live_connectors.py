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
        self.assertEqual(payload["cursor"], "2026-04-06T10:00:00Z")
        self.assertEqual(payload["documents"][0]["document_id"], "CONF-501")
        self.assertEqual(payload["documents"][0]["source_type"], "confluence")
        self.assertIn("attachments", payload["documents"][0])
        self.assertEqual(payload["documents"][0]["metadata"]["space"], "SSDENG")
        self.assertEqual(payload["documents"][0]["metadata"]["sync_cursor"], "2026-04-06T10:00:00Z")
        self.assertEqual(payload["documents"][0]["version"], "9")
        self.assertIn("# Flush Architecture", payload["documents"][0]["markdown"])
        self.assertIn("## Attachments", payload["documents"][0]["markdown"])
        self.assertIn("[diagram.png](/download/attachments/1/diagram.png)", payload["documents"][0]["markdown"])
        self.assertGreaterEqual(len(build_page_index(payload["documents"])), 1)

    def test_jira_atlassian_api_backend_supports_selective_fetch_and_document_build(self) -> None:
        with patch(
            "services.connectors.jira.connector.fetch_jira_server_sync_atlassian_api",
            return_value={
                "sync_type": "full",
                "cursor": None,
                "names": {},
                "issues": [
                    {
                        "key": "SSD-777",
                        "fields": {
                            "summary": "Selective live fetch",
                            "description": "Pull only this issue.",
                            "updated": "2026-04-08T09:00:00Z",
                            "project": {"key": "SSD"},
                            "comment": {"comments": []},
                            "attachment": [
                                {
                                    "filename": "failure.png",
                                    "mimeType": "image/png",
                                    "content": "https://jira.example.com/secure/attachment/777/failure.png",
                                }
                            ],
                        },
                    }
                ],
                "selector_summary": {"fetch_backend": "atlassian-api", "issue_key": "SSD-777"},
            },
        ) as mocked:
            payload = fetch_jira_server_sync(
                base_url="https://jira.example.com",
                token="secret",
                fetch_backend="atlassian-api",
                issue_key="SSD-777",
            )

        mocked.assert_called_once()
        self.assertEqual(payload["documents"][0]["document_id"], "SSD-777")
        self.assertEqual(payload["selector_summary"]["issue_key"], "SSD-777")
        self.assertEqual(payload["selector_summary"]["fetch_backend"], "atlassian-api")
        self.assertEqual(payload["documents"][0]["metadata"]["visual_asset_count"], 1)

    def test_confluence_atlassian_api_backend_supports_selective_fetch_and_document_build(self) -> None:
        with patch(
            "services.connectors.confluence.connector.fetch_confluence_page_sync_atlassian_api",
            return_value={
                "sync_type": "full",
                "cursor": None,
                "pages": [
                    {
                        "id": "CONF-888",
                        "title": "Selective page",
                        "space": {"key": "SSDENG"},
                        "version": {"number": 4, "when": "2026-04-08T10:00:00Z"},
                        "body": {"storage": {"value": "<h1>Selective page</h1><p>Only one page.</p>"}},
                        "attachments": [],
                        "_links": {"webui": "/pages/viewpage.action?pageId=CONF-888"},
                    }
                ],
                "selector_summary": {"fetch_backend": "atlassian-api", "page_id": "CONF-888"},
            },
        ) as mocked:
            payload = fetch_confluence_page_sync(
                base_url="https://confluence.example.com",
                token="secret",
                fetch_backend="atlassian-api",
                page_id="CONF-888",
            )

        mocked.assert_called_once()
        self.assertEqual(payload["documents"][0]["document_id"], "CONF-888")
        self.assertEqual(payload["selector_summary"]["page_id"], "CONF-888")
        self.assertEqual(payload["selector_summary"]["fetch_backend"], "atlassian-api")


if __name__ == "__main__":
    unittest.main()

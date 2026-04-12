import unittest
from unittest.mock import patch

from services.connectors.confluence.atlassian_api_fetch import (
    _fetch_page_tree_by_root_id,
    fetch_confluence_page_sync_atlassian_api,
)


class ConfluenceAtlassianApiFetchTest(unittest.TestCase):
    def test_fetch_page_tree_by_root_id_traverses_descendants_breadth_first(self) -> None:
        root = {"id": "100", "title": "Root"}
        child_1 = {"id": "101", "title": "Child 1"}
        child_2 = {"id": "102", "title": "Child 2"}
        grandchild = {"id": "103", "title": "Grandchild"}

        child_payloads = [
            {"results": [child_1, child_2]},
            {"results": []},
            {"results": [grandchild]},
            {"results": []},
            {"results": []},
            {"results": []},
        ]

        with patch(
            "services.connectors.confluence.atlassian_api_fetch._fetch_page_by_id",
            return_value=root,
        ), patch(
            "services.connectors.confluence.atlassian_api_fetch._fetch_child_pages",
            side_effect=child_payloads,
        ):
            pages = _fetch_page_tree_by_root_id(object(), root_page_id="100")

        self.assertEqual([page["id"] for page in pages], ["100", "101", "102", "103"])

    def test_atlassian_api_fetch_supports_page_tree_mode(self) -> None:
        pages = [
            {"id": "100", "title": "Root", "version": {"number": 1}, "body": {"storage": {"value": ""}}, "space": {"key": "SSD"}},
            {"id": "101", "title": "Child", "version": {"number": 1}, "body": {"storage": {"value": ""}}, "space": {"key": "SSD"}},
        ]

        with patch(
            "services.connectors.confluence.atlassian_api_fetch._build_client",
            return_value=object(),
        ), patch(
            "services.connectors.confluence.atlassian_api_fetch._fetch_page_tree_by_root_id",
            return_value=pages,
        ), patch(
            "services.connectors.confluence.atlassian_api_fetch._normalize_page",
            side_effect=lambda page, **kwargs: {**page, "attachments": []},
        ):
            payload = fetch_confluence_page_sync_atlassian_api(
                base_url="https://confluence.example.com",
                token="secret",
                root_page_id="100",
                include_descendants=True,
            )

        self.assertEqual(len(payload["pages"]), 2)
        self.assertEqual(payload["selector_summary"]["root_page_id"], "100")
        self.assertTrue(payload["selector_summary"]["include_descendants"])


if __name__ == "__main__":
    unittest.main()

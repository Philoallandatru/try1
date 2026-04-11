import unittest

from services.connectors.jira.atlassian_api_fetch import _build_jql


class JiraAtlassianApiFetchTest(unittest.TestCase):
    def test_default_order_by_jql_does_not_override_helper_selectors(self) -> None:
        query = _build_jql(
            issue_key="SSD-777",
            jql="order by updated asc",
        )

        self.assertIn('issuekey = "SSD-777"', query)
        self.assertTrue(query.endswith("order by updated asc"))


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest

from services.connectors.confluence.connector import load_confluence_sync
from services.connectors.jira.connector import load_jira_sync
from services.retrieval.indexing.page_index import build_page_index
from services.retrieval.search.hybrid_search import search_page_index


class ConnectorPageIndexTest(unittest.TestCase):
    def test_jira_fixture_documents_can_be_indexed_and_searched(self) -> None:
        payload = load_jira_sync(Path("fixtures/connectors/jira/full_sync.json"))
        index = build_page_index(payload["documents"])
        results = search_page_index(index, "S4 black screen BSOD", {"team:ssd"})
        self.assertTrue(any(result["document_id"] == "SSD-101" for result in results))

    def test_confluence_fixture_documents_can_be_indexed_and_searched(self) -> None:
        payload = load_confluence_sync(Path("fixtures/connectors/confluence/page_sync.json"))
        index = build_page_index(payload["documents"])
        results = search_page_index(index, "telemetry architecture", {"team:ssd"})
        self.assertTrue(any(result["document_id"] == "CONF-201" for result in results))


if __name__ == "__main__":
    unittest.main()

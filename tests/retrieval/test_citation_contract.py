from pathlib import Path
import unittest

from services.connectors.confluence.connector import _page_to_document
from services.retrieval.citations.assembler import assemble_citation, build_source_inspection
from services.retrieval.indexing.page_index import build_page_index, load_documents
from services.retrieval.search.hybrid_search import search_page_index


class CitationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        documents = load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
        index = build_page_index(documents)
        cls.result = search_page_index(index, "flush command", {"team:ssd", "public"})[0]

    def test_citation_payload_contains_required_location_fields(self) -> None:
        citation = assemble_citation(self.result)
        self.assertEqual(citation["document"], "nvme-spec-v1")
        self.assertEqual(citation["version"], "1.0")
        self.assertEqual(citation["page"], 1)
        self.assertEqual(citation["section"], "Overview")
        self.assertEqual(citation["clause"], "1")
        self.assertEqual(citation["table_id"], "table-1")
        self.assertEqual(citation["figure_id"], "figure-1")

    def test_source_inspection_payload_exposes_bound_evidence(self) -> None:
        inspection = build_source_inspection(self.result)
        self.assertEqual(inspection["document_id"], "nvme-spec-v1")
        self.assertEqual(inspection["version"], "1.0")
        self.assertEqual(inspection["page"], 1)
        self.assertEqual(inspection["clause"], "1")
        self.assertTrue(len(inspection["content_blocks"]) >= 1)

    def test_source_inspection_exposes_bound_table_details_when_present(self) -> None:
        document = _page_to_document(
            {
                "id": "CONF-701",
                "space": "SSDENG",
                "title": "Queue Budget Table",
                "version": {"number": 1, "when": "2026-04-08T12:00:00Z"},
                "body": {
                    "storage": {
                        "value": (
                            "<h1>Overview</h1>"
                            "<p>Queue budgets are listed below.</p>"
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
            source_uri="https://confluence.example.com/pages/viewpage.action?pageId=CONF-701",
            incremental=False,
            acl_policy="team:ssd",
        )
        result = search_page_index(build_page_index([document]), "queue wait", {"team:ssd"})[0]

        inspection = build_source_inspection(result)
        self.assertEqual(inspection["table_id"], "table-1")
        self.assertEqual(inspection["table"]["title"], "HTML Table 1")
        self.assertEqual(inspection["table"]["rows"][1], ["Queue wait", "5us"])


if __name__ == "__main__":
    unittest.main()

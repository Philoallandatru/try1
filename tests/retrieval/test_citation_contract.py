from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()


from pathlib import Path
import unittest

from services.retrieval.indexing.page_index import build_page_index, load_documents
from services.retrieval.search.hybrid_search import search_page_index


class AclFilteredSearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        documents = load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
        cls.index = build_page_index(documents)

    def test_acl_filter_happens_before_ordering(self) -> None:
        results = search_page_index(self.index, "confidential flush review", {"team:ssd", "public"})
        self.assertFalse(any(result["document_id"] == "restricted-review" for result in results))

    def test_restricted_document_is_visible_when_acl_allows(self) -> None:
        results = search_page_index(self.index, "confidential flush review", {"team:ssd", "team:secret", "public"})
        self.assertTrue(any(result["document_id"] == "restricted-review" for result in results))


if __name__ == "__main__":
    unittest.main()


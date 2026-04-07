from pathlib import Path
import json
import unittest

from services.retrieval.indexing.page_index import build_page_index, load_documents
from services.retrieval.search.hybrid_search import search_page_index


class HybridSearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        documents = load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
        cls.index = build_page_index(documents)

    def test_hybrid_retrieval_prefers_canonical_authority(self) -> None:
        results = search_page_index(self.index, "flush command", {"team:ssd", "public"})
        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0]["document_id"], "nvme-spec-v1")
        self.assertEqual(results[0]["authority_level"], "canonical")

    def test_cross_language_query_recalls_english_spec(self) -> None:
        results = search_page_index(self.index, "刷新 命令", {"team:ssd", "public"})
        self.assertTrue(any(result["document_id"] == "nvme-spec-v1" for result in results))

    def test_abbreviation_query_uses_terminology_expansion(self) -> None:
        results = search_page_index(self.index, "FTL", {"team:ssd", "public"})
        self.assertEqual(results[0]["document_id"], "nvme-spec-v1")

    def test_explicit_background_query_can_prefer_contextual_source(self) -> None:
        results = search_page_index(self.index, "flush press release announcement", {"team:ssd", "public"})
        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0]["document_id"], "press-release")
        self.assertEqual(results[0]["authority_level"], "contextual")

    def test_search_accepts_json_restored_token_lists(self) -> None:
        restored_index = json.loads(json.dumps(self.index, default=list))
        self.assertIsInstance(restored_index[0]["tokens"], list)

        results = search_page_index(restored_index, "flush command", {"team:ssd", "public"})

        self.assertTrue(any(result["document_id"] == "nvme-spec-v1" for result in results))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import unittest

from services.retrieval.engine import PAGE_INDEX_ENGINE, build_shared_retrieval_bundle
from services.retrieval.indexing.page_index import build_page_index, load_documents


class RetrievalEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents = load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
        cls.index = build_page_index(cls.documents)

    def test_pageindex_engine_search_matches_existing_expectations(self) -> None:
        results = PAGE_INDEX_ENGINE.search(self.index, "flush command", {"team:ssd", "public"})
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["document_id"], "nvme-spec-v1")

    def test_pageindex_engine_citation_returns_contract_payload(self) -> None:
        payload = PAGE_INDEX_ENGINE.citation(self.index, "flush command", {"team:ssd", "public"})
        self.assertEqual(payload["citation"]["document"], "nvme-spec-v1")
        self.assertIn("inspection", payload)

    def test_shared_retrieval_bundle_includes_comparison_baseline(self) -> None:
        bundle = build_shared_retrieval_bundle(
            engine=PAGE_INDEX_ENGINE,
            entries=self.index,
            query="flush command",
            allowed_policies={"team:ssd", "public"},
        )
        self.assertEqual(bundle["engine"], "pageindex")
        self.assertEqual(bundle["comparison"]["engine"], "pageindex")
        self.assertIn("hit_quality", bundle["comparison"]["manual_review"])
        self.assertEqual(bundle["comparison"]["top_result_document"], "nvme-spec-v1")
        self.assertGreaterEqual(len(bundle["citations"]), 1)
        self.assertIn("pdf", bundle["source_breakdown"])

    def test_shared_retrieval_bundle_is_stable_for_one_shot_iterables(self) -> None:
        bundle = build_shared_retrieval_bundle(
            engine=PAGE_INDEX_ENGINE,
            entries=(entry for entry in self.index),
            query="flush command",
            allowed_policies={"team:ssd", "public"},
        )
        self.assertGreaterEqual(len(bundle["results"]), 1)
        self.assertEqual(bundle["citation"]["document"], "nvme-spec-v1")
        self.assertEqual(bundle["comparison"]["top_result_document"], "nvme-spec-v1")


if __name__ == "__main__":
    unittest.main()

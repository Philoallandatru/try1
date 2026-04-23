"""End-to-End Retrieval Tests - Simplified Version.

Tests the complete retrieval pipeline from query to results.
"""
import tempfile
import unittest
from pathlib import Path

from packages.retrieval.index_manager import IndexManager
from packages.retrieval.bm25_retriever import BM25Retriever
from packages.retrieval.enhanced_retrieval import EnhancedRetriever
from apps.portal_runner.retrieval_api import RetrievalAPI


class TestE2ERetrievalSimple(unittest.TestCase):
    """Simplified E2E tests for retrieval pipeline."""

    @classmethod
    def setUpClass(cls):
        """Set up test workspace with sample documents."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Initialize index
        cls.db_path = cls.workspace_dir / "documents.db"
        cls.index_dir = cls.workspace_dir / ".index"
        cls.index_manager = IndexManager(
            db_path=str(cls.db_path),
            index_dir=str(cls.index_dir)
        )

        # Add test documents to database
        test_docs = [
            {
                "id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "content": "The NVMe Flush command commits data and metadata to non-volatile media.",
                "source_type": "pdf",
                "metadata": {"document_type": "spec"}
            },
            {
                "id": "SSD-777",
                "title": "NVMe flush command failure",
                "content": "NVMe flush command fails intermittently under high load.",
                "source_type": "jira",
                "metadata": {"document_type": "issue"}
            },
            {
                "id": "CONF-123",
                "title": "NVMe Flush Implementation Guide",
                "content": "The flush command implementation requires proper queue management.",
                "source_type": "confluence",
                "metadata": {"document_type": "guide"}
            },
        ]

        for doc in test_docs:
            cls.index_manager.db.create_document(
                id=doc["id"],
                source_id=doc["id"],
                source_type=doc["source_type"],
                title=doc["title"],
                content=doc["content"],
                url="",
                metadata=doc["metadata"]
            )

        # Build index
        cls.index_manager.build_full_index()

    def test_basic_bm25_retrieval(self):
        """Test basic BM25 retrieval."""
        retriever = BM25Retriever(self.index_manager.index)
        results = retriever.search("NVMe flush command", top_k=3)

        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 3)

        # Check first result
        first = results[0]
        self.assertIsNotNone(first.doc_id)
        self.assertGreater(first.score, 0)

        # Verify spec document is in results
        doc_ids = [r.doc_id for r in results]
        self.assertIn("nvme-spec-1.4", doc_ids)

    def test_enhanced_retrieval(self):
        """Test enhanced retrieval with all features."""
        base_retriever = BM25Retriever(self.index_manager.index)
        enhanced = EnhancedRetriever(base_retriever)

        # Add synonym
        enhanced.query_expander.add_synonym("flush", ["commit"])

        results = enhanced.search(
            query="flush command",
            top_k=3,
            expand_query=True,
            rerank_results=True,
            filter_results=True
        )

        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 3)

    def test_retrieval_api(self):
        """Test retrieval through API layer."""
        api = RetrievalAPI(
            workspace_dir=self.workspace_dir,
            storage_dir=self.workspace_dir / ".local" / "retrieval"
        )

        result = api.search(query="NVMe flush", top_k=3)

        self.assertEqual(result["status"], "success")
        self.assertIn("results", result)
        self.assertGreater(result["total_results"], 0)

    def test_enhanced_api(self):
        """Test enhanced search through API."""
        api = RetrievalAPI(
            workspace_dir=self.workspace_dir,
            storage_dir=self.workspace_dir / ".local" / "retrieval"
        )

        result = api.enhanced_search(
            query="flush command",
            top_k=3,
            enable_expansion=True,
            enable_reranking=True,
            enable_filtering=True
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("enhancements", result)
        self.assertTrue(result["enhancements"]["expansion"])

    def test_empty_query(self):
        """Test empty query handling."""
        retriever = BM25Retriever(self.index_manager.index)
        results = retriever.search("", top_k=5)
        self.assertIsInstance(results, list)

    def test_min_score_threshold(self):
        """Test minimum score threshold."""
        retriever = BM25Retriever(self.index_manager.index)
        results = retriever.search("NVMe", top_k=10, min_score=5.0)

        for result in results:
            self.assertGreaterEqual(result.score, 5.0)

    def test_retrieval_consistency(self):
        """Test retrieval consistency across multiple calls."""
        retriever = BM25Retriever(self.index_manager.index)

        results1 = retriever.search("NVMe flush", top_k=5)
        results2 = retriever.search("NVMe flush", top_k=5)

        self.assertEqual(len(results1), len(results2))
        for r1, r2 in zip(results1, results2):
            self.assertEqual(r1.doc_id, r2.doc_id)
            self.assertAlmostEqual(r1.score, r2.score, places=5)


if __name__ == "__main__":
    unittest.main()

"""
Test SPLADE integration with RetrievalAPI.
"""
import tempfile
import unittest
from pathlib import Path

from apps.portal_runner.retrieval_api import RetrievalAPI


class TestSPLADEAPIIntegration(unittest.TestCase):
    """Test SPLADE integration with RetrievalAPI."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Initialize API
        cls.api = RetrievalAPI(
            workspace_dir=cls.workspace_dir,
            storage_dir=cls.workspace_dir / ".local" / "retrieval"
        )

        # Add test documents
        test_docs = [
            {
                "id": "nvme-spec",
                "title": "NVMe Specification",
                "content": "The NVMe flush command commits data to non-volatile media",
                "source_type": "pdf"
            },
            {
                "id": "ssd-issue",
                "title": "SSD Performance Issue",
                "content": "SSD performance degradation under high load conditions",
                "source_type": "jira"
            },
            {
                "id": "pcie-doc",
                "title": "PCIe Documentation",
                "content": "PCIe interface provides high bandwidth for NVMe devices",
                "source_type": "confluence"
            },
        ]

        for doc in test_docs:
            cls.api.index_manager.db.create_document(
                id=doc["id"],
                source_id=doc["id"],
                source_type=doc["source_type"],
                title=doc["title"],
                content=doc["content"],
                url="",
                metadata={}
            )

        # Build index
        cls.api.build_index()

    def test_splade_search(self):
        """Test SPLADE search through API."""
        result = self.api.splade_search(
            query="NVMe flush command",
            top_k=3,
            enable_expansion=True
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["retrieval_method"], "splade")
        self.assertIn("results", result)
        self.assertGreater(result["total_results"], 0)

    def test_splade_with_expansion(self):
        """Test SPLADE search with query expansion."""
        result = self.api.splade_search(
            query="flush",
            top_k=3,
            enable_expansion=True
        )

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["expansion_enabled"])
        self.assertIn("expansion_terms", result)

    def test_splade_without_expansion(self):
        """Test SPLADE search without query expansion."""
        result = self.api.splade_search(
            query="NVMe",
            top_k=3,
            enable_expansion=False
        )

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["expansion_enabled"])

    def test_hybrid_search(self):
        """Test hybrid search through API."""
        result = self.api.hybrid_search(
            query="NVMe performance",
            top_k=3,
            bm25_weight=0.5,
            splade_weight=0.5
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["retrieval_method"], "hybrid")
        self.assertIn("weights", result)
        self.assertEqual(result["weights"]["bm25"], 0.5)
        self.assertEqual(result["weights"]["splade"], 0.5)
        self.assertGreater(result["total_results"], 0)

    def test_hybrid_with_different_weights(self):
        """Test hybrid search with different weight configurations."""
        # BM25-heavy
        result_bm25 = self.api.hybrid_search(
            query="NVMe",
            top_k=3,
            bm25_weight=0.8,
            splade_weight=0.2
        )

        # SPLADE-heavy
        result_splade = self.api.hybrid_search(
            query="NVMe",
            top_k=3,
            bm25_weight=0.2,
            splade_weight=0.8
        )

        self.assertEqual(result_bm25["status"], "success")
        self.assertEqual(result_splade["status"], "success")

    def test_compare_retrieval_methods(self):
        """Test comparing different retrieval methods."""
        query = "NVMe flush"

        # BM25
        bm25_result = self.api.search(query, top_k=3)

        # Enhanced
        enhanced_result = self.api.enhanced_search(
            query,
            top_k=3,
            enable_expansion=True,
            enable_reranking=True,
            enable_filtering=True
        )

        # SPLADE
        splade_result = self.api.splade_search(
            query,
            top_k=3,
            enable_expansion=True
        )

        # Hybrid
        hybrid_result = self.api.hybrid_search(
            query,
            top_k=3,
            bm25_weight=0.5,
            splade_weight=0.5
        )

        # All should succeed
        self.assertEqual(bm25_result["status"], "success")
        self.assertEqual(enhanced_result["status"], "success")
        self.assertEqual(splade_result["status"], "success")
        self.assertEqual(hybrid_result["status"], "success")

        # All should return results
        self.assertGreater(bm25_result["total_results"], 0)
        self.assertGreater(enhanced_result["total_results"], 0)
        self.assertGreater(splade_result["total_results"], 0)
        self.assertGreater(hybrid_result["total_results"], 0)


if __name__ == "__main__":
    unittest.main()

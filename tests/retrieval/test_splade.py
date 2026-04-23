"""
Tests for SPLADE retriever.
"""
import tempfile
import unittest
from pathlib import Path

from packages.retrieval.splade_retriever import SPLADERetriever, HybridRetriever
from packages.retrieval.tokenizer import Tokenizer
from packages.retrieval.index_manager import IndexManager
from packages.retrieval.bm25_retriever import BM25Retriever


class TestSPLADERetriever(unittest.TestCase):
    """Tests for SPLADE retriever."""

    def setUp(self):
        """Set up test environment."""
        self.tokenizer = Tokenizer()
        self.retriever = SPLADERetriever(
            tokenizer=self.tokenizer,
            use_idf=True,
            expansion_terms=5,
            alpha=0.5
        )

        # Test documents
        self.documents = [
            {
                "id": "doc1",
                "content": "NVMe flush command commits data to non-volatile media"
            },
            {
                "id": "doc2",
                "content": "SSD performance degradation under high load"
            },
            {
                "id": "doc3",
                "content": "PCIe interface provides high bandwidth for NVMe devices"
            },
            {
                "id": "doc4",
                "content": "Flush command ensures data persistence across power cycles"
            },
        ]

        self.retriever.build_index(self.documents)

    def test_build_index(self):
        """Test index building."""
        stats = self.retriever.get_stats()

        self.assertEqual(stats["num_documents"], 4)
        self.assertGreater(stats["vocab_size"], 0)
        self.assertTrue(stats["use_idf"])

    def test_basic_search(self):
        """Test basic SPLADE search."""
        results = self.retriever.search("NVMe flush command", top_k=3)

        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 3)

        # Check result structure
        first = results[0]
        self.assertIsNotNone(first.doc_id)
        self.assertGreater(first.score, 0)

    def test_search_with_expansion(self):
        """Test search with query expansion."""
        results_with_expansion = self.retriever.search(
            "flush command",
            top_k=3,
            enable_expansion=True
        )

        results_without_expansion = self.retriever.search(
            "flush command",
            top_k=3,
            enable_expansion=False
        )

        # Both should return results
        self.assertGreater(len(results_with_expansion), 0)
        self.assertGreater(len(results_without_expansion), 0)

    def test_query_expansion(self):
        """Test query expansion functionality."""
        expansion_terms = self.retriever.get_query_expansion("NVMe")

        # Should return expansion terms
        self.assertIsInstance(expansion_terms, list)

        # Each term should have a weight
        for term, weight in expansion_terms:
            self.assertIsInstance(term, str)
            self.assertIsInstance(weight, float)
            self.assertGreater(weight, 0)

    def test_min_score_threshold(self):
        """Test minimum score threshold."""
        results = self.retriever.search(
            "NVMe",
            top_k=10,
            min_score=0.5
        )

        # All results should meet threshold
        for result in results:
            self.assertGreaterEqual(result.score, 0.5)

    def test_empty_query(self):
        """Test empty query handling."""
        results = self.retriever.search("", top_k=5)
        self.assertIsInstance(results, list)

    def test_sparse_vector_computation(self):
        """Test sparse vector computation."""
        text = "NVMe flush command"
        vector = self.retriever._compute_sparse_vector(text)

        # Should be a dict
        self.assertIsInstance(vector, dict)

        # Should contain terms
        self.assertGreater(len(vector), 0)

        # All weights should be positive
        for term, weight in vector.items():
            self.assertGreater(weight, 0)

    def test_similarity_computation(self):
        """Test similarity computation."""
        vec1 = {"nvme": 0.5, "flush": 0.3}
        vec2 = {"nvme": 0.4, "command": 0.6}

        similarity = self.retriever._compute_similarity(vec1, vec2)

        # Should be a float
        self.assertIsInstance(similarity, float)
        self.assertGreaterEqual(similarity, 0)


class TestHybridRetriever(unittest.TestCase):
    """Tests for hybrid BM25 + SPLADE retriever."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Initialize index manager
        cls.db_path = cls.workspace_dir / "documents.db"
        cls.index_dir = cls.workspace_dir / ".index"
        cls.index_manager = IndexManager(
            db_path=str(cls.db_path),
            index_dir=str(cls.index_dir)
        )

        # Add test documents
        test_docs = [
            {
                "id": "nvme-spec",
                "title": "NVMe Specification",
                "content": "NVMe flush command commits data to non-volatile media",
                "source_type": "pdf"
            },
            {
                "id": "ssd-issue",
                "title": "SSD Performance Issue",
                "content": "SSD performance degradation under high load",
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
            cls.index_manager.db.create_document(
                id=doc["id"],
                source_id=doc["id"],
                source_type=doc["source_type"],
                title=doc["title"],
                content=doc["content"],
                url="",
                metadata={}
            )

        cls.index_manager.build_full_index()

        # Create BM25 retriever
        cls.bm25_retriever = BM25Retriever(cls.index_manager.index)

        # Create SPLADE retriever
        cls.tokenizer = Tokenizer()
        cls.splade_retriever = SPLADERetriever(
            tokenizer=cls.tokenizer,
            use_idf=True,
            expansion_terms=5
        )

        # Build SPLADE index
        splade_docs = []
        for doc in test_docs:
            splade_docs.append({
                "id": doc["id"],
                "content": f"{doc['title']} {doc['content']}"
            })
        cls.splade_retriever.build_index(splade_docs)

        # Create hybrid retriever
        cls.hybrid_retriever = HybridRetriever(
            bm25_retriever=cls.bm25_retriever,
            splade_retriever=cls.splade_retriever,
            bm25_weight=0.5,
            splade_weight=0.5
        )

    def test_hybrid_search(self):
        """Test hybrid search combining BM25 and SPLADE."""
        results = self.hybrid_retriever.search("NVMe flush", top_k=3)

        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 3)

        # Check result structure
        first = results[0]
        self.assertIsNotNone(first.doc_id)
        self.assertGreater(first.score, 0)

    def test_hybrid_vs_bm25(self):
        """Test that hybrid retrieval works alongside BM25."""
        query = "NVMe performance"

        bm25_results = self.bm25_retriever.search(query, top_k=3)
        hybrid_results = self.hybrid_retriever.search(query, top_k=3)

        # Both should return results
        self.assertGreater(len(bm25_results), 0)
        self.assertGreater(len(hybrid_results), 0)

    def test_hybrid_vs_splade(self):
        """Test that hybrid retrieval works alongside SPLADE."""
        query = "flush command"

        splade_results = self.splade_retriever.search(query, top_k=3)
        hybrid_results = self.hybrid_retriever.search(query, top_k=3)

        # Both should return results
        self.assertGreater(len(splade_results), 0)
        self.assertGreater(len(hybrid_results), 0)

    def test_hybrid_weight_adjustment(self):
        """Test hybrid retriever with different weights."""
        # BM25-heavy
        hybrid_bm25 = HybridRetriever(
            bm25_retriever=self.bm25_retriever,
            splade_retriever=self.splade_retriever,
            bm25_weight=0.8,
            splade_weight=0.2
        )

        # SPLADE-heavy
        hybrid_splade = HybridRetriever(
            bm25_retriever=self.bm25_retriever,
            splade_retriever=self.splade_retriever,
            bm25_weight=0.2,
            splade_weight=0.8
        )

        query = "NVMe"
        results_bm25 = hybrid_bm25.search(query, top_k=3)
        results_splade = hybrid_splade.search(query, top_k=3)

        # Both should return results
        self.assertGreater(len(results_bm25), 0)
        self.assertGreater(len(results_splade), 0)

    def test_score_normalization(self):
        """Test score normalization in hybrid retriever."""
        results = self.bm25_retriever.search("NVMe", top_k=3)

        normalized = self.hybrid_retriever._normalize_scores(results)

        # Should be a dict
        self.assertIsInstance(normalized, dict)

        # All scores should be in [0, 1]
        for score in normalized.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


class TestSPLADEIntegration(unittest.TestCase):
    """Integration tests for SPLADE retriever."""

    def test_splade_with_real_documents(self):
        """Test SPLADE with realistic document collection."""
        tokenizer = Tokenizer()
        retriever = SPLADERetriever(tokenizer=tokenizer)

        # Realistic documents
        documents = [
            {
                "id": "doc1",
                "content": "The NVMe flush command is used to commit data and metadata "
                          "to non-volatile media. This ensures data persistence."
            },
            {
                "id": "doc2",
                "content": "SSD performance can degrade over time due to write amplification "
                          "and garbage collection overhead."
            },
            {
                "id": "doc3",
                "content": "PCIe Gen4 provides 16 GT/s per lane, doubling the bandwidth "
                          "compared to PCIe Gen3."
            },
            {
                "id": "doc4",
                "content": "NVMe over Fabrics (NVMe-oF) extends NVMe protocol to work "
                          "over network fabrics like RDMA and TCP."
            },
        ]

        retriever.build_index(documents)

        # Test various queries
        test_queries = [
            "NVMe flush command",
            "SSD performance",
            "PCIe bandwidth",
            "network storage"
        ]

        for query in test_queries:
            results = retriever.search(query, top_k=2)
            self.assertGreater(len(results), 0, f"No results for query: {query}")

    def test_splade_query_expansion_quality(self):
        """Test quality of query expansion."""
        tokenizer = Tokenizer()
        retriever = SPLADERetriever(tokenizer=tokenizer, expansion_terms=10)

        documents = [
            {"id": "1", "content": "NVMe SSD flash storage device"},
            {"id": "2", "content": "Solid state drive performance optimization"},
            {"id": "3", "content": "Flash memory controller firmware"},
        ]

        retriever.build_index(documents)

        # Get expansion for "SSD"
        expansions = retriever.get_query_expansion("SSD")

        # Should have expansion terms
        self.assertGreater(len(expansions), 0)

        # Expansion terms should be related
        expansion_terms = [term for term, _ in expansions]
        self.assertIsInstance(expansion_terms, list)


if __name__ == "__main__":
    unittest.main()

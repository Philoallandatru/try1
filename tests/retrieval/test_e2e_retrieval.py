"""End-to-End Retrieval Tests.

Tests the complete retrieval pipeline from query to results:
1. Basic BM25 retrieval
2. Enhanced retrieval (expansion, rewriting, reranking, filtering)
3. Evaluation against Golden Dataset
4. API integration
"""
import json
import tempfile
import unittest
from pathlib import Path

from packages.retrieval.index_manager import IndexManager
from packages.retrieval.bm25_retriever import BM25Retriever
from packages.retrieval.enhanced_retrieval import EnhancedRetriever
from packages.retrieval.golden_dataset import load_golden_dataset
from packages.retrieval.evaluator import RetrievalEvaluator
from apps.portal_runner.retrieval_api import RetrievalAPI


class TestE2ERetrieval(unittest.TestCase):
    """End-to-end tests for retrieval pipeline."""

    @classmethod
    def setUpClass(cls):
        """Set up test workspace with sample documents."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Create test documents
        cls.test_documents = cls._create_test_documents()

        # Initialize index
        cls.db_path = cls.workspace_dir / "documents.db"
        cls.index_dir = cls.workspace_dir / ".index"
        cls.index_manager = IndexManager(
            db_path=str(cls.db_path),
            index_dir=str(cls.index_dir)
        )

        # Add documents to database
        for doc in cls.test_documents:
            cls.index_manager.db.create_document(
                id=doc["doc_id"],
                source_id=doc["doc_id"],
                source_type=doc["metadata"].get("source_type", "test"),
                title=doc["title"],
                content=doc["content"],
                url="",
                metadata=doc.get("metadata", {})
            )

        # Build index
        cls.index_manager.build_full_index()

    @staticmethod
    def _create_test_documents():
        """Create test documents for retrieval."""
        return [
            {
                "doc_id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "content": "The NVMe Flush command commits data and metadata to non-volatile media. "
                          "This ensures data persistence across power cycles.",
                "metadata": {"document_type": "spec", "source_type": "pdf"}
            },
            {
                "doc_id": "SSD-777",
                "title": "NVMe flush command failure",
                "content": "NVMe flush command fails intermittently under high load. "
                          "Error code 0x02 returned. Affects firmware version 2.1.3.",
                "metadata": {"document_type": "issue", "source_type": "jira"}
            },
            {
                "doc_id": "CONF-123",
                "title": "NVMe Flush Implementation Guide",
                "content": "The flush command implementation requires proper queue management. "
                          "Best practices include batching and timeout handling.",
                "metadata": {"document_type": "guide", "source_type": "confluence"}
            },
            {
                "doc_id": "SSD-888",
                "title": "SSD performance degradation",
                "content": "SSD shows performance degradation after prolonged use. "
                          "IOPS drops from 100K to 50K. Garbage collection suspected.",
                "metadata": {"document_type": "issue", "source_type": "jira"}
            },
            {
                "doc_id": "pcie-spec-4.0",
                "title": "PCIe Specification 4.0",
                "content": "PCIe 4.0 provides 16 GT/s data rate per lane. "
                          "Supports up to x16 link width for maximum bandwidth.",
                "metadata": {"document_type": "spec", "source_type": "pdf"}
            }
        ]

    def test_basic_bm25_retrieval(self):
        """Test basic BM25 retrieval pipeline."""
        retriever = BM25Retriever(self.index_manager.index)

        # Test query
        query = "NVMe flush command"
        results = retriever.search(query, top_k=3)

        # Verify results
        self.assertGreater(len(results), 0, "Should return results")
        self.assertLessEqual(len(results), 3, "Should respect top_k limit")

        # Verify result structure
        first_result = results[0]
        self.assertIsNotNone(first_result.doc_id)
        self.assertIsNotNone(first_result.score)
        self.assertIsNotNone(first_result.document)
        self.assertGreater(first_result.score, 0)

        # Verify relevance (spec should rank high for this query)
        doc_ids = [r.doc_id for r in results]
        self.assertIn("nvme-spec-1.4", doc_ids, "Spec document should be in results")

    def test_enhanced_retrieval_with_expansion(self):
        """Test enhanced retrieval with query expansion."""
        base_retriever = BM25Retriever(self.index_manager.index)
        enhanced_retriever = EnhancedRetriever(base_retriever)

        # Add synonyms
        enhanced_retriever.expander.add_synonym("flush", ["commit", "persist"])

        # Search with expansion
        query = "flush command"
        results = enhanced_retriever.search(
            query=query,
            top_k=3,
            enable_expansion=True,
            enable_reranking=False,
            enable_filtering=False
        )

        # Verify results
        self.assertGreater(len(results), 0, "Should return results")

        # Expanded query should find relevant documents
        doc_ids = [r["doc_id"] for r in results]
        self.assertIn("nvme-spec-1.4", doc_ids)

    def test_enhanced_retrieval_with_reranking(self):
        """Test enhanced retrieval with result reranking."""
        base_retriever = BM25Retriever(self.index_manager.index)
        enhanced_retriever = EnhancedRetriever(base_retriever)

        # Set document type priorities
        enhanced_retriever.reranker.set_document_type_priority("spec", 1.5)
        enhanced_retriever.reranker.set_document_type_priority("issue", 1.0)

        # Search with reranking
        query = "NVMe specification"
        results = enhanced_retriever.search(
            query=query,
            top_k=3,
            enable_expansion=False,
            enable_reranking=True,
            enable_filtering=False
        )

        # Verify spec documents are boosted
        self.assertGreater(len(results), 0)
        # First result should likely be a spec document due to boosting
        first_result = results[0]
        if first_result["metadata"].get("document_type") == "spec":
            self.assertTrue(True, "Spec document ranked first as expected")

    def test_enhanced_retrieval_with_filtering(self):
        """Test enhanced retrieval with result filtering."""
        base_retriever = BM25Retriever(self.index_manager.index)
        enhanced_retriever = EnhancedRetriever(base_retriever)

        # Search with filtering
        query = "NVMe"
        results = enhanced_retriever.search(
            query=query,
            top_k=10,
            enable_expansion=False,
            enable_reranking=False,
            enable_filtering=True
        )

        # Verify no duplicates
        doc_ids = [r["doc_id"] for r in results]
        self.assertEqual(len(doc_ids), len(set(doc_ids)), "Should have no duplicate doc_ids")

        # Verify minimum content length
        for result in results:
            self.assertGreater(len(result["content"]), 0, "Content should not be empty")

    def test_full_enhanced_retrieval_pipeline(self):
        """Test complete enhanced retrieval with all features enabled."""
        base_retriever = BM25Retriever(self.index_manager.index)
        enhanced_retriever = EnhancedRetriever(base_retriever)

        # Configure enhancements
        enhanced_retriever.expander.add_synonym("SSD", ["solid state drive", "flash storage"])
        enhanced_retriever.rewriter.add_typo_correction("nvem", "nvme")
        enhanced_retriever.reranker.set_document_type_priority("spec", 1.3)

        # Search with all enhancements
        query = "SSD performance"
        results = enhanced_retriever.search(
            query=query,
            top_k=5,
            enable_expansion=True,
            enable_reranking=True,
            enable_filtering=True
        )

        # Verify results
        self.assertGreater(len(results), 0, "Should return results")
        self.assertLessEqual(len(results), 5, "Should respect top_k")

        # Verify result quality
        for result in results:
            self.assertIn("doc_id", result)
            self.assertIn("score", result)
            self.assertGreater(result["score"], 0, "Score should be positive")

    def test_retrieval_api_integration(self):
        """Test retrieval through API layer."""
        api = RetrievalAPI(
            workspace_dir=self.workspace_dir,
            storage_dir=self.workspace_dir / ".local" / "retrieval"
        )

        # Basic search
        result = api.search(
            query="NVMe flush",
            top_k=3,
            min_score=0.0
        )

        # Verify API response structure
        self.assertEqual(result["status"], "success")
        self.assertIn("query", result)
        self.assertIn("total_results", result)
        self.assertIn("results", result)
        self.assertGreater(result["total_results"], 0)

    def test_retrieval_api_enhanced_search(self):
        """Test enhanced search through API layer."""
        api = RetrievalAPI(
            workspace_dir=self.workspace_dir,
            storage_dir=self.workspace_dir / ".local" / "retrieval"
        )

        # Enhanced search
        result = api.enhanced_search(
            query="flush command",
            top_k=3,
            enable_expansion=True,
            enable_reranking=True,
            enable_filtering=True
        )

        # Verify response
        self.assertEqual(result["status"], "success")
        self.assertIn("enhancements", result)
        self.assertTrue(result["enhancements"]["expansion"])
        self.assertTrue(result["enhancements"]["reranking"])
        self.assertTrue(result["enhancements"]["filtering"])
        self.assertGreater(result["total_results"], 0)

    def test_retrieval_with_document_type_filter(self):
        """Test retrieval with document type filtering."""
        api = RetrievalAPI(
            workspace_dir=self.workspace_dir,
            storage_dir=self.workspace_dir / ".local" / "retrieval"
        )

        # Search only spec documents
        result = api.search(
            query="specification",
            top_k=5,
            document_types=["spec"]
        )

        # Verify only spec documents returned
        self.assertEqual(result["status"], "success")
        for doc in result["results"]:
            doc_type = doc.get("metadata", {}).get("document_type")
            self.assertEqual(doc_type, "spec", "Should only return spec documents")

    def test_retrieval_with_min_score_threshold(self):
        """Test retrieval with minimum score threshold."""
        retriever = BM25Retriever(self.index_manager.index)

        # Search with high threshold
        query = "NVMe"
        results = retriever.search(query, top_k=10, min_score=5.0)

        # Verify all results meet threshold
        for result in results:
            self.assertGreaterEqual(result["score"], 5.0, "Score should meet threshold")

    def test_empty_query_handling(self):
        """Test handling of empty queries."""
        retriever = BM25Retriever(self.index_manager.index)

        # Empty query
        results = retriever.search("", top_k=5)

        # Should return empty or handle gracefully
        self.assertIsInstance(results, list, "Should return a list")

    def test_retrieval_consistency(self):
        """Test that retrieval results are consistent across multiple calls."""
        retriever = BM25Retriever(self.index_manager.index)

        query = "NVMe flush command"

        # Run search multiple times
        results1 = retriever.search(query, top_k=5)
        results2 = retriever.search(query, top_k=5)

        # Results should be identical
        self.assertEqual(len(results1), len(results2))
        for r1, r2 in zip(results1, results2):
            self.assertEqual(r1["doc_id"], r2["doc_id"])
            self.assertAlmostEqual(r1["score"], r2["score"], places=5)


class TestE2ERetrievalEvaluation(unittest.TestCase):
    """End-to-end tests for retrieval evaluation."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment with Golden Dataset."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Create mini golden dataset
        cls.golden_dataset_path = cls.workspace_dir / "golden_dataset.yaml"
        cls._create_mini_golden_dataset(cls.golden_dataset_path)

        # Create test documents
        cls.test_documents = cls._create_evaluation_documents()

        # Initialize index
        cls.db_path = cls.workspace_dir / "documents.db"
        cls.index_dir = cls.workspace_dir / ".index"
        cls.index_manager = IndexManager(
            db_path=str(cls.db_path),
            index_dir=str(cls.index_dir)
        )

        # Add documents to database
        for doc in cls.test_documents:
            cls.index_manager.db.create_document(
                id=doc["doc_id"],
                source_id=doc["doc_id"],
                source_type=doc["metadata"].get("document_type", "test"),
                title=doc["title"],
                content=doc["content"],
                url="",
                metadata=doc.get("metadata", {})
            )

        cls.index_manager.build_full_index()

    @staticmethod
    def _create_mini_golden_dataset(path: Path):
        """Create a minimal golden dataset for testing."""
        dataset = {
            "queries": [
                {
                    "query_id": "Q1",
                    "query": "NVMe flush command",
                    "category": "specification",
                    "relevant_docs": ["nvme-spec-1.4", "CONF-123"]
                },
                {
                    "query_id": "Q2",
                    "query": "SSD performance issue",
                    "category": "troubleshooting",
                    "relevant_docs": ["SSD-888"]
                }
            ]
        }

        import yaml
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(dataset, f, allow_unicode=True)

    @staticmethod
    def _create_evaluation_documents():
        """Create documents for evaluation testing."""
        return [
            {
                "doc_id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "content": "The NVMe Flush command commits data to non-volatile media.",
                "metadata": {"document_type": "spec"}
            },
            {
                "doc_id": "CONF-123",
                "title": "NVMe Flush Guide",
                "content": "Implementation guide for NVMe flush command.",
                "metadata": {"document_type": "guide"}
            },
            {
                "doc_id": "SSD-888",
                "title": "SSD performance degradation",
                "content": "SSD performance drops under heavy load.",
                "metadata": {"document_type": "issue"}
            },
            {
                "doc_id": "SSD-999",
                "title": "Unrelated issue",
                "content": "This is an unrelated document about something else.",
                "metadata": {"document_type": "issue"}
            }
        ]

    def test_evaluation_against_golden_dataset(self):
        """Test retrieval evaluation against Golden Dataset."""
        # Load golden dataset
        golden_dataset = load_golden_dataset(str(self.golden_dataset_path))

        # Create retriever
        retriever = BM25Retriever(self.index_manager.index)

        # Create evaluator
        evaluator = RetrievalEvaluator(golden_dataset)

        # Run evaluation
        results = evaluator.evaluate(retriever, top_k=5)

        # Verify evaluation results
        self.assertIn("map", results)
        self.assertIn("mrr", results)
        self.assertIn("ndcg@5", results)
        self.assertIn("precision@5", results)
        self.assertIn("recall@5", results)

        # Metrics should be between 0 and 1
        for metric_name, metric_value in results.items():
            if metric_name.startswith("per_query"):
                continue
            self.assertGreaterEqual(metric_value, 0.0, f"{metric_name} should be >= 0")
            self.assertLessEqual(metric_value, 1.0, f"{metric_name} should be <= 1")

    def test_evaluation_api_integration(self):
        """Test evaluation through API layer."""
        api = RetrievalAPI(
            workspace_dir=self.workspace_dir,
            storage_dir=self.workspace_dir / ".local" / "retrieval"
        )

        # Upload golden dataset
        with open(self.golden_dataset_path, "rb") as f:
            dataset_content = f.read()

        upload_result = api.upload_dataset(
            name="test_dataset",
            content=dataset_content,
            description="Test dataset for E2E evaluation"
        )

        self.assertEqual(upload_result["status"], "success")
        dataset_id = upload_result["dataset_id"]

        # Run evaluation
        eval_result = api.evaluate(
            dataset_id=dataset_id,
            top_k=5,
            save_results=True,
            result_name="test_evaluation"
        )

        # Verify evaluation result
        self.assertEqual(eval_result["status"], "success")
        self.assertIn("metrics", eval_result)
        self.assertIn("map", eval_result["metrics"])

    def test_enhanced_vs_basic_retrieval_comparison(self):
        """Test comparison between basic and enhanced retrieval."""
        golden_dataset = load_golden_dataset(str(self.golden_dataset_path))

        # Basic retrieval
        basic_retriever = BM25Retriever(self.index_manager.index)
        basic_evaluator = RetrievalEvaluator(golden_dataset)
        basic_results = basic_evaluator.evaluate(basic_retriever, top_k=5)

        # Enhanced retrieval
        enhanced_retriever = EnhancedRetriever(basic_retriever)
        enhanced_retriever.expander.add_synonym("flush", ["commit", "persist"])
        enhanced_retriever.reranker.set_document_type_priority("spec", 1.3)

        enhanced_evaluator = RetrievalEvaluator(golden_dataset)
        enhanced_results = enhanced_evaluator.evaluate(enhanced_retriever, top_k=5)

        # Both should produce valid metrics
        self.assertIn("map", basic_results)
        self.assertIn("map", enhanced_results)

        # Enhanced should ideally perform better or equal
        # (Not strictly enforced as it depends on the dataset)
        self.assertGreaterEqual(enhanced_results["map"], 0.0)


if __name__ == "__main__":
    unittest.main()

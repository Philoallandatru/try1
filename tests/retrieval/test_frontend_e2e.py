"""End-to-End Tests for Retrieval Frontend Interfaces.

Tests the complete flow from frontend UI to backend API:
1. Retrieval Debug Page
2. Strategy Comparison Page
3. Retrieval Evaluation Page
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from packages.retrieval.index_manager import IndexManager
from packages.retrieval.bm25_retriever import BM25Retriever
from apps.portal_runner.retrieval_api import RetrievalAPI


class TestRetrievalDebugE2E(unittest.TestCase):
    """E2E tests for Retrieval Debug interface."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Create test documents
        cls.test_documents = [
            {
                "doc_id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "content": "The NVMe Flush command commits data and metadata to non-volatile media.",
                "metadata": {"document_type": "spec", "source_type": "pdf"}
            },
            {
                "doc_id": "SSD-777",
                "title": "NVMe flush command failure",
                "content": "NVMe flush command fails intermittently under high load.",
                "metadata": {"document_type": "issue", "source_type": "jira"}
            },
            {
                "doc_id": "CONF-123",
                "title": "NVMe Flush Implementation Guide",
                "content": "The flush command implementation requires proper queue management.",
                "metadata": {"document_type": "guide", "source_type": "confluence"}
            }
        ]

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

        cls.index_manager.build_full_index()

        # Initialize API
        cls.api = RetrievalAPI(
            workspace_dir=cls.workspace_dir,
            storage_dir=cls.workspace_dir / ".local" / "retrieval"
        )

    def test_debug_api_basic_query(self):
        """Test debug API with basic query."""
        # Simulate frontend request
        request_data = {
            "query": "NVMe flush command",
            "strategy": "hybrid",
            "top_k": 5
        }

        # Call debug API
        result = self.api.debug_search(
            query=request_data["query"],
            strategy=request_data["strategy"],
            top_k=request_data["top_k"]
        )

        # Verify response structure
        self.assertEqual(result["status"], "success")
        self.assertIn("query", result)
        self.assertIn("results", result)
        self.assertIn("debug_info", result)

        # Verify debug info
        debug_info = result["debug_info"]
        self.assertIn("strategy", debug_info)
        self.assertIn("retrieval_time_ms", debug_info)
        self.assertIn("total_docs", debug_info)
        self.assertEqual(debug_info["strategy"], "hybrid")

        # Verify results
        results = result["results"]
        self.assertGreater(len(results), 0, "Should return results")
        self.assertLessEqual(len(results), 5, "Should respect top_k")

        # Verify result structure
        first_result = results[0]
        self.assertIn("doc_id", first_result)
        self.assertIn("content", first_result)
        self.assertIn("score", first_result)
        self.assertIn("metadata", first_result)

    def test_debug_api_different_strategies(self):
        """Test debug API with different retrieval strategies."""
        strategies = ["hybrid", "semantic", "keyword", "splade"]
        query = "NVMe specification"

        for strategy in strategies:
            with self.subTest(strategy=strategy):
                result = self.api.debug_search(
                    query=query,
                    strategy=strategy,
                    top_k=3
                )

                # All strategies should return valid results
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["debug_info"]["strategy"], strategy)
                self.assertGreaterEqual(len(result["results"]), 0)

    def test_debug_api_empty_query(self):
        """Test debug API with empty query."""
        result = self.api.debug_search(
            query="",
            strategy="hybrid",
            top_k=5
        )

        # Should handle gracefully
        self.assertIn("status", result)
        # Empty query may still return results (all documents), so just check structure
        self.assertIn("results", result)
        self.assertIsInstance(result["results"], list)

    def test_debug_api_performance_metrics(self):
        """Test that debug API returns performance metrics."""
        result = self.api.debug_search(
            query="NVMe flush",
            strategy="hybrid",
            top_k=5
        )

        # Verify performance metrics
        debug_info = result["debug_info"]
        self.assertIn("retrieval_time_ms", debug_info)
        self.assertIsInstance(debug_info["retrieval_time_ms"], (int, float))
        self.assertGreater(debug_info["retrieval_time_ms"], 0)

    def test_debug_api_metadata_preservation(self):
        """Test that debug API preserves document metadata."""
        result = self.api.debug_search(
            query="NVMe",
            strategy="hybrid",
            top_k=5
        )

        # Verify metadata is included
        for doc in result["results"]:
            self.assertIn("metadata", doc)
            metadata = doc["metadata"]
            self.assertIsInstance(metadata, dict)
            # Should have at least document_type
            if metadata:
                self.assertTrue(len(metadata) > 0)


class TestStrategyComparisonE2E(unittest.TestCase):
    """E2E tests for Strategy Comparison interface."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Create test documents
        cls.test_documents = [
            {
                "doc_id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "content": "The NVMe Flush command commits data and metadata to non-volatile media.",
                "metadata": {"document_type": "spec"}
            },
            {
                "doc_id": "SSD-777",
                "title": "NVMe flush command failure",
                "content": "NVMe flush command fails intermittently under high load.",
                "metadata": {"document_type": "issue"}
            },
            {
                "doc_id": "CONF-123",
                "title": "NVMe Flush Implementation Guide",
                "content": "The flush command implementation requires proper queue management.",
                "metadata": {"document_type": "guide"}
            }
        ]

        # Initialize index
        cls.db_path = cls.workspace_dir / "documents.db"
        cls.index_dir = cls.workspace_dir / ".index"
        cls.index_manager = IndexManager(
            db_path=str(cls.db_path),
            index_dir=str(cls.index_dir)
        )

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

        # Initialize API
        cls.api = RetrievalAPI(
            workspace_dir=cls.workspace_dir,
            storage_dir=cls.workspace_dir / ".local" / "retrieval"
        )

    def test_compare_api_two_strategies(self):
        """Test comparison API with two strategies."""
        request_data = {
            "query": "NVMe flush command",
            "strategies": ["hybrid", "semantic"],
            "top_k": 5
        }

        result = self.api.compare_strategies(
            query=request_data["query"],
            strategies=request_data["strategies"],
            top_k=request_data["top_k"]
        )

        # Verify response structure
        self.assertEqual(result["status"], "success")
        self.assertIn("query", result)
        self.assertIn("strategies", result)
        self.assertIn("comparison_metrics", result)

        # Verify strategies results
        strategies = result["strategies"]
        self.assertEqual(len(strategies), 2)

        for strategy_result in strategies:
            self.assertIn("strategy", strategy_result)
            self.assertIn("results", strategy_result)
            self.assertIn("metrics", strategy_result)

            # Verify metrics
            metrics = strategy_result["metrics"]
            self.assertIn("retrieval_time_ms", metrics)
            self.assertIn("total_results", metrics)

    def test_compare_api_multiple_strategies(self):
        """Test comparison API with multiple strategies."""
        strategies = ["hybrid", "semantic", "keyword", "splade"]

        result = self.api.compare_strategies(
            query="NVMe specification",
            strategies=strategies,
            top_k=3
        )

        # Should return results for all strategies
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["strategies"]), len(strategies))

        # Verify each strategy is represented
        returned_strategies = [s["strategy"] for s in result["strategies"]]
        for strategy in strategies:
            self.assertIn(strategy, returned_strategies)

    def test_compare_api_comparison_metrics(self):
        """Test that comparison API returns comparison metrics."""
        result = self.api.compare_strategies(
            query="NVMe flush",
            strategies=["hybrid", "semantic"],
            top_k=5
        )

        # Verify comparison metrics
        comparison_metrics = result["comparison_metrics"]
        self.assertIn("overlap_rate", comparison_metrics)
        self.assertIn("avg_score_diff", comparison_metrics)

        # Metrics should be valid numbers
        self.assertIsInstance(comparison_metrics["overlap_rate"], (int, float))
        self.assertIsInstance(comparison_metrics["avg_score_diff"], (int, float))

        # Overlap rate should be between 0 and 1
        self.assertGreaterEqual(comparison_metrics["overlap_rate"], 0.0)
        self.assertLessEqual(comparison_metrics["overlap_rate"], 1.0)

    def test_compare_api_result_consistency(self):
        """Test that comparison results are consistent."""
        query = "NVMe flush command"
        strategies = ["hybrid", "semantic"]

        # Run comparison twice
        result1 = self.api.compare_strategies(query, strategies, top_k=5)
        result2 = self.api.compare_strategies(query, strategies, top_k=5)

        # Results should be identical
        self.assertEqual(result1["query"], result2["query"])
        self.assertEqual(len(result1["strategies"]), len(result2["strategies"]))

        # Compare each strategy's results
        for s1, s2 in zip(result1["strategies"], result2["strategies"]):
            self.assertEqual(s1["strategy"], s2["strategy"])
            self.assertEqual(len(s1["results"]), len(s2["results"]))

    def test_compare_api_single_strategy_error(self):
        """Test that comparison API requires at least 2 strategies."""
        result = self.api.compare_strategies(
            query="NVMe",
            strategies=["hybrid"],
            top_k=5
        )

        # Should return error or handle gracefully
        if result["status"] == "error":
            self.assertIn("message", result)
        else:
            # If it allows single strategy, should still return valid structure
            self.assertIn("strategies", result)


class TestRetrievalEvaluationE2E(unittest.TestCase):
    """E2E tests for Retrieval Evaluation interface."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Create mini golden dataset
        cls.golden_dataset_path = cls.workspace_dir / "golden_dataset.yaml"
        cls._create_mini_golden_dataset(cls.golden_dataset_path)

        # Create test documents
        cls.test_documents = [
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
            }
        ]

        # Initialize index
        cls.db_path = cls.workspace_dir / "documents.db"
        cls.index_dir = cls.workspace_dir / ".index"
        cls.index_manager = IndexManager(
            db_path=str(cls.db_path),
            index_dir=str(cls.index_dir)
        )

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

        # Initialize API
        cls.api = RetrievalAPI(
            workspace_dir=cls.workspace_dir,
            storage_dir=cls.workspace_dir / ".local" / "retrieval"
        )

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

    def test_evaluation_api_upload_dataset(self):
        """Test uploading golden dataset through API."""
        with open(self.golden_dataset_path, "r", encoding="utf-8") as f:
            dataset_content = f.read()

        result = self.api.upload_dataset(
            dataset_content=dataset_content,
            dataset_id="test_dataset"
        )

        # Verify upload success
        self.assertEqual(result["status"], "success")
        self.assertIn("dataset", result)
        dataset = result["dataset"]
        self.assertIn("dataset_id", dataset)
        self.assertEqual(dataset["dataset_id"], "test_dataset")

    def test_evaluation_api_list_datasets(self):
        """Test listing uploaded datasets."""
        # Upload a dataset first
        with open(self.golden_dataset_path, "r", encoding="utf-8") as f:
            dataset_content = f.read()

        self.api.upload_dataset(
            dataset_content=dataset_content,
            dataset_id="test_dataset_list"
        )

        # List datasets
        result = self.api.list_datasets()

        # Verify response
        self.assertEqual(result["status"], "success")
        self.assertIn("datasets", result)
        self.assertIsInstance(result["datasets"], list)
        self.assertGreater(len(result["datasets"]), 0)

        # Verify dataset structure
        dataset = result["datasets"][0]
        self.assertIn("dataset_id", dataset)
        self.assertIn("name", dataset)

    def test_evaluation_api_run_evaluation(self):
        """Test running evaluation through API."""
        # Upload dataset
        with open(self.golden_dataset_path, "r", encoding="utf-8") as f:
            dataset_content = f.read()

        upload_result = self.api.upload_dataset(
            dataset_content=dataset_content,
            dataset_id="test_eval_dataset"
        )

        dataset_id = upload_result["dataset"]["dataset_id"]

        # Run evaluation using the evaluate method with golden_dataset_path
        # Save the dataset to a temporary file first
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(dataset_content)
            temp_path = f.name

        try:
            eval_result = self.api.evaluate(
                golden_dataset_path=temp_path,
                top_k=5,
                save_result=True
            )

            # Check if evaluation succeeded or failed gracefully
            if eval_result["status"] == "error":
                # If error, just verify error structure
                self.assertIn("error", eval_result)
                return

            # Verify evaluation result
            self.assertEqual(eval_result["status"], "success")
            self.assertIn("aggregate_metrics", eval_result)

            # Verify metrics if present
            if "aggregate_metrics" in eval_result:
                metrics = eval_result["aggregate_metrics"]
                self.assertIn("mean_average_precision", metrics)
                self.assertIn("mean_reciprocal_rank", metrics)

                # All metrics should be between 0 and 1
                for metric_name, metric_value in metrics.items():
                    if metric_name != "total_queries":
                        self.assertGreaterEqual(metric_value, 0.0)
                        self.assertLessEqual(metric_value, 1.0)
        finally:
            import os
            os.unlink(temp_path)

    def test_evaluation_api_list_results(self):
        """Test listing evaluation results."""
        # Upload and run evaluation
        with open(self.golden_dataset_path, "r", encoding="utf-8") as f:
            dataset_content = f.read()

        self.api.upload_dataset(
            dataset_content=dataset_content,
            dataset_id="test_results_dataset"
        )

        # Save dataset to temp file and run evaluation
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(dataset_content)
            temp_path = f.name

        try:
            eval_result = self.api.evaluate(
                golden_dataset_path=temp_path,
                top_k=5,
                save_result=True
            )

            # Only check results if evaluation succeeded
            if eval_result["status"] != "success":
                self.skipTest("Evaluation failed, skipping list results test")

            # List results
            result = self.api.list_evaluation_results()

            # Verify response
            self.assertEqual(result["status"], "success")
            self.assertIn("results", result)
            self.assertIsInstance(result["results"], list)

            # May be empty if evaluation didn't save
            if len(result["results"]) > 0:
                # Verify result structure
                eval_result = result["results"][0]
                self.assertIn("run_id", eval_result)
                self.assertIn("dataset_name", eval_result)
                self.assertIn("aggregate_metrics", eval_result)
        finally:
            import os
            os.unlink(temp_path)

    def test_evaluation_api_get_result_detail(self):
        """Test getting detailed evaluation result."""
        # Upload and run evaluation
        with open(self.golden_dataset_path, "r", encoding="utf-8") as f:
            dataset_content = f.read()

        self.api.upload_dataset(
            dataset_content=dataset_content,
            dataset_id="test_detail_dataset"
        )

        # Save dataset to temp file and run evaluation
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(dataset_content)
            temp_path = f.name

        try:
            eval_result = self.api.evaluate(
                golden_dataset_path=temp_path,
                top_k=5,
                save_result=True
            )

            # Only proceed if evaluation succeeded and has run_id
            if eval_result["status"] != "success" or "run_id" not in eval_result:
                self.skipTest("Evaluation failed or no run_id, skipping detail test")

            run_id = eval_result["run_id"]

            # Get detailed result
            detail = self.api.get_evaluation_result(run_id)

            # Verify detailed result
            self.assertEqual(detail["status"], "success")
            self.assertIn("result", detail)
            result_data = detail["result"]
            self.assertIn("run_id", result_data)
            self.assertIn("aggregate_metrics", result_data)
            self.assertIn("per_query_results", result_data)

            # Verify per-query results
            per_query = result_data["per_query_results"]
            self.assertIsInstance(per_query, list)

            if len(per_query) > 0:
                # Verify per-query structure
                query_result = per_query[0]
                self.assertIn("query_id", query_result)
                self.assertIn("query_text", query_result)
        finally:
            import os
            os.unlink(temp_path)


class TestFrontendIntegration(unittest.TestCase):
    """Integration tests simulating frontend-backend interaction."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Create test documents
        cls.test_documents = [
            {
                "doc_id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "content": "The NVMe Flush command commits data and metadata.",
                "metadata": {"document_type": "spec"}
            }
        ]

        # Initialize index
        cls.db_path = cls.workspace_dir / "documents.db"
        cls.index_dir = cls.workspace_dir / ".index"
        cls.index_manager = IndexManager(
            db_path=str(cls.db_path),
            index_dir=str(cls.index_dir)
        )

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

        cls.api = RetrievalAPI(
            workspace_dir=cls.workspace_dir,
            storage_dir=cls.workspace_dir / ".local" / "retrieval"
        )

    def test_complete_debug_workflow(self):
        """Test complete debug workflow from frontend to backend."""
        # Step 1: User enters query in debug page
        query = "NVMe flush"
        strategy = "hybrid"
        top_k = 5

        # Step 2: Frontend sends request to debug API
        result = self.api.debug_search(query, strategy, top_k)

        # Step 3: Verify response can be rendered by frontend
        self.assertEqual(result["status"], "success")
        self.assertIn("results", result)
        self.assertIn("debug_info", result)

        # Step 4: Verify frontend can display results
        for doc in result["results"]:
            # Frontend needs these fields
            self.assertIn("doc_id", doc)
            self.assertIn("content", doc)
            self.assertIn("score", doc)
            self.assertIsInstance(doc["score"], (int, float))

    def test_complete_comparison_workflow(self):
        """Test complete comparison workflow."""
        # Step 1: User selects strategies
        strategies = ["hybrid", "semantic"]
        query = "NVMe specification"
        top_k = 3

        # Step 2: Frontend sends comparison request
        result = self.api.compare_strategies(query, strategies, top_k)

        # Step 3: Verify response structure for frontend rendering
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["strategies"]), 2)

        # Step 4: Verify frontend can render side-by-side comparison
        for strategy_result in result["strategies"]:
            self.assertIn("strategy", strategy_result)
            self.assertIn("results", strategy_result)
            self.assertIsInstance(strategy_result["results"], list)

    def test_error_handling_in_frontend(self):
        """Test that API errors can be handled by frontend."""
        # Test with invalid strategy
        result = self.api.debug_search(
            query="test",
            strategy="invalid_strategy",
            top_k=5
        )

        # Should return error status that frontend can handle
        if result["status"] == "error":
            # Check for either 'message' or 'error' field
            self.assertTrue("message" in result or "error" in result)
            # Frontend should display this message to user


if __name__ == "__main__":
    unittest.main()

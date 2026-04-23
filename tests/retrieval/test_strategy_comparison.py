"""
Test multi-strategy retrieval comparison.
"""
import tempfile
import unittest
from pathlib import Path

from packages.retrieval.index_manager import IndexManager
from packages.retrieval.bm25_retriever import BM25Retriever
from packages.retrieval.enhanced_retrieval import EnhancedRetriever
from packages.retrieval.splade_retriever import SPLADERetriever, HybridRetriever
from packages.retrieval.strategy_comparator import StrategyComparator
from packages.retrieval.golden_dataset import GoldenDataset, GoldenQuery
from packages.retrieval.tokenizer import Tokenizer


class TestStrategyComparison(unittest.TestCase):
    """Test multi-strategy retrieval comparison."""

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
                "content": "The NVMe flush command commits data to non-volatile media",
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
            {
                "id": "flush-guide",
                "title": "Flush Command Guide",
                "content": "Implementation guide for NVMe flush command",
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

        # Create retrievers
        cls.bm25_retriever = BM25Retriever(cls.index_manager.index)
        cls.enhanced_retriever = EnhancedRetriever(cls.bm25_retriever)

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

        cls.hybrid_retriever = HybridRetriever(
            bm25_retriever=cls.bm25_retriever,
            splade_retriever=cls.splade_retriever,
            bm25_weight=0.5,
            splade_weight=0.5
        )

        # Create golden dataset
        from packages.retrieval.golden_dataset import ExpectedDocument
        cls.golden_dataset = GoldenDataset(queries=[
            GoldenQuery(
                id="Q1",
                query="NVMe flush command",
                description="Find information about NVMe flush command",
                expected_docs=[
                    ExpectedDocument("nvme-spec", 1.0, "Contains flush command spec"),
                    ExpectedDocument("flush-guide", 0.8, "Implementation guide")
                ]
            ),
            GoldenQuery(
                id="Q2",
                query="SSD performance",
                description="Find SSD performance issues",
                expected_docs=[
                    ExpectedDocument("ssd-issue", 1.0, "Performance issue documentation")
                ]
            ),
            GoldenQuery(
                id="Q3",
                query="PCIe bandwidth",
                description="Find PCIe bandwidth information",
                expected_docs=[
                    ExpectedDocument("pcie-doc", 1.0, "PCIe documentation")
                ]
            ),
        ])

        # Create comparator
        cls.comparator = StrategyComparator(
            bm25_retriever=cls.bm25_retriever,
            enhanced_retriever=cls.enhanced_retriever,
            splade_retriever=cls.splade_retriever,
            hybrid_retriever=cls.hybrid_retriever
        )

    def test_compare_all_strategies(self):
        """Test comparing all retrieval strategies."""
        results = self.comparator.compare_strategies(
            self.golden_dataset,
            top_k=5
        )

        # Should have results for all strategies
        self.assertIn("bm25", results)
        self.assertIn("enhanced", results)
        self.assertIn("splade", results)
        self.assertIn("hybrid", results)

        # Each result should have metrics
        for strategy_name, result in results.items():
            self.assertIn("metrics", result)
            self.assertIn("elapsed_time", result)
            self.assertIn("queries_per_second", result)

            # Check metrics
            metrics = result["metrics"]
            self.assertIn("map", metrics)
            self.assertIn("mrr", metrics)
            self.assertIn("ndcg@5", metrics)

    def test_compare_specific_strategies(self):
        """Test comparing specific strategies."""
        results = self.comparator.compare_strategies(
            self.golden_dataset,
            top_k=5,
            strategies=["bm25", "splade"]
        )

        # Should only have specified strategies
        self.assertEqual(len(results), 2)
        self.assertIn("bm25", results)
        self.assertIn("splade", results)
        self.assertNotIn("enhanced", results)
        self.assertNotIn("hybrid", results)

    def test_generate_comparison_report(self):
        """Test generating comparison report."""
        results = self.comparator.compare_strategies(
            self.golden_dataset,
            top_k=5
        )

        report = self.comparator.generate_comparison_report(results)

        # Report should be a string
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)

        # Should contain key sections
        self.assertIn("# Retrieval Strategy Comparison Report", report)
        self.assertIn("## Metrics Comparison", report)
        self.assertIn("## Performance Analysis", report)
        self.assertIn("## Recommendations", report)

        # Should contain all strategies
        self.assertIn("bm25", report)
        self.assertIn("enhanced", report)
        self.assertIn("splade", report)
        self.assertIn("hybrid", report)

    def test_save_comparison_report(self):
        """Test saving comparison report to file."""
        results = self.comparator.compare_strategies(
            self.golden_dataset,
            top_k=5
        )

        output_path = self.workspace_dir / "comparison_report.md"
        report = self.comparator.generate_comparison_report(
            results,
            output_path=output_path
        )

        # File should exist
        self.assertTrue(output_path.exists())

        # File content should match report
        with open(output_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        self.assertEqual(file_content, report)

    def test_compare_on_query_categories(self):
        """Test category-wise comparison."""
        category_results = self.comparator.compare_on_query_categories(
            self.golden_dataset,
            top_k=5
        )

        # Should have results for categories (based on first word of description)
        self.assertGreater(len(category_results), 0)

        # Each category should have strategy results
        for category, results in category_results.items():
            self.assertIn("bm25", results)
            self.assertIn("enhanced", results)
            self.assertIn("splade", results)
            self.assertIn("hybrid", results)

    def test_generate_category_report(self):
        """Test generating category-wise report."""
        category_results = self.comparator.compare_on_query_categories(
            self.golden_dataset,
            top_k=5
        )

        report = self.comparator.generate_category_report(category_results)

        # Report should be a string
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)

        # Should contain category header
        self.assertIn("Category-wise", report)

    def test_performance_metrics(self):
        """Test that performance metrics are captured."""
        results = self.comparator.compare_strategies(
            self.golden_dataset,
            top_k=5
        )

        for strategy_name, result in results.items():
            # Should have timing information (may be 0 for very fast execution)
            self.assertGreaterEqual(result["elapsed_time"], 0)
            self.assertGreaterEqual(result["queries_per_second"], 0)

    def test_metric_comparison(self):
        """Test that metrics can be compared across strategies."""
        results = self.comparator.compare_strategies(
            self.golden_dataset,
            top_k=5
        )

        # Extract MAP scores
        map_scores = {
            name: result["metrics"]["map"]
            for name, result in results.items()
        }

        # All scores should be between 0 and 1
        for score in map_scores.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()

"""
Multi-strategy retrieval comparison system.

Compares different retrieval strategies (BM25, Enhanced, SPLADE, Hybrid)
and generates evaluation reports.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import time

from packages.retrieval.golden_dataset import load_golden_dataset, GoldenDataset
from packages.retrieval.evaluator import RetrievalEvaluator
from packages.retrieval.bm25_retriever import BM25Retriever
from packages.retrieval.enhanced_retrieval import EnhancedRetriever
from packages.retrieval.splade_retriever import SPLADERetriever, HybridRetriever


class StrategyComparator:
    """
    Compare multiple retrieval strategies on a golden dataset.
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        enhanced_retriever: EnhancedRetriever,
        splade_retriever: SPLADERetriever,
        hybrid_retriever: HybridRetriever
    ):
        """
        Initialize strategy comparator.

        Args:
            bm25_retriever: BM25 retriever
            enhanced_retriever: Enhanced retriever
            splade_retriever: SPLADE retriever
            hybrid_retriever: Hybrid retriever
        """
        self.retrievers = {
            "bm25": bm25_retriever,
            "enhanced": enhanced_retriever,
            "splade": splade_retriever,
            "hybrid": hybrid_retriever
        }

    def compare_strategies(
        self,
        golden_dataset: GoldenDataset,
        top_k: int = 10,
        strategies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare retrieval strategies on golden dataset.

        Args:
            golden_dataset: Golden dataset for evaluation
            top_k: Number of results to retrieve
            strategies: List of strategies to compare (default: all)

        Returns:
            Comparison results
        """
        if strategies is None:
            strategies = list(self.retrievers.keys())

        results = {}

        for strategy_name in strategies:
            if strategy_name not in self.retrievers:
                continue

            retriever = self.retrievers[strategy_name]

            # Run evaluation
            start_time = time.time()
            evaluator = RetrievalEvaluator(retriever, golden_dataset)
            _, aggregate_metrics = evaluator.evaluate_all(top_k=top_k)
            elapsed_time = time.time() - start_time

            # Convert aggregate metrics to dict
            metrics = {
                "map": aggregate_metrics.mean_average_precision,
                "mrr": aggregate_metrics.mean_reciprocal_rank,
                "ndcg@5": aggregate_metrics.mean_ndcg_at_5,
                "ndcg@10": aggregate_metrics.mean_ndcg_at_10,
                "precision@5": aggregate_metrics.mean_precision_at_5,
                "recall@5": aggregate_metrics.mean_recall_at_5,
            }

            results[strategy_name] = {
                "metrics": metrics,
                "elapsed_time": elapsed_time,
                "queries_per_second": len(golden_dataset.queries) / elapsed_time if elapsed_time > 0 else 0
            }

        return results

    def generate_comparison_report(
        self,
        comparison_results: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate comparison report in markdown format.

        Args:
            comparison_results: Results from compare_strategies
            output_path: Optional path to save report

        Returns:
            Markdown report
        """
        report_lines = [
            "# Retrieval Strategy Comparison Report",
            "",
            f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Overview",
            "",
            f"Compared {len(comparison_results)} retrieval strategies.",
            ""
        ]

        # Metrics comparison table
        report_lines.extend([
            "## Metrics Comparison",
            "",
            "| Strategy | MAP | MRR | NDCG@5 | NDCG@10 | P@5 | R@5 | QPS |",
            "|----------|-----|-----|--------|---------|-----|-----|-----|"
        ])

        for strategy_name, result in comparison_results.items():
            metrics = result["metrics"]
            qps = result["queries_per_second"]

            row = (
                f"| {strategy_name} "
                f"| {metrics.get('map', 0):.4f} "
                f"| {metrics.get('mrr', 0):.4f} "
                f"| {metrics.get('ndcg@5', 0):.4f} "
                f"| {metrics.get('ndcg@10', 0):.4f} "
                f"| {metrics.get('precision@5', 0):.4f} "
                f"| {metrics.get('recall@5', 0):.4f} "
                f"| {qps:.2f} |"
            )
            report_lines.append(row)

        report_lines.extend(["", ""])

        # Performance comparison
        report_lines.extend([
            "## Performance Analysis",
            ""
        ])

        # Find best strategy for each metric
        metrics_to_compare = ["map", "mrr", "ndcg@5", "ndcg@10", "precision@5", "recall@5"]

        for metric in metrics_to_compare:
            best_strategy = max(
                comparison_results.items(),
                key=lambda x: x[1]["metrics"].get(metric, 0)
            )
            best_value = best_strategy[1]["metrics"].get(metric, 0)

            report_lines.append(
                f"- **Best {metric.upper()}**: {best_strategy[0]} ({best_value:.4f})"
            )

        # Speed comparison
        fastest_strategy = min(
            comparison_results.items(),
            key=lambda x: x[1]["elapsed_time"]
        )
        report_lines.append(
            f"- **Fastest**: {fastest_strategy[0]} "
            f"({fastest_strategy[1]['elapsed_time']:.2f}s, "
            f"{fastest_strategy[1]['queries_per_second']:.2f} QPS)"
        )

        report_lines.extend(["", ""])

        # Detailed results per strategy
        report_lines.extend([
            "## Detailed Results",
            ""
        ])

        for strategy_name, result in comparison_results.items():
            report_lines.extend([
                f"### {strategy_name.upper()}",
                "",
                f"**Execution Time**: {result['elapsed_time']:.2f}s",
                f"**Queries Per Second**: {result['queries_per_second']:.2f}",
                "",
                "**Metrics**:",
                ""
            ])

            metrics = result["metrics"]
            for metric_name, metric_value in sorted(metrics.items()):
                if not metric_name.startswith("per_query"):
                    report_lines.append(f"- {metric_name}: {metric_value:.4f}")

            report_lines.extend(["", ""])

        # Recommendations
        report_lines.extend([
            "## Recommendations",
            ""
        ])

        # Find overall best strategy (weighted average)
        weighted_scores = {}
        for strategy_name, result in comparison_results.items():
            metrics = result["metrics"]
            # Weight: MAP (30%), MRR (20%), NDCG@5 (20%), NDCG@10 (15%), P@5 (10%), R@5 (5%)
            score = (
                metrics.get("map", 0) * 0.30 +
                metrics.get("mrr", 0) * 0.20 +
                metrics.get("ndcg@5", 0) * 0.20 +
                metrics.get("ndcg@10", 0) * 0.15 +
                metrics.get("precision@5", 0) * 0.10 +
                metrics.get("recall@5", 0) * 0.05
            )
            weighted_scores[strategy_name] = score

        best_overall = max(weighted_scores.items(), key=lambda x: x[1])

        report_lines.extend([
            f"**Best Overall Strategy**: {best_overall[0]} (weighted score: {best_overall[1]:.4f})",
            "",
            "**Use Cases**:",
            "",
            "- **BM25**: Fast, simple, good baseline",
            "- **Enhanced**: Better quality with query expansion and reranking",
            "- **SPLADE**: Semantic understanding with sparse representations",
            "- **Hybrid**: Best of both worlds, combining BM25 and SPLADE",
            ""
        ])

        report = "\n".join(report_lines)

        # Save to file if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

        return report

    def compare_on_query_categories(
        self,
        golden_dataset: GoldenDataset,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Compare strategies on different query categories.

        Args:
            golden_dataset: Golden dataset with categorized queries
            top_k: Number of results to retrieve

        Returns:
            Category-wise comparison results
        """
        # Group queries by category (using description as category if available)
        categories = {}
        for query in golden_dataset.queries:
            # Use first word of description as category
            category = query.description.split()[0].lower() if query.description else "general"
            if category not in categories:
                categories[category] = []
            categories[category].append(query)

        # Compare strategies on each category
        category_results = {}

        for category, queries in categories.items():
            # Create temporary dataset for this category
            category_dataset = GoldenDataset(queries=queries)

            # Compare strategies
            comparison = self.compare_strategies(
                category_dataset,
                top_k=top_k
            )

            category_results[category] = comparison

        return category_results

    def generate_category_report(
        self,
        category_results: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate category-wise comparison report.

        Args:
            category_results: Results from compare_on_query_categories
            output_path: Optional path to save report

        Returns:
            Markdown report
        """
        report_lines = [
            "# Category-wise Retrieval Comparison",
            "",
            f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        for category, results in category_results.items():
            report_lines.extend([
                f"## Category: {category.upper()}",
                "",
                "| Strategy | MAP | MRR | NDCG@5 | P@5 | R@5 |",
                "|----------|-----|-----|--------|-----|-----|"
            ])

            for strategy_name, result in results.items():
                metrics = result["metrics"]
                row = (
                    f"| {strategy_name} "
                    f"| {metrics.get('map', 0):.4f} "
                    f"| {metrics.get('mrr', 0):.4f} "
                    f"| {metrics.get('ndcg@5', 0):.4f} "
                    f"| {metrics.get('precision@5', 0):.4f} "
                    f"| {metrics.get('recall@5', 0):.4f} |"
                )
                report_lines.append(row)

            # Find best strategy for this category
            best_strategy = max(
                results.items(),
                key=lambda x: x[1]["metrics"].get("map", 0)
            )

            report_lines.extend([
                "",
                f"**Best for {category}**: {best_strategy[0]} "
                f"(MAP: {best_strategy[1]['metrics'].get('map', 0):.4f})",
                "",
                ""
            ])

        report = "\n".join(report_lines)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

        return report

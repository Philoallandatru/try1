"""
Retrieval API for Portal Runner.

Provides search and index management functionality.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from packages.retrieval.bm25_retriever import BM25Retriever
from packages.retrieval.index_manager import IndexManager
from packages.retrieval.golden_dataset import load_golden_dataset
from packages.retrieval.evaluator import RetrievalEvaluator


class RetrievalAPI:
    """
    API layer for retrieval and search functionality.
    """

    def __init__(self, workspace_dir: str | Path):
        """
        Initialize Retrieval API.

        Args:
            workspace_dir: Path to workspace directory
        """
        self.workspace_dir = Path(workspace_dir)

        # Database path
        db_path = self.workspace_dir / "documents.db"

        # Index directory
        index_dir = self.workspace_dir / ".index"

        # Initialize index manager
        self.index_manager = IndexManager(
            db_path=str(db_path),
            index_dir=str(index_dir),
        )

        # Load index if exists
        self.index_manager.load_index()

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        """
        Execute search query.

        Args:
            query: Search query text
            top_k: Number of results to return
            min_score: Minimum relevance score

        Returns:
            Search results with metadata
        """
        # Check if index exists
        if self.index_manager.index.bm25 is None:
            return {
                "status": "error",
                "error": "Index not built. Please build index first.",
                "results": [],
            }

        # Create retriever
        retriever = BM25Retriever(self.index_manager.index)

        # Execute search
        results = retriever.search(query, top_k=top_k)

        # Filter by min_score
        filtered_results = [r for r in results if r.score >= min_score]

        # Get document details from database
        result_list = []
        for result in filtered_results:
            doc = self.index_manager.db.get_document(result.doc_id)
            if doc:
                result_list.append({
                    "doc_id": result.doc_id,
                    "score": result.score,
                    "rank": result.rank,
                    "title": doc.title,
                    "content": doc.content[:500],  # First 500 chars
                    "source_id": doc.source_id,
                    "source_type": doc.source_type,
                    "url": doc.url,
                    "metadata": doc.metadata,
                })

        return {
            "status": "success",
            "query": query,
            "total_results": len(result_list),
            "results": result_list,
        }

    def get_index_stats(self) -> dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Index statistics
        """
        stats = self.index_manager.get_stats()

        return {
            "status": "success",
            "stats": stats,
        }

    def build_index(self, batch_size: int = 1000) -> dict[str, Any]:
        """
        Build full index from database.

        Args:
            batch_size: Batch size for processing

        Returns:
            Build result
        """
        try:
            result = self.index_manager.build_full_index(batch_size=batch_size)
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def update_index(self) -> dict[str, Any]:
        """
        Update index incrementally.

        Returns:
            Update result
        """
        try:
            result = self.index_manager.update_index_incremental()
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def rebuild_index(self) -> dict[str, Any]:
        """
        Rebuild index from scratch.

        Returns:
            Rebuild result
        """
        try:
            result = self.index_manager.rebuild_index()
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def health_check(self) -> dict[str, Any]:
        """
        Check index health.

        Returns:
            Health check result
        """
        health = self.index_manager.health_check()

        return {
            "status": "success",
            "health": health,
        }

    def evaluate(
        self,
        golden_dataset_path: str = "data/golden_dataset.yaml",
        top_k: int = 10,
    ) -> dict[str, Any]:
        """
        Run evaluation on golden dataset.

        Args:
            golden_dataset_path: Path to golden dataset
            top_k: Number of results to retrieve

        Returns:
            Evaluation results
        """
        try:
            # Load golden dataset
            golden_dataset = load_golden_dataset(golden_dataset_path)

            # Create retriever
            retriever = BM25Retriever(self.index_manager.index)

            # Create evaluator
            evaluator = RetrievalEvaluator(retriever, golden_dataset)

            # Run evaluation
            results, aggregate = evaluator.evaluate_all(top_k=top_k)

            # Format results
            return {
                "status": "success",
                "aggregate_metrics": {
                    "total_queries": aggregate.total_queries,
                    "mean_average_precision": aggregate.mean_average_precision,
                    "mean_reciprocal_rank": aggregate.mean_reciprocal_rank,
                    "mean_ndcg_at_5": aggregate.mean_ndcg_at_5,
                    "mean_ndcg_at_10": aggregate.mean_ndcg_at_10,
                    "mean_precision_at_1": aggregate.mean_precision_at_1,
                    "mean_precision_at_3": aggregate.mean_precision_at_3,
                    "mean_precision_at_5": aggregate.mean_precision_at_5,
                    "mean_precision_at_10": aggregate.mean_precision_at_10,
                    "mean_recall_at_1": aggregate.mean_recall_at_1,
                    "mean_recall_at_3": aggregate.mean_recall_at_3,
                    "mean_recall_at_5": aggregate.mean_recall_at_5,
                    "mean_recall_at_10": aggregate.mean_recall_at_10,
                },
                "per_query_results": [
                    {
                        "query_id": r.query_id,
                        "query_text": r.query_text,
                        "average_precision": r.average_precision,
                        "reciprocal_rank": r.reciprocal_rank,
                        "ndcg_at_5": r.ndcg_at_5,
                        "precision_at_5": r.precision_at_5,
                        "recall_at_5": r.recall_at_5,
                    }
                    for r in results
                ],
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

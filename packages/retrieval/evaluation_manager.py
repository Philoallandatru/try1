"""
Evaluation Manager for managing evaluation datasets and results.

Handles storage, retrieval, and comparison of evaluation runs.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from packages.retrieval.evaluator import AggregateMetrics, EvaluationResult
from packages.retrieval.golden_dataset import GoldenDataset


@dataclass
class EvaluationRun:
    """Represents a single evaluation run."""

    run_id: str
    dataset_id: str
    dataset_name: str
    timestamp: str
    top_k: int
    total_queries: int
    aggregate_metrics: dict[str, float]
    per_query_results: list[dict[str, Any]]
    config: dict[str, Any] | None = None


@dataclass
class DatasetInfo:
    """Information about a golden dataset."""

    dataset_id: str
    name: str
    description: str
    version: int
    created_at: str
    updated_at: str
    total_queries: int
    total_documents: int
    categories: dict[str, int]
    file_path: str


class EvaluationManager:
    """
    Manages evaluation datasets and results.

    Directory structure:
    .local/retrieval/
        datasets/
            dataset_id_1.yaml
            dataset_id_2.yaml
        results/
            run_id_1.json
            run_id_2.json
    """

    def __init__(self, storage_dir: str | Path):
        """
        Initialize Evaluation Manager.

        Args:
            storage_dir: Base directory for storing datasets and results
        """
        self.storage_dir = Path(storage_dir)
        self.datasets_dir = self.storage_dir / "datasets"
        self.results_dir = self.storage_dir / "results"

        # Create directories
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    # ==================== Dataset Management ====================

    def upload_dataset(
        self,
        dataset_content: str,
        dataset_id: str | None = None,
    ) -> DatasetInfo:
        """
        Upload a golden dataset.

        Args:
            dataset_content: YAML content of the dataset
            dataset_id: Optional dataset ID (generated if not provided)

        Returns:
            Dataset information

        Raises:
            ValueError: If dataset is invalid
        """
        # Parse YAML
        try:
            data = yaml.safe_load(dataset_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")

        # Validate required fields
        if "queries" not in data:
            raise ValueError("Dataset must contain 'queries' field")

        # Generate dataset ID if not provided
        if dataset_id is None:
            dataset_id = self._generate_dataset_id(data.get("name", "dataset"))

        # Add metadata
        now = datetime.utcnow().isoformat()
        if "created_at" not in data:
            data["created_at"] = now
        data["updated_at"] = now

        # Save to file
        file_path = self.datasets_dir / f"{dataset_id}.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        # Create dataset info
        return self._create_dataset_info(dataset_id, data, str(file_path))

    def list_datasets(self) -> list[DatasetInfo]:
        """
        List all available datasets.

        Returns:
            List of dataset information
        """
        datasets = []
        for file_path in self.datasets_dir.glob("*.yaml"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                dataset_id = file_path.stem
                datasets.append(self._create_dataset_info(dataset_id, data, str(file_path)))
            except Exception:
                # Skip invalid files
                continue

        # Sort by updated_at descending
        datasets.sort(key=lambda d: d.updated_at, reverse=True)
        return datasets

    def get_dataset(self, dataset_id: str) -> DatasetInfo:
        """
        Get dataset information.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset information

        Raises:
            FileNotFoundError: If dataset not found
        """
        file_path = self.datasets_dir / f"{dataset_id}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_id}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return self._create_dataset_info(dataset_id, data, str(file_path))

    def get_dataset_content(self, dataset_id: str) -> str:
        """
        Get dataset YAML content.

        Args:
            dataset_id: Dataset ID

        Returns:
            YAML content

        Raises:
            FileNotFoundError: If dataset not found
        """
        file_path = self.datasets_dir / f"{dataset_id}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_id}")

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def delete_dataset(self, dataset_id: str) -> None:
        """
        Delete a dataset.

        Args:
            dataset_id: Dataset ID

        Raises:
            FileNotFoundError: If dataset not found
        """
        file_path = self.datasets_dir / f"{dataset_id}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_id}")

        file_path.unlink()

    # ==================== Evaluation Results Management ====================

    def save_evaluation_result(
        self,
        dataset_id: str,
        dataset_name: str,
        top_k: int,
        aggregate_metrics: AggregateMetrics,
        per_query_results: list[EvaluationResult],
        config: dict[str, Any] | None = None,
    ) -> EvaluationRun:
        """
        Save evaluation result.

        Args:
            dataset_id: Dataset ID
            dataset_name: Dataset name
            top_k: Top K parameter
            aggregate_metrics: Aggregate metrics
            per_query_results: Per-query results
            config: Optional configuration

        Returns:
            Evaluation run information
        """
        # Generate run ID
        run_id = self._generate_run_id()

        # Create evaluation run
        run = EvaluationRun(
            run_id=run_id,
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            timestamp=datetime.utcnow().isoformat(),
            top_k=top_k,
            total_queries=aggregate_metrics.total_queries,
            aggregate_metrics={
                "mean_average_precision": aggregate_metrics.mean_average_precision,
                "mean_reciprocal_rank": aggregate_metrics.mean_reciprocal_rank,
                "mean_ndcg_at_5": aggregate_metrics.mean_ndcg_at_5,
                "mean_ndcg_at_10": aggregate_metrics.mean_ndcg_at_10,
                "mean_precision_at_1": aggregate_metrics.mean_precision_at_1,
                "mean_precision_at_3": aggregate_metrics.mean_precision_at_3,
                "mean_precision_at_5": aggregate_metrics.mean_precision_at_5,
                "mean_precision_at_10": aggregate_metrics.mean_precision_at_10,
                "mean_recall_at_1": aggregate_metrics.mean_recall_at_1,
                "mean_recall_at_3": aggregate_metrics.mean_recall_at_3,
                "mean_recall_at_5": aggregate_metrics.mean_recall_at_5,
                "mean_recall_at_10": aggregate_metrics.mean_recall_at_10,
            },
            per_query_results=[
                {
                    "query_id": r.query_id,
                    "query_text": r.query_text,
                    "average_precision": r.average_precision,
                    "reciprocal_rank": r.reciprocal_rank,
                    "ndcg_at_5": r.ndcg_at_5,
                    "ndcg_at_10": r.ndcg_at_10,
                    "precision_at_1": r.precision_at_1,
                    "precision_at_3": r.precision_at_3,
                    "precision_at_5": r.precision_at_5,
                    "precision_at_10": r.precision_at_10,
                    "recall_at_1": r.recall_at_1,
                    "recall_at_3": r.recall_at_3,
                    "recall_at_5": r.recall_at_5,
                    "recall_at_10": r.recall_at_10,
                    "retrieved_docs": r.retrieved_docs,
                    "relevant_docs": r.relevant_docs,
                }
                for r in per_query_results
            ],
            config=config,
        )

        # Save to file
        file_path = self.results_dir / f"{run_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(run), f, indent=2, ensure_ascii=False)

        return run

    def list_evaluation_results(
        self,
        dataset_id: str | None = None,
        limit: int | None = None,
    ) -> list[EvaluationRun]:
        """
        List evaluation results.

        Args:
            dataset_id: Optional filter by dataset ID
            limit: Optional limit number of results

        Returns:
            List of evaluation runs
        """
        results = []
        for file_path in self.results_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                run = EvaluationRun(**data)

                # Filter by dataset_id if provided
                if dataset_id and run.dataset_id != dataset_id:
                    continue

                results.append(run)
            except Exception:
                # Skip invalid files
                continue

        # Sort by timestamp descending
        results.sort(key=lambda r: r.timestamp, reverse=True)

        # Apply limit
        if limit:
            results = results[:limit]

        return results

    def get_evaluation_result(self, run_id: str) -> EvaluationRun:
        """
        Get evaluation result.

        Args:
            run_id: Run ID

        Returns:
            Evaluation run

        Raises:
            FileNotFoundError: If result not found
        """
        file_path = self.results_dir / f"{run_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Evaluation result not found: {run_id}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return EvaluationRun(**data)

    def delete_evaluation_result(self, run_id: str) -> None:
        """
        Delete evaluation result.

        Args:
            run_id: Run ID

        Raises:
            FileNotFoundError: If result not found
        """
        file_path = self.results_dir / f"{run_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Evaluation result not found: {run_id}")

        file_path.unlink()

    def compare_evaluation_results(
        self,
        run_ids: list[str],
    ) -> dict[str, Any]:
        """
        Compare multiple evaluation results.

        Args:
            run_ids: List of run IDs to compare

        Returns:
            Comparison data

        Raises:
            FileNotFoundError: If any result not found
        """
        runs = [self.get_evaluation_result(run_id) for run_id in run_ids]

        # Extract metrics for comparison
        comparison = {
            "runs": [
                {
                    "run_id": run.run_id,
                    "dataset_name": run.dataset_name,
                    "timestamp": run.timestamp,
                    "top_k": run.top_k,
                    "metrics": run.aggregate_metrics,
                }
                for run in runs
            ],
            "metric_names": list(runs[0].aggregate_metrics.keys()) if runs else [],
        }

        return comparison

    # ==================== Helper Methods ====================

    def _generate_dataset_id(self, name: str) -> str:
        """Generate unique dataset ID."""
        base_id = name.lower().replace(" ", "_")
        counter = 1
        dataset_id = base_id

        while (self.datasets_dir / f"{dataset_id}.yaml").exists():
            dataset_id = f"{base_id}_{counter}"
            counter += 1

        return dataset_id

    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        counter = 1
        run_id = f"eval_{timestamp}"

        while (self.results_dir / f"{run_id}.json").exists():
            run_id = f"eval_{timestamp}_{counter}"
            counter += 1

        return run_id

    def _create_dataset_info(
        self,
        dataset_id: str,
        data: dict[str, Any],
        file_path: str,
    ) -> DatasetInfo:
        """Create DatasetInfo from dataset data."""
        queries = data.get("queries", [])
        documents = data.get("documents", [])

        # Count categories
        categories: dict[str, int] = {}
        for query in queries:
            category = query.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1

        return DatasetInfo(
            dataset_id=dataset_id,
            name=data.get("name", dataset_id),
            description=data.get("description", ""),
            version=data.get("version", 1),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            total_queries=len(queries),
            total_documents=len(documents),
            categories=categories,
            file_path=file_path,
        )

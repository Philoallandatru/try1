"""
Golden Dataset loader for retrieval evaluation.

Loads and validates the golden dataset used for evaluating retrieval quality.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import yaml


class ExpectedDocument:
    """Expected document for a query."""

    def __init__(self, doc_id: str, relevance: float, reason: str):
        """
        Initialize expected document.

        Args:
            doc_id: Document ID
            relevance: Relevance score (0.0 - 1.0)
            reason: Why this document is relevant
        """
        self.doc_id = doc_id
        self.relevance = relevance
        self.reason = reason

    def __repr__(self) -> str:
        return f"ExpectedDocument(doc_id={self.doc_id}, relevance={self.relevance})"


class GoldenQuery:
    """A query in the golden dataset."""

    def __init__(
        self,
        id: str,
        query: str,
        description: str,
        expected_docs: List[ExpectedDocument],
    ):
        """
        Initialize golden query.

        Args:
            id: Query ID
            query: Query text
            description: What the user is looking for
            expected_docs: List of expected relevant documents
        """
        self.id = id
        self.query = query
        self.description = description
        self.expected_docs = expected_docs

    def get_relevant_doc_ids(self, min_relevance: float = 0.5) -> List[str]:
        """
        Get IDs of relevant documents.

        Args:
            min_relevance: Minimum relevance score to consider

        Returns:
            List of document IDs
        """
        return [
            doc.doc_id
            for doc in self.expected_docs
            if doc.relevance >= min_relevance
        ]

    def get_relevance_score(self, doc_id: str) -> float:
        """
        Get relevance score for a document.

        Args:
            doc_id: Document ID

        Returns:
            Relevance score (0.0 if not found)
        """
        for doc in self.expected_docs:
            if doc.doc_id == doc_id:
                return doc.relevance
        return 0.0

    def __repr__(self) -> str:
        return f"GoldenQuery(id={self.id}, query='{self.query}', expected_docs={len(self.expected_docs)})"


class GoldenDataset:
    """Golden dataset for retrieval evaluation."""

    def __init__(self, queries: List[GoldenQuery], metadata: Optional[dict] = None):
        """
        Initialize golden dataset.

        Args:
            queries: List of golden queries
            metadata: Dataset metadata
        """
        self.queries = queries
        self.metadata = metadata or {}

    def get_query(self, query_id: str) -> Optional[GoldenQuery]:
        """
        Get query by ID.

        Args:
            query_id: Query ID

        Returns:
            GoldenQuery or None
        """
        for query in self.queries:
            if query.id == query_id:
                return query
        return None

    def get_queries_by_language(self, language: str) -> List[GoldenQuery]:
        """
        Get queries by language.

        Args:
            language: Language code (e.g., "en", "zh")

        Returns:
            List of queries
        """
        # Simple heuristic: check if query contains Chinese characters
        if language == "zh":
            return [q for q in self.queries if any('\u4e00' <= c <= '\u9fff' for c in q.query)]
        elif language == "en":
            return [q for q in self.queries if not any('\u4e00' <= c <= '\u9fff' for c in q.query)]
        else:
            return self.queries

    def __len__(self) -> int:
        return len(self.queries)

    def __repr__(self) -> str:
        return f"GoldenDataset(queries={len(self.queries)})"


def load_golden_dataset(path: str = "data/golden_dataset.yaml") -> GoldenDataset:
    """
    Load golden dataset from YAML file.

    Args:
        path: Path to golden dataset file

    Returns:
        GoldenDataset instance
    """
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Golden dataset not found: {path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Parse queries
    queries = []
    for query_data in data.get("queries", []):
        expected_docs = [
            ExpectedDocument(
                doc_id=doc["doc_id"],
                relevance=doc["relevance"],
                reason=doc["reason"],
            )
            for doc in query_data.get("expected_docs", [])
        ]

        query = GoldenQuery(
            id=query_data["id"],
            query=query_data["query"],
            description=query_data["description"],
            expected_docs=expected_docs,
        )
        queries.append(query)

    metadata = data.get("metadata", {})

    return GoldenDataset(queries=queries, metadata=metadata)


def validate_golden_dataset(dataset: GoldenDataset) -> dict:
    """
    Validate golden dataset.

    Args:
        dataset: GoldenDataset to validate

    Returns:
        Validation results
    """
    issues = []

    # Check if dataset is empty
    if len(dataset) == 0:
        issues.append("Dataset is empty")

    # Check each query
    for query in dataset.queries:
        # Check if query has expected documents
        if len(query.expected_docs) == 0:
            issues.append(f"Query {query.id} has no expected documents")

        # Check relevance scores
        for doc in query.expected_docs:
            if not 0.0 <= doc.relevance <= 1.0:
                issues.append(
                    f"Query {query.id}, doc {doc.doc_id}: "
                    f"relevance {doc.relevance} out of range [0.0, 1.0]"
                )

    return {
        "valid": len(issues) == 0,
        "total_queries": len(dataset),
        "total_expected_docs": sum(len(q.expected_docs) for q in dataset.queries),
        "issues": issues,
    }

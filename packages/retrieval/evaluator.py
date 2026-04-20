"""
Evaluation framework for retrieval system.

Implements standard IR metrics:
- Precision@K
- Recall@K
- Mean Average Precision (MAP)
- Normalized Discounted Cumulative Gain (NDCG)
- Mean Reciprocal Rank (MRR)
"""

from __future__ import annotations

import math
from typing import List, Dict, Tuple
from dataclasses import dataclass

from packages.retrieval.golden_dataset import GoldenDataset, GoldenQuery
from packages.retrieval.bm25_retriever import BM25Retriever, SearchResult


@dataclass
class EvaluationResult:
    """Results from evaluating a single query."""

    query_id: str
    query_text: str
    precision_at_1: float
    precision_at_3: float
    precision_at_5: float
    precision_at_10: float
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    recall_at_10: float
    average_precision: float
    ndcg_at_5: float
    ndcg_at_10: float
    reciprocal_rank: float
    retrieved_docs: List[str]
    relevant_docs: List[str]


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all queries."""

    total_queries: int
    mean_precision_at_1: float
    mean_precision_at_3: float
    mean_precision_at_5: float
    mean_precision_at_10: float
    mean_recall_at_1: float
    mean_recall_at_3: float
    mean_recall_at_5: float
    mean_recall_at_10: float
    mean_average_precision: float
    mean_ndcg_at_5: float
    mean_ndcg_at_10: float
    mean_reciprocal_rank: float


class RetrievalEvaluator:
    """Evaluates retrieval quality using golden dataset."""

    def __init__(self, retriever: BM25Retriever, golden_dataset: GoldenDataset):
        """
        Initialize evaluator.

        Args:
            retriever: BM25Retriever instance
            golden_dataset: Golden dataset for evaluation
        """
        self.retriever = retriever
        self.golden_dataset = golden_dataset

    def precision_at_k(
        self, retrieved: List[str], relevant: List[str], k: int
    ) -> float:
        """
        Calculate Precision@K.

        Precision@K = (# relevant docs in top K) / K

        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs
            k: Cutoff position

        Returns:
            Precision@K score
        """
        if k == 0 or len(retrieved) == 0:
            return 0.0

        top_k = retrieved[:k]
        relevant_set = set(relevant)
        relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant_set)

        return relevant_in_top_k / k

    def recall_at_k(
        self, retrieved: List[str], relevant: List[str], k: int
    ) -> float:
        """
        Calculate Recall@K.

        Recall@K = (# relevant docs in top K) / (total # relevant docs)

        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs
            k: Cutoff position

        Returns:
            Recall@K score
        """
        if len(relevant) == 0:
            return 0.0

        top_k = retrieved[:k]
        relevant_set = set(relevant)
        relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant_set)

        return relevant_in_top_k / len(relevant)

    def average_precision(self, retrieved: List[str], relevant: List[str]) -> float:
        """
        Calculate Average Precision.

        AP = (sum of P@k for each relevant doc) / (total # relevant docs)

        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs

        Returns:
            Average Precision score
        """
        if len(relevant) == 0:
            return 0.0

        relevant_set = set(relevant)
        precision_sum = 0.0
        relevant_count = 0

        for i, doc_id in enumerate(retrieved):
            if doc_id in relevant_set:
                relevant_count += 1
                precision_at_i = relevant_count / (i + 1)
                precision_sum += precision_at_i

        return precision_sum / len(relevant)

    def dcg_at_k(
        self, retrieved: List[str], relevance_scores: Dict[str, float], k: int
    ) -> float:
        """
        Calculate Discounted Cumulative Gain at K.

        DCG@K = sum(rel_i / log2(i + 1)) for i in [1, k]

        Args:
            retrieved: List of retrieved document IDs
            relevance_scores: Dict mapping doc_id to relevance score
            k: Cutoff position

        Returns:
            DCG@K score
        """
        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k]):
            relevance = relevance_scores.get(doc_id, 0.0)
            dcg += relevance / math.log2(i + 2)  # i+2 because i starts at 0

        return dcg

    def ndcg_at_k(
        self, retrieved: List[str], relevance_scores: Dict[str, float], k: int
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain at K.

        NDCG@K = DCG@K / IDCG@K

        Args:
            retrieved: List of retrieved document IDs
            relevance_scores: Dict mapping doc_id to relevance score
            k: Cutoff position

        Returns:
            NDCG@K score
        """
        # Calculate DCG
        dcg = self.dcg_at_k(retrieved, relevance_scores, k)

        # Calculate IDCG (ideal DCG with perfect ranking)
        ideal_ranking = sorted(
            relevance_scores.items(), key=lambda x: x[1], reverse=True
        )
        ideal_doc_ids = [doc_id for doc_id, _ in ideal_ranking]
        idcg = self.dcg_at_k(ideal_doc_ids, relevance_scores, k)

        if idcg == 0.0:
            return 0.0

        return dcg / idcg

    def reciprocal_rank(self, retrieved: List[str], relevant: List[str]) -> float:
        """
        Calculate Reciprocal Rank.

        RR = 1 / (rank of first relevant document)

        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs

        Returns:
            Reciprocal Rank score
        """
        relevant_set = set(relevant)

        for i, doc_id in enumerate(retrieved):
            if doc_id in relevant_set:
                return 1.0 / (i + 1)

        return 0.0

    def evaluate_query(
        self, query: GoldenQuery, top_k: int = 10
    ) -> EvaluationResult:
        """
        Evaluate retrieval for a single query.

        Args:
            query: Golden query to evaluate
            top_k: Number of results to retrieve

        Returns:
            EvaluationResult
        """
        # Retrieve documents
        results = self.retriever.search(query.query, top_k=top_k)
        retrieved_ids = [result.doc_id for result in results]

        # Get relevant documents
        relevant_ids = query.get_relevant_doc_ids(min_relevance=0.5)

        # Build relevance scores dict
        relevance_scores = {
            doc.doc_id: doc.relevance for doc in query.expected_docs
        }

        # Calculate metrics
        return EvaluationResult(
            query_id=query.id,
            query_text=query.query,
            precision_at_1=self.precision_at_k(retrieved_ids, relevant_ids, 1),
            precision_at_3=self.precision_at_k(retrieved_ids, relevant_ids, 3),
            precision_at_5=self.precision_at_k(retrieved_ids, relevant_ids, 5),
            precision_at_10=self.precision_at_k(retrieved_ids, relevant_ids, 10),
            recall_at_1=self.recall_at_k(retrieved_ids, relevant_ids, 1),
            recall_at_3=self.recall_at_k(retrieved_ids, relevant_ids, 3),
            recall_at_5=self.recall_at_k(retrieved_ids, relevant_ids, 5),
            recall_at_10=self.recall_at_k(retrieved_ids, relevant_ids, 10),
            average_precision=self.average_precision(retrieved_ids, relevant_ids),
            ndcg_at_5=self.ndcg_at_k(retrieved_ids, relevance_scores, 5),
            ndcg_at_10=self.ndcg_at_k(retrieved_ids, relevance_scores, 10),
            reciprocal_rank=self.reciprocal_rank(retrieved_ids, relevant_ids),
            retrieved_docs=retrieved_ids,
            relevant_docs=relevant_ids,
        )

    def evaluate_all(self, top_k: int = 10) -> Tuple[List[EvaluationResult], AggregateMetrics]:
        """
        Evaluate all queries in golden dataset.

        Args:
            top_k: Number of results to retrieve per query

        Returns:
            Tuple of (individual results, aggregate metrics)
        """
        results = []

        for query in self.golden_dataset.queries:
            result = self.evaluate_query(query, top_k=top_k)
            results.append(result)

        # Calculate aggregate metrics
        n = len(results)
        aggregate = AggregateMetrics(
            total_queries=n,
            mean_precision_at_1=sum(r.precision_at_1 for r in results) / n,
            mean_precision_at_3=sum(r.precision_at_3 for r in results) / n,
            mean_precision_at_5=sum(r.precision_at_5 for r in results) / n,
            mean_precision_at_10=sum(r.precision_at_10 for r in results) / n,
            mean_recall_at_1=sum(r.recall_at_1 for r in results) / n,
            mean_recall_at_3=sum(r.recall_at_3 for r in results) / n,
            mean_recall_at_5=sum(r.recall_at_5 for r in results) / n,
            mean_recall_at_10=sum(r.recall_at_10 for r in results) / n,
            mean_average_precision=sum(r.average_precision for r in results) / n,
            mean_ndcg_at_5=sum(r.ndcg_at_5 for r in results) / n,
            mean_ndcg_at_10=sum(r.ndcg_at_10 for r in results) / n,
            mean_reciprocal_rank=sum(r.reciprocal_rank for r in results) / n,
        )

        return results, aggregate

    def print_report(self, results: List[EvaluationResult], aggregate: AggregateMetrics):
        """
        Print evaluation report.

        Args:
            results: Individual query results
            aggregate: Aggregate metrics
        """
        print("\n" + "="*70)
        print("RETRIEVAL EVALUATION REPORT")
        print("="*70)

        print(f"\nTotal Queries: {aggregate.total_queries}")

        print("\n--- Aggregate Metrics ---")
        print(f"Mean Average Precision (MAP): {aggregate.mean_average_precision:.4f}")
        print(f"Mean Reciprocal Rank (MRR):  {aggregate.mean_reciprocal_rank:.4f}")
        print(f"Mean NDCG@5:                  {aggregate.mean_ndcg_at_5:.4f}")
        print(f"Mean NDCG@10:                 {aggregate.mean_ndcg_at_10:.4f}")

        print("\n--- Precision@K ---")
        print(f"P@1:  {aggregate.mean_precision_at_1:.4f}")
        print(f"P@3:  {aggregate.mean_precision_at_3:.4f}")
        print(f"P@5:  {aggregate.mean_precision_at_5:.4f}")
        print(f"P@10: {aggregate.mean_precision_at_10:.4f}")

        print("\n--- Recall@K ---")
        print(f"R@1:  {aggregate.mean_recall_at_1:.4f}")
        print(f"R@3:  {aggregate.mean_recall_at_3:.4f}")
        print(f"R@5:  {aggregate.mean_recall_at_5:.4f}")
        print(f"R@10: {aggregate.mean_recall_at_10:.4f}")

        print("\n--- Per-Query Results (Top 5 by MAP) ---")
        sorted_results = sorted(results, key=lambda r: r.average_precision, reverse=True)
        for i, result in enumerate(sorted_results[:5]):
            print(f"\n{i+1}. Query: {result.query_text}")
            print(f"   MAP: {result.average_precision:.4f}, "
                  f"NDCG@5: {result.ndcg_at_5:.4f}, "
                  f"MRR: {result.reciprocal_rank:.4f}")
            print(f"   Retrieved: {result.retrieved_docs[:3]}")
            print(f"   Relevant:  {result.relevant_docs}")

        print("\n--- Per-Query Results (Bottom 5 by MAP) ---")
        for i, result in enumerate(sorted_results[-5:]):
            print(f"\n{i+1}. Query: {result.query_text}")
            print(f"   MAP: {result.average_precision:.4f}, "
                  f"NDCG@5: {result.ndcg_at_5:.4f}, "
                  f"MRR: {result.reciprocal_rank:.4f}")
            print(f"   Retrieved: {result.retrieved_docs[:3]}")
            print(f"   Relevant:  {result.relevant_docs}")

        print("\n" + "="*70)

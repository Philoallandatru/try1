"""
Retrieval debugging and analysis tools.

Provides utilities for analyzing queries, explaining scores, and debugging retrieval quality.
"""

from typing import List, Dict, Any, Optional, Tuple
import math
from collections import Counter

from .bm25_retriever import BM25Retriever, SearchResult
from .bm25_index import BM25Index
from .tokenizer import Tokenizer


class QueryAnalyzer:
    """Analyze and explain query processing."""

    def __init__(self, tokenizer: Tokenizer):
        self.tokenizer = tokenizer

    def analyze(self, query: str) -> Dict[str, Any]:
        """
        Analyze a query and return detailed information.

        Args:
            query: Search query

        Returns:
            Dict with query analysis
        """
        # Tokenize
        tokens = self.tokenizer.tokenize(query)

        # Token statistics
        token_counts = Counter(tokens)

        return {
            "original_query": query,
            "tokens": tokens,
            "token_count": len(tokens),
            "unique_tokens": len(set(tokens)),
            "token_frequencies": dict(token_counts),
            "query_length": len(query),
        }


class ScoreExplainer:
    """Explain BM25 scoring in detail."""

    def __init__(self, retriever: BM25Retriever):
        self.retriever = retriever
        self.index = retriever.index

    def explain_score(
        self,
        query: str,
        doc_id: str,
        k1: float = 1.5,
        b: float = 0.75
    ) -> Dict[str, Any]:
        """
        Explain BM25 score calculation for a specific document.

        Args:
            query: Search query
            doc_id: Document ID
            k1: BM25 k1 parameter (term frequency saturation)
            b: BM25 b parameter (length normalization)

        Returns:
            Dict with score explanation
        """
        # Find document
        doc = self.retriever.get_document_by_id(doc_id)
        if not doc:
            return {"error": f"Document {doc_id} not found"}

        # Find document index
        doc_idx = None
        for i, d in enumerate(self.index.documents):
            if d.get("id") == doc_id:
                doc_idx = i
                break

        if doc_idx is None:
            return {"error": f"Document {doc_id} not in index"}

        # Tokenize query
        query_tokens = self.retriever.tokenizer.tokenize(query)
        doc_tokens = self.index.tokenized_corpus[doc_idx]

        # Calculate BM25 components
        N = len(self.index.documents)  # Total documents
        avgdl = sum(len(tokens) for tokens in self.index.tokenized_corpus) / N  # Average doc length
        doc_len = len(doc_tokens)

        # Calculate score for each query term
        term_scores = []
        total_score = 0.0

        for term in query_tokens:
            # Document frequency (how many docs contain this term)
            df = sum(1 for tokens in self.index.tokenized_corpus if term in tokens)

            if df == 0:
                continue

            # Term frequency in this document
            tf = doc_tokens.count(term)

            # IDF calculation
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

            # BM25 score for this term
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_len / avgdl))
            term_score = idf * (numerator / denominator)

            term_scores.append({
                "term": term,
                "tf": tf,
                "df": df,
                "idf": round(idf, 4),
                "score": round(term_score, 4),
            })

            total_score += term_score

        return {
            "doc_id": doc_id,
            "query": query,
            "query_tokens": query_tokens,
            "total_score": round(total_score, 4),
            "doc_length": doc_len,
            "avg_doc_length": round(avgdl, 2),
            "total_documents": N,
            "term_scores": term_scores,
            "parameters": {
                "k1": k1,
                "b": b,
            },
        }

    def compare_documents(
        self,
        query: str,
        doc_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare BM25 scores across multiple documents.

        Args:
            query: Search query
            doc_ids: List of document IDs to compare

        Returns:
            Dict with comparison results
        """
        explanations = []
        for doc_id in doc_ids:
            explanation = self.explain_score(query, doc_id)
            if "error" not in explanation:
                explanations.append(explanation)

        # Sort by score
        explanations.sort(key=lambda x: x["total_score"], reverse=True)

        return {
            "query": query,
            "document_count": len(explanations),
            "explanations": explanations,
        }


class RelevanceAnnotator:
    """Tool for annotating document relevance."""

    def __init__(self, storage_path: str = ".local/retrieval/annotations.json"):
        self.storage_path = storage_path
        self.annotations: Dict[str, Dict[str, Any]] = {}

    def annotate(
        self,
        query: str,
        doc_id: str,
        relevance: int,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Annotate document relevance for a query.

        Args:
            query: Search query
            doc_id: Document ID
            relevance: Relevance score (0-3: 0=not relevant, 1=marginally, 2=relevant, 3=highly relevant)
            notes: Optional notes

        Returns:
            Annotation record
        """
        key = f"{query}::{doc_id}"

        annotation = {
            "query": query,
            "doc_id": doc_id,
            "relevance": relevance,
            "notes": notes,
        }

        self.annotations[key] = annotation
        return annotation

    def get_annotations(
        self,
        query: Optional[str] = None,
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get annotations filtered by query or doc_id.

        Args:
            query: Optional query filter
            doc_id: Optional doc_id filter

        Returns:
            List of matching annotations
        """
        results = []
        for key, annotation in self.annotations.items():
            if query and annotation["query"] != query:
                continue
            if doc_id and annotation["doc_id"] != doc_id:
                continue
            results.append(annotation)
        return results

    def get_relevance_stats(self, query: str) -> Dict[str, Any]:
        """
        Get relevance statistics for a query.

        Args:
            query: Search query

        Returns:
            Dict with relevance statistics
        """
        annotations = self.get_annotations(query=query)

        if not annotations:
            return {
                "query": query,
                "total_annotations": 0,
            }

        relevance_counts = Counter(a["relevance"] for a in annotations)

        return {
            "query": query,
            "total_annotations": len(annotations),
            "relevance_distribution": dict(relevance_counts),
            "avg_relevance": sum(a["relevance"] for a in annotations) / len(annotations),
        }


class ABTestComparator:
    """Compare retrieval results from different configurations."""

    def __init__(self, retriever_a: BM25Retriever, retriever_b: BM25Retriever):
        self.retriever_a = retriever_a
        self.retriever_b = retriever_b

    def compare(
        self,
        query: str,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Compare retrieval results from two configurations.

        Args:
            query: Search query
            top_k: Number of results to compare

        Returns:
            Dict with comparison results
        """
        # Get results from both retrievers
        results_a = self.retriever_a.search(query, top_k=top_k)
        results_b = self.retriever_b.search(query, top_k=top_k)

        # Extract doc IDs
        doc_ids_a = set(r.doc_id for r in results_a)
        doc_ids_b = set(r.doc_id for r in results_b)

        # Calculate overlap
        overlap = doc_ids_a & doc_ids_b
        only_a = doc_ids_a - doc_ids_b
        only_b = doc_ids_b - doc_ids_a

        # Rank correlation (for overlapping docs)
        rank_diffs = []
        for doc_id in overlap:
            rank_a = next(i for i, r in enumerate(results_a) if r.doc_id == doc_id)
            rank_b = next(i for i, r in enumerate(results_b) if r.doc_id == doc_id)
            rank_diffs.append(abs(rank_a - rank_b))

        return {
            "query": query,
            "top_k": top_k,
            "config_a": {
                "result_count": len(results_a),
                "doc_ids": [r.doc_id for r in results_a],
                "scores": [round(r.score, 4) for r in results_a],
            },
            "config_b": {
                "result_count": len(results_b),
                "doc_ids": [r.doc_id for r in results_b],
                "scores": [round(r.score, 4) for r in results_b],
            },
            "comparison": {
                "overlap_count": len(overlap),
                "overlap_percentage": round(len(overlap) / top_k * 100, 2) if top_k > 0 else 0,
                "only_in_a": list(only_a),
                "only_in_b": list(only_b),
                "avg_rank_diff": round(sum(rank_diffs) / len(rank_diffs), 2) if rank_diffs else 0,
            },
        }

    def batch_compare(
        self,
        queries: List[str],
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Compare retrieval results across multiple queries.

        Args:
            queries: List of search queries
            top_k: Number of results to compare per query

        Returns:
            Dict with aggregated comparison results
        """
        comparisons = []
        total_overlap = 0
        total_rank_diff = 0

        for query in queries:
            comparison = self.compare(query, top_k)
            comparisons.append(comparison)
            total_overlap += comparison["comparison"]["overlap_count"]
            total_rank_diff += comparison["comparison"]["avg_rank_diff"]

        return {
            "query_count": len(queries),
            "top_k": top_k,
            "avg_overlap_count": round(total_overlap / len(queries), 2) if queries else 0,
            "avg_overlap_percentage": round(total_overlap / (len(queries) * top_k) * 100, 2) if queries and top_k > 0 else 0,
            "avg_rank_diff": round(total_rank_diff / len(queries), 2) if queries else 0,
            "comparisons": comparisons,
        }

"""BM25 search implementation for better retrieval quality.

This module implements the BM25 (Best Matching 25) ranking function,
which is a probabilistic retrieval model that considers:
- Term frequency (TF) with saturation
- Inverse document frequency (IDF)
- Document length normalization
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Iterable

from services.retrieval.indexing.page_index import tokenize


# English stop words (common words that don't add semantic value)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "will", "with", "this", "but", "they", "have", "had",
    "what", "when", "where", "who", "which", "why", "how", "all", "each",
    "other", "some", "such", "no", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "just", "should", "now",
}


def filter_stop_words(tokens: list[str]) -> list[str]:
    """Remove common stop words from token list."""
    return [token for token in tokens if token not in STOP_WORDS]


def compute_idf(term: str, doc_freq: dict[str, int], total_docs: int) -> float:
    """Compute Inverse Document Frequency (IDF) for a term.

    IDF measures how rare/important a term is across all documents.
    Rare terms get higher scores.

    Formula: IDF(term) = log((N - df + 0.5) / (df + 0.5) + 1)
    where N = total documents, df = documents containing term
    """
    df = doc_freq.get(term, 0)
    if df == 0:
        return 0.0
    return math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)


def compute_bm25_score(
    term_freq: int,
    doc_length: int,
    avg_doc_length: float,
    idf: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Compute BM25 score for a single term in a document.

    Args:
        term_freq: Number of times term appears in document
        doc_length: Total number of tokens in document
        avg_doc_length: Average document length across corpus
        idf: Inverse document frequency of the term
        k1: Term frequency saturation parameter (default 1.5)
        b: Length normalization parameter (default 0.75)

    Returns:
        BM25 score for this term
    """
    # Normalize document length
    normalized_length = doc_length / avg_doc_length if avg_doc_length > 0 else 1.0

    # BM25 formula with saturation
    numerator = term_freq * (k1 + 1.0)
    denominator = term_freq + k1 * (1.0 - b + b * normalized_length)

    return idf * (numerator / denominator)


def build_bm25_index(entries: Iterable[dict]) -> dict:
    """Build BM25 index from page index entries.

    Returns:
        Dictionary containing:
        - entries: List of indexed entries
        - doc_freq: Document frequency for each term
        - total_docs: Total number of documents
        - avg_doc_length: Average document length
    """
    entries_list = list(entries)
    total_docs = len(entries_list)

    if total_docs == 0:
        return {
            "entries": [],
            "doc_freq": {},
            "total_docs": 0,
            "avg_doc_length": 0.0,
        }

    # Compute document frequency for each term
    doc_freq: dict[str, int] = {}
    total_length = 0

    for entry in entries_list:
        tokens = entry.get("tokens", set())
        if isinstance(tokens, list):
            tokens = set(tokens)

        # Count documents containing each term
        for token in tokens:
            doc_freq[token] = doc_freq.get(token, 0) + 1

        # Track document lengths
        doc_length = sum(entry.get("token_counts", {}).values())
        total_length += doc_length

    avg_doc_length = total_length / total_docs if total_docs > 0 else 0.0

    return {
        "entries": entries_list,
        "doc_freq": doc_freq,
        "total_docs": total_docs,
        "avg_doc_length": avg_doc_length,
    }


def search_bm25(
    bm25_index: dict,
    query: str,
    allowed_policies: set[str],
    top_k: int = 10,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[dict]:
    """Search using BM25 ranking algorithm.

    Args:
        bm25_index: BM25 index built from build_bm25_index()
        query: Search query string
        allowed_policies: Set of allowed ACL policies
        top_k: Number of top results to return
        k1: BM25 term frequency saturation parameter
        b: BM25 length normalization parameter

    Returns:
        List of top-k scored entries with BM25 scores
    """
    entries = bm25_index["entries"]
    doc_freq = bm25_index["doc_freq"]
    total_docs = bm25_index["total_docs"]
    avg_doc_length = bm25_index["avg_doc_length"]

    if total_docs == 0:
        return []

    # Tokenize and filter query
    query_tokens = tokenize(query)
    query_tokens = filter_stop_words(query_tokens)
    query_terms = set(query_tokens)

    if not query_terms:
        return []

    # Compute IDF for each query term
    term_idfs = {
        term: compute_idf(term, doc_freq, total_docs)
        for term in query_terms
    }

    # Score each document
    scored = []
    for entry in entries:
        # Check ACL
        policy = entry.get("acl", {}).get("policy", "deny")
        if policy == "deny":
            continue
        if policy != "public" and policy not in allowed_policies:
            continue

        # Get document tokens and length
        token_counts = entry.get("token_counts", {})
        doc_length = sum(token_counts.values())

        if doc_length == 0:
            continue

        # Compute BM25 score for each query term
        bm25_score = 0.0
        for term in query_terms:
            term_freq = token_counts.get(term, 0)
            if term_freq > 0:
                idf = term_idfs[term]
                bm25_score += compute_bm25_score(
                    term_freq=term_freq,
                    doc_length=doc_length,
                    avg_doc_length=avg_doc_length,
                    idf=idf,
                    k1=k1,
                    b=b,
                )

        if bm25_score > 0:
            # Add authority boost (from original implementation)
            authority_level = entry.get("authority_level", "contextual")
            authority_boost = {
                "canonical": 3.0,
                "supporting": 2.0,
                "contextual": 1.0,
            }.get(authority_level, 0.0)

            total_score = bm25_score + authority_boost

            scored.append({
                **entry,
                "scores": {
                    "bm25": bm25_score,
                    "authority": authority_boost,
                    "total": total_score,
                }
            })

    # Sort by total score
    scored.sort(
        key=lambda item: (
            item["scores"]["total"],
            item["scores"]["bm25"],
            item["document_id"],
        ),
        reverse=True,
    )

    return scored[:top_k]

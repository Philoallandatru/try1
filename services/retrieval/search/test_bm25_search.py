"""Tests for BM25 search implementation."""
from __future__ import annotations

import pytest

from services.retrieval.search.bm25_search import (
    build_bm25_index,
    compute_bm25_score,
    compute_idf,
    filter_stop_words,
    search_bm25,
)


def test_filter_stop_words():
    """Test that common stop words are filtered out."""
    tokens = ["the", "quick", "brown", "fox", "is", "very", "fast"]
    filtered = filter_stop_words(tokens)
    assert "the" not in filtered
    assert "is" not in filtered
    assert "very" not in filtered
    assert "quick" in filtered
    assert "brown" in filtered
    assert "fox" in filtered
    assert "fast" in filtered


def test_compute_idf():
    """Test IDF computation."""
    # Term appears in 1 out of 10 documents (rare term, high IDF)
    doc_freq = {"rare": 1, "common": 9}
    total_docs = 10

    rare_idf = compute_idf("rare", doc_freq, total_docs)
    common_idf = compute_idf("common", doc_freq, total_docs)

    # Rare terms should have higher IDF
    assert rare_idf > common_idf
    assert rare_idf > 0
    assert common_idf > 0

    # Term not in corpus should have 0 IDF
    missing_idf = compute_idf("missing", doc_freq, total_docs)
    assert missing_idf == 0.0


def test_compute_bm25_score():
    """Test BM25 score computation."""
    # Test saturation effect: increasing term frequency has diminishing returns
    score_1 = compute_bm25_score(
        term_freq=1,
        doc_length=100,
        avg_doc_length=100,
        idf=2.0,
        k1=1.5,
        b=0.75,
    )
    score_2 = compute_bm25_score(
        term_freq=2,
        doc_length=100,
        avg_doc_length=100,
        idf=2.0,
        k1=1.5,
        b=0.75,
    )
    score_10 = compute_bm25_score(
        term_freq=10,
        doc_length=100,
        avg_doc_length=100,
        idf=2.0,
        k1=1.5,
        b=0.75,
    )

    # Score should increase with term frequency
    assert score_2 > score_1
    assert score_10 > score_2

    # But the increase should saturate (diminishing returns)
    increase_1_to_2 = score_2 - score_1
    increase_2_to_10 = score_10 - score_2
    # The increase from 2 to 10 should be less than 4x the increase from 1 to 2
    assert increase_2_to_10 < 4 * increase_1_to_2


def test_compute_bm25_score_length_normalization():
    """Test that BM25 normalizes for document length."""
    # Same term frequency, but different document lengths
    score_short = compute_bm25_score(
        term_freq=5,
        doc_length=50,  # Short document
        avg_doc_length=100,
        idf=2.0,
        k1=1.5,
        b=0.75,
    )
    score_long = compute_bm25_score(
        term_freq=5,
        doc_length=200,  # Long document
        avg_doc_length=100,
        idf=2.0,
        k1=1.5,
        b=0.75,
    )

    # Shorter documents should get higher scores for same term frequency
    assert score_short > score_long


def test_build_bm25_index():
    """Test building BM25 index from entries."""
    entries = [
        {
            "document_id": "doc1",
            "tokens": {"nvme", "flush", "command"},
            "token_counts": {"nvme": 5, "flush": 3, "command": 2},
        },
        {
            "document_id": "doc2",
            "tokens": {"nvme", "specification"},
            "token_counts": {"nvme": 10, "specification": 5},
        },
        {
            "document_id": "doc3",
            "tokens": {"flush", "cache"},
            "token_counts": {"flush": 2, "cache": 3},
        },
    ]

    index = build_bm25_index(entries)

    assert index["total_docs"] == 3
    assert index["doc_freq"]["nvme"] == 2  # Appears in doc1 and doc2
    assert index["doc_freq"]["flush"] == 2  # Appears in doc1 and doc3
    assert index["doc_freq"]["specification"] == 1  # Only in doc2
    assert index["doc_freq"]["cache"] == 1  # Only in doc3

    # Average document length
    total_tokens = (5 + 3 + 2) + (10 + 5) + (2 + 3)
    expected_avg = total_tokens / 3
    assert index["avg_doc_length"] == expected_avg


def test_build_bm25_index_empty():
    """Test building index with no entries."""
    index = build_bm25_index([])

    assert index["total_docs"] == 0
    assert index["avg_doc_length"] == 0.0
    assert len(index["doc_freq"]) == 0


def test_search_bm25_basic():
    """Test basic BM25 search."""
    entries = [
        {
            "document_id": "doc1",
            "tokens": {"nvme", "flush", "command"},
            "token_counts": {"nvme": 5, "flush": 3, "command": 2},
            "acl": {"policy": "public"},
            "authority_level": "canonical",
        },
        {
            "document_id": "doc2",
            "tokens": {"nvme", "specification", "protocol"},
            "token_counts": {"nvme": 10, "specification": 5, "protocol": 3},
            "acl": {"policy": "public"},
            "authority_level": "supporting",
        },
        {
            "document_id": "doc3",
            "tokens": {"flush", "cache", "memory"},
            "token_counts": {"flush": 2, "cache": 3, "memory": 1},
            "acl": {"policy": "public"},
            "authority_level": "contextual",
        },
    ]

    index = build_bm25_index(entries)
    results = search_bm25(index, "nvme flush command", allowed_policies=set(), top_k=10)

    # Should return all matching documents
    assert len(results) > 0

    # doc1 should rank high (has all three terms)
    doc_ids = [r["document_id"] for r in results]
    assert "doc1" in doc_ids

    # Results should have scores
    for result in results:
        assert "scores" in result
        assert "bm25" in result["scores"]
        assert "authority" in result["scores"]
        assert "total" in result["scores"]
        assert result["scores"]["total"] > 0


def test_search_bm25_rare_terms_rank_higher():
    """Test that documents with rare terms rank higher."""
    entries = [
        {
            "document_id": "doc1",
            "tokens": {"nvme", "flush"},  # Common terms
            "token_counts": {"nvme": 5, "flush": 5},
            "acl": {"policy": "public"},
            "authority_level": "contextual",
        },
        {
            "document_id": "doc2",
            "tokens": {"nvme", "rare_technical_term"},  # One rare term
            "token_counts": {"nvme": 5, "rare_technical_term": 5},
            "acl": {"policy": "public"},
            "authority_level": "contextual",
        },
        {
            "document_id": "doc3",
            "tokens": {"nvme", "flush"},  # Common terms
            "token_counts": {"nvme": 5, "flush": 5},
            "acl": {"policy": "public"},
            "authority_level": "contextual",
        },
    ]

    index = build_bm25_index(entries)
    results = search_bm25(index, "nvme rare_technical_term", allowed_policies=set(), top_k=10)

    # doc2 should rank first because it has the rare term
    assert results[0]["document_id"] == "doc2"


def test_search_bm25_acl_filtering():
    """Test that ACL policies are respected."""
    entries = [
        {
            "document_id": "public_doc",
            "tokens": {"nvme", "flush"},
            "token_counts": {"nvme": 5, "flush": 3},
            "acl": {"policy": "public"},
            "authority_level": "canonical",
        },
        {
            "document_id": "private_doc",
            "tokens": {"nvme", "flush"},
            "token_counts": {"nvme": 5, "flush": 3},
            "acl": {"policy": "team_a"},
            "authority_level": "canonical",
        },
        {
            "document_id": "denied_doc",
            "tokens": {"nvme", "flush"},
            "token_counts": {"nvme": 5, "flush": 3},
            "acl": {"policy": "deny"},
            "authority_level": "canonical",
        },
    ]

    index = build_bm25_index(entries)

    # Search with no allowed policies (only public)
    results = search_bm25(index, "nvme flush", allowed_policies=set(), top_k=10)
    doc_ids = [r["document_id"] for r in results]
    assert "public_doc" in doc_ids
    assert "private_doc" not in doc_ids
    assert "denied_doc" not in doc_ids

    # Search with team_a policy allowed
    results = search_bm25(index, "nvme flush", allowed_policies={"team_a"}, top_k=10)
    doc_ids = [r["document_id"] for r in results]
    assert "public_doc" in doc_ids
    assert "private_doc" in doc_ids
    assert "denied_doc" not in doc_ids


def test_search_bm25_top_k_limit():
    """Test that top_k limits results."""
    entries = [
        {
            "document_id": f"doc{i}",
            "tokens": {"nvme", "test"},
            "token_counts": {"nvme": i, "test": 1},
            "acl": {"policy": "public"},
            "authority_level": "contextual",
        }
        for i in range(1, 11)
    ]

    index = build_bm25_index(entries)
    results = search_bm25(index, "nvme test", allowed_policies=set(), top_k=3)

    assert len(results) == 3


def test_search_bm25_stop_words_filtered():
    """Test that stop words in query are filtered."""
    entries = [
        {
            "document_id": "doc1",
            "tokens": {"nvme", "flush", "command"},
            "token_counts": {"nvme": 5, "flush": 3, "command": 2},
            "acl": {"policy": "public"},
            "authority_level": "canonical",
        },
    ]

    index = build_bm25_index(entries)

    # Query with stop words
    results = search_bm25(
        index,
        "the nvme flush command is very important",
        allowed_policies=set(),
        top_k=10,
    )

    # Should still find the document (stop words filtered)
    assert len(results) > 0
    assert results[0]["document_id"] == "doc1"


def test_search_bm25_empty_query():
    """Test search with empty query after stop word filtering."""
    entries = [
        {
            "document_id": "doc1",
            "tokens": {"nvme"},
            "token_counts": {"nvme": 5},
            "acl": {"policy": "public"},
            "authority_level": "canonical",
        },
    ]

    index = build_bm25_index(entries)

    # Query with only stop words
    results = search_bm25(index, "the is a", allowed_policies=set(), top_k=10)

    # Should return no results
    assert len(results) == 0


def test_search_bm25_authority_boost():
    """Test that authority level provides score boost."""
    entries = [
        {
            "document_id": "canonical_doc",
            "tokens": {"nvme"},
            "token_counts": {"nvme": 5},
            "acl": {"policy": "public"},
            "authority_level": "canonical",
        },
        {
            "document_id": "supporting_doc",
            "tokens": {"nvme"},
            "token_counts": {"nvme": 5},
            "acl": {"policy": "public"},
            "authority_level": "supporting",
        },
        {
            "document_id": "contextual_doc",
            "tokens": {"nvme"},
            "token_counts": {"nvme": 5},
            "acl": {"policy": "public"},
            "authority_level": "contextual",
        },
    ]

    index = build_bm25_index(entries)
    results = search_bm25(index, "nvme", allowed_policies=set(), top_k=10)

    # Canonical should rank first (highest authority boost)
    assert results[0]["document_id"] == "canonical_doc"
    assert results[1]["document_id"] == "supporting_doc"
    assert results[2]["document_id"] == "contextual_doc"

    # Check authority scores
    assert results[0]["scores"]["authority"] == 3.0
    assert results[1]["scores"]["authority"] == 2.0
    assert results[2]["scores"]["authority"] == 1.0

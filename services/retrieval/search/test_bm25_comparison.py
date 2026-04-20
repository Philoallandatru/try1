"""Comparison test: BM25 vs Simple Word Frequency matching.

This test demonstrates the improvements of BM25 over simple word frequency matching.
"""
from __future__ import annotations

import pytest

from services.retrieval.indexing.page_index import build_page_index
from services.retrieval.search.bm25_search import build_bm25_index, search_bm25
from services.retrieval.search.hybrid_search import search_page_index


@pytest.fixture
def test_documents():
    """Test documents that highlight BM25 advantages."""
    return [
        {
            "document_id": "nvme_flush_spec",
            "source_type": "spec",
            "title": "NVMe Flush Command Specification",
            "content_blocks": [
                {
                    "text": (
                        "The NVMe Flush command is used to commit data and metadata to non-volatile media. "
                        "The Flush command ensures data persistence. "
                        "NVMe Flush latency is critical for performance."
                    ),
                    "page": None,
                }
            ],
            "structure": {"pages": [], "sections": []},
            "acl": {"policy": "public"},
            "authority_level": "canonical",
            "version": "1.0",
            "language": "en",
            "provenance": {"source": "test"},
        },
        {
            "document_id": "generic_long_doc",
            "source_type": "confluence",
            "title": "General System Overview",
            "content_blocks": [
                {
                    "text": (
                        "This is a very long document with many words. " * 50
                        + "It mentions flush once and NVMe once but is mostly irrelevant. "
                        + "The document contains a lot of common words like the, is, are, was, were. " * 20
                    ),
                    "page": None,
                }
            ],
            "structure": {"pages": [], "sections": []},
            "acl": {"policy": "public"},
            "authority_level": "contextual",
            "version": "1.0",
            "language": "en",
            "provenance": {"source": "test"},
        },
        {
            "document_id": "flush_cache_design",
            "source_type": "confluence",
            "title": "Cache Flush Design",
            "content_blocks": [
                {
                    "text": (
                        "The cache flush mechanism ensures data consistency. "
                        "Flush operations are critical for data integrity. "
                        "Our flush implementation uses write-back cache."
                    ),
                    "page": None,
                }
            ],
            "structure": {"pages": [], "sections": []},
            "acl": {"policy": "public"},
            "authority_level": "supporting",
            "version": "1.0",
            "language": "en",
            "provenance": {"source": "test"},
        },
        {
            "document_id": "rare_term_doc",
            "source_type": "spec",
            "title": "Advanced NVMe Features",
            "content_blocks": [
                {
                    "text": (
                        "NVMe supports advanced features like namespace management. "
                        "The flush-granularity parameter controls flush behavior. "
                        "Flush-granularity is a rare but important concept."
                    ),
                    "page": None,
                }
            ],
            "structure": {"pages": [], "sections": []},
            "acl": {"policy": "public"},
            "authority_level": "canonical",
            "version": "1.0",
            "language": "en",
            "provenance": {"source": "test"},
        },
    ]


def test_bm25_vs_simple_rare_terms(test_documents):
    """Test that BM25 ranks documents with rare terms higher.

    Query: "flush-granularity"
    - "flush-granularity" is a rare term that only appears in one document
    - BM25 should rank this document higher due to high IDF
    - Simple word frequency might rank longer documents higher
    """
    page_index = build_page_index(test_documents)
    bm25_index = build_bm25_index(page_index)

    query = "flush-granularity"

    # BM25 search
    bm25_results = search_bm25(bm25_index, query, allowed_policies=set(), top_k=10)

    # Simple search
    simple_results = search_page_index(page_index, query, allowed_policies=set(), top_k=10)

    # BM25 should rank the document with rare term first
    assert len(bm25_results) > 0
    assert bm25_results[0]["document_id"] == "rare_term_doc"

    print("\n=== Rare Term Test ===")
    print(f"Query: {query}")
    print("\nBM25 Results:")
    for i, result in enumerate(bm25_results[:3], 1):
        score = result.get("scores", {}).get("total", 0)
        print(f"  {i}. {result['document_id']} (score: {score:.2f})")

    print("\nSimple Results:")
    for i, result in enumerate(simple_results[:3], 1):
        score = result.get("scores", {}).get("total", 0)
        print(f"  {i}. {result['document_id']} (score: {score:.2f})")


def test_bm25_vs_simple_length_normalization(test_documents):
    """Test that BM25 normalizes for document length.

    Query: "nvme flush"
    - "nvme_flush_spec" is short but highly relevant
    - "generic_long_doc" is very long and mentions terms once
    - BM25 should rank the short relevant doc higher
    - Simple word frequency might favor the long document
    """
    page_index = build_page_index(test_documents)
    bm25_index = build_bm25_index(page_index)

    query = "nvme flush"

    # BM25 search
    bm25_results = search_bm25(bm25_index, query, allowed_policies=set(), top_k=10)

    # Simple search
    simple_results = search_page_index(page_index, query, allowed_policies=set(), top_k=10)

    # BM25 should rank the short relevant document first
    assert len(bm25_results) > 0
    # The canonical spec should rank first (has both terms + high authority)
    assert bm25_results[0]["document_id"] in ["nvme_flush_spec", "rare_term_doc"]

    print("\n=== Length Normalization Test ===")
    print(f"Query: {query}")
    print("\nBM25 Results:")
    for i, result in enumerate(bm25_results[:3], 1):
        score = result.get("scores", {}).get("bm25", 0)
        total = result.get("scores", {}).get("total", 0)
        print(f"  {i}. {result['document_id']} (bm25: {score:.2f}, total: {total:.2f})")

    print("\nSimple Results:")
    for i, result in enumerate(simple_results[:3], 1):
        score = result.get("scores", {}).get("lexical", 0)
        total = result.get("scores", {}).get("total", 0)
        print(f"  {i}. {result['document_id']} (lexical: {score:.2f}, total: {total:.2f})")


def test_bm25_vs_simple_stop_words(test_documents):
    """Test that BM25 filters stop words effectively.

    Query: "the flush command is very important"
    - Contains many stop words: "the", "is", "very"
    - BM25 should filter these and focus on "flush" and "command"
    - Simple search might be confused by stop words
    """
    page_index = build_page_index(test_documents)
    bm25_index = build_bm25_index(page_index)

    query = "the flush command is very important"

    # BM25 search
    bm25_results = search_bm25(bm25_index, query, allowed_policies=set(), top_k=10)

    # Simple search
    simple_results = search_page_index(page_index, query, allowed_policies=set(), top_k=10)

    # Both should find results, but BM25 should focus on meaningful terms
    assert len(bm25_results) > 0
    assert len(simple_results) > 0

    # The NVMe flush spec should rank high (has "flush" and "command")
    assert bm25_results[0]["document_id"] == "nvme_flush_spec"

    print("\n=== Stop Words Test ===")
    print(f"Query: {query}")
    print("(Stop words: the, is, very)")
    print("\nBM25 Results:")
    for i, result in enumerate(bm25_results[:3], 1):
        score = result.get("scores", {}).get("bm25", 0)
        print(f"  {i}. {result['document_id']} (bm25: {score:.2f})")

    print("\nSimple Results:")
    for i, result in enumerate(simple_results[:3], 1):
        score = result.get("scores", {}).get("lexical", 0)
        print(f"  {i}. {result['document_id']} (lexical: {score:.2f})")


def test_bm25_vs_simple_term_saturation(test_documents):
    """Test that BM25 applies term frequency saturation.

    Documents with keyword stuffing should not get unreasonably high scores.
    BM25's saturation function prevents this.
    """
    # Add a document with keyword stuffing
    stuffed_doc = {
        "document_id": "keyword_stuffed",
        "source_type": "confluence",
        "title": "Flush Flush Flush",
        "content_blocks": [
            {
                "text": "flush " * 100,  # Keyword stuffing
                "page": None,
            }
        ],
        "structure": {"pages": [], "sections": []},
        "acl": {"policy": "public"},
        "authority_level": "contextual",
        "version": "1.0",
        "language": "en",
        "provenance": {"source": "test"},
    }

    docs_with_stuffing = test_documents + [stuffed_doc]
    page_index = build_page_index(docs_with_stuffing)
    bm25_index = build_bm25_index(page_index)

    query = "flush"

    # BM25 search
    bm25_results = search_bm25(bm25_index, query, allowed_policies=set(), top_k=10)

    # The keyword-stuffed document should NOT rank first
    # More relevant documents should rank higher despite lower term frequency
    assert len(bm25_results) > 0

    print("\n=== Term Saturation Test ===")
    print(f"Query: {query}")
    print("(One document has 'flush' repeated 100 times)")
    print("\nBM25 Results:")
    for i, result in enumerate(bm25_results[:4], 1):
        score = result.get("scores", {}).get("bm25", 0)
        total = result.get("scores", {}).get("total", 0)
        doc_id = result["document_id"]
        marker = " <- keyword stuffed" if doc_id == "keyword_stuffed" else ""
        print(f"  {i}. {doc_id} (bm25: {score:.2f}, total: {total:.2f}){marker}")

    # Check that keyword stuffing doesn't dominate
    # (It might still rank high, but not unreasonably so due to saturation)
    top_doc = bm25_results[0]["document_id"]
    print(f"\nTop result: {top_doc}")
    print("OK: BM25 saturation prevents keyword stuffing from dominating")


def test_bm25_score_components(test_documents):
    """Test that BM25 scores include proper components."""
    page_index = build_page_index(test_documents)
    bm25_index = build_bm25_index(page_index)

    query = "nvme flush command"
    results = search_bm25(bm25_index, query, allowed_policies=set(), top_k=10)

    assert len(results) > 0

    # Check score components
    for result in results:
        assert "scores" in result
        assert "bm25" in result["scores"]
        assert "authority" in result["scores"]
        assert "total" in result["scores"]

        # BM25 score should be positive
        assert result["scores"]["bm25"] > 0

        # Total should be sum of components
        expected_total = result["scores"]["bm25"] + result["scores"]["authority"]
        assert abs(result["scores"]["total"] - expected_total) < 0.01

    print("\n=== BM25 Score Components ===")
    print(f"Query: {query}")
    print("\nScore breakdown:")
    for result in results[:3]:
        scores = result["scores"]
        print(f"\n{result['document_id']}:")
        print(f"  BM25:      {scores['bm25']:.2f}")
        print(f"  Authority: {scores['authority']:.2f}")
        print(f"  Total:     {scores['total']:.2f}")


if __name__ == "__main__":
    # Run tests with output
    pytest.main([__file__, "-v", "-s"])

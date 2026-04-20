"""
Tests for BM25 retrieval components.
"""

import pytest
from pathlib import Path
import tempfile

from packages.retrieval.tokenizer import Tokenizer
from packages.retrieval.bm25_index import BM25Index
from packages.retrieval.bm25_retriever import BM25Retriever


class TestTokenizer:
    """Test Tokenizer class."""

    def test_tokenize_english(self):
        """Test English tokenization."""
        tokenizer = Tokenizer()
        text = "The quick brown fox jumps over the lazy dog"
        tokens = tokenizer.tokenize(text)

        # Should tokenize and lowercase
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens

        # Stop words should be filtered
        assert "the" not in tokens
        assert "over" not in tokens

    def test_tokenize_chinese(self):
        """Test Chinese tokenization."""
        tokenizer = Tokenizer()
        text = "NVMe 固态硬盘的性能测试"
        tokens = tokenizer.tokenize(text)

        # Should contain key terms
        assert "nvme" in tokens or "NVMe" in tokens
        assert "固态硬盘" in tokens or "固态" in tokens or "硬盘" in tokens
        assert "性能" in tokens
        assert "测试" in tokens

    def test_tokenize_mixed(self):
        """Test mixed Chinese and English tokenization."""
        tokenizer = Tokenizer()
        text = "SSD-777 issue: NVMe flush command 失败"
        tokens = tokenizer.tokenize(text)

        # Should contain both English and Chinese terms
        assert any("ssd" in t.lower() for t in tokens)
        assert any("nvme" in t.lower() for t in tokens)
        assert "失败" in tokens

    def test_stop_words(self):
        """Test stop words filtering."""
        tokenizer = Tokenizer(use_stop_words=True)
        text = "这是一个测试"
        tokens = tokenizer.tokenize(text)

        # Stop words should be filtered
        assert "这" not in tokens
        assert "是" not in tokens
        assert "一个" not in tokens

        # Content word should remain
        assert "测试" in tokens

    def test_no_stop_words(self):
        """Test without stop words filtering."""
        tokenizer = Tokenizer(use_stop_words=False)
        text = "这是一个测试"
        tokens = tokenizer.tokenize(text)

        # All tokens should be present
        assert len(tokens) > 0


class TestBM25Index:
    """Test BM25Index class."""

    def test_build_index(self):
        """Test building index from documents."""
        documents = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
            {"id": "doc2", "content": "固态硬盘性能测试"},
            {"id": "doc3", "content": "SSD-777 flush command failed"},
        ]

        index = BM25Index()
        index.build(documents)

        assert index.get_document_count() == 3
        assert len(index.tokenized_corpus) == 3

    def test_add_documents(self):
        """Test adding documents incrementally."""
        initial_docs = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
        ]

        index = BM25Index()
        index.build(initial_docs)
        assert index.get_document_count() == 1

        new_docs = [
            {"id": "doc2", "content": "固态硬盘性能测试"},
        ]
        index.add_documents(new_docs)
        assert index.get_document_count() == 2

    def test_remove_documents(self):
        """Test removing documents."""
        documents = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
            {"id": "doc2", "content": "固态硬盘性能测试"},
            {"id": "doc3", "content": "SSD-777 flush command failed"},
        ]

        index = BM25Index()
        index.build(documents)
        assert index.get_document_count() == 3

        index.remove_documents(["doc2"])
        assert index.get_document_count() == 2

        # Check that doc2 is removed
        doc_ids = [doc["id"] for doc in index.documents]
        assert "doc2" not in doc_ids
        assert "doc1" in doc_ids
        assert "doc3" in doc_ids

    def test_save_load(self):
        """Test saving and loading index."""
        documents = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
            {"id": "doc2", "content": "固态硬盘性能测试"},
        ]

        index = BM25Index()
        index.build(documents)

        # Save index
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test_index.pkl"
            index.save(index_path)

            # Load index
            new_index = BM25Index()
            new_index.load(index_path)

            assert new_index.get_document_count() == 2
            assert len(new_index.tokenized_corpus) == 2

    def test_get_stats(self):
        """Test getting index statistics."""
        documents = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
            {"id": "doc2", "content": "固态硬盘性能测试"},
        ]

        index = BM25Index()
        index.build(documents)

        stats = index.get_stats()
        assert stats["document_count"] == 2
        assert stats["avg_doc_length"] > 0
        assert stats["total_tokens"] > 0


class TestBM25Retriever:
    """Test BM25Retriever class."""

    def test_search_english(self):
        """Test searching English documents."""
        documents = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
            {"id": "doc2", "content": "SATA HDD speed benchmark"},
            {"id": "doc3", "content": "SSD firmware update guide"},
        ]

        index = BM25Index()
        index.build(documents)
        retriever = BM25Retriever(index)

        results = retriever.search("SSD performance", top_k=2)

        assert len(results) <= 2
        assert results[0].doc_id in ["doc1", "doc3"]

    def test_search_chinese(self):
        """Test searching Chinese documents."""
        documents = [
            {"id": "doc1", "content": "固态硬盘性能测试报告"},
            {"id": "doc2", "content": "机械硬盘速度评测"},
            {"id": "doc3", "content": "固态硬盘固件升级指南"},
        ]

        index = BM25Index()
        index.build(documents)
        retriever = BM25Retriever(index)

        results = retriever.search("固态硬盘性能", top_k=2)

        assert len(results) <= 2
        assert results[0].doc_id in ["doc1", "doc3"]

    def test_search_mixed(self):
        """Test searching mixed language documents."""
        documents = [
            {"id": "doc1", "content": "SSD-777: NVMe flush command 失败"},
            {"id": "doc2", "content": "SSD-778: 固态硬盘性能下降"},
            {"id": "doc3", "content": "SSD-779: firmware update required"},
        ]

        index = BM25Index()
        index.build(documents)
        retriever = BM25Retriever(index)

        results = retriever.search("SSD flush 失败", top_k=2)

        assert len(results) <= 2
        # doc1 should be most relevant
        assert results[0].doc_id == "doc1"

    def test_search_with_highlights(self):
        """Test search with highlighted matching terms."""
        documents = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
            {"id": "doc2", "content": "SSD firmware update guide"},
        ]

        index = BM25Index()
        index.build(documents)
        retriever = BM25Retriever(index)

        results = retriever.search_with_highlights("SSD performance", top_k=2)

        assert len(results) <= 2
        assert "matching_tokens" in results[0]
        assert "match_count" in results[0]

    def test_get_document_by_id(self):
        """Test getting document by ID."""
        documents = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
            {"id": "doc2", "content": "固态硬盘性能测试"},
        ]

        index = BM25Index()
        index.build(documents)
        retriever = BM25Retriever(index)

        doc = retriever.get_document_by_id("doc1")
        assert doc is not None
        assert doc["id"] == "doc1"

        doc = retriever.get_document_by_id("nonexistent")
        assert doc is None

    def test_empty_query(self):
        """Test searching with empty query."""
        documents = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
        ]

        index = BM25Index()
        index.build(documents)
        retriever = BM25Retriever(index)

        results = retriever.search("", top_k=5)
        assert len(results) == 0

    def test_min_score_threshold(self):
        """Test minimum score threshold."""
        documents = [
            {"id": "doc1", "content": "NVMe SSD performance test"},
            {"id": "doc2", "content": "completely unrelated content"},
        ]

        index = BM25Index()
        index.build(documents)
        retriever = BM25Retriever(index)

        # With high min_score, should filter out low-scoring results
        results = retriever.search("SSD performance", top_k=5, min_score=1.0)
        assert len(results) <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

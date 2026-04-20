"""
Simple test script for BM25 retrieval (without pytest).
"""

from pathlib import Path
import tempfile
import sys
import io

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.retrieval.tokenizer import Tokenizer
from packages.retrieval.bm25_index import BM25Index
from packages.retrieval.bm25_retriever import BM25Retriever


def test_tokenizer():
    """Test Tokenizer."""
    print("\n=== Testing Tokenizer ===")

    tokenizer = Tokenizer()

    # Test English
    text = "The quick brown fox jumps over the lazy dog"
    tokens = tokenizer.tokenize(text)
    print(f"English: '{text}'")
    print(f"Tokens: {tokens}")
    assert "quick" in tokens
    assert "the" not in tokens  # Stop word filtered
    print("✓ English tokenization passed")

    # Test Chinese
    text = "NVMe 固态硬盘的性能测试"
    tokens = tokenizer.tokenize(text)
    print(f"\nChinese: '{text}'")
    print(f"Tokens: {tokens}")
    assert "性能" in tokens
    assert "测试" in tokens
    print("✓ Chinese tokenization passed")

    # Test mixed
    text = "SSD-777 issue: NVMe flush command 失败"
    tokens = tokenizer.tokenize(text)
    print(f"\nMixed: '{text}'")
    print(f"Tokens: {tokens}")
    assert "失败" in tokens
    print("✓ Mixed tokenization passed")


def test_bm25_index():
    """Test BM25Index."""
    print("\n=== Testing BM25Index ===")

    documents = [
        {"id": "doc1", "content": "NVMe SSD performance test"},
        {"id": "doc2", "content": "固态硬盘性能测试"},
        {"id": "doc3", "content": "SSD-777 flush command failed"},
    ]

    index = BM25Index()
    index.build(documents)

    print(f"Built index with {index.get_document_count()} documents")
    assert index.get_document_count() == 3
    print("✓ Index building passed")

    # Test add documents
    new_docs = [{"id": "doc4", "content": "New document"}]
    index.add_documents(new_docs)
    assert index.get_document_count() == 4
    print("✓ Add documents passed")

    # Test remove documents
    index.remove_documents(["doc4"])
    assert index.get_document_count() == 3
    print("✓ Remove documents passed")

    # Test save/load
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "test_index.pkl"
        index.save(index_path)
        print(f"Saved index to {index_path}")

        new_index = BM25Index()
        new_index.load(index_path)
        assert new_index.get_document_count() == 3
        print("✓ Save/load passed")

    # Test stats
    stats = index.get_stats()
    print(f"\nIndex stats: {stats}")
    assert stats["document_count"] == 3
    print("✓ Stats passed")


def test_bm25_retriever():
    """Test BM25Retriever."""
    print("\n=== Testing BM25Retriever ===")

    documents = [
        {"id": "doc1", "content": "NVMe SSD performance test"},
        {"id": "doc2", "content": "SATA HDD speed benchmark"},
        {"id": "doc3", "content": "SSD firmware update guide"},
        {"id": "doc4", "content": "固态硬盘性能测试报告"},
        {"id": "doc5", "content": "SSD-777: NVMe flush command 失败"},
    ]

    index = BM25Index()
    index.build(documents)
    retriever = BM25Retriever(index)

    # Test English search
    print("\nSearch: 'SSD performance'")
    results = retriever.search("SSD performance", top_k=3)
    print(f"Found {len(results)} results:")
    for r in results:
        print(f"  {r.rank}. {r.doc_id} (score: {r.score:.2f}) - {r.document['content']}")
    assert len(results) > 0
    assert results[0].doc_id in ["doc1", "doc3", "doc4"]
    print("✓ English search passed")

    # Test Chinese search
    print("\nSearch: '固态硬盘性能'")
    results = retriever.search("固态硬盘性能", top_k=3)
    print(f"Found {len(results)} results:")
    for r in results:
        print(f"  {r.rank}. {r.doc_id} (score: {r.score:.2f}) - {r.document['content']}")
    assert len(results) > 0
    print("✓ Chinese search passed")

    # Test mixed search
    print("\nSearch: 'SSD flush 失败'")
    results = retriever.search("SSD flush 失败", top_k=3)
    print(f"Found {len(results)} results:")
    for r in results:
        print(f"  {r.rank}. {r.doc_id} (score: {r.score:.2f}) - {r.document['content']}")
    assert len(results) > 0
    assert results[0].doc_id == "doc5"
    print("✓ Mixed search passed")

    # Test search with highlights
    print("\nSearch with highlights: 'SSD performance'")
    results = retriever.search_with_highlights("SSD performance", top_k=2)
    print(f"Found {len(results)} results:")
    for r in results:
        print(f"  {r['rank']}. {r['doc_id']} - Matching tokens: {r['matching_tokens']}")
    assert len(results) > 0
    assert "matching_tokens" in results[0]
    print("✓ Search with highlights passed")

    # Test get document by ID
    doc = retriever.get_document_by_id("doc1")
    assert doc is not None
    assert doc["id"] == "doc1"
    print("✓ Get document by ID passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("BM25 Retrieval Test Suite")
    print("=" * 60)

    try:
        test_tokenizer()
        test_bm25_index()
        test_bm25_retriever()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()

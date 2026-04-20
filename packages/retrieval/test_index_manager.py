"""
Test script for IndexManager.

Tests:
1. Document database operations
2. Full index building
3. Incremental updates
4. Index persistence
5. Health checks
"""

import os
import sys
import io
import tempfile
import shutil
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.source_models.document_database import DocumentDatabase
from packages.retrieval.index_manager import IndexManager
from packages.retrieval.bm25_retriever import BM25Retriever


def test_document_database():
    """Test document database operations."""
    print("\n=== Test 1: Document Database ===")

    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")

    try:
        db = DocumentDatabase(db_path)

        # Create documents
        doc1 = db.create_document(
            id="doc1",
            source_id="source1",
            source_type="jira",
            title="Bug in login system",
            content="Users cannot login with special characters in password",
            url="https://jira.example.com/browse/BUG-123",
            metadata={"project": "AUTH", "priority": "high"}
        )
        print(f"✓ Created document: {doc1.id}")

        doc2 = db.create_document(
            id="doc2",
            source_id="source1",
            source_type="confluence",
            title="API Documentation",
            content="REST API endpoints for authentication service",
            url="https://confluence.example.com/pages/123",
            metadata={"space": "DOCS"}
        )
        print(f"✓ Created document: {doc2.id}")

        # List documents
        docs = db.list_documents()
        print(f"✓ Listed {len(docs)} documents")

        # Count documents
        count = db.count_documents()
        print(f"✓ Total documents: {count}")

        # Get unindexed documents
        unindexed = db.get_unindexed_documents()
        print(f"✓ Unindexed documents: {len(unindexed)}")

        return db_path, temp_dir

    except Exception as e:
        print(f"✗ Error: {e}")
        shutil.rmtree(temp_dir)
        raise


def test_full_index_build(db_path, temp_dir):
    """Test full index building."""
    print("\n=== Test 2: Full Index Build ===")

    try:
        index_dir = os.path.join(temp_dir, ".index")
        manager = IndexManager(db_path=db_path, index_dir=index_dir)

        # Build full index
        result = manager.build_full_index()
        print(f"✓ Build status: {result['status']}")
        print(f"✓ Indexed documents: {result['indexed_documents']}")
        print(f"✓ Index stats: {result['stats']}")

        # Check index file exists
        assert manager.index_path.exists(), "Index file should exist"
        print(f"✓ Index file created: {manager.index_path}")

        return manager

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_retrieval(manager):
    """Test retrieval with built index."""
    print("\n=== Test 3: Retrieval ===")

    try:
        retriever = BM25Retriever(manager.index)

        # Search for "login"
        results = retriever.search("login", top_k=5)
        print(f"✓ Search 'login': {len(results)} results")
        for result in results:
            doc_db = manager.db.get_document(result.doc_id)
            if doc_db:
                print(f"  - {result.doc_id}: {result.score:.4f} - {doc_db.title}")

        # Search for "API"
        results = retriever.search("API", top_k=5)
        print(f"✓ Search 'API': {len(results)} results")
        for result in results:
            doc_db = manager.db.get_document(result.doc_id)
            if doc_db:
                print(f"  - {result.doc_id}: {result.score:.4f} - {doc_db.title}")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_incremental_update(db_path, temp_dir):
    """Test incremental index updates."""
    print("\n=== Test 4: Incremental Update ===")

    try:
        db = DocumentDatabase(db_path)
        index_dir = os.path.join(temp_dir, ".index")
        manager = IndexManager(db_path=db_path, index_dir=index_dir)

        # Load existing index
        loaded = manager.load_index()
        print(f"✓ Loaded existing index: {loaded}")

        # Add new document
        doc3 = db.create_document(
            id="doc3",
            source_id="source2",
            source_type="file_upload",
            title="Security Guidelines",
            content="Best practices for secure authentication",
            metadata={"category": "security"}
        )
        print(f"✓ Added new document: {doc3.id}")

        # Update existing document
        db.update_document(
            document_id="doc1",
            content="Users cannot login with special characters in password. Fixed in v2.0"
        )
        print(f"✓ Updated document: doc1")

        # Perform incremental update
        result = manager.update_index_incremental()
        print(f"✓ Update status: {result['status']}")
        print(f"✓ Added: {result['added']}, Updated: {result['updated']}")

        # Verify new document is searchable
        retriever = BM25Retriever(manager.index)
        results = retriever.search("security", top_k=5)
        print(f"✓ Search 'security': {len(results)} results")
        assert len(results) > 0, "Should find security document"

        # Verify updated document
        results = retriever.search("v2.0", top_k=5)
        print(f"✓ Search 'v2.0': {len(results)} results")
        assert len(results) > 0, "Should find updated content"

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_health_check(db_path, temp_dir):
    """Test index health checks."""
    print("\n=== Test 5: Health Check ===")

    try:
        index_dir = os.path.join(temp_dir, ".index")
        manager = IndexManager(db_path=db_path, index_dir=index_dir)

        # Load index
        manager.load_index()

        # Get stats
        stats = manager.get_stats()
        print(f"✓ Index stats:")
        print(f"  - Documents in index: {stats['index']['document_count']}")
        print(f"  - Total documents in DB: {stats['database']['total_documents']}")
        print(f"  - Unindexed: {stats['database']['unindexed_documents']}")
        print(f"  - Stale: {stats['database']['stale_documents']}")

        # Health check
        health = manager.health_check()
        print(f"✓ Health status: {health['status']}")
        print(f"✓ Message: {health['message']}")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def main():
    """Run all tests."""
    print("Testing IndexManager...")

    temp_dir = None
    try:
        # Test 1: Document database
        db_path, temp_dir = test_document_database()

        # Test 2: Full index build
        manager = test_full_index_build(db_path, temp_dir)

        # Test 3: Retrieval
        test_retrieval(manager)

        # Test 4: Incremental update
        test_incremental_update(db_path, temp_dir)

        # Test 5: Health check
        test_health_check(db_path, temp_dir)

        print("\n" + "="*50)
        print("✅ All tests passed!")
        print("="*50)

    except Exception as e:
        print("\n" + "="*50)
        print(f"❌ Tests failed: {e}")
        print("="*50)
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"\n✓ Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                print(f"\n⚠ Warning: Could not clean up {temp_dir}: {e}")


if __name__ == "__main__":
    main()

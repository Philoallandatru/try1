"""
Test Retrieval API endpoints.
"""

import io
import sys
import tempfile
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.portal_runner.retrieval_api import RetrievalAPI
from packages.source_models.document_database import DocumentDatabase


def test_retrieval_api():
    """Test Retrieval API functionality."""
    print("Testing Retrieval API...\n")

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir)

        # Initialize document database with test data
        db_path = workspace_dir / "documents.db"
        doc_db = DocumentDatabase(str(db_path))

        # Add test documents
        test_docs = [
            {
                "id": "DOC-1",
                "title": "Authentication Guide",
                "content": "How to authenticate users with OAuth2 and JWT tokens",
                "source_id": "confluence-1",
                "source_type": "confluence",
                "url": "https://example.com/auth",
                "metadata": {"space": "Engineering"},
            },
            {
                "id": "DOC-2",
                "title": "API Documentation",
                "content": "REST API endpoints for user management and authentication",
                "source_id": "confluence-1",
                "source_type": "confluence",
                "url": "https://example.com/api",
                "metadata": {"space": "Engineering"},
            },
            {
                "id": "DOC-3",
                "title": "Performance Optimization",
                "content": "Database query optimization and caching strategies",
                "source_id": "confluence-1",
                "source_type": "confluence",
                "url": "https://example.com/perf",
                "metadata": {"space": "Engineering"},
            },
        ]

        for doc in test_docs:
            doc_db.create_document(**doc)

        print(f"✓ Added {len(test_docs)} test documents\n")

        # Initialize API
        api = RetrievalAPI(workspace_dir)

        # Test 1: Get stats (before building index)
        print("=== Test 1: Get Index Stats (Before Build) ===")
        result = api.get_index_stats()
        print(f"Status: {result['status']}")
        print(f"Stats: {result['stats']}\n")

        # Test 2: Build index
        print("=== Test 2: Build Index ===")
        result = api.build_index()
        print(f"Status: {result['status']}")
        if result["status"] == "success":
            print(f"Documents indexed: {result['result']['indexed_documents']}")
            print(f"Total documents: {result['result']['total_documents']}\n")
        else:
            print(f"Error: {result.get('error')}\n")

        # Test 3: Get stats (after building index)
        print("=== Test 3: Get Index Stats (After Build) ===")
        result = api.get_index_stats()
        print(f"Status: {result['status']}")
        print(f"Total documents: {result['stats']['database']['total_documents']}")
        print(f"Indexed documents: {result['stats']['index']['document_count']}\n")

        # Test 4: Search
        print("=== Test 4: Search ===")
        queries = [
            "authentication OAuth2",
            "API endpoints",
            "database optimization",
        ]

        for query in queries:
            result = api.search(query, top_k=3)
            print(f"Query: {query}")
            print(f"Status: {result['status']}")
            print(f"Total results: {result['total_results']}")
            if result["total_results"] > 0:
                print("Top result:")
                top = result["results"][0]
                print(f"  - {top['title']} (score: {top['score']:.4f})")
            print()

        # Test 5: Health check
        print("=== Test 5: Health Check ===")
        result = api.health_check()
        print(f"Status: {result['status']}")
        print(f"Health: {result['health']}\n")

        # Test 6: Update index (incremental)
        print("=== Test 6: Update Index (Incremental) ===")
        # Add a new document
        doc_db.create_document(
            id="DOC-4",
            title="Security Best Practices",
            content="Security guidelines for web applications",
            source_id="confluence-1",
            source_type="confluence",
            url="https://example.com/security",
            metadata={"space": "Engineering"},
        )
        result = api.update_index()
        print(f"Status: {result['status']}")
        if result["status"] == "success":
            print(f"Documents added: {result['result']['added']}")
            print(f"Documents updated: {result['result']['updated']}\n")
        else:
            print(f"Error: {result.get('error')}\n")

        # Test 7: Search for new document
        print("=== Test 7: Search for New Document ===")
        result = api.search("security guidelines", top_k=3)
        print(f"Query: security guidelines")
        print(f"Total results: {result['total_results']}")
        if result["total_results"] > 0:
            print("Top result:")
            top = result["results"][0]
            print(f"  - {top['title']} (score: {top['score']:.4f})")
        print()

        # Close database connections
        doc_db.engine.dispose()
        api.index_manager.db.engine.dispose()

    print("=" * 50)
    print("✅ All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    test_retrieval_api()

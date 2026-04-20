"""
Test script for Golden Dataset.

Tests:
1. Load golden dataset
2. Validate dataset
3. Query operations
4. Language filtering
"""

import os
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.retrieval.golden_dataset import load_golden_dataset, validate_golden_dataset


def test_load_dataset():
    """Test loading golden dataset."""
    print("\n=== Test 1: Load Golden Dataset ===")

    try:
        dataset = load_golden_dataset("data/golden_dataset.yaml")
        print(f"✓ Loaded dataset: {dataset}")
        print(f"✓ Total queries: {len(dataset)}")
        print(f"✓ Metadata: {dataset.metadata}")

        return dataset

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_validate_dataset(dataset):
    """Test dataset validation."""
    print("\n=== Test 2: Validate Dataset ===")

    try:
        result = validate_golden_dataset(dataset)
        print(f"✓ Validation result: {result['valid']}")
        print(f"✓ Total queries: {result['total_queries']}")
        print(f"✓ Total expected docs: {result['total_expected_docs']}")

        if result['issues']:
            print(f"⚠ Issues found:")
            for issue in result['issues']:
                print(f"  - {issue}")
        else:
            print(f"✓ No issues found")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_query_operations(dataset):
    """Test query operations."""
    print("\n=== Test 3: Query Operations ===")

    try:
        # Get query by ID
        query = dataset.get_query("q1")
        print(f"✓ Get query by ID: {query}")
        print(f"  Query text: {query.query}")
        print(f"  Description: {query.description}")
        print(f"  Expected docs: {len(query.expected_docs)}")

        # Get relevant doc IDs
        relevant_ids = query.get_relevant_doc_ids(min_relevance=0.8)
        print(f"✓ Relevant docs (relevance >= 0.8): {relevant_ids}")

        # Get relevance score
        score = query.get_relevance_score("BUG-123")
        print(f"✓ Relevance score for BUG-123: {score}")

        # Show expected documents
        print(f"✓ Expected documents:")
        for doc in query.expected_docs:
            print(f"  - {doc.doc_id}: {doc.relevance} - {doc.reason}")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_language_filtering(dataset):
    """Test language filtering."""
    print("\n=== Test 4: Language Filtering ===")

    try:
        # Get English queries
        en_queries = dataset.get_queries_by_language("en")
        print(f"✓ English queries: {len(en_queries)}")
        print(f"  Examples:")
        for query in en_queries[:3]:
            print(f"    - {query.id}: {query.query}")

        # Get Chinese queries
        zh_queries = dataset.get_queries_by_language("zh")
        print(f"✓ Chinese queries: {len(zh_queries)}")
        print(f"  Examples:")
        for query in zh_queries[:3]:
            print(f"    - {query.id}: {query.query}")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_query_coverage(dataset):
    """Test query coverage."""
    print("\n=== Test 5: Query Coverage ===")

    try:
        # Count queries by category (inferred from query text)
        categories = {
            "authentication": 0,
            "api": 0,
            "performance": 0,
            "security": 0,
            "configuration": 0,
        }

        for query in dataset.queries:
            query_lower = query.query.lower()
            if any(word in query_lower for word in ["login", "auth", "token", "password"]):
                categories["authentication"] += 1
            if any(word in query_lower for word in ["api", "rest", "endpoint"]):
                categories["api"] += 1
            if any(word in query_lower for word in ["slow", "performance", "memory", "cpu"]):
                categories["performance"] += 1
            if any(word in query_lower for word in ["security", "xss", "sql injection", "vulnerability"]):
                categories["security"] += 1
            if any(word in query_lower for word in ["config", "deployment", "docker", "environment"]):
                categories["configuration"] += 1

        print(f"✓ Query coverage by category:")
        for category, count in categories.items():
            print(f"  - {category}: {count}")

        # Check relevance score distribution
        all_relevances = []
        for query in dataset.queries:
            for doc in query.expected_docs:
                all_relevances.append(doc.relevance)

        avg_relevance = sum(all_relevances) / len(all_relevances)
        print(f"✓ Average relevance score: {avg_relevance:.2f}")
        print(f"✓ Total expected documents: {len(all_relevances)}")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def main():
    """Run all tests."""
    print("Testing Golden Dataset...")

    try:
        # Test 1: Load dataset
        dataset = test_load_dataset()

        # Test 2: Validate dataset
        test_validate_dataset(dataset)

        # Test 3: Query operations
        test_query_operations(dataset)

        # Test 4: Language filtering
        test_language_filtering(dataset)

        # Test 5: Query coverage
        test_query_coverage(dataset)

        print("\n" + "="*50)
        print("✅ All tests passed!")
        print("="*50)

    except Exception as e:
        print("\n" + "="*50)
        print(f"❌ Tests failed: {e}")
        print("="*50)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

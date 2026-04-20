"""
Test script for Retrieval Evaluator.

Tests:
1. Load golden dataset and build index
2. Evaluate single query
3. Evaluate all queries
4. Generate evaluation report
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

from packages.retrieval.tokenizer import Tokenizer
from packages.retrieval.bm25_index import BM25Index
from packages.retrieval.bm25_retriever import BM25Retriever
from packages.retrieval.golden_dataset import load_golden_dataset
from packages.retrieval.evaluator import RetrievalEvaluator


def create_test_index():
    """Create a test index with sample documents."""
    print("\n=== Creating Test Index ===")

    # Sample documents matching golden dataset
    documents = [
        {"id": "BUG-123", "text": "Bug in login system: Special characters in password cause authentication failure"},
        {"id": "AUTH-456", "text": "Authentication service returns 401 for valid credentials"},
        {"id": "BUG-234", "text": "Session token expires too quickly, users logged out after 5 minutes"},
        {"id": "DOC-789", "text": "Documentation: Token lifecycle and refresh mechanism"},
        {"id": "DOC-101", "text": "REST API Authentication Endpoints: /login, /logout, /refresh"},
        {"id": "DOC-102", "text": "API Best Practices: Authentication, rate limiting, error handling"},
        {"id": "BUG-345", "text": "API returns 429 Too Many Requests error under normal load"},
        {"id": "DOC-201", "text": "Rate Limiting Documentation: Default limits and configuration"},
        {"id": "PERF-567", "text": "Database query performance investigation: Slow SELECT queries"},
        {"id": "PERF-568", "text": "Query optimization recommendations: Add indexes, use prepared statements"},
        {"id": "BUG-678", "text": "Memory leak in background worker process"},
        {"id": "PERF-789", "text": "Performance profiling results: CPU hotspots identified"},
        {"id": "SEC-890", "text": "XSS vulnerability in user input fields - CRITICAL"},
        {"id": "DOC-301", "text": "Security Best Practices: Input validation, output encoding, CSP"},
        {"id": "DOC-302", "text": "SQL Injection Prevention Guide: Use parameterized queries"},
        {"id": "SEC-901", "text": "Security audit findings: Multiple vulnerabilities discovered"},
        {"id": "DOC-401", "text": "Production Deployment Guide: Configuration, monitoring, rollback"},
        {"id": "DOC-402", "text": "Configuration Examples: Database, cache, logging settings"},
        {"id": "DOC-501", "text": "Docker Container Setup: Dockerfile, docker-compose, environment variables"},
        {"id": "BUG-1012", "text": "Docker container fails to start with missing environment variables"},
        {"id": "BUG-1234", "text": "500 Internal Server Error on /api/users endpoint"},
        {"id": "DOC-601", "text": "Error Handling Documentation: Status codes, error messages"},
        {"id": "HW-777", "text": "NVMe SSD Firmware Update Guide: Version 2.0 release notes"},
        {"id": "BUG-888", "text": "Firmware update fails with timeout error"},
    ]

    tokenizer = Tokenizer()
    index = BM25Index(tokenizer)
    index.build(documents, text_field="text")

    print(f"✓ Built index with {len(documents)} documents")

    return index


def test_single_query_evaluation(evaluator):
    """Test evaluating a single query."""
    print("\n=== Test 1: Single Query Evaluation ===")

    try:
        query = evaluator.golden_dataset.get_query("q1")
        result = evaluator.evaluate_query(query, top_k=10)

        print(f"✓ Query: {result.query_text}")
        print(f"✓ Precision@5: {result.precision_at_5:.4f}")
        print(f"✓ Recall@5: {result.recall_at_5:.4f}")
        print(f"✓ Average Precision: {result.average_precision:.4f}")
        print(f"✓ NDCG@5: {result.ndcg_at_5:.4f}")
        print(f"✓ MRR: {result.reciprocal_rank:.4f}")
        print(f"✓ Retrieved: {result.retrieved_docs[:5]}")
        print(f"✓ Relevant: {result.relevant_docs}")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_all_queries_evaluation(evaluator):
    """Test evaluating all queries."""
    print("\n=== Test 2: All Queries Evaluation ===")

    try:
        results, aggregate = evaluator.evaluate_all(top_k=10)

        print(f"✓ Evaluated {len(results)} queries")
        print(f"✓ Mean Average Precision: {aggregate.mean_average_precision:.4f}")
        print(f"✓ Mean Reciprocal Rank: {aggregate.mean_reciprocal_rank:.4f}")
        print(f"✓ Mean NDCG@5: {aggregate.mean_ndcg_at_5:.4f}")
        print(f"✓ Mean Precision@5: {aggregate.mean_precision_at_5:.4f}")
        print(f"✓ Mean Recall@5: {aggregate.mean_recall_at_5:.4f}")

        return results, aggregate

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def test_metric_calculations(evaluator):
    """Test individual metric calculations."""
    print("\n=== Test 3: Metric Calculations ===")

    try:
        # Test data
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = ["doc1", "doc3", "doc6"]

        # Precision@K
        p_at_3 = evaluator.precision_at_k(retrieved, relevant, 3)
        print(f"✓ Precision@3: {p_at_3:.4f} (expected: 0.6667)")

        # Recall@K
        r_at_5 = evaluator.recall_at_k(retrieved, relevant, 5)
        print(f"✓ Recall@5: {r_at_5:.4f} (expected: 0.6667)")

        # Average Precision
        ap = evaluator.average_precision(retrieved, relevant)
        print(f"✓ Average Precision: {ap:.4f}")

        # Reciprocal Rank
        rr = evaluator.reciprocal_rank(retrieved, relevant)
        print(f"✓ Reciprocal Rank: {rr:.4f} (expected: 1.0)")

        # NDCG
        relevance_scores = {"doc1": 1.0, "doc3": 0.8, "doc6": 0.6}
        ndcg = evaluator.ndcg_at_k(retrieved, relevance_scores, 5)
        print(f"✓ NDCG@5: {ndcg:.4f}")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


def main():
    """Run all tests."""
    print("Testing Retrieval Evaluator...")

    try:
        # Create test index
        index = create_test_index()
        retriever = BM25Retriever(index)

        # Load golden dataset
        print("\n=== Loading Golden Dataset ===")
        golden_dataset = load_golden_dataset("data/golden_dataset.yaml")
        print(f"✓ Loaded {len(golden_dataset)} queries")

        # Create evaluator
        evaluator = RetrievalEvaluator(retriever, golden_dataset)

        # Test 1: Single query evaluation
        test_single_query_evaluation(evaluator)

        # Test 2: All queries evaluation
        results, aggregate = test_all_queries_evaluation(evaluator)

        # Test 3: Metric calculations
        test_metric_calculations(evaluator)

        # Generate full report
        print("\n=== Generating Full Report ===")
        evaluator.print_report(results, aggregate)

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

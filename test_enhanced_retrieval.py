"""
Test script for enhanced retrieval features.
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/retrieval"


def test_basic_vs_enhanced_search():
    """Compare basic search vs enhanced search."""
    print("\n=== Test Basic vs Enhanced Search ===")

    query = "NVMe 固件升级失败"

    # Basic search
    print("\n--- Basic Search ---")
    response = requests.post(
        f"{BASE_URL}/search",
        json={"query": query, "top_k": 5}
    )
    basic_result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Total results: {basic_result.get('total_results', 0)}")
    if basic_result.get("results"):
        print("Top 3 results:")
        for i, r in enumerate(basic_result["results"][:3], 1):
            print(f"  {i}. [{r['score']:.4f}] {r['title']}")

    # Enhanced search
    print("\n--- Enhanced Search ---")
    response = requests.post(
        f"{BASE_URL}/enhanced-search",
        json={
            "query": query,
            "top_k": 5,
            "enable_expansion": True,
            "enable_reranking": True,
            "enable_filtering": True
        }
    )
    enhanced_result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Total results: {enhanced_result.get('total_results', 0)}")
    print(f"Enhancements: {enhanced_result.get('enhancements', {})}")
    if enhanced_result.get("results"):
        print("Top 3 results:")
        for i, r in enumerate(enhanced_result["results"][:3], 1):
            print(f"  {i}. [{r['score']:.4f}] {r['title']}")


def test_query_expansion():
    """Test query expansion with synonyms."""
    print("\n=== Test Query Expansion ===")

    # Add synonyms
    print("\n--- Adding Synonyms ---")
    response = requests.post(
        f"{BASE_URL}/enhanced/add-synonym",
        json={
            "term": "升级",
            "synonyms": ["更新", "刷新", "update"]
        }
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    # Search with expansion
    print("\n--- Search with Expansion ---")
    response = requests.post(
        f"{BASE_URL}/enhanced-search",
        json={
            "query": "固件升级",
            "top_k": 5,
            "enable_expansion": True,
            "enable_reranking": False,
            "enable_filtering": False
        }
    )
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Total results: {result.get('total_results', 0)}")


def test_typo_correction():
    """Test typo correction."""
    print("\n=== Test Typo Correction ===")

    # Add correction
    print("\n--- Adding Correction ---")
    response = requests.post(
        f"{BASE_URL}/enhanced/add-correction",
        json={
            "typo": "nvem",
            "correction": "nvme"
        }
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    # Search with typo
    print("\n--- Search with Typo ---")
    response = requests.post(
        f"{BASE_URL}/enhanced-search",
        json={
            "query": "nvem 驱动",  # Typo: nvem -> nvme
            "top_k": 5
        }
    )
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Total results: {result.get('total_results', 0)}")


def test_document_type_priority():
    """Test document type priority in reranking."""
    print("\n=== Test Document Type Priority ===")

    # Set priority for spec documents
    print("\n--- Setting Priority ---")
    response = requests.post(
        f"{BASE_URL}/enhanced/set-priority",
        json={
            "doc_type": "spec",
            "priority": 1.5  # Boost spec documents
        }
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    # Search with reranking
    print("\n--- Search with Reranking ---")
    response = requests.post(
        f"{BASE_URL}/enhanced-search",
        json={
            "query": "PCIe 规范",
            "top_k": 5,
            "enable_expansion": False,
            "enable_reranking": True,
            "enable_filtering": False
        }
    )
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Total results: {result.get('total_results', 0)}")
    if result.get("results"):
        print("Top 3 results:")
        for i, r in enumerate(result["results"][:3], 1):
            doc_type = r.get("metadata", {}).get("document_type", "unknown")
            print(f"  {i}. [{r['score']:.4f}] [{doc_type}] {r['title']}")


def test_selective_enhancements():
    """Test enabling/disabling individual enhancements."""
    print("\n=== Test Selective Enhancements ===")

    query = "BSOD 蓝屏"

    # Only expansion
    print("\n--- Only Expansion ---")
    response = requests.post(
        f"{BASE_URL}/enhanced-search",
        json={
            "query": query,
            "top_k": 3,
            "enable_expansion": True,
            "enable_reranking": False,
            "enable_filtering": False
        }
    )
    result = response.json()
    print(f"Enhancements: {result.get('enhancements', {})}")
    print(f"Total results: {result.get('total_results', 0)}")

    # Only reranking
    print("\n--- Only Reranking ---")
    response = requests.post(
        f"{BASE_URL}/enhanced-search",
        json={
            "query": query,
            "top_k": 3,
            "enable_expansion": False,
            "enable_reranking": True,
            "enable_filtering": False
        }
    )
    result = response.json()
    print(f"Enhancements: {result.get('enhancements', {})}")
    print(f"Total results: {result.get('total_results', 0)}")

    # Only filtering
    print("\n--- Only Filtering ---")
    response = requests.post(
        f"{BASE_URL}/enhanced-search",
        json={
            "query": query,
            "top_k": 3,
            "enable_expansion": False,
            "enable_reranking": False,
            "enable_filtering": True
        }
    )
    result = response.json()
    print(f"Enhancements: {result.get('enhancements', {})}")
    print(f"Total results: {result.get('total_results', 0)}")

    # All enhancements
    print("\n--- All Enhancements ---")
    response = requests.post(
        f"{BASE_URL}/enhanced-search",
        json={
            "query": query,
            "top_k": 3,
            "enable_expansion": True,
            "enable_reranking": True,
            "enable_filtering": True
        }
    )
    result = response.json()
    print(f"Enhancements: {result.get('enhancements', {})}")
    print(f"Total results: {result.get('total_results', 0)}")


def main():
    """Run all tests."""
    print("Testing Enhanced Retrieval Features")
    print("=" * 50)

    try:
        test_basic_vs_enhanced_search()
        test_query_expansion()
        test_typo_correction()
        test_document_type_priority()
        test_selective_enhancements()

        print("\n" + "=" * 50)
        print("All tests completed!")

    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to server.")
        print("Please make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

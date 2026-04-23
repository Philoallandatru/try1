"""
Test script for retrieval debug tools.
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/retrieval"


def test_analyze_query():
    """Test query analysis."""
    print("\n=== Test Query Analysis ===")

    response = requests.post(
        f"{BASE_URL}/debug/analyze-query",
        json={"query": "NVMe SSD 固件升级失败"}
    )

    print(f"Status: {response.status_code}")
    result = response.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))


def test_explain_score():
    """Test score explanation."""
    print("\n=== Test Score Explanation ===")

    # First, do a search to get a doc_id
    search_response = requests.post(
        f"{BASE_URL}/search",
        json={"query": "NVMe 固件升级", "top_k": 3}
    )

    search_result = search_response.json()
    if search_result.get("results"):
        doc_id = search_result["results"][0]["doc_id"]
        print(f"Explaining score for doc_id: {doc_id}")

        response = requests.post(
            f"{BASE_URL}/debug/explain-score",
            json={"query": "NVMe 固件升级", "doc_id": doc_id}
        )

        print(f"Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("No search results found")


def test_compare_scores():
    """Test score comparison."""
    print("\n=== Test Score Comparison ===")

    # First, do a search to get doc_ids
    search_response = requests.post(
        f"{BASE_URL}/search",
        json={"query": "PCIe 链路训练", "top_k": 5}
    )

    search_result = search_response.json()
    if search_result.get("results") and len(search_result["results"]) >= 3:
        doc_ids = [r["doc_id"] for r in search_result["results"][:3]]
        print(f"Comparing scores for doc_ids: {doc_ids}")

        response = requests.post(
            f"{BASE_URL}/debug/compare-scores",
            json={"query": "PCIe 链路训练", "doc_ids": doc_ids}
        )

        print(f"Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Not enough search results found")


def test_annotate_relevance():
    """Test relevance annotation."""
    print("\n=== Test Relevance Annotation ===")

    # First, do a search to get a doc_id
    search_response = requests.post(
        f"{BASE_URL}/search",
        json={"query": "BSOD 蓝屏", "top_k": 3}
    )

    search_result = search_response.json()
    if search_result.get("results"):
        doc_id = search_result["results"][0]["doc_id"]
        print(f"Annotating relevance for doc_id: {doc_id}")

        response = requests.post(
            f"{BASE_URL}/debug/annotate",
            json={
                "query": "BSOD 蓝屏",
                "doc_id": doc_id,
                "relevance": 3,
                "notes": "Highly relevant - directly addresses BSOD issue"
            }
        )

        print(f"Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Get annotations
        print("\n--- Get Annotations ---")
        response = requests.get(
            f"{BASE_URL}/debug/annotations",
            params={"query": "BSOD 蓝屏"}
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Get relevance stats
        print("\n--- Get Relevance Stats ---")
        response = requests.get(
            f"{BASE_URL}/debug/relevance-stats/BSOD 蓝屏"
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("No search results found")


def main():
    """Run all tests."""
    print("Testing Retrieval Debug Tools")
    print("=" * 50)

    try:
        test_analyze_query()
        test_explain_score()
        test_compare_scores()
        test_annotate_relevance()

        print("\n" + "=" * 50)
        print("All tests completed!")

    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to server.")
        print("Please make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()

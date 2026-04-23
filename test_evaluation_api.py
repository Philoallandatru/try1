"""
Test script for Retrieval Evaluation API.

Tests the evaluation management functionality.
"""

from apps.portal_runner.retrieval_api import RetrievalAPI
from pathlib import Path


def test_evaluation_api():
    """Test evaluation API functionality."""

    # Initialize API
    workspace_dir = ".tmp/portal-runner/workspaces/demo"
    api = RetrievalAPI(workspace_dir)

    print("=" * 60)
    print("Testing Retrieval Evaluation API")
    print("=" * 60)

    # Test 1: List datasets
    print("\n[Test 1] List datasets")
    result = api.list_datasets()
    print(f"Status: {result['status']}")
    print(f"Datasets: {len(result.get('datasets', []))}")
    for ds in result.get('datasets', []):
        print(f"  - {ds['dataset_id']}: {ds['name']} ({ds['total_queries']} queries)")

    # Test 2: Upload dataset
    print("\n[Test 2] Upload dataset")
    with open("data/golden_dataset.yaml", "r", encoding="utf-8") as f:
        content = f.read()

    result = api.upload_dataset(content, "test_dataset")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        ds = result['dataset']
        print(f"Uploaded: {ds['name']}")
        print(f"  - Queries: {ds['total_queries']}")
        print(f"  - Documents: {ds['total_documents']}")
        print(f"  - Categories: {ds['categories']}")

    # Test 3: Get dataset
    print("\n[Test 3] Get dataset")
    result = api.get_dataset("test_dataset")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        ds = result['dataset']
        print(f"Dataset: {ds['name']}")
        print(f"  - Version: {ds['version']}")
        print(f"  - Created: {ds['created_at']}")

    # Test 4: List evaluation results
    print("\n[Test 4] List evaluation results")
    result = api.list_evaluation_results()
    print(f"Status: {result['status']}")
    print(f"Results: {len(result.get('results', []))}")
    for r in result.get('results', [])[:5]:
        print(f"  - {r['run_id']}: {r['dataset_name']} (MAP: {r['aggregate_metrics']['mean_average_precision']:.3f})")

    # Test 5: Run evaluation (without saving)
    print("\n[Test 5] Run evaluation (dry run)")
    result = api.evaluate(
        golden_dataset_path="data/golden_dataset.yaml",
        top_k=10,
        save_result=False,
    )
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        metrics = result['aggregate_metrics']
        print(f"Metrics:")
        print(f"  - Total Queries: {metrics['total_queries']}")
        print(f"  - MAP: {metrics['mean_average_precision']:.3f}")
        print(f"  - MRR: {metrics['mean_reciprocal_rank']:.3f}")
        print(f"  - NDCG@5: {metrics['mean_ndcg_at_5']:.3f}")
        print(f"  - P@5: {metrics['mean_precision_at_5']:.3f}")
        print(f"  - R@5: {metrics['mean_recall_at_5']:.3f}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_evaluation_api()

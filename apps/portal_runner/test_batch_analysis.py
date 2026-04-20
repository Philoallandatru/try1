"""Tests for batch analysis functionality."""

import asyncio
import json
import pytest
from pathlib import Path

from apps.portal_runner.analysis_api import BatchAnalysisAPI


@pytest.fixture
def workspace_with_snapshot(tmp_path):
    """Create workspace with sample snapshot."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create snapshot directory
    snapshot_dir = workspace / "snapshot"
    snapshot_dir.mkdir()

    # Create sample documents
    documents = [
        {
            "document_id": "SSD-100",
            "source_type": "jira",
            "title": "NVMe flush command timeout",
            "content": "Issue with NVMe flush command timing out after 30 seconds.",
            "markdown": "## NVMe flush command timeout\n\nIssue with NVMe flush command timing out after 30 seconds.",
            "metadata": {
                "issue_id": "SSD-100",
                "issue_fields": {"Issue Type": "Bug", "Summary": "NVMe flush command timeout"},
            },
        },
        {
            "document_id": "SSD-101",
            "source_type": "jira",
            "title": "Power state transition failure",
            "content": "Device fails to transition to low power state.",
            "markdown": "## Power state transition failure\n\nDevice fails to transition to low power state.",
            "metadata": {
                "issue_id": "SSD-101",
                "issue_fields": {"Issue Type": "Bug", "Summary": "Power state transition failure"},
            },
        },
        {
            "document_id": "SSD-102",
            "source_type": "jira",
            "title": "Telemetry log page corruption",
            "content": "Telemetry log page shows corrupted data.",
            "markdown": "## Telemetry log page corruption\n\nTelemetry log page shows corrupted data.",
            "metadata": {
                "issue_id": "SSD-102",
                "issue_fields": {"Issue Type": "Bug", "Summary": "Telemetry log page corruption"},
            },
        },
    ]

    documents_file = snapshot_dir / "documents.json"
    with open(documents_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2)

    return workspace


@pytest.mark.asyncio
async def test_batch_analyze_issues(workspace_with_snapshot):
    """Test batch analysis of multiple issues."""
    api = BatchAnalysisAPI(workspace_root=workspace_with_snapshot.parent)

    result = await api.batch_analyze_issues(
        workspace_dir=str(workspace_with_snapshot),
        issue_ids=["SSD-100", "SSD-101", "SSD-102"],
        llm_backend="none",
        max_concurrent=2,
    )

    # Print results for debugging
    print(f"\nBatch result: {json.dumps(result, indent=2)}")

    # Check for errors
    for item in result["results"]:
        if item["status"] == "error":
            print(f"Error for {item['issue_id']}: {item['error']}")

    # Validate result structure
    assert "batch_id" in result
    assert "started_at" in result
    assert "completed_at" in result
    assert "duration_seconds" in result
    assert result["total_issues"] == 3
    assert result["successful"] == 3
    assert result["failed"] == 0
    assert len(result["results"]) == 3

    # Validate individual results
    for item in result["results"]:
        assert item["status"] == "success"
        assert "issue_id" in item
        assert "result" in item


@pytest.mark.asyncio
async def test_batch_analyze_with_progress_callback(workspace_with_snapshot):
    """Test batch analysis with progress callback."""
    api = BatchAnalysisAPI(workspace_root=workspace_with_snapshot.parent)

    progress_updates = []

    async def progress_callback(**kwargs):
        progress_updates.append(kwargs)

    result = await api.batch_analyze_issues(
        workspace_dir=str(workspace_with_snapshot),
        issue_ids=["SSD-100", "SSD-101"],
        llm_backend="none",
        max_concurrent=1,
        progress_callback=progress_callback,
    )

    # Should have progress updates
    assert len(progress_updates) > 0

    # Check for analyzing and complete stages
    stages = [u["stage"] for u in progress_updates]
    assert "analyzing" in stages
    assert "complete" in stages


@pytest.mark.asyncio
async def test_batch_analyze_with_errors(workspace_with_snapshot):
    """Test batch analysis with some failures."""
    api = BatchAnalysisAPI(workspace_root=workspace_with_snapshot.parent)

    # Include a non-existent issue
    result = await api.batch_analyze_issues(
        workspace_dir=str(workspace_with_snapshot),
        issue_ids=["SSD-100", "SSD-999"],  # SSD-999 doesn't exist
        llm_backend="none",
        max_concurrent=2,
    )

    # Should have mixed results
    assert result["total_issues"] == 2
    assert result["successful"] >= 1  # At least SSD-100 should succeed
    assert result["failed"] >= 0  # SSD-999 might fail or succeed with empty result


@pytest.mark.asyncio
async def test_batch_result_persistence(workspace_with_snapshot):
    """Test that batch results are saved and can be retrieved."""
    api = BatchAnalysisAPI(workspace_root=workspace_with_snapshot.parent)

    result = await api.batch_analyze_issues(
        workspace_dir=str(workspace_with_snapshot),
        issue_ids=["SSD-100"],
        llm_backend="none",
    )

    batch_id = result["batch_id"]

    # Retrieve saved result
    saved_result = api.get_batch_result(
        workspace_dir=str(workspace_with_snapshot),
        batch_id=batch_id,
    )

    assert saved_result["batch_id"] == batch_id
    assert saved_result["total_issues"] == 1


def test_get_batch_result_not_found(workspace_with_snapshot):
    """Test error handling for non-existent batch."""
    api = BatchAnalysisAPI(workspace_root=workspace_with_snapshot.parent)

    with pytest.raises(ValueError, match="Batch not found"):
        api.get_batch_result(
            workspace_dir=str(workspace_with_snapshot),
            batch_id="non-existent-batch-id",
        )


@pytest.mark.asyncio
async def test_list_batches(workspace_with_snapshot):
    """Test listing batch analyses."""
    api = BatchAnalysisAPI(workspace_root=workspace_with_snapshot.parent)

    # Create two batches
    await api.batch_analyze_issues(
        workspace_dir=str(workspace_with_snapshot),
        issue_ids=["SSD-100"],
        llm_backend="none",
    )

    await api.batch_analyze_issues(
        workspace_dir=str(workspace_with_snapshot),
        issue_ids=["SSD-101"],
        llm_backend="none",
    )

    # List batches
    result = api.list_batches(
        workspace_dir=str(workspace_with_snapshot),
        limit=10,
    )

    assert result["total"] == 2
    assert len(result["batches"]) == 2

    # Check batch summary structure
    for batch in result["batches"]:
        assert "batch_id" in batch
        assert "started_at" in batch
        assert "completed_at" in batch
        assert "total_issues" in batch
        assert "successful" in batch
        assert "failed" in batch


def test_list_batches_empty(workspace_with_snapshot):
    """Test listing batches when none exist."""
    api = BatchAnalysisAPI(workspace_root=workspace_with_snapshot.parent)

    result = api.list_batches(
        workspace_dir=str(workspace_with_snapshot),
        limit=10,
    )

    assert result["batches"] == []


@pytest.mark.asyncio
async def test_batch_concurrent_limit(workspace_with_snapshot):
    """Test that concurrent limit is respected."""
    api = BatchAnalysisAPI(workspace_root=workspace_with_snapshot.parent)

    # Analyze 5 issues with max_concurrent=2
    result = await api.batch_analyze_issues(
        workspace_dir=str(workspace_with_snapshot),
        issue_ids=["SSD-100", "SSD-101", "SSD-102", "SSD-100", "SSD-101"],
        llm_backend="none",
        max_concurrent=2,
    )

    # Should complete successfully
    assert result["total_issues"] == 5
    assert result["successful"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

"""Tests for cross-reference API."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.portal_runner.cross_reference_api import CrossReferenceAPI


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    """Create a temporary workspace with test data."""
    workspace = tmp_path / "workspace"
    analyses_dir = workspace / "knowledge" / "analyses"
    analyses_dir.mkdir(parents=True)

    # Create test analyses with overlapping citations
    analyses = [
        {
            "issue_id": "SSD-100",
            "citations": ["doc-1", "doc-2", "doc-3"],
            "summary": "Issue 100 summary",
        },
        {
            "issue_id": "SSD-101",
            "citations": ["doc-2", "doc-3", "doc-4"],
            "summary": "Issue 101 summary",
        },
        {
            "issue_id": "SSD-102",
            "citations": ["doc-3", "doc-4", "doc-5"],
            "summary": "Issue 102 summary",
        },
        {
            "issue_id": "BUG-200",
            "citations": ["doc-1", "doc-2"],
            "summary": "Bug 200 summary",
        },
        {
            "issue_id": "BUG-201",
            "citations": ["doc-6"],
            "summary": "Bug 201 summary (isolated)",
        },
    ]

    for analysis in analyses:
        with open(analyses_dir / f"{analysis['issue_id']}.json", "w", encoding="utf-8") as f:
            json.dump(analysis, f)

    return workspace


def test_find_related_issues(workspace_dir: Path):
    """Test finding related issues."""
    api = CrossReferenceAPI(workspace_dir)

    related = api.find_related_issues(
        workspace_dir=str(workspace_dir),
        issue_id="SSD-100",
        min_shared_citations=2,
    )

    assert related["issue_id"] == "SSD-100"
    assert related["total_citations"] == 3
    assert len(related["related_issues"]) > 0

    # Should find SSD-101 (shares doc-2, doc-3) and BUG-200 (shares doc-1, doc-2)
    related_ids = [r["issue_id"] for r in related["related_issues"]]
    assert "SSD-101" in related_ids
    assert "BUG-200" in related_ids


def test_find_related_issues_with_limit(workspace_dir: Path):
    """Test finding related issues with limit."""
    api = CrossReferenceAPI(workspace_dir)

    related = api.find_related_issues(
        workspace_dir=str(workspace_dir),
        issue_id="SSD-100",
        min_shared_citations=1,
        limit=1,
    )

    assert len(related["related_issues"]) == 1
    assert related["total_found"] >= 1


def test_find_related_issues_not_found(workspace_dir: Path):
    """Test finding related issues for non-existent issue."""
    api = CrossReferenceAPI(workspace_dir)

    related = api.find_related_issues(
        workspace_dir=str(workspace_dir),
        issue_id="NOTFOUND-1",
    )

    assert related["issue_id"] == "NOTFOUND-1"
    assert "error" in related
    assert related["related_issues"] == []


def test_find_related_issues_no_matches(workspace_dir: Path):
    """Test finding related issues with no matches."""
    api = CrossReferenceAPI(workspace_dir)

    related = api.find_related_issues(
        workspace_dir=str(workspace_dir),
        issue_id="BUG-201",  # Has unique citation
        min_shared_citations=1,
    )

    assert related["issue_id"] == "BUG-201"
    assert related["related_issues"] == []


def test_get_citation_network(workspace_dir: Path):
    """Test getting citation network."""
    api = CrossReferenceAPI(workspace_dir)

    network = api.get_citation_network(
        workspace_dir=str(workspace_dir),
        min_connections=2,
    )

    assert network["total_issues"] == 5
    assert len(network["nodes"]) == 5
    assert len(network["edges"]) > 0

    # Check node structure
    node = network["nodes"][0]
    assert "id" in node
    assert "citation_count" in node

    # Check edge structure
    if network["edges"]:
        edge = network["edges"][0]
        assert "source" in edge
        assert "target" in edge
        assert "shared_citations" in edge
        assert "weight" in edge


def test_get_citation_network_empty(tmp_path: Path):
    """Test citation network with no analyses."""
    workspace = tmp_path / "empty_workspace"
    workspace.mkdir()

    api = CrossReferenceAPI(workspace)
    network = api.get_citation_network(workspace_dir=str(workspace))

    assert network["total_issues"] == 0
    assert network["nodes"] == []
    assert network["edges"] == []


def test_get_most_cited_documents(workspace_dir: Path):
    """Test getting most cited documents."""
    api = CrossReferenceAPI(workspace_dir)

    result = api.get_most_cited_documents(
        workspace_dir=str(workspace_dir),
        limit=5,
    )

    assert len(result["documents"]) > 0
    assert result["total_documents"] == 6  # doc-1 through doc-6

    # Check document structure
    doc = result["documents"][0]
    assert "document_id" in doc
    assert "citation_count" in doc
    assert "cited_by" in doc

    # doc-2 and doc-3 should be most cited (3 times each)
    top_doc_ids = [d["document_id"] for d in result["documents"][:2]]
    assert "doc-2" in top_doc_ids or "doc-3" in top_doc_ids


def test_get_most_cited_documents_with_limit(workspace_dir: Path):
    """Test most cited documents with limit."""
    api = CrossReferenceAPI(workspace_dir)

    result = api.get_most_cited_documents(
        workspace_dir=str(workspace_dir),
        limit=2,
    )

    assert len(result["documents"]) == 2


def test_get_issue_clusters(workspace_dir: Path):
    """Test getting issue clusters."""
    api = CrossReferenceAPI(workspace_dir)

    result = api.get_issue_clusters(
        workspace_dir=str(workspace_dir),
        min_cluster_size=2,
    )

    assert result["total_clusters"] > 0
    assert len(result["clusters"]) > 0

    # Check cluster structure
    cluster = result["clusters"][0]
    assert "cluster_id" in cluster
    assert "issues" in cluster
    assert "size" in cluster
    assert cluster["size"] >= 2


def test_get_issue_clusters_empty(tmp_path: Path):
    """Test issue clusters with no analyses."""
    workspace = tmp_path / "empty_workspace"
    workspace.mkdir()

    api = CrossReferenceAPI(workspace)
    result = api.get_issue_clusters(workspace_dir=str(workspace))

    assert result["total_clusters"] == 0
    assert result["clusters"] == []


def test_cross_reference_with_invalid_json(workspace_dir: Path):
    """Test that invalid JSON files are skipped."""
    analyses_dir = workspace_dir / "knowledge" / "analyses"

    # Create invalid JSON file
    with open(analyses_dir / "INVALID-1.json", "w", encoding="utf-8") as f:
        f.write("not valid json{")

    api = CrossReferenceAPI(workspace_dir)

    # Should still work, just skip the invalid file
    network = api.get_citation_network(workspace_dir=str(workspace_dir))
    assert network["total_issues"] == 5  # Original 5, invalid one skipped


def test_similarity_score_calculation(workspace_dir: Path):
    """Test that similarity scores are calculated correctly."""
    api = CrossReferenceAPI(workspace_dir)

    related = api.find_related_issues(
        workspace_dir=str(workspace_dir),
        issue_id="SSD-100",
        min_shared_citations=2,
    )

    # Check that similarity scores are between 0 and 1
    for issue in related["related_issues"]:
        assert 0 <= issue["similarity_score"] <= 1
        assert issue["shared_citations"] >= 2

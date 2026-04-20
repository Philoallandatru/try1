"""Tests for trends API."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from apps.portal_runner.trends_api import TrendsAPI


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    """Create a temporary workspace with test data."""
    workspace = tmp_path / "workspace"
    analyses_dir = workspace / "knowledge" / "analyses"
    analyses_dir.mkdir(parents=True)

    # Create test analyses with different dates and issue types
    base_date = datetime.now()

    # SSD issues
    for i in range(5):
        date = base_date - timedelta(days=i)
        analysis = {
            "issue_id": f"SSD-{100 + i}",
            "timestamp": date.isoformat(),
            "citations": [f"doc-{j}" for j in range(3 + i)],  # Varying citation counts
            "summary": f"Test analysis {i}",
        }
        with open(analyses_dir / f"SSD-{100 + i}.json", "w", encoding="utf-8") as f:
            json.dump(analysis, f)

    # BUG issues
    for i in range(3):
        date = base_date - timedelta(days=i * 2)
        analysis = {
            "issue_id": f"BUG-{200 + i}",
            "timestamp": date.isoformat(),
            "citations": [f"doc-{j}" for j in range(2)],
            "summary": f"Bug analysis {i}",
        }
        with open(analyses_dir / f"BUG-{200 + i}.json", "w", encoding="utf-8") as f:
            json.dump(analysis, f)

    return workspace


def test_get_analysis_trends(workspace_dir: Path):
    """Test getting overall analysis trends."""
    api = TrendsAPI(workspace_dir)

    trends = api.get_analysis_trends(workspace_dir=str(workspace_dir))

    assert trends["total_analyses"] == 8
    assert "daily_counts" in trends
    assert "issue_type_distribution" in trends
    assert trends["issue_type_distribution"]["SSD"] == 5
    assert trends["issue_type_distribution"]["BUG"] == 3
    assert trends["average_citations"] > 0


def test_get_analysis_trends_with_date_range(workspace_dir: Path):
    """Test getting trends with date filtering."""
    api = TrendsAPI(workspace_dir)

    # Get trends for last 2 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)

    trends = api.get_analysis_trends(
        workspace_dir=str(workspace_dir),
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )

    # Should have fewer analyses than total
    assert trends["total_analyses"] < 8
    assert trends["total_analyses"] > 0


def test_get_analysis_trends_empty_workspace(tmp_path: Path):
    """Test trends with no analyses."""
    workspace = tmp_path / "empty_workspace"
    workspace.mkdir()

    api = TrendsAPI(workspace)
    trends = api.get_analysis_trends(workspace_dir=str(workspace))

    assert trends["total_analyses"] == 0
    assert trends["daily_counts"] == {}
    assert trends["issue_type_distribution"] == {}
    assert trends["average_citations"] == 0


def test_get_issue_type_trends(workspace_dir: Path):
    """Test getting trends for specific issue type."""
    api = TrendsAPI(workspace_dir)

    trends = api.get_issue_type_trends(
        workspace_dir=str(workspace_dir),
        issue_type="SSD",
        days=30,
    )

    assert trends["issue_type"] == "SSD"
    assert trends["total_count"] == 5
    assert "daily_counts" in trends
    assert trends["average_citations"] > 0


def test_get_issue_type_trends_not_found(workspace_dir: Path):
    """Test getting trends for non-existent issue type."""
    api = TrendsAPI(workspace_dir)

    trends = api.get_issue_type_trends(
        workspace_dir=str(workspace_dir),
        issue_type="NOTFOUND",
        days=30,
    )

    assert trends["issue_type"] == "NOTFOUND"
    assert trends["total_count"] == 0
    assert trends["daily_counts"] == {}


def test_get_citation_trends(workspace_dir: Path):
    """Test getting citation trends."""
    api = TrendsAPI(workspace_dir)

    trends = api.get_citation_trends(
        workspace_dir=str(workspace_dir),
        days=30,
    )

    assert trends["days"] == 30
    assert "daily_citation_counts" in trends
    assert "daily_averages" in trends
    assert trends["average_per_analysis"] > 0


def test_get_citation_trends_with_days_filter(workspace_dir: Path):
    """Test citation trends with custom day range."""
    api = TrendsAPI(workspace_dir)

    trends = api.get_citation_trends(
        workspace_dir=str(workspace_dir),
        days=7,
    )

    assert trends["days"] == 7
    # Should have data for recent days
    assert len(trends["daily_citation_counts"]) > 0


def test_trends_with_invalid_json(workspace_dir: Path):
    """Test that invalid JSON files are skipped."""
    analyses_dir = workspace_dir / "knowledge" / "analyses"

    # Create invalid JSON file
    with open(analyses_dir / "INVALID-1.json", "w", encoding="utf-8") as f:
        f.write("not valid json{")

    api = TrendsAPI(workspace_dir)
    trends = api.get_analysis_trends(workspace_dir=str(workspace_dir))

    # Should still work, just skip the invalid file
    assert trends["total_analyses"] == 8  # Original 8, invalid one skipped


def test_trends_with_missing_timestamp(workspace_dir: Path):
    """Test that analyses without timestamps are skipped."""
    analyses_dir = workspace_dir / "knowledge" / "analyses"

    # Create analysis without timestamp
    analysis = {
        "issue_id": "TEST-1",
        "citations": ["doc-1"],
        "summary": "No timestamp",
    }
    with open(analyses_dir / "TEST-1.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f)

    api = TrendsAPI(workspace_dir)
    trends = api.get_analysis_trends(workspace_dir=str(workspace_dir))

    # Should skip the one without timestamp
    assert trends["total_analyses"] == 8  # Original 8, new one skipped

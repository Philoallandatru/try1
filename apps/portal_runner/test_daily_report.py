"""Tests for daily report generation."""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from apps.portal_runner.analysis_api import AnalysisAPI


@pytest.fixture
def workspace_with_analyses(tmp_path):
    """Create workspace with sample analyses."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    knowledge_dir = workspace / "knowledge" / "issues"
    knowledge_dir.mkdir(parents=True)

    # Create sample analyses
    analyses = [
        {
            "issue_id": "SSD-100",
            "title": "NVMe flush command timeout",
            "citation_count": 15,
            "analyzed_at": "2026-04-20T10:00:00Z",
        },
        {
            "issue_id": "SSD-101",
            "title": "Power state transition failure",
            "citation_count": 8,
            "analyzed_at": "2026-04-20T11:00:00Z",
        },
        {
            "issue_id": "SSD-102",
            "title": "Telemetry log page corruption",
            "citation_count": 22,
            "analyzed_at": "2026-04-20T12:00:00Z",
        },
        {
            "issue_id": "SSD-103",
            "title": "SPOR rebuild metadata error",
            "citation_count": 5,
            "analyzed_at": "2026-04-20T13:00:00Z",
        },
        {
            "issue_id": "SSD-104",
            "title": "Queue creation race condition",
            "citation_count": 12,
            "analyzed_at": "2026-04-20T14:00:00Z",
        },
    ]

    for analysis in analyses:
        issue_dir = knowledge_dir / analysis["issue_id"]
        issue_dir.mkdir()

        # Save analysis markdown
        analysis_md = issue_dir / "analysis.md"
        analysis_md.write_text(f"# Analysis for {analysis['issue_id']}\n\nSample analysis content.")

        # Save metadata
        metadata = {
            "issue_id": analysis["issue_id"],
            "title": analysis["title"],
            "analyzed_at": analysis["analyzed_at"],
            "citation_count": analysis["citation_count"],
            "analysis_profile": "strict",
        }
        metadata_file = issue_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))

    return workspace


def test_generate_daily_report_fast_mode(workspace_with_analyses):
    """Test fast mode daily report generation (< 5s)."""
    api = AnalysisAPI(workspace_root=workspace_with_analyses.parent)

    result = api.generate_daily_report(
        workspace_dir=str(workspace_with_analyses),
        date="2026-04-20",
        mode="fast",
    )

    # Validate result structure
    assert result["date"] == "2026-04-20"
    assert result["mode"] == "fast"
    assert result["total_issues"] == 5
    assert len(result["sections"]) == 2  # Summary + Recent Analyses

    # Validate sections
    sections = {s["title"]: s for s in result["sections"]}
    assert "Summary" in sections
    assert "Recent Analyses" in sections

    # Fast mode should show top 5 recent issues
    recent_content = sections["Recent Analyses"]["content"]
    assert "SSD-104" in recent_content  # Most recent
    assert "SSD-103" in recent_content
    assert "SSD-102" in recent_content
    assert "SSD-101" in recent_content
    assert "SSD-100" in recent_content


def test_generate_daily_report_full_mode(workspace_with_analyses):
    """Test full mode daily report generation (< 30s)."""
    api = AnalysisAPI(workspace_root=workspace_with_analyses.parent)

    result = api.generate_daily_report(
        workspace_dir=str(workspace_with_analyses),
        date="2026-04-20",
        mode="full",
    )

    # Validate result structure
    assert result["date"] == "2026-04-20"
    assert result["mode"] == "full"
    assert result["total_issues"] == 5
    assert len(result["sections"]) == 3  # Summary + Recent + Top by Citations

    # Validate sections
    sections = {s["title"]: s for s in result["sections"]}
    assert "Summary" in sections
    assert "Recent Analyses" in sections
    assert "Top Issues by Citations" in sections

    # Top by citations should show SSD-102 first (22 citations)
    top_content = sections["Top Issues by Citations"]["content"]
    lines = top_content.split("\n")
    assert "SSD-102" in lines[0]  # Highest citation count
    assert "22 citations" in lines[0]


def test_daily_report_persistence(workspace_with_analyses):
    """Test that daily report is saved to knowledge base."""
    api = AnalysisAPI(workspace_root=workspace_with_analyses.parent)

    result = api.generate_daily_report(
        workspace_dir=str(workspace_with_analyses),
        date="2026-04-20",
        mode="fast",
    )

    # Check report file exists
    report_dir = workspace_with_analyses / "knowledge" / "reports" / "daily" / "2026-04-20"
    assert report_dir.exists()

    report_md = report_dir / "report.md"
    assert report_md.exists()

    # Validate markdown content
    content = report_md.read_text()
    assert "# Daily Report - 2026-04-20" in content
    assert "## Summary" in content
    assert "## Recent Analyses" in content
    assert "Total analyzed issues: 5" in content

    # Check metadata file
    metadata_file = report_dir / "metadata.json"
    assert metadata_file.exists()

    metadata = json.loads(metadata_file.read_text())
    assert metadata["mode"] == "fast"
    assert metadata["total_issues"] == 5
    assert "generated_at" in metadata


def test_daily_report_empty_knowledge_base(tmp_path):
    """Test daily report with empty knowledge base."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    api = AnalysisAPI(workspace_root=workspace.parent)

    result = api.generate_daily_report(
        workspace_dir=str(workspace),
        date="2026-04-20",
        mode="fast",
    )

    # Should return empty report
    assert result["date"] == "2026-04-20"
    assert result["mode"] == "fast"
    assert result["total_issues"] == 0
    assert len(result["sections"]) == 0


def test_daily_report_default_date(workspace_with_analyses):
    """Test daily report with default date (today)."""
    api = AnalysisAPI(workspace_root=workspace_with_analyses.parent)

    result = api.generate_daily_report(
        workspace_dir=str(workspace_with_analyses),
        mode="fast",
    )

    # Should use today's date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert result["date"] == today
    assert result["total_issues"] == 5


def test_daily_report_sorting_by_citations(workspace_with_analyses):
    """Test that full mode correctly sorts by citation count."""
    api = AnalysisAPI(workspace_root=workspace_with_analyses.parent)

    result = api.generate_daily_report(
        workspace_dir=str(workspace_with_analyses),
        date="2026-04-20",
        mode="full",
    )

    sections = {s["title"]: s for s in result["sections"]}
    top_content = sections["Top Issues by Citations"]["content"]
    lines = top_content.split("\n")

    # Extract citation counts from lines
    citation_counts = []
    for line in lines:
        if "citations)" in line:
            count = int(line.split("(")[1].split(" citations")[0])
            citation_counts.append(count)

    # Should be sorted in descending order
    assert citation_counts == sorted(citation_counts, reverse=True)
    assert citation_counts[0] == 22  # SSD-102
    assert citation_counts[1] == 15  # SSD-100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

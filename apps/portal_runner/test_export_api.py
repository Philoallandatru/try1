"""Tests for export API functionality."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from apps.portal_runner.export_api import ExportAPI


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace with test data."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create knowledge directory structure
    knowledge = workspace / "knowledge"
    analyses = knowledge / "analyses"
    daily_reports = knowledge / "daily_reports"
    analyses.mkdir(parents=True)
    daily_reports.mkdir(parents=True)

    # Create batch_results directory
    batch_results = workspace / "batch_results"
    batch_results.mkdir()

    # Create test analysis
    analysis = {
        "issue_id": "TEST-100",
        "timestamp": "2026-04-20T10:00:00Z",
        "summary": "This is a test analysis summary.",
        "citations": [
            {
                "document_id": "DOC-1",
                "score": 0.95,
                "content": "Test citation content",
            }
        ],
        "recommendations": [
            "Recommendation 1",
            "Recommendation 2",
        ],
    }
    with open(analyses / "TEST-100.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f)

    # Create test daily report
    report = {
        "date": "2026-04-20",
        "timestamp": "2026-04-20T23:59:59Z",
        "total_issues": 2,
        "summary": "Daily summary",
        "issues": [
            {"issue_id": "TEST-100", "summary": "Issue 1 summary"},
            {"issue_id": "TEST-101", "summary": "Issue 2 summary"},
        ],
    }
    with open(daily_reports / "2026-04-20.json", "w", encoding="utf-8") as f:
        json.dump(report, f)

    # Create test batch result
    batch = {
        "batch_id": "batch-123",
        "started_at": "2026-04-20T10:00:00Z",
        "completed_at": "2026-04-20T10:05:00Z",
        "total": 2,
        "completed": 2,
        "failed": 0,
        "results": [
            {
                "issue_id": "TEST-100",
                "success": True,
                "result": {"summary": "Analysis 1"},
            },
            {
                "issue_id": "TEST-101",
                "success": True,
                "result": {"summary": "Analysis 2"},
            },
        ],
    }
    with open(batch_results / "batch-123.json", "w", encoding="utf-8") as f:
        json.dump(batch, f)

    return workspace


def test_export_analysis_markdown(temp_workspace: Path):
    """Test exporting analysis as Markdown."""
    export_api = ExportAPI(temp_workspace)

    markdown = export_api.export_analysis_markdown(
        workspace_dir=str(temp_workspace),
        issue_id="TEST-100",
    )

    assert "# Analysis Report: TEST-100" in markdown
    assert "This is a test analysis summary" in markdown
    assert "## Citations" in markdown
    assert "DOC-1" in markdown
    assert "## Recommendations" in markdown
    assert "Recommendation 1" in markdown


def test_export_analysis_html(temp_workspace: Path):
    """Test exporting analysis as HTML."""
    export_api = ExportAPI(temp_workspace)

    html = export_api.export_analysis_html(
        workspace_dir=str(temp_workspace),
        issue_id="TEST-100",
    )

    assert "<!DOCTYPE html>" in html
    assert "<h1>Analysis Report: TEST-100</h1>" in html
    assert "This is a test analysis summary" in html
    assert "<h2>Citations</h2>" in html


def test_export_analysis_not_found(temp_workspace: Path):
    """Test exporting non-existent analysis."""
    export_api = ExportAPI(temp_workspace)

    with pytest.raises(ValueError, match="Analysis not found"):
        export_api.export_analysis_markdown(
            workspace_dir=str(temp_workspace),
            issue_id="NONEXISTENT",
        )


def test_export_daily_report_markdown(temp_workspace: Path):
    """Test exporting daily report as Markdown."""
    export_api = ExportAPI(temp_workspace)

    markdown = export_api.export_daily_report_markdown(
        workspace_dir=str(temp_workspace),
        date="2026-04-20",
    )

    assert "# Daily Report: 2026-04-20" in markdown
    assert "**Total Issues Analyzed:** 2" in markdown
    assert "Daily summary" in markdown
    assert "TEST-100" in markdown
    assert "TEST-101" in markdown


def test_export_daily_report_html(temp_workspace: Path):
    """Test exporting daily report as HTML."""
    export_api = ExportAPI(temp_workspace)

    html = export_api.export_daily_report_html(
        workspace_dir=str(temp_workspace),
        date="2026-04-20",
    )

    assert "<!DOCTYPE html>" in html
    assert "<h1>Daily Report: 2026-04-20</h1>" in html
    assert "Daily summary" in html


def test_export_daily_report_not_found(temp_workspace: Path):
    """Test exporting non-existent daily report."""
    export_api = ExportAPI(temp_workspace)

    with pytest.raises(ValueError, match="Daily report not found"):
        export_api.export_daily_report_markdown(
            workspace_dir=str(temp_workspace),
            date="2026-01-01",
        )


def test_export_batch_result_markdown(temp_workspace: Path):
    """Test exporting batch result as Markdown."""
    export_api = ExportAPI(temp_workspace)

    markdown = export_api.export_batch_result_markdown(
        workspace_dir=str(temp_workspace),
        batch_id="batch-123",
    )

    assert "# Batch Analysis Report: batch-123" in markdown
    assert "**Total Issues:** 2" in markdown
    assert "**Completed:** 2" in markdown
    assert "**Failed:** 0" in markdown
    assert "✓ TEST-100" in markdown
    assert "✓ TEST-101" in markdown


def test_export_batch_result_html(temp_workspace: Path):
    """Test exporting batch result as HTML."""
    export_api = ExportAPI(temp_workspace)

    html = export_api.export_batch_result_html(
        workspace_dir=str(temp_workspace),
        batch_id="batch-123",
    )

    assert "<!DOCTYPE html>" in html
    assert "<h1>Batch Analysis Report: batch-123</h1>" in html
    assert "TEST-100" in html


def test_export_batch_result_not_found(temp_workspace: Path):
    """Test exporting non-existent batch result."""
    export_api = ExportAPI(temp_workspace)

    with pytest.raises(ValueError, match="Batch result not found"):
        export_api.export_batch_result_markdown(
            workspace_dir=str(temp_workspace),
            batch_id="nonexistent",
        )


def test_export_batch_with_failures(temp_workspace: Path):
    """Test exporting batch result with failures."""
    export_api = ExportAPI(temp_workspace)

    # Create batch with failures
    batch = {
        "batch_id": "batch-456",
        "started_at": "2026-04-20T10:00:00Z",
        "completed_at": "2026-04-20T10:05:00Z",
        "total": 2,
        "completed": 1,
        "failed": 1,
        "results": [
            {
                "issue_id": "TEST-100",
                "success": True,
                "result": {"summary": "Success"},
            },
            {
                "issue_id": "TEST-101",
                "success": False,
                "error": "Analysis failed",
            },
        ],
    }
    batch_file = temp_workspace / "batch_results" / "batch-456.json"
    with open(batch_file, "w", encoding="utf-8") as f:
        json.dump(batch, f)

    markdown = export_api.export_batch_result_markdown(
        workspace_dir=str(temp_workspace),
        batch_id="batch-456",
    )

    assert "✓ TEST-100" in markdown
    assert "✗ TEST-101" in markdown
    assert "**Error:** Analysis failed" in markdown

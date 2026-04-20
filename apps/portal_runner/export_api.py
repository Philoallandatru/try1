"""Export API for generating reports in various formats.

Supports Markdown and HTML export for analysis results and daily reports.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ExportAPI:
    """Business logic for exporting reports."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.knowledge_root = self.workspace_root / "knowledge"

    def export_analysis_markdown(
        self,
        *,
        workspace_dir: str,
        issue_id: str,
    ) -> str:
        """Export single analysis result as Markdown.

        Args:
            workspace_dir: Path to workspace directory
            issue_id: Issue ID to export

        Returns:
            Markdown formatted report
        """
        workspace_path = Path(workspace_dir)
        analysis_file = workspace_path / "knowledge" / "analyses" / f"{issue_id}.json"

        if not analysis_file.exists():
            raise ValueError(f"Analysis not found: {issue_id}")

        with open(analysis_file, encoding="utf-8") as f:
            analysis = json.load(f)

        return self._format_analysis_markdown(analysis)

    def export_analysis_html(
        self,
        *,
        workspace_dir: str,
        issue_id: str,
    ) -> str:
        """Export single analysis result as HTML.

        Args:
            workspace_dir: Path to workspace directory
            issue_id: Issue ID to export

        Returns:
            HTML formatted report
        """
        markdown = self.export_analysis_markdown(
            workspace_dir=workspace_dir,
            issue_id=issue_id,
        )
        return self._markdown_to_html(markdown)

    def export_daily_report_markdown(
        self,
        *,
        workspace_dir: str,
        date: str,
    ) -> str:
        """Export daily report as Markdown.

        Args:
            workspace_dir: Path to workspace directory
            date: Date in YYYY-MM-DD format

        Returns:
            Markdown formatted daily report
        """
        workspace_path = Path(workspace_dir)
        report_file = workspace_path / "knowledge" / "daily_reports" / f"{date}.json"

        if not report_file.exists():
            raise ValueError(f"Daily report not found: {date}")

        with open(report_file, encoding="utf-8") as f:
            report = json.load(f)

        return self._format_daily_report_markdown(report)

    def export_daily_report_html(
        self,
        *,
        workspace_dir: str,
        date: str,
    ) -> str:
        """Export daily report as HTML.

        Args:
            workspace_dir: Path to workspace directory
            date: Date in YYYY-MM-DD format

        Returns:
            HTML formatted daily report
        """
        markdown = self.export_daily_report_markdown(
            workspace_dir=workspace_dir,
            date=date,
        )
        return self._markdown_to_html(markdown)

    def export_batch_result_markdown(
        self,
        *,
        workspace_dir: str,
        batch_id: str,
    ) -> str:
        """Export batch analysis result as Markdown.

        Args:
            workspace_dir: Path to workspace directory
            batch_id: Batch ID to export

        Returns:
            Markdown formatted batch report
        """
        workspace_path = Path(workspace_dir)
        batch_file = workspace_path / "batch_results" / f"{batch_id}.json"

        if not batch_file.exists():
            raise ValueError(f"Batch result not found: {batch_id}")

        with open(batch_file, encoding="utf-8") as f:
            batch = json.load(f)

        return self._format_batch_result_markdown(batch)

    def export_batch_result_html(
        self,
        *,
        workspace_dir: str,
        batch_id: str,
    ) -> str:
        """Export batch analysis result as HTML.

        Args:
            workspace_dir: Path to workspace directory
            batch_id: Batch ID to export

        Returns:
            HTML formatted batch report
        """
        markdown = self.export_batch_result_markdown(
            workspace_dir=workspace_dir,
            batch_id=batch_id,
        )
        return self._markdown_to_html(markdown)

    def _format_analysis_markdown(self, analysis: dict[str, Any]) -> str:
        """Format analysis result as Markdown."""
        lines = [
            f"# Analysis Report: {analysis['issue_id']}",
            "",
            f"**Generated:** {analysis['timestamp']}",
            "",
            "## Summary",
            "",
            analysis.get("summary", "No summary available"),
            "",
        ]

        # Add citations
        if "citations" in analysis and analysis["citations"]:
            lines.extend([
                "## Citations",
                "",
            ])
            for i, citation in enumerate(analysis["citations"], 1):
                lines.append(f"### {i}. {citation.get('document_id', 'Unknown')}")
                lines.append("")
                lines.append(f"**Relevance Score:** {citation.get('score', 0):.4f}")
                lines.append("")
                if "content" in citation:
                    lines.append("**Content:**")
                    lines.append("")
                    lines.append(f"> {citation['content']}")
                    lines.append("")

        # Add recommendations
        if "recommendations" in analysis and analysis["recommendations"]:
            lines.extend([
                "## Recommendations",
                "",
            ])
            for i, rec in enumerate(analysis["recommendations"], 1):
                lines.append(f"{i}. {rec}")

        return "\n".join(lines)

    def _format_daily_report_markdown(self, report: dict[str, Any]) -> str:
        """Format daily report as Markdown."""
        lines = [
            f"# Daily Report: {report['date']}",
            "",
            f"**Generated:** {report['timestamp']}",
            "",
            f"**Total Issues Analyzed:** {report['total_issues']}",
            "",
        ]

        # Add summary
        if "summary" in report:
            lines.extend([
                "## Summary",
                "",
                report["summary"],
                "",
            ])

        # Add issue breakdown
        if "issues" in report and report["issues"]:
            lines.extend([
                "## Issues Analyzed",
                "",
            ])
            for issue in report["issues"]:
                lines.append(f"### {issue['issue_id']}")
                lines.append("")
                if "summary" in issue:
                    lines.append(issue["summary"])
                    lines.append("")

        return "\n".join(lines)

    def _format_batch_result_markdown(self, batch: dict[str, Any]) -> str:
        """Format batch result as Markdown."""
        lines = [
            f"# Batch Analysis Report: {batch['batch_id']}",
            "",
            f"**Started:** {batch['started_at']}",
            f"**Completed:** {batch.get('completed_at', 'In progress')}",
            "",
            f"**Total Issues:** {batch['total']}",
            f"**Completed:** {batch['completed']}",
            f"**Failed:** {batch['failed']}",
            "",
        ]

        # Add results
        if "results" in batch and batch["results"]:
            lines.extend([
                "## Results",
                "",
            ])
            for result in batch["results"]:
                issue_id = result["issue_id"]
                status = "✓" if result["success"] else "✗"
                lines.append(f"### {status} {issue_id}")
                lines.append("")

                if result["success"]:
                    analysis = result.get("result", {})
                    if "summary" in analysis:
                        lines.append(analysis["summary"])
                else:
                    error = result.get("error", "Unknown error")
                    lines.append(f"**Error:** {error}")

                lines.append("")

        return "\n".join(lines)

    def _markdown_to_html(self, markdown: str) -> str:
        """Convert Markdown to HTML (basic implementation)."""
        lines = markdown.split("\n")
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "  <meta charset='utf-8'>",
            "  <style>",
            "    body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }",
            "    h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }",
            "    h2 { color: #34495e; margin-top: 30px; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }",
            "    h3 { color: #7f8c8d; margin-top: 20px; }",
            "    blockquote { background: #f9f9f9; border-left: 4px solid #3498db; padding: 10px 20px; margin: 10px 0; }",
            "    code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }",
            "    strong { color: #2c3e50; }",
            "  </style>",
            "</head>",
            "<body>",
        ]

        in_blockquote = False
        for line in lines:
            # Headers
            if line.startswith("# "):
                html_lines.append(f"  <h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"  <h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_lines.append(f"  <h3>{line[4:]}</h3>")
            # Blockquotes
            elif line.startswith("> "):
                if not in_blockquote:
                    html_lines.append("  <blockquote>")
                    in_blockquote = True
                html_lines.append(f"    {line[2:]}")
            else:
                if in_blockquote:
                    html_lines.append("  </blockquote>")
                    in_blockquote = False

                # Bold text
                line = line.replace("**", "<strong>", 1)
                line = line.replace("**", "</strong>", 1)

                # Empty lines
                if not line.strip():
                    html_lines.append("  <br>")
                else:
                    html_lines.append(f"  <p>{line}</p>")

        if in_blockquote:
            html_lines.append("  </blockquote>")

        html_lines.extend([
            "</body>",
            "</html>",
        ])

        return "\n".join(html_lines)

"""Trends API for analyzing issue patterns and statistics.

Provides trend analysis for issue types, reference counts, and analysis activity.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class TrendsAPI:
    """Business logic for trend analysis."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.knowledge_root = self.workspace_root / "knowledge"

    def get_analysis_trends(
        self,
        *,
        workspace_dir: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get analysis trends over a date range.

        Args:
            workspace_dir: Path to workspace directory
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)

        Returns:
            Trend analysis data including daily counts, issue types, etc.
        """
        workspace_path = Path(workspace_dir)
        analyses_dir = workspace_path / "knowledge" / "analyses"

        if not analyses_dir.exists():
            return {
                "start_date": start_date,
                "end_date": end_date,
                "total_analyses": 0,
                "daily_counts": {},
                "issue_type_distribution": {},
                "average_citations": 0,
            }

        # Parse date range
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Collect analysis data
        daily_counts: dict[str, int] = defaultdict(int)
        issue_types: dict[str, int] = defaultdict(int)
        total_citations = 0
        total_analyses = 0

        for analysis_file in analyses_dir.glob("*.json"):
            try:
                with open(analysis_file, encoding="utf-8") as f:
                    analysis = json.load(f)

                # Parse timestamp
                timestamp_str = analysis.get("timestamp", "")
                if not timestamp_str:
                    continue

                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

                # Filter by date range
                if start_dt and timestamp < start_dt:
                    continue
                if end_dt and timestamp > end_dt:
                    continue

                # Count by date
                date_key = timestamp.strftime("%Y-%m-%d")
                daily_counts[date_key] += 1

                # Count issue types (extract from issue_id prefix)
                issue_id = analysis.get("issue_id", "")
                if "-" in issue_id:
                    issue_type = issue_id.split("-")[0]
                    issue_types[issue_type] += 1

                # Count citations
                citations = analysis.get("citations", [])
                total_citations += len(citations)
                total_analyses += 1

            except (json.JSONDecodeError, ValueError):
                continue

        # Calculate average citations
        avg_citations = total_citations / total_analyses if total_analyses > 0 else 0

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_analyses": total_analyses,
            "daily_counts": dict(sorted(daily_counts.items())),
            "issue_type_distribution": dict(sorted(issue_types.items(), key=lambda x: x[1], reverse=True)),
            "average_citations": round(avg_citations, 2),
            "total_citations": total_citations,
        }

    def get_issue_type_trends(
        self,
        *,
        workspace_dir: str,
        issue_type: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get trends for a specific issue type.

        Args:
            workspace_dir: Path to workspace directory
            issue_type: Issue type prefix (e.g., "SSD", "BUG")
            days: Number of days to analyze

        Returns:
            Trend data for the specific issue type
        """
        workspace_path = Path(workspace_dir)
        analyses_dir = workspace_path / "knowledge" / "analyses"

        if not analyses_dir.exists():
            return {
                "issue_type": issue_type,
                "days": days,
                "total_count": 0,
                "daily_counts": {},
                "average_citations": 0,
            }

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Collect data
        daily_counts: dict[str, int] = defaultdict(int)
        total_citations = 0
        total_count = 0

        for analysis_file in analyses_dir.glob(f"{issue_type}-*.json"):
            try:
                with open(analysis_file, encoding="utf-8") as f:
                    analysis = json.load(f)

                # Parse timestamp
                timestamp_str = analysis.get("timestamp", "")
                if not timestamp_str:
                    continue

                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

                # Filter by date range
                if timestamp < start_date or timestamp > end_date:
                    continue

                # Count by date
                date_key = timestamp.strftime("%Y-%m-%d")
                daily_counts[date_key] += 1

                # Count citations
                citations = analysis.get("citations", [])
                total_citations += len(citations)
                total_count += 1

            except (json.JSONDecodeError, ValueError):
                continue

        # Calculate average
        avg_citations = total_citations / total_count if total_count > 0 else 0

        return {
            "issue_type": issue_type,
            "days": days,
            "total_count": total_count,
            "daily_counts": dict(sorted(daily_counts.items())),
            "average_citations": round(avg_citations, 2),
        }

    def get_citation_trends(
        self,
        *,
        workspace_dir: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get citation count trends over time.

        Args:
            workspace_dir: Path to workspace directory
            days: Number of days to analyze

        Returns:
            Citation trend data
        """
        workspace_path = Path(workspace_dir)
        analyses_dir = workspace_path / "knowledge" / "analyses"

        if not analyses_dir.exists():
            return {
                "days": days,
                "daily_citation_counts": {},
                "average_per_analysis": 0,
            }

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Collect data
        daily_citations: dict[str, int] = defaultdict(int)
        daily_analyses: dict[str, int] = defaultdict(int)

        for analysis_file in analyses_dir.glob("*.json"):
            try:
                with open(analysis_file, encoding="utf-8") as f:
                    analysis = json.load(f)

                # Parse timestamp
                timestamp_str = analysis.get("timestamp", "")
                if not timestamp_str:
                    continue

                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

                # Filter by date range
                if timestamp < start_date or timestamp > end_date:
                    continue

                # Count by date
                date_key = timestamp.strftime("%Y-%m-%d")
                citations = analysis.get("citations", [])
                daily_citations[date_key] += len(citations)
                daily_analyses[date_key] += 1

            except (json.JSONDecodeError, ValueError):
                continue

        # Calculate averages per day
        daily_averages = {}
        for date_key in daily_citations:
            if daily_analyses[date_key] > 0:
                daily_averages[date_key] = round(
                    daily_citations[date_key] / daily_analyses[date_key], 2
                )

        # Overall average
        total_citations = sum(daily_citations.values())
        total_analyses = sum(daily_analyses.values())
        overall_avg = total_citations / total_analyses if total_analyses > 0 else 0

        return {
            "days": days,
            "daily_citation_counts": dict(sorted(daily_citations.items())),
            "daily_averages": dict(sorted(daily_averages.items())),
            "average_per_analysis": round(overall_avg, 2),
        }

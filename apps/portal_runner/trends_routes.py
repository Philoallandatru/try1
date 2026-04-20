"""Trends API routes for Portal Runner.

Provides endpoints for trend analysis.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from .trends_api import TrendsAPI

router = APIRouter(prefix="/api/trends", tags=["trends"])


def create_trends_routes(workspace_root: Path) -> APIRouter:
    """Create trends API routes with workspace context."""
    trends_api = TrendsAPI(workspace_root)

    @router.get("/analysis")
    async def get_analysis_trends(
        workspace_dir: str,
        start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
        end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    ):
        """Get analysis trends over a date range."""
        try:
            trends = trends_api.get_analysis_trends(
                workspace_dir=workspace_dir,
                start_date=start_date,
                end_date=end_date,
            )
            return trends
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/issue-type/{issue_type}")
    async def get_issue_type_trends(
        issue_type: str,
        workspace_dir: str,
        days: int = Query(30, description="Number of days to analyze"),
    ):
        """Get trends for a specific issue type."""
        try:
            trends = trends_api.get_issue_type_trends(
                workspace_dir=workspace_dir,
                issue_type=issue_type,
                days=days,
            )
            return trends
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/citations")
    async def get_citation_trends(
        workspace_dir: str,
        days: int = Query(30, description="Number of days to analyze"),
    ):
        """Get citation count trends over time."""
        try:
            trends = trends_api.get_citation_trends(
                workspace_dir=workspace_dir,
                days=days,
            )
            return trends
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

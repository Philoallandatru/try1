"""Analysis API routes for Portal Runner."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter, Depends
    from typing import Callable


def create_analysis_router(*, require_auth: Callable) -> "APIRouter":
    """Create analysis API router.

    Args:
        require_auth: Authentication dependency

    Returns:
        Configured FastAPI router
    """
    from fastapi import APIRouter, Depends, HTTPException, Request

    from apps.portal_runner.analysis_api import (
        deep_analyze_issue_response,
        get_analysis_result_response,
        search_knowledge_base_response,
        generate_daily_report_response,
    )

    router = APIRouter(prefix="/api/analysis", tags=["analysis"])

    @router.post("/deep")
    async def deep_analyze(request: Request, _: None = Depends(require_auth)) -> dict:
        """Trigger deep analysis for a Jira issue.

        Request body:
        {
            "workspace_dir": "/path/to/workspace",
            "issue_id": "SSD-777",
            "llm_backend": "none",  // "none", "mock", "openai-compatible"
            "llm_base_url": "http://localhost:1234/v1",  // optional
            "llm_model": "qwen2.5-coder-7b-instruct",  // optional
            "prompt_mode": "strict",  // "strict", "balanced", "exploratory"
            "top_k": 5
        }

        Returns:
        {
            "status": "completed",
            "issue_id": "SSD-777",
            "result": { ... }
        }
        """
        try:
            payload = await request.json()
            return deep_analyze_issue_response(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/deep/{issue_id}")
    def get_analysis(
        issue_id: str,
        workspace_dir: str,
        _: None = Depends(require_auth),
    ) -> dict:
        """Get saved deep analysis result.

        Query params:
        - workspace_dir: Path to workspace directory

        Returns:
        {
            "issue_id": "SSD-777",
            "content": "# Deep Analysis...",
            "metadata": { ... }
        }
        """
        try:
            return get_analysis_result_response(workspace_dir, issue_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/knowledge/search")
    def search_knowledge(
        workspace_dir: str,
        query: str,
        limit: int = 10,
        _: None = Depends(require_auth),
    ) -> dict:
        """Search knowledge base for relevant analyses.

        Query params:
        - workspace_dir: Path to workspace directory
        - query: Search query
        - limit: Maximum number of results (default: 10)

        Returns:
        {
            "query": "NVMe flush",
            "total": 5,
            "results": [
                {
                    "issue_id": "SSD-777",
                    "title": "NVMe flush command failure",
                    "analyzed_at": "2026-04-20T10:30:00Z",
                    "citation_count": 12
                },
                ...
            ]
        }
        """
        try:
            return search_knowledge_base_response(workspace_dir, query, limit)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/daily-report")
    async def generate_daily_report(request: Request, _: None = Depends(require_auth)) -> dict:
        """Generate daily report from knowledge base.

        Request body:
        {
            "workspace_dir": "/path/to/workspace",
            "date": "2026-04-20",  // optional, defaults to today
            "mode": "fast"  // "fast" (< 5s) or "full" (< 30s)
        }

        Returns:
        {
            "date": "2026-04-20",
            "mode": "fast",
            "sections": [
                {
                    "title": "Summary",
                    "content": "Total analyzed issues: 42",
                    "order": 1
                },
                ...
            ],
            "total_issues": 42
        }
        """
        try:
            payload = await request.json()
            return generate_daily_report_response(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router

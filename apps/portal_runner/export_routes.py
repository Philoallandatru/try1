"""Export API routes for Portal Runner.

Provides endpoints for exporting reports in various formats.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse

from .export_api import ExportAPI

router = APIRouter(prefix="/api/export", tags=["export"])


def create_export_routes(workspace_root: Path) -> APIRouter:
    """Create export API routes with workspace context."""
    export_api = ExportAPI(workspace_root)

    @router.get("/analysis/{issue_id}/markdown", response_class=PlainTextResponse)
    async def export_analysis_markdown(issue_id: str, workspace_dir: str):
        """Export analysis result as Markdown."""
        try:
            markdown = export_api.export_analysis_markdown(
                workspace_dir=workspace_dir,
                issue_id=issue_id,
            )
            return PlainTextResponse(content=markdown, media_type="text/markdown")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/analysis/{issue_id}/html", response_class=HTMLResponse)
    async def export_analysis_html(issue_id: str, workspace_dir: str):
        """Export analysis result as HTML."""
        try:
            html = export_api.export_analysis_html(
                workspace_dir=workspace_dir,
                issue_id=issue_id,
            )
            return HTMLResponse(content=html)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/daily-report/{date}/markdown", response_class=PlainTextResponse)
    async def export_daily_report_markdown(date: str, workspace_dir: str):
        """Export daily report as Markdown."""
        try:
            markdown = export_api.export_daily_report_markdown(
                workspace_dir=workspace_dir,
                date=date,
            )
            return PlainTextResponse(content=markdown, media_type="text/markdown")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/daily-report/{date}/html", response_class=HTMLResponse)
    async def export_daily_report_html(date: str, workspace_dir: str):
        """Export daily report as HTML."""
        try:
            html = export_api.export_daily_report_html(
                workspace_dir=workspace_dir,
                date=date,
            )
            return HTMLResponse(content=html)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/batch/{batch_id}/markdown", response_class=PlainTextResponse)
    async def export_batch_result_markdown(batch_id: str, workspace_dir: str):
        """Export batch result as Markdown."""
        try:
            markdown = export_api.export_batch_result_markdown(
                workspace_dir=workspace_dir,
                batch_id=batch_id,
            )
            return PlainTextResponse(content=markdown, media_type="text/markdown")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/batch/{batch_id}/html", response_class=HTMLResponse)
    async def export_batch_result_html(batch_id: str, workspace_dir: str):
        """Export batch result as HTML."""
        try:
            html = export_api.export_batch_result_html(
                workspace_dir=workspace_dir,
                batch_id=batch_id,
            )
            return HTMLResponse(content=html)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

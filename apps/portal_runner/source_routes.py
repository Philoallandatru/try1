"""
FastAPI routes for unified Source API.

Integrates with Portal Runner server.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .source_api import SourceAPI


def create_source_router(workspace_root: str) -> APIRouter:
    """
    Create FastAPI router for source endpoints.

    Args:
        workspace_root: Root directory for workspaces

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/v2/sources", tags=["sources"])

    def get_api(workspace_dir: str) -> SourceAPI:
        """Get SourceAPI instance for workspace."""
        return SourceAPI(workspace_dir)

    @router.post("")
    async def create_source(request: Request) -> dict[str, Any]:
        """
        Create a new source.

        Request body:
        {
            "workspace_dir": "/path/to/workspace",
            "name": "My Jira",
            "type": "jira",
            "config": {
                "base_url": "https://jira.example.com",
                "credential_ref": "jira_token",
                "scope_type": "project",
                "project": "NVME"
            },
            "enabled": true
        }
        """
        try:
            payload = await request.json()
            workspace_dir = payload.get("workspace_dir")
            if not workspace_dir:
                raise ValueError("workspace_dir is required")

            api = get_api(workspace_dir)
            return api.create_source(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("")
    async def list_sources(workspace_dir: str, enabled_only: bool = False) -> dict[str, Any]:
        """
        List all sources in a workspace.

        Query params:
        - workspace_dir: Path to workspace
        - enabled_only: Only return enabled sources (default: false)
        """
        try:
            api = get_api(workspace_dir)
            return api.list_sources(enabled_only=enabled_only)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/{source_id}")
    async def get_source(source_id: str, workspace_dir: str) -> dict[str, Any]:
        """
        Get source by ID.

        Path params:
        - source_id: Source ID

        Query params:
        - workspace_dir: Path to workspace
        """
        try:
            api = get_api(workspace_dir)
            return api.get_source(source_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.put("/{source_id}")
    async def update_source(source_id: str, request: Request) -> dict[str, Any]:
        """
        Update source.

        Path params:
        - source_id: Source ID

        Request body:
        {
            "workspace_dir": "/path/to/workspace",
            "name": "Updated Name",  // optional
            "config": {...},  // optional
            "enabled": false  // optional
        }
        """
        try:
            payload = await request.json()
            workspace_dir = payload.get("workspace_dir")
            if not workspace_dir:
                raise ValueError("workspace_dir is required")

            api = get_api(workspace_dir)
            return api.update_source(source_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.delete("/{source_id}")
    async def delete_source(source_id: str, workspace_dir: str) -> dict[str, Any]:
        """
        Delete source.

        Path params:
        - source_id: Source ID

        Query params:
        - workspace_dir: Path to workspace
        """
        try:
            api = get_api(workspace_dir)
            return api.delete_source(source_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/{source_id}/test")
    async def test_connection(source_id: str, workspace_dir: str) -> dict[str, Any]:
        """
        Test source connection.

        Path params:
        - source_id: Source ID

        Query params:
        - workspace_dir: Path to workspace
        """
        try:
            api = get_api(workspace_dir)
            return api.test_connection(source_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/{source_id}/sync")
    async def trigger_sync(source_id: str, workspace_dir: str) -> dict[str, Any]:
        """
        Trigger sync for a source.

        Path params:
        - source_id: Source ID

        Query params:
        - workspace_dir: Path to workspace
        """
        try:
            api = get_api(workspace_dir)
            return api.trigger_sync(source_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/{source_id}/status")
    async def get_sync_status(source_id: str, workspace_dir: str) -> dict[str, Any]:
        """
        Get sync status for a source.

        Path params:
        - source_id: Source ID

        Query params:
        - workspace_dir: Path to workspace
        """
        try:
            api = get_api(workspace_dir)
            return api.get_sync_status(source_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router

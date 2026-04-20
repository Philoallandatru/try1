"""Cross-reference API routes for Portal Runner.

Provides endpoints for finding related issues and citation networks.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from .cross_reference_api import CrossReferenceAPI

router = APIRouter(prefix="/api/cross-reference", tags=["cross-reference"])


def create_cross_reference_routes(workspace_root: Path) -> APIRouter:
    """Create cross-reference API routes with workspace context."""
    cross_ref_api = CrossReferenceAPI(workspace_root)

    @router.get("/related/{issue_id}")
    async def get_related_issues(
        issue_id: str,
        workspace_dir: str,
        min_shared_citations: int = Query(2, description="Minimum shared citations"),
        limit: int = Query(10, description="Maximum results to return"),
    ):
        """Find issues related to the given issue."""
        try:
            related = cross_ref_api.find_related_issues(
                workspace_dir=workspace_dir,
                issue_id=issue_id,
                min_shared_citations=min_shared_citations,
                limit=limit,
            )
            return related
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/network")
    async def get_citation_network(
        workspace_dir: str,
        min_connections: int = Query(2, description="Minimum shared citations for edge"),
    ):
        """Get the citation network graph."""
        try:
            network = cross_ref_api.get_citation_network(
                workspace_dir=workspace_dir,
                min_connections=min_connections,
            )
            return network
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/most-cited")
    async def get_most_cited_documents(
        workspace_dir: str,
        limit: int = Query(20, description="Maximum documents to return"),
    ):
        """Get the most frequently cited documents."""
        try:
            documents = cross_ref_api.get_most_cited_documents(
                workspace_dir=workspace_dir,
                limit=limit,
            )
            return documents
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/clusters")
    async def get_issue_clusters(
        workspace_dir: str,
        min_cluster_size: int = Query(2, description="Minimum issues per cluster"),
    ):
        """Get clusters of related issues."""
        try:
            clusters = cross_ref_api.get_issue_clusters(
                workspace_dir=workspace_dir,
                min_cluster_size=min_cluster_size,
            )
            return clusters
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

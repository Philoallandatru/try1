"""
FastAPI routes for retrieval endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.portal_runner.retrieval_api import RetrievalAPI


class SearchRequest(BaseModel):
    """Search request payload."""

    query: str = Field(..., description="Search query text")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    min_score: float = Field(0.0, ge=0.0, description="Minimum relevance score")


class BuildIndexRequest(BaseModel):
    """Build index request payload."""

    batch_size: int = Field(1000, ge=1, description="Batch size for processing")


class EvaluateRequest(BaseModel):
    """Evaluate request payload."""

    golden_dataset_path: str = Field(
        "data/golden_dataset.yaml",
        description="Path to golden dataset",
    )
    top_k: int = Field(10, ge=1, le=100, description="Number of results to retrieve")


def create_retrieval_router(workspace_root: str) -> APIRouter:
    """
    Create retrieval router.

    Args:
        workspace_root: Path to workspace root directory

    Returns:
        FastAPI router
    """
    router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])

    # Initialize API
    api = RetrievalAPI(workspace_root)

    @router.post("/search")
    def search(request: SearchRequest) -> dict[str, Any]:
        """
        Execute search query.

        Args:
            request: Search request

        Returns:
            Search results
        """
        try:
            result = api.search(
                query=request.query,
                top_k=request.top_k,
                min_score=request.min_score,
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/stats")
    def get_stats() -> dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Index statistics
        """
        try:
            result = api.get_index_stats()
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/index/build")
    def build_index(request: BuildIndexRequest) -> dict[str, Any]:
        """
        Build full index from database.

        Args:
            request: Build index request

        Returns:
            Build result
        """
        try:
            result = api.build_index(batch_size=request.batch_size)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/index/update")
    def update_index() -> dict[str, Any]:
        """
        Update index incrementally.

        Returns:
            Update result
        """
        try:
            result = api.update_index()
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/index/rebuild")
    def rebuild_index() -> dict[str, Any]:
        """
        Rebuild index from scratch.

        Returns:
            Rebuild result
        """
        try:
            result = api.rebuild_index()
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/health")
    def health_check() -> dict[str, Any]:
        """
        Check index health.

        Returns:
            Health check result
        """
        try:
            result = api.health_check()
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/evaluate")
    def evaluate(request: EvaluateRequest) -> dict[str, Any]:
        """
        Run evaluation on golden dataset.

        Args:
            request: Evaluate request

        Returns:
            Evaluation results
        """
        try:
            result = api.evaluate(
                golden_dataset_path=request.golden_dataset_path,
                top_k=request.top_k,
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

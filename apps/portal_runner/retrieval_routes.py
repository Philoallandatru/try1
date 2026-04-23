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
    document_types: list[str] | None = Field(None, description="Filter by document types (e.g., ['spec', 'policy'])")


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
    save_result: bool = Field(True, description="Whether to save the evaluation result")


class UploadDatasetRequest(BaseModel):
    """Upload dataset request payload."""

    content: str = Field(..., description="YAML content of the dataset")
    dataset_id: str | None = Field(None, description="Optional dataset ID")


class CompareResultsRequest(BaseModel):
    """Compare results request payload."""

    run_ids: list[str] = Field(..., description="List of run IDs to compare")


class AnalyzeQueryRequest(BaseModel):
    """Analyze query request payload."""

    query: str = Field(..., description="Search query to analyze")


class ExplainScoreRequest(BaseModel):
    """Explain score request payload."""

    query: str = Field(..., description="Search query")
    doc_id: str = Field(..., description="Document ID")


class CompareScoresRequest(BaseModel):
    """Compare scores request payload."""

    query: str = Field(..., description="Search query")
    doc_ids: list[str] = Field(..., description="List of document IDs to compare")


class AnnotateRelevanceRequest(BaseModel):
    """Annotate relevance request payload."""

    query: str = Field(..., description="Search query")
    doc_id: str = Field(..., description="Document ID")
    relevance: int = Field(..., ge=0, le=3, description="Relevance score (0-3)")
    notes: str = Field("", description="Optional notes")


class EnhancedSearchRequest(BaseModel):
    """Enhanced search request payload."""

    query: str = Field(..., description="Search query text")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    min_score: float = Field(0.0, ge=0.0, description="Minimum relevance score")
    document_types: list[str] | None = Field(None, description="Filter by document types")
    enable_expansion: bool = Field(True, description="Enable query expansion")
    enable_reranking: bool = Field(True, description="Enable result reranking")
    enable_filtering: bool = Field(True, description="Enable result filtering")


class AddSynonymRequest(BaseModel):
    """Add synonym request payload."""

    term: str = Field(..., description="Original term")
    synonyms: list[str] = Field(..., description="List of synonyms")


class AddCorrectionRequest(BaseModel):
    """Add typo correction request payload."""

    typo: str = Field(..., description="Typo to correct")
    correction: str = Field(..., description="Correct form")


class SetPriorityRequest(BaseModel):
    """Set document type priority request payload."""

    doc_type: str = Field(..., description="Document type")
    priority: float = Field(..., ge=0.0, description="Priority multiplier (1.0 = neutral)")


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
                document_types=request.document_types,
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
                save_result=request.save_result,
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Dataset Management ====================

    @router.post("/datasets")
    def upload_dataset(request: UploadDatasetRequest) -> dict[str, Any]:
        """
        Upload a golden dataset.

        Args:
            request: Upload dataset request

        Returns:
            Dataset information
        """
        try:
            result = api.upload_dataset(
                dataset_content=request.content,
                dataset_id=request.dataset_id,
            )
            if result["status"] == "error":
                raise HTTPException(status_code=400, detail=result["error"])
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/datasets")
    def list_datasets() -> dict[str, Any]:
        """
        List all available datasets.

        Returns:
            List of datasets
        """
        try:
            result = api.list_datasets()
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/datasets/{dataset_id}")
    def get_dataset(dataset_id: str) -> dict[str, Any]:
        """
        Get dataset information and content.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset information and content
        """
        try:
            result = api.get_dataset(dataset_id)
            if result["status"] == "error":
                raise HTTPException(status_code=404, detail=result["error"])
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/datasets/{dataset_id}")
    def delete_dataset(dataset_id: str) -> dict[str, Any]:
        """
        Delete a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            Success status
        """
        try:
            result = api.delete_dataset(dataset_id)
            if result["status"] == "error":
                raise HTTPException(status_code=404, detail=result["error"])
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Evaluation Results Management ====================

    @router.get("/results")
    def list_evaluation_results(
        dataset_id: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        List evaluation results.

        Args:
            dataset_id: Optional filter by dataset ID
            limit: Optional limit number of results

        Returns:
            List of evaluation results
        """
        try:
            result = api.list_evaluation_results(dataset_id, limit)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/results/{run_id}")
    def get_evaluation_result(run_id: str) -> dict[str, Any]:
        """
        Get detailed evaluation result.

        Args:
            run_id: Run ID

        Returns:
            Evaluation result
        """
        try:
            result = api.get_evaluation_result(run_id)
            if result["status"] == "error":
                raise HTTPException(status_code=404, detail=result["error"])
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/results/{run_id}")
    def delete_evaluation_result(run_id: str) -> dict[str, Any]:
        """
        Delete evaluation result.

        Args:
            run_id: Run ID

        Returns:
            Success status
        """
        try:
            result = api.delete_evaluation_result(run_id)
            if result["status"] == "error":
                raise HTTPException(status_code=404, detail=result["error"])
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/results/compare")
    def compare_evaluation_results(request: CompareResultsRequest) -> dict[str, Any]:
        """
        Compare multiple evaluation results.

        Args:
            request: Compare results request

        Returns:
            Comparison data
        """
        try:
            result = api.compare_evaluation_results(request.run_ids)
            if result["status"] == "error":
                raise HTTPException(status_code=404, detail=result["error"])
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Debug Tools ====================

    @router.post("/debug/analyze-query")
    def analyze_query(request: AnalyzeQueryRequest) -> dict[str, Any]:
        """
        Analyze query tokenization and statistics.

        Args:
            request: Analyze query request

        Returns:
            Query analysis
        """
        try:
            result = api.analyze_query(request.query)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/debug/explain-score")
    def explain_score(request: ExplainScoreRequest) -> dict[str, Any]:
        """
        Explain BM25 score for a specific document.

        Args:
            request: Explain score request

        Returns:
            Score explanation
        """
        try:
            result = api.explain_score(request.query, request.doc_id)
            if result["status"] == "error":
                raise HTTPException(status_code=400, detail=result["error"])
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/debug/compare-scores")
    def compare_scores(request: CompareScoresRequest) -> dict[str, Any]:
        """
        Compare BM25 scores across multiple documents.

        Args:
            request: Compare scores request

        Returns:
            Score comparison
        """
        try:
            result = api.compare_document_scores(request.query, request.doc_ids)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/debug/annotate")
    def annotate_relevance(request: AnnotateRelevanceRequest) -> dict[str, Any]:
        """
        Annotate document relevance for a query.

        Args:
            request: Annotate relevance request

        Returns:
            Annotation record
        """
        try:
            result = api.annotate_relevance(
                request.query,
                request.doc_id,
                request.relevance,
                request.notes,
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/debug/annotations")
    def get_annotations(
        query: str | None = None,
        doc_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get relevance annotations.

        Args:
            query: Optional query filter
            doc_id: Optional doc_id filter

        Returns:
            List of annotations
        """
        try:
            result = api.get_relevance_annotations(query, doc_id)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/debug/relevance-stats/{query}")
    def get_relevance_stats(query: str) -> dict[str, Any]:
        """
        Get relevance statistics for a query.

        Args:
            query: Search query

        Returns:
            Relevance statistics
        """
        try:
            result = api.get_relevance_stats(query)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Enhanced Retrieval ====================

    @router.post("/enhanced-search")
    def enhanced_search(request: EnhancedSearchRequest) -> dict[str, Any]:
        """
        Execute enhanced search with query expansion, reranking, and filtering.

        Args:
            request: Enhanced search request

        Returns:
            Enhanced search results
        """
        try:
            result = api.enhanced_search(
                query=request.query,
                top_k=request.top_k,
                min_score=request.min_score,
                document_types=request.document_types,
                enable_expansion=request.enable_expansion,
                enable_reranking=request.enable_reranking,
                enable_filtering=request.enable_filtering,
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/enhanced/add-synonym")
    def add_synonym(request: AddSynonymRequest) -> dict[str, Any]:
        """
        Add synonym mapping for query expansion.

        Args:
            request: Add synonym request

        Returns:
            Success status
        """
        try:
            result = api.add_synonym(request.term, request.synonyms)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/enhanced/add-correction")
    def add_correction(request: AddCorrectionRequest) -> dict[str, Any]:
        """
        Add typo correction for query rewriting.

        Args:
            request: Add correction request

        Returns:
            Success status
        """
        try:
            result = api.add_typo_correction(request.typo, request.correction)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/enhanced/set-priority")
    def set_priority(request: SetPriorityRequest) -> dict[str, Any]:
        """
        Set priority for a document type in reranking.

        Args:
            request: Set priority request

        Returns:
            Success status
        """
        try:
            result = api.set_document_type_priority(request.doc_type, request.priority)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router

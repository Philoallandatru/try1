"""
FastAPI routes for document asset management.
"""
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
import tempfile
import shutil
from typing import Optional

from services.workspace.document_assets import (
    upload_document_asset,
    list_document_assets,
    load_document_asset_documents,
    delete_document_asset,
    DOCUMENT_TYPES,
)
from packages.source_models.document_database import DocumentDatabase
from apps.portal_runner.background_tasks import get_task_manager
import uuid


def create_document_router(workspace_root: str, *, require_auth: Callable) -> APIRouter:
    """
    Create document management router.

    Args:
        workspace_root: Root directory for workspaces
        require_auth: Authentication dependency

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/documents", tags=["documents"])

    @router.post("/upload")
    async def upload_document(
        workspace: str = Form(...),
        file: UploadFile = File(...),
        document_type: str = Form("other"),
        display_name: Optional[str] = Form(None),
    ):
        """
        Upload a document to the workspace.

        Args:
            workspace: Workspace name
            file: PDF file to upload
            document_type: Type of document (spec, policy, other)
            display_name: Optional display name

        Returns:
            Upload metadata
        """
        if document_type not in DOCUMENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document_type. Must be one of: {list(DOCUMENT_TYPES.keys())}"
            )

        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )

        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        try:
            workspace_dir = Path(workspace_root) / workspace
            if not workspace_dir.exists():
                raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace}")

            # Upload the document file (this parses with MinerU)
            metadata = upload_document_asset(
                workspace_dir=workspace_dir,
                file_path=tmp_path,
                document_type=document_type,
                display_name=display_name or file.filename,
            )

            # Submit background task for database and index processing
            task_id = str(uuid.uuid4())
            task_manager = get_task_manager()
            task_manager.submit_document_processing(
                task_id=task_id,
                workspace_dir=workspace_dir,
                workspace_root=workspace_root,
                doc_id=metadata["doc_id"],
                document_type=document_type,
                metadata=metadata,
            )

            return {
                "success": True,
                "message": "Document uploaded successfully. Processing in background.",
                "metadata": metadata,
                "task_id": task_id,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)

    @router.get("/list")
    async def list_documents(
        workspace: str,
        document_type: Optional[str] = None,
    ):
        """
        List all uploaded documents in a workspace.

        Args:
            workspace: Workspace name
            document_type: Optional filter by document type

        Returns:
            List of document metadata
        """
        print(f"[DEBUG] list_documents called with workspace={workspace}, document_type={document_type}")
        workspace_dir = Path(workspace_root) / workspace
        if not workspace_dir.exists():
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace}")

        try:
            documents = list_document_assets(
                workspace_dir=workspace_dir,
                document_type=document_type,
            )
            return {
                "success": True,
                "documents": documents,
                "count": len(documents),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/types")
    async def get_document_types():
        """
        Get available document types.

        Returns:
            Dict of document types with metadata
        """
        return {
            "success": True,
            "types": DOCUMENT_TYPES,
        }

    @router.delete("/delete")
    async def delete_document(
        workspace: str,
        doc_id: str,
        version: Optional[str] = None,
    ):
        """
        Delete a document asset.

        Args:
            workspace: Workspace name
            doc_id: Document ID to delete
            version: Optional specific version (deletes all versions if not provided)

        Returns:
            Deletion information
        """
        workspace_dir = Path(workspace_root) / workspace
        if not workspace_dir.exists():
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace}")

        try:
            result = delete_document_asset(
                workspace_dir=workspace_dir,
                doc_id=doc_id,
                version=version,
            )
            return {
                "success": True,
                "message": f"Deleted {result['deleted_count']} version(s)",
                "result": result,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/task/{task_id}")
    async def get_task_status(task_id: str):
        """Get the status of a document processing task."""
        task_manager = get_task_manager()
        status = task_manager.get_task_status(task_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return status

    return router

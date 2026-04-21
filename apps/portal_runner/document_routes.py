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
        _: None = Depends(require_auth),
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

            metadata = upload_document_asset(
                workspace_dir=workspace_dir,
                file_path=tmp_path,
                document_type=document_type,
                display_name=display_name or file.filename,
            )

            return {
                "success": True,
                "message": "Document uploaded successfully",
                "metadata": metadata,
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
        _: None = Depends(require_auth),
    ):
        """
        List all uploaded documents in a workspace.

        Args:
            workspace: Workspace name
            document_type: Optional filter by document type

        Returns:
            List of document metadata
        """
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
    async def get_document_types(_: None = Depends(require_auth)):
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
        _: None = Depends(require_auth),
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

    return router

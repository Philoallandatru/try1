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

            # Load the uploaded document into the database
            # Use workspace_root database (not workspace-specific)
            db_path = Path(workspace_root) / "documents.db"
            doc_db = DocumentDatabase(str(db_path))

            # Load document assets (returns tuple of documents, sources)
            documents, sources = load_document_asset_documents(workspace_dir)

            # Add new documents to database
            for doc in documents:
                doc_id = doc.get("document_id")
                if not doc_id:
                    continue

                # Check if document already exists
                existing_doc = doc_db.get_document(doc_id)
                if not existing_doc:
                    # Extract text content from content_blocks
                    content_parts = []
                    for block in doc.get("content_blocks", []):
                        if block.get("block_type") in ["text", "paragraph", "title", "heading"]:
                            text = block.get("text", "")
                            if text:
                                content_parts.append(text)

                    content = "\n".join(content_parts)

                    doc_db.create_document(
                        id=doc_id,
                        source_id=f"document-asset:{metadata['doc_id']}",
                        source_type="document-asset",
                        title=doc.get("title", metadata.get("display_name", "")),
                        content=content,
                        url=metadata.get("paths", {}).get("original_file", ""),
                        metadata={
                            "document_type": document_type,
                            "document_type_priority": DOCUMENT_TYPES[document_type]["priority"],
                            "doc_id": metadata["doc_id"],
                            "version": metadata["version"],
                        },
                    )

            # Trigger incremental index update
            try:
                from packages.retrieval.index_manager import IndexManager
                index_dir = Path(workspace_root) / ".index"
                index_manager = IndexManager(
                    db_path=str(db_path),
                    index_dir=str(index_dir),
                )
                index_manager.load_index()
                index_manager.update_index_incremental()
            except Exception as e:
                # Don't fail the upload if index update fails
                pass

            return {
                "success": True,
                "message": "Document uploaded successfully and added to database",
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

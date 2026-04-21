"""
Background task processing for document operations.
"""
import threading
import queue
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

from services.workspace.document_assets import load_document_asset_documents
from packages.source_models.document_database import DocumentDatabase
from packages.retrieval.index_manager import IndexManager


class TaskStatus:
    """Task status tracking."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundTaskManager:
    """Manages background document processing tasks."""

    def __init__(self):
        self.task_queue = queue.Queue()
        self.task_status: Dict[str, Dict[str, Any]] = {}
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False

    def start(self):
        """Start the background worker thread."""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """Stop the background worker thread."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

    def submit_document_processing(
        self,
        task_id: str,
        workspace_dir: Path,
        workspace_root: str,
        doc_id: str,
        document_type: str,
        metadata: Dict[str, Any],
    ):
        """
        Submit a document processing task.

        Args:
            task_id: Unique task identifier
            workspace_dir: Workspace directory path
            workspace_root: Root workspace directory
            doc_id: Document ID
            document_type: Type of document
            metadata: Document metadata
        """
        task = {
            "task_id": task_id,
            "type": "document_processing",
            "workspace_dir": workspace_dir,
            "workspace_root": workspace_root,
            "doc_id": doc_id,
            "document_type": document_type,
            "metadata": metadata,
            "submitted_at": datetime.utcnow().isoformat(),
        }

        self.task_status[task_id] = {
            "status": TaskStatus.PENDING,
            "submitted_at": task["submitted_at"],
            "message": "Waiting to process document",
        }

        self.task_queue.put(task)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task."""
        return self.task_status.get(task_id)

    def _worker(self):
        """Background worker that processes tasks from the queue."""
        while self.running:
            try:
                # Wait for a task with timeout to allow checking self.running
                task = self.task_queue.get(timeout=1)
            except queue.Empty:
                continue

            task_id = task["task_id"]

            try:
                self.task_status[task_id]["status"] = TaskStatus.PROCESSING
                self.task_status[task_id]["started_at"] = datetime.utcnow().isoformat()
                self.task_status[task_id]["message"] = "Processing document"

                if task["type"] == "document_processing":
                    self._process_document(task)

                self.task_status[task_id]["status"] = TaskStatus.COMPLETED
                self.task_status[task_id]["completed_at"] = datetime.utcnow().isoformat()
                self.task_status[task_id]["message"] = "Document processed successfully"

            except Exception as e:
                self.task_status[task_id]["status"] = TaskStatus.FAILED
                self.task_status[task_id]["error"] = str(e)
                self.task_status[task_id]["traceback"] = traceback.format_exc()
                self.task_status[task_id]["message"] = f"Processing failed: {str(e)}"

            finally:
                self.task_queue.task_done()

    def _process_document(self, task: Dict[str, Any]):
        """
        Process a document: load into database and update index.

        Args:
            task: Task dictionary with processing parameters
        """
        workspace_dir = task["workspace_dir"]
        workspace_root = task["workspace_root"]
        doc_id = task["doc_id"]
        document_type = task["document_type"]
        metadata = task["metadata"]

        # Load document into database
        db_path = Path(workspace_root) / "documents.db"
        doc_db = DocumentDatabase(str(db_path))

        # Load document assets
        documents, sources = load_document_asset_documents(workspace_dir)

        # Find and add the specific document
        for doc in documents:
            if doc.get("document_id") == metadata.get("document_id"):
                # Check if already exists
                existing_doc = doc_db.get_document(doc["document_id"])
                if existing_doc:
                    continue

                # Extract text content
                content_parts = []
                for block in doc.get("content_blocks", []):
                    if block.get("block_type") in ["text", "paragraph", "title", "heading"]:
                        text = block.get("text", "")
                        if text:
                            content_parts.append(text)

                content = "\n".join(content_parts)

                # Import DOCUMENT_TYPES here to avoid circular import
                from services.workspace.document_assets import DOCUMENT_TYPES

                doc_db.create_document(
                    id=doc["document_id"],
                    source_id=f"document-asset:{doc_id}",
                    source_type="document-asset",
                    title=doc.get("title", metadata.get("display_name", "")),
                    content=content,
                    url=metadata.get("paths", {}).get("original_file", ""),
                    metadata={
                        "document_type": document_type,
                        "document_type_priority": DOCUMENT_TYPES[document_type]["priority"],
                        "doc_id": doc_id,
                        "version": metadata["version"],
                    },
                )
                break

        # Update search index
        index_dir = Path(workspace_root) / ".index"
        index_manager = IndexManager(
            db_path=str(db_path),
            index_dir=str(index_dir),
        )
        index_manager.load_index()
        index_manager.update_index_incremental()


# Global task manager instance
_task_manager: Optional[BackgroundTaskManager] = None


def get_task_manager() -> BackgroundTaskManager:
    """Get or create the global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = BackgroundTaskManager()
        _task_manager.start()
    return _task_manager

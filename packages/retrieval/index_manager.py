"""
Index manager for BM25 retrieval system.

Manages the lifecycle of document indexes:
- Building indexes from database
- Incremental updates
- Index persistence
- Index statistics
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from packages.source_models.document_database import DocumentDatabase
from packages.retrieval.bm25_index import BM25Index
from packages.retrieval.tokenizer import Tokenizer

logger = logging.getLogger(__name__)


class IndexManager:
    """
    Manages BM25 index lifecycle.

    Responsibilities:
    - Build index from database documents
    - Incremental index updates
    - Index persistence and loading
    - Index statistics and health checks
    """

    def __init__(
        self,
        db_path: str = "workspace.db",
        index_dir: str = ".index",
        use_stop_words: bool = True,
    ):
        """
        Initialize index manager.

        Args:
            db_path: Path to document database
            index_dir: Directory to store index files
            use_stop_words: Whether to filter stop words
        """
        self.db = DocumentDatabase(db_path)
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.tokenizer = Tokenizer(use_stop_words=use_stop_words)
        self.index = BM25Index(tokenizer=self.tokenizer)

        self.index_path = self.index_dir / "bm25_index.pkl"
        self.metadata_path = self.index_dir / "index_metadata.json"

    def build_full_index(self, batch_size: int = 1000) -> dict:
        """
        Build complete index from all documents in database.

        Args:
            batch_size: Number of documents to process at once

        Returns:
            Build statistics
        """
        logger.info("Building full index from database...")

        # Get total document count
        total_docs = self.db.count_documents()
        logger.info(f"Found {total_docs} documents to index")

        if total_docs == 0:
            logger.warning("No documents found in database")
            return {
                "status": "empty",
                "total_documents": 0,
                "indexed_documents": 0,
            }

        # Load documents in batches
        all_documents = []
        offset = 0

        while offset < total_docs:
            batch = self.db.list_documents(limit=batch_size, offset=offset)

            for doc_db in batch:
                doc_dict = doc_db.to_dict()
                all_documents.append({
                    "id": doc_dict["id"],
                    "content": f"{doc_dict['title']} {doc_dict['content']}",
                    "metadata": {
                        "source_id": doc_dict["source_id"],
                        "source_type": doc_dict["source_type"],
                        "title": doc_dict["title"],
                        "url": doc_dict["url"],
                        **doc_dict["metadata"],
                    }
                })

            offset += len(batch)
            logger.info(f"Loaded {offset}/{total_docs} documents")

        # Build index
        logger.info("Building BM25 index...")
        self.index.build(all_documents)

        # Mark all documents as indexed
        logger.info("Marking documents as indexed...")
        for doc in all_documents:
            self.db.mark_indexed(doc["id"])

        # Save index
        logger.info(f"Saving index to {self.index_path}")
        self.index.save(self.index_path)

        stats = self.index.get_stats()
        logger.info(f"Index built successfully: {stats}")

        return {
            "status": "success",
            "total_documents": total_docs,
            "indexed_documents": len(all_documents),
            "stats": stats,
        }

    def update_index_incremental(self) -> dict:
        """
        Update index with new and modified documents.

        Returns:
            Update statistics
        """
        logger.info("Performing incremental index update...")

        # Load existing index if available
        if self.index_path.exists():
            logger.info(f"Loading existing index from {self.index_path}")
            self.index.load(self.index_path)
        else:
            logger.info("No existing index found, will build from scratch")

        # Get unindexed documents
        unindexed = self.db.get_unindexed_documents()
        logger.info(f"Found {len(unindexed)} unindexed documents")

        # Get stale documents (updated after indexing)
        stale = self.db.get_stale_documents()
        logger.info(f"Found {len(stale)} stale documents")

        if not unindexed and not stale:
            logger.info("Index is up to date")
            return {
                "status": "up_to_date",
                "added": 0,
                "updated": 0,
            }

        # Add new documents
        added_count = 0
        if unindexed:
            new_docs = []
            for doc_db in unindexed:
                doc_dict = doc_db.to_dict()
                new_docs.append({
                    "id": doc_dict["id"],
                    "content": f"{doc_dict['title']} {doc_dict['content']}",
                    "metadata": {
                        "source_id": doc_dict["source_id"],
                        "source_type": doc_dict["source_type"],
                        "title": doc_dict["title"],
                        "url": doc_dict["url"],
                        **doc_dict["metadata"],
                    }
                })

            logger.info(f"Adding {len(new_docs)} new documents to index")
            self.index.add_documents(new_docs)

            # Mark as indexed
            for doc in new_docs:
                self.db.mark_indexed(doc["id"])

            added_count = len(new_docs)

        # Update stale documents
        updated_count = 0
        if stale:
            stale_ids = [doc.id for doc in stale]
            logger.info(f"Removing {len(stale_ids)} stale documents from index")
            self.index.remove_documents(stale_ids)

            # Re-add updated documents
            updated_docs = []
            for doc_db in stale:
                doc_dict = doc_db.to_dict()
                updated_docs.append({
                    "id": doc_dict["id"],
                    "content": f"{doc_dict['title']} {doc_dict['content']}",
                    "metadata": {
                        "source_id": doc_dict["source_id"],
                        "source_type": doc_dict["source_type"],
                        "title": doc_dict["title"],
                        "url": doc_dict["url"],
                        **doc_dict["metadata"],
                    }
                })

            logger.info(f"Re-adding {len(updated_docs)} updated documents to index")
            self.index.add_documents(updated_docs)

            # Mark as indexed
            for doc in updated_docs:
                self.db.mark_indexed(doc["id"])

            updated_count = len(updated_docs)

        # Save updated index
        logger.info(f"Saving updated index to {self.index_path}")
        self.index.save(self.index_path)

        stats = self.index.get_stats()
        logger.info(f"Index updated successfully: {stats}")

        return {
            "status": "success",
            "added": added_count,
            "updated": updated_count,
            "stats": stats,
        }

    def rebuild_index(self) -> dict:
        """
        Rebuild index from scratch.

        Returns:
            Rebuild statistics
        """
        logger.info("Rebuilding index from scratch...")

        # Clear existing index
        self.index = BM25Index(tokenizer=self.tokenizer)

        # Build full index
        return self.build_full_index()

    def load_index(self) -> bool:
        """
        Load index from disk.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.index_path.exists():
            logger.warning(f"Index file not found: {self.index_path}")
            return False

        try:
            logger.info(f"Loading index from {self.index_path}")
            self.index.load(self.index_path)
            logger.info("Index loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def get_stats(self) -> dict:
        """
        Get index statistics.

        Returns:
            Index statistics
        """
        index_stats = self.index.get_stats()

        # Add database statistics
        total_docs = self.db.count_documents()
        unindexed = len(self.db.get_unindexed_documents())
        stale = len(self.db.get_stale_documents())

        return {
            "index": index_stats,
            "database": {
                "total_documents": total_docs,
                "unindexed_documents": unindexed,
                "stale_documents": stale,
            },
            "index_file": {
                "path": str(self.index_path),
                "exists": self.index_path.exists(),
                "size_bytes": self.index_path.stat().st_size if self.index_path.exists() else 0,
            }
        }

    def health_check(self) -> dict:
        """
        Check index health.

        Returns:
            Health check results
        """
        stats = self.get_stats()

        # Check if index exists
        if not stats["index_file"]["exists"]:
            return {
                "status": "missing",
                "message": "Index file does not exist",
                "needs_rebuild": True,
            }

        # Check if index is empty
        if stats["index"]["document_count"] == 0:
            return {
                "status": "empty",
                "message": "Index is empty",
                "needs_rebuild": True,
            }

        # Check if index is stale
        unindexed = stats["database"]["unindexed_documents"]
        stale = stats["database"]["stale_documents"]

        if unindexed > 0 or stale > 0:
            return {
                "status": "stale",
                "message": f"Index needs update: {unindexed} unindexed, {stale} stale",
                "needs_update": True,
                "unindexed": unindexed,
                "stale": stale,
            }

        # Index is healthy
        return {
            "status": "healthy",
            "message": "Index is up to date",
            "stats": stats,
        }

"""
SQLAlchemy database models for document storage.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base = declarative_base()


class DocumentDB(Base):
    """Database model for Document."""

    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    source_id = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False)  # jira, confluence, file_upload
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=False)  # JSON serialized metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    indexed_at = Column(DateTime, nullable=True)  # When document was indexed

    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_source_updated', 'source_id', 'updated_at'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "metadata": json.loads(self.metadata_json),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
        }


class DocumentDatabase:
    """Database manager for documents."""

    def __init__(self, db_path: str = "workspace.db"):
        """
        Initialize database.

        Args:
            db_path: Path to SQLite database file
        """
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def create_document(
        self,
        id: str,
        source_id: str,
        source_type: str,
        title: str,
        content: str,
        url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> DocumentDB:
        """
        Create a new document.

        Args:
            id: Document ID
            source_id: Source ID
            source_type: Source type
            title: Document title
            content: Document content
            url: Document URL (optional)
            metadata: Document metadata (optional)

        Returns:
            Created DocumentDB instance
        """
        session = self.get_session()
        try:
            if metadata is None:
                metadata = {}

            document = DocumentDB(
                id=id,
                source_id=source_id,
                source_type=source_type,
                title=title,
                content=content,
                url=url,
                metadata_json=json.dumps(metadata),
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            return document
        finally:
            session.close()

    def get_document(self, document_id: str) -> Optional[DocumentDB]:
        """
        Get document by ID.

        Args:
            document_id: Document ID

        Returns:
            DocumentDB instance or None
        """
        session = self.get_session()
        try:
            return session.query(DocumentDB).filter(DocumentDB.id == document_id).first()
        finally:
            session.close()

    def list_documents(
        self,
        source_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[DocumentDB]:
        """
        List documents.

        Args:
            source_id: Filter by source ID (optional)
            limit: Maximum number of documents to return (optional)
            offset: Number of documents to skip

        Returns:
            List of DocumentDB instances
        """
        session = self.get_session()
        try:
            query = session.query(DocumentDB)
            if source_id:
                query = query.filter(DocumentDB.source_id == source_id)
            query = query.order_by(DocumentDB.updated_at.desc())
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()

    def count_documents(self, source_id: Optional[str] = None) -> int:
        """
        Count documents.

        Args:
            source_id: Filter by source ID (optional)

        Returns:
            Number of documents
        """
        session = self.get_session()
        try:
            query = session.query(DocumentDB)
            if source_id:
                query = query.filter(DocumentDB.source_id == source_id)
            return query.count()
        finally:
            session.close()

    def update_document(
        self,
        document_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[DocumentDB]:
        """
        Update document.

        Args:
            document_id: Document ID
            title: New title (optional)
            content: New content (optional)
            url: New URL (optional)
            metadata: New metadata (optional)

        Returns:
            Updated DocumentDB instance or None
        """
        session = self.get_session()
        try:
            document = session.query(DocumentDB).filter(DocumentDB.id == document_id).first()
            if not document:
                return None

            if title is not None:
                document.title = title
            if content is not None:
                document.content = content
            if url is not None:
                document.url = url
            if metadata is not None:
                document.metadata_json = json.dumps(metadata)

            document.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(document)
            return document
        finally:
            session.close()

    def delete_document(self, document_id: str) -> bool:
        """
        Delete document.

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        session = self.get_session()
        try:
            document = session.query(DocumentDB).filter(DocumentDB.id == document_id).first()
            if not document:
                return False

            session.delete(document)
            session.commit()
            return True
        finally:
            session.close()

    def delete_documents_by_source(self, source_id: str) -> int:
        """
        Delete all documents from a source.

        Args:
            source_id: Source ID

        Returns:
            Number of documents deleted
        """
        session = self.get_session()
        try:
            count = session.query(DocumentDB).filter(DocumentDB.source_id == source_id).delete()
            session.commit()
            return count
        finally:
            session.close()

    def mark_indexed(self, document_id: str) -> Optional[DocumentDB]:
        """
        Mark document as indexed.

        Args:
            document_id: Document ID

        Returns:
            Updated DocumentDB instance or None
        """
        session = self.get_session()
        try:
            document = session.query(DocumentDB).filter(DocumentDB.id == document_id).first()
            if not document:
                return None

            document.indexed_at = datetime.utcnow()
            session.commit()
            session.refresh(document)
            return document
        finally:
            session.close()

    def get_unindexed_documents(self, limit: Optional[int] = None) -> list[DocumentDB]:
        """
        Get documents that haven't been indexed yet.

        Args:
            limit: Maximum number of documents to return (optional)

        Returns:
            List of DocumentDB instances
        """
        session = self.get_session()
        try:
            query = session.query(DocumentDB).filter(DocumentDB.indexed_at.is_(None))
            query = query.order_by(DocumentDB.created_at)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()

    def get_stale_documents(self, limit: Optional[int] = None) -> list[DocumentDB]:
        """
        Get documents that need re-indexing (updated after last index).

        Args:
            limit: Maximum number of documents to return (optional)

        Returns:
            List of DocumentDB instances
        """
        session = self.get_session()
        try:
            query = session.query(DocumentDB).filter(
                DocumentDB.indexed_at.isnot(None),
                DocumentDB.updated_at > DocumentDB.indexed_at
            )
            query = query.order_by(DocumentDB.updated_at)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()

"""
SQLAlchemy database models for source management.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base = declarative_base()


class SourceDB(Base):
    """Database model for Source."""

    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # jira, confluence, file_upload
    config_json = Column(Text, nullable=False)  # JSON serialized config
    sync_state_json = Column(Text, nullable=False)  # JSON serialized sync state
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    enabled = Column(Boolean, nullable=False, default=True)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "config": json.loads(self.config_json),
            "sync_state": json.loads(self.sync_state_json),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "enabled": self.enabled,
        }


class SourceDatabase:
    """Database manager for sources."""

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

    def create_source(
        self,
        id: str,
        name: str,
        type: str,
        config: dict,
        sync_state: Optional[dict] = None,
        enabled: bool = True,
    ) -> SourceDB:
        """
        Create a new source.

        Args:
            id: Source ID
            name: Source name
            type: Source type
            config: Source configuration
            sync_state: Sync state (optional)
            enabled: Whether source is enabled

        Returns:
            Created SourceDB instance
        """
        session = self.get_session()
        try:
            if sync_state is None:
                sync_state = {
                    "last_sync_time": None,
                    "cursor": None,
                    "total_items": 0,
                    "sync_status": "idle",
                    "error_message": None,
                    "started_at": None,
                    "completed_at": None,
                }

            source = SourceDB(
                id=id,
                name=name,
                type=type,
                config_json=json.dumps(config),
                sync_state_json=json.dumps(sync_state),
                enabled=enabled,
            )
            session.add(source)
            session.commit()
            session.refresh(source)
            return source
        finally:
            session.close()

    def get_source(self, source_id: str) -> Optional[SourceDB]:
        """
        Get source by ID.

        Args:
            source_id: Source ID

        Returns:
            SourceDB instance or None
        """
        session = self.get_session()
        try:
            return session.query(SourceDB).filter(SourceDB.id == source_id).first()
        finally:
            session.close()

    def list_sources(self, enabled_only: bool = False) -> list[SourceDB]:
        """
        List all sources.

        Args:
            enabled_only: Only return enabled sources

        Returns:
            List of SourceDB instances
        """
        session = self.get_session()
        try:
            query = session.query(SourceDB)
            if enabled_only:
                query = query.filter(SourceDB.enabled == True)
            return query.all()
        finally:
            session.close()

    def update_source(
        self,
        source_id: str,
        name: Optional[str] = None,
        config: Optional[dict] = None,
        sync_state: Optional[dict] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[SourceDB]:
        """
        Update source.

        Args:
            source_id: Source ID
            name: New name (optional)
            config: New config (optional)
            sync_state: New sync state (optional)
            enabled: New enabled status (optional)

        Returns:
            Updated SourceDB instance or None
        """
        session = self.get_session()
        try:
            source = session.query(SourceDB).filter(SourceDB.id == source_id).first()
            if not source:
                return None

            if name is not None:
                source.name = name
            if config is not None:
                source.config_json = json.dumps(config)
            if sync_state is not None:
                source.sync_state_json = json.dumps(sync_state)
            if enabled is not None:
                source.enabled = enabled

            source.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(source)
            return source
        finally:
            session.close()

    def delete_source(self, source_id: str) -> bool:
        """
        Delete source.

        Args:
            source_id: Source ID

        Returns:
            True if deleted, False if not found
        """
        session = self.get_session()
        try:
            source = session.query(SourceDB).filter(SourceDB.id == source_id).first()
            if not source:
                return False

            session.delete(source)
            session.commit()
            return True
        finally:
            session.close()

    def update_sync_state(self, source_id: str, sync_state: dict) -> Optional[SourceDB]:
        """
        Update sync state for a source.

        Args:
            source_id: Source ID
            sync_state: New sync state

        Returns:
            Updated SourceDB instance or None
        """
        return self.update_source(source_id, sync_state=sync_state)

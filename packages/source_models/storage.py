"""
Source storage service - bridges Pydantic models and database.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from .database import SourceDatabase
from .models import (
    ConfluenceSourceConfig,
    FileUploadSourceConfig,
    JiraSourceConfig,
    Source,
    SourceConfig,
    SourceType,
    SyncState,
)


class SourceStorage:
    """
    Storage service for sources.

    Bridges Pydantic models and SQLAlchemy database.
    """

    def __init__(self, db_path: str = "workspace.db"):
        """
        Initialize storage.

        Args:
            db_path: Path to SQLite database
        """
        self.db = SourceDatabase(db_path)

    def create_source(
        self,
        name: str,
        type: SourceType,
        config: SourceConfig,
        enabled: bool = True,
    ) -> Source:
        """
        Create a new source.

        Args:
            name: Source name
            type: Source type
            config: Source configuration
            enabled: Whether source is enabled

        Returns:
            Created Source instance
        """
        source_id = str(uuid.uuid4())
        config_dict = config.model_dump()

        db_source = self.db.create_source(
            id=source_id,
            name=name,
            type=type.value,
            config=config_dict,
            enabled=enabled,
        )

        return self._db_to_pydantic(db_source)

    def get_source(self, source_id: str) -> Optional[Source]:
        """
        Get source by ID.

        Args:
            source_id: Source ID

        Returns:
            Source instance or None
        """
        db_source = self.db.get_source(source_id)
        if not db_source:
            return None

        return self._db_to_pydantic(db_source)

    def list_sources(self, enabled_only: bool = False) -> list[Source]:
        """
        List all sources.

        Args:
            enabled_only: Only return enabled sources

        Returns:
            List of Source instances
        """
        db_sources = self.db.list_sources(enabled_only=enabled_only)
        return [self._db_to_pydantic(db_source) for db_source in db_sources]

    def update_source(
        self,
        source_id: str,
        name: Optional[str] = None,
        config: Optional[SourceConfig] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[Source]:
        """
        Update source.

        Args:
            source_id: Source ID
            name: New name (optional)
            config: New config (optional)
            enabled: New enabled status (optional)

        Returns:
            Updated Source instance or None
        """
        config_dict = config.model_dump() if config else None

        db_source = self.db.update_source(
            source_id=source_id,
            name=name,
            config=config_dict,
            enabled=enabled,
        )

        if not db_source:
            return None

        return self._db_to_pydantic(db_source)

    def delete_source(self, source_id: str) -> bool:
        """
        Delete source.

        Args:
            source_id: Source ID

        Returns:
            True if deleted, False if not found
        """
        return self.db.delete_source(source_id)

    def update_sync_state(self, source_id: str, sync_state: SyncState) -> Optional[Source]:
        """
        Update sync state for a source.

        Args:
            source_id: Source ID
            sync_state: New sync state

        Returns:
            Updated Source instance or None
        """
        sync_state_dict = sync_state.model_dump()
        # Convert datetime to ISO string for JSON serialization
        if sync_state_dict.get("last_sync_time"):
            sync_state_dict["last_sync_time"] = sync_state_dict["last_sync_time"].isoformat()
        if sync_state_dict.get("started_at"):
            sync_state_dict["started_at"] = sync_state_dict["started_at"].isoformat()
        if sync_state_dict.get("completed_at"):
            sync_state_dict["completed_at"] = sync_state_dict["completed_at"].isoformat()

        db_source = self.db.update_sync_state(source_id, sync_state_dict)

        if not db_source:
            return None

        return self._db_to_pydantic(db_source)

    def _db_to_pydantic(self, db_source) -> Source:
        """
        Convert database model to Pydantic model.

        Args:
            db_source: SourceDB instance

        Returns:
            Source instance
        """
        source_dict = db_source.to_dict()

        # Parse config based on type
        source_type = SourceType(source_dict["type"])
        config_dict = source_dict["config"]

        if source_type == SourceType.JIRA:
            config = JiraSourceConfig(**config_dict)
        elif source_type == SourceType.CONFLUENCE:
            config = ConfluenceSourceConfig(**config_dict)
        elif source_type == SourceType.FILE_UPLOAD:
            config = FileUploadSourceConfig(**config_dict)
        else:
            raise ValueError(f"Unknown source type: {source_type}")

        # Parse sync state
        sync_state_dict = source_dict["sync_state"]
        # Convert ISO strings back to datetime
        if sync_state_dict.get("last_sync_time"):
            sync_state_dict["last_sync_time"] = datetime.fromisoformat(sync_state_dict["last_sync_time"])
        if sync_state_dict.get("started_at"):
            sync_state_dict["started_at"] = datetime.fromisoformat(sync_state_dict["started_at"])
        if sync_state_dict.get("completed_at"):
            sync_state_dict["completed_at"] = datetime.fromisoformat(sync_state_dict["completed_at"])

        sync_state = SyncState(**sync_state_dict)

        return Source(
            id=source_dict["id"],
            name=source_dict["name"],
            type=source_type,
            config=config,
            sync_state=sync_state,
            created_at=datetime.fromisoformat(source_dict["created_at"]),
            updated_at=datetime.fromisoformat(source_dict["updated_at"]),
            enabled=source_dict["enabled"],
        )

"""
Unified Source API endpoints for Portal Runner.

Based on the redesigned Source models (packages/source_models).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from packages.source_models import (
    ConfluenceSourceConfig,
    ConfluenceScopeType,
    ConnectionTestResult,
    FileUploadSourceConfig,
    JiraSourceConfig,
    JiraScopeType,
    Source,
    SourceStorage,
    SourceType,
    SyncState,
    SyncStatus,
)


class SourceAPI:
    """
    API layer for unified source management.
    """

    def __init__(self, workspace_dir: str | Path):
        """
        Initialize API.

        Args:
            workspace_dir: Path to workspace directory
        """
        self.workspace_dir = Path(workspace_dir)
        db_path = self.workspace_dir / "sources.db"
        self.storage = SourceStorage(str(db_path))

    def create_source(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new source.

        Args:
            payload: Source creation payload

        Returns:
            Created source as dict

        Raises:
            ValueError: If payload is invalid
        """
        name = payload.get("name")
        if not name:
            raise ValueError("name is required")

        source_type_str = payload.get("type")
        if not source_type_str:
            raise ValueError("type is required")

        try:
            source_type = SourceType(source_type_str)
        except ValueError:
            raise ValueError(f"Invalid source type: {source_type_str}")

        # Parse config based on type
        config_payload = payload.get("config", {})

        if source_type == SourceType.JIRA:
            config = self._parse_jira_config(config_payload)
        elif source_type == SourceType.CONFLUENCE:
            config = self._parse_confluence_config(config_payload)
        elif source_type == SourceType.FILE_UPLOAD:
            config = self._parse_file_upload_config(config_payload)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        enabled = payload.get("enabled", True)

        source = self.storage.create_source(
            name=name,
            type=source_type,
            config=config,
            enabled=enabled,
        )

        return self._source_to_dict(source)

    def get_source(self, source_id: str) -> dict[str, Any]:
        """
        Get source by ID.

        Args:
            source_id: Source ID

        Returns:
            Source as dict

        Raises:
            ValueError: If source not found
        """
        source = self.storage.get_source(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")

        return self._source_to_dict(source)

    def list_sources(self, enabled_only: bool = False) -> dict[str, Any]:
        """
        List all sources.

        Args:
            enabled_only: Only return enabled sources

        Returns:
            Dict with sources list
        """
        sources = self.storage.list_sources(enabled_only=enabled_only)
        return {
            "sources": [self._source_to_dict(source) for source in sources],
            "total": len(sources),
        }

    def update_source(self, source_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Update source.

        Args:
            source_id: Source ID
            payload: Update payload

        Returns:
            Updated source as dict

        Raises:
            ValueError: If source not found or payload invalid
        """
        name = payload.get("name")
        enabled = payload.get("enabled")

        config = None
        if "config" in payload:
            # Get current source to determine type
            current_source = self.storage.get_source(source_id)
            if not current_source:
                raise ValueError(f"Source not found: {source_id}")

            config_payload = payload["config"]
            if current_source.type == SourceType.JIRA:
                config = self._parse_jira_config(config_payload)
            elif current_source.type == SourceType.CONFLUENCE:
                config = self._parse_confluence_config(config_payload)
            elif current_source.type == SourceType.FILE_UPLOAD:
                config = self._parse_file_upload_config(config_payload)

        updated_source = self.storage.update_source(
            source_id=source_id,
            name=name,
            config=config,
            enabled=enabled,
        )

        if not updated_source:
            raise ValueError(f"Source not found: {source_id}")

        return self._source_to_dict(updated_source)

    def delete_source(self, source_id: str) -> dict[str, Any]:
        """
        Delete source.

        Args:
            source_id: Source ID

        Returns:
            Success status

        Raises:
            ValueError: If source not found
        """
        deleted = self.storage.delete_source(source_id)
        if not deleted:
            raise ValueError(f"Source not found: {source_id}")

        return {"success": True, "source_id": source_id}

    def test_connection(self, source_id: str) -> dict[str, Any]:
        """
        Test source connection.

        Args:
            source_id: Source ID

        Returns:
            Connection test result

        Raises:
            ValueError: If source not found
            NotImplementedError: Connection testing not yet implemented
        """
        source = self.storage.get_source(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")

        # TODO: Implement actual connection testing via connectors
        raise NotImplementedError("Connection testing not yet implemented")

    def trigger_sync(self, source_id: str) -> dict[str, Any]:
        """
        Trigger sync for a source.

        Args:
            source_id: Source ID

        Returns:
            Sync status

        Raises:
            ValueError: If source not found
            NotImplementedError: Sync not yet implemented
        """
        source = self.storage.get_source(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")

        # TODO: Implement actual sync via connectors
        raise NotImplementedError("Sync not yet implemented")

    def get_sync_status(self, source_id: str) -> dict[str, Any]:
        """
        Get sync status for a source.

        Args:
            source_id: Source ID

        Returns:
            Sync status

        Raises:
            ValueError: If source not found
        """
        source = self.storage.get_source(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")

        return {
            "source_id": source_id,
            "sync_state": self._sync_state_to_dict(source.sync_state),
        }

    def _parse_jira_config(self, payload: dict[str, Any]) -> JiraSourceConfig:
        """Parse Jira config from payload."""
        base_url = payload.get("base_url")
        if not base_url:
            raise ValueError("base_url is required for Jira source")

        credential_ref = payload.get("credential_ref")
        if not credential_ref:
            raise ValueError("credential_ref is required for Jira source")

        scope_type_str = payload.get("scope_type")
        if not scope_type_str:
            raise ValueError("scope_type is required for Jira source")

        try:
            scope_type = JiraScopeType(scope_type_str)
        except ValueError:
            raise ValueError(f"Invalid Jira scope type: {scope_type_str}")

        return JiraSourceConfig(
            base_url=base_url,
            credential_ref=credential_ref,
            scope_type=scope_type,
            issue_key=payload.get("issue_key"),
            project=payload.get("project"),
            jql=payload.get("jql"),
        )

    def _parse_confluence_config(self, payload: dict[str, Any]) -> ConfluenceSourceConfig:
        """Parse Confluence config from payload."""
        base_url = payload.get("base_url")
        if not base_url:
            raise ValueError("base_url is required for Confluence source")

        credential_ref = payload.get("credential_ref")
        if not credential_ref:
            raise ValueError("credential_ref is required for Confluence source")

        scope_type_str = payload.get("scope_type")
        if not scope_type_str:
            raise ValueError("scope_type is required for Confluence source")

        try:
            scope_type = ConfluenceScopeType(scope_type_str)
        except ValueError:
            raise ValueError(f"Invalid Confluence scope type: {scope_type_str}")

        return ConfluenceSourceConfig(
            base_url=base_url,
            credential_ref=credential_ref,
            scope_type=scope_type,
            page_id=payload.get("page_id"),
            space_key=payload.get("space_key"),
        )

    def _parse_file_upload_config(self, payload: dict[str, Any]) -> FileUploadSourceConfig:
        """Parse file upload config from payload."""
        file_path = payload.get("file_path")
        if not file_path:
            raise ValueError("file_path is required for file upload source")

        file_type = payload.get("file_type")
        if not file_type:
            raise ValueError("file_type is required for file upload source")

        return FileUploadSourceConfig(
            file_path=file_path,
            file_type=file_type,
            parser=payload.get("parser", "mineru"),
            original_filename=payload.get("original_filename"),
        )

    def _source_to_dict(self, source: Source) -> dict[str, Any]:
        """Convert Source to dict."""
        return {
            "id": source.id,
            "name": source.name,
            "type": source.type.value,
            "config": source.config.model_dump(),
            "sync_state": self._sync_state_to_dict(source.sync_state),
            "created_at": source.created_at.isoformat(),
            "updated_at": source.updated_at.isoformat(),
            "enabled": source.enabled,
        }

    def _sync_state_to_dict(self, sync_state: SyncState) -> dict[str, Any]:
        """Convert SyncState to dict."""
        return {
            "last_sync_time": sync_state.last_sync_time.isoformat() if sync_state.last_sync_time else None,
            "cursor": sync_state.cursor,
            "total_items": sync_state.total_items,
            "sync_status": sync_state.sync_status.value,
            "error_message": sync_state.error_message,
            "started_at": sync_state.started_at.isoformat() if sync_state.started_at else None,
            "completed_at": sync_state.completed_at.isoformat() if sync_state.completed_at else None,
        }

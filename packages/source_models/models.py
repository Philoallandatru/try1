"""
Core data models for unified source management.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Type of data source."""

    JIRA = "jira"
    CONFLUENCE = "confluence"
    FILE_UPLOAD = "file_upload"


class SyncStatus(str, Enum):
    """Status of sync operation."""

    INITIAL = "initial"  # First sync in progress
    INCREMENTAL = "incremental"  # Incremental sync in progress
    COMPLETED = "completed"  # Sync completed successfully
    FAILED = "failed"  # Sync failed
    IDLE = "idle"  # No sync in progress


class JiraScopeType(str, Enum):
    """Jira scope type."""

    SINGLE_ISSUE = "single_issue"
    PROJECT = "project"
    JQL = "jql"


class ConfluenceScopeType(str, Enum):
    """Confluence scope type."""

    SINGLE_PAGE = "single_page"
    SPACE = "space"


# Source Configurations


class JiraSourceConfig(BaseModel):
    """Configuration for Jira source."""

    base_url: str = Field(..., description="Jira base URL")
    credential_ref: str = Field(..., description="Reference to stored credential")
    scope_type: JiraScopeType = Field(..., description="Type of scope")
    issue_key: Optional[str] = Field(None, description="Single issue key (for single_issue)")
    project: Optional[str] = Field(None, description="Project key (for project)")
    jql: Optional[str] = Field(None, description="JQL query (for jql)")


class ConfluenceSourceConfig(BaseModel):
    """Configuration for Confluence source."""

    base_url: str = Field(..., description="Confluence base URL")
    credential_ref: str = Field(..., description="Reference to stored credential")
    scope_type: ConfluenceScopeType = Field(..., description="Type of scope")
    page_id: Optional[str] = Field(None, description="Single page ID (for single_page)")
    space_key: Optional[str] = Field(None, description="Space key (for space)")


class FileUploadSourceConfig(BaseModel):
    """Configuration for file upload source."""

    file_path: str = Field(..., description="Path to uploaded file")
    file_type: str = Field(..., description="File type (pdf, docx, xlsx, pptx, image)")
    parser: str = Field(default="mineru", description="Parser to use (mineru, pypdf, python-docx)")
    original_filename: Optional[str] = Field(None, description="Original filename")


SourceConfig = Union[JiraSourceConfig, ConfluenceSourceConfig, FileUploadSourceConfig]


# Sync State


class SyncState(BaseModel):
    """State of sync operation."""

    last_sync_time: Optional[datetime] = Field(None, description="Last successful sync time")
    cursor: Optional[str] = Field(None, description="Cursor for pagination (initial sync)")
    total_items: int = Field(default=0, description="Total items synced")
    sync_status: SyncStatus = Field(default=SyncStatus.IDLE, description="Current sync status")
    error_message: Optional[str] = Field(None, description="Error message if sync failed")
    started_at: Optional[datetime] = Field(None, description="Sync start time")
    completed_at: Optional[datetime] = Field(None, description="Sync completion time")


# Source Model


class Source(BaseModel):
    """Unified source model."""

    id: str = Field(..., description="Unique source ID")
    name: str = Field(..., description="Human-readable source name")
    type: SourceType = Field(..., description="Source type")
    config: SourceConfig = Field(..., description="Type-specific configuration")
    sync_state: SyncState = Field(default_factory=SyncState, description="Sync state")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    enabled: bool = Field(default=True, description="Whether source is enabled")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Connection Test Result


class ConnectionTestResult(BaseModel):
    """Result of connection test."""

    success: bool = Field(..., description="Whether connection test succeeded")
    message: str = Field(..., description="Human-readable message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional details")
    tested_at: datetime = Field(default_factory=datetime.utcnow, description="Test time")


# Fetch Result


class FetchResult(BaseModel):
    """Result of fetch operation."""

    success: bool = Field(..., description="Whether fetch succeeded")
    items_fetched: int = Field(default=0, description="Number of items fetched")
    cursor: Optional[str] = Field(None, description="Next cursor for pagination")
    has_more: bool = Field(default=False, description="Whether more items available")
    raw_data: list[dict[str, Any]] = Field(default_factory=list, description="Raw fetched data")
    error_message: Optional[str] = Field(None, description="Error message if fetch failed")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="Fetch time")

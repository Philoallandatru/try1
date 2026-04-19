"""
Unified Confluence connector implementing SourceConnector interface.

Supports:
- Connection testing
- Initial sync with cursor-based pagination
- Incremental sync based on modification time
- Conversion to canonical document format
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from packages.source_models import (
    ConfluenceSourceConfig,
    ConnectionTestResult,
    FetchResult,
    SourceConnector,
)
from services.connectors.confluence.atlassian_api_fetch import (
    fetch_confluence_page_sync_atlassian_api,
)
from services.connectors.confluence.connector import _page_to_document


class ConfluenceConnector(SourceConnector):
    """
    Confluence connector implementing unified SourceConnector interface.
    """

    def __init__(self, config: ConfluenceSourceConfig, credential: dict[str, str]):
        """
        Initialize Confluence connector.

        Args:
            config: Confluence source configuration
            credential: Credential dictionary with username/password/token
        """
        self.config = config
        self.credential = credential

    async def test_connection(self) -> ConnectionTestResult:
        """
        Test Confluence connection.

        Returns:
            ConnectionTestResult with success status
        """
        try:
            # Try to fetch a single page to verify connection
            payload = fetch_confluence_page_sync_atlassian_api(
                base_url=self.config.base_url,
                username=self.credential.get("username"),
                password=self.credential.get("password"),
                token=self.credential.get("token"),
                auth_mode="auto",
                page_id=self.config.page_id if self.config.scope_type.value == "single_page" else None,
                space_key=self.config.space_key if self.config.scope_type.value == "space" else None,
                page_size=1,
                verify_ssl=True,
                include_attachments=False,
            )

            # If we got here without exception, connection is good
            return ConnectionTestResult(
                success=True,
                message=f"Successfully connected to {self.config.base_url}",
                details={
                    "base_url": self.config.base_url,
                    "scope_type": self.config.scope_type.value,
                },
            )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={
                    "base_url": self.config.base_url,
                    "error": str(e),
                },
            )

    async def fetch_initial(self, cursor: Optional[str] = None) -> FetchResult:
        """
        Initial sync with cursor-based pagination.

        Args:
            cursor: Optional cursor for resuming pagination (ISO datetime string)

        Returns:
            FetchResult with fetched items and next cursor
        """
        try:
            payload = fetch_confluence_page_sync_atlassian_api(
                base_url=self.config.base_url,
                username=self.credential.get("username"),
                password=self.credential.get("password"),
                token=self.credential.get("token"),
                auth_mode="auto",
                page_id=self.config.page_id if self.config.scope_type.value == "single_page" else None,
                space_key=self.config.space_key if self.config.scope_type.value == "space" else None,
                cursor=cursor,
                page_size=50,
                verify_ssl=True,
                include_attachments=True,
            )

            pages = payload.get("pages", [])

            # Determine next cursor (max modified time from fetched pages)
            next_cursor = None
            if pages:
                modified_times = []
                for page in pages:
                    version = page.get("version", {})
                    modified = version.get("when") or page.get("lastmodified")
                    if modified:
                        modified_times.append(modified)

                if modified_times:
                    next_cursor = max(modified_times)

            has_more = len(pages) >= 50  # If we got a full page, there might be more

            return FetchResult(
                success=True,
                items_fetched=len(pages),
                cursor=next_cursor,
                has_more=has_more,
                raw_data=pages,
            )

        except Exception as e:
            return FetchResult(
                success=False,
                items_fetched=0,
                error_message=f"Initial fetch failed: {str(e)}",
            )

    async def fetch_incremental(self, since: datetime) -> FetchResult:
        """
        Incremental sync based on modification time.

        Args:
            since: Fetch items modified since this time

        Returns:
            FetchResult with updated items
        """
        try:
            # Format datetime for CQL
            since_str = since.strftime("%Y-%m-%d %H:%M")

            payload = fetch_confluence_page_sync_atlassian_api(
                base_url=self.config.base_url,
                username=self.credential.get("username"),
                password=self.credential.get("password"),
                token=self.credential.get("token"),
                auth_mode="auto",
                page_id=self.config.page_id if self.config.scope_type.value == "single_page" else None,
                space_key=self.config.space_key if self.config.scope_type.value == "space" else None,
                modified_from=since_str,
                page_size=100,  # Incremental syncs typically have fewer items
                verify_ssl=True,
                include_attachments=True,
            )

            pages = payload.get("pages", [])

            return FetchResult(
                success=True,
                items_fetched=len(pages),
                has_more=False,  # Incremental sync fetches all at once
                raw_data=pages,
            )

        except Exception as e:
            return FetchResult(
                success=False,
                items_fetched=0,
                error_message=f"Incremental fetch failed: {str(e)}",
            )

    def to_canonical(self, raw_data: Any) -> dict[str, Any]:
        """
        Convert Confluence page to canonical document format.

        Args:
            raw_data: Raw Confluence page data

        Returns:
            Canonical document as dictionary
        """
        if not isinstance(raw_data, dict):
            raise ValueError("raw_data must be a dictionary")

        page_id = raw_data.get("id")
        if not page_id:
            raise ValueError("Page must have an 'id' field")

        # Use existing converter
        document = _page_to_document(
            raw_data,
            source_uri=f"{self.config.base_url.rstrip('/')}/pages/viewpage.action?pageId={page_id}",
            incremental=False,  # Will be set by sync logic
            acl_policy="team:ssd",  # Default policy
        )

        return document

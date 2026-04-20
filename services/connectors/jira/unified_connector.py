"""
Unified Jira connector implementing SourceConnector interface.

Supports:
- Connection testing
- Initial sync with cursor-based pagination
- Incremental sync based on update time
- Conversion to canonical document format
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from packages.source_models import (
    ConnectionTestResult,
    FetchResult,
    JiraSourceConfig,
    SourceConnector,
)
from services.connectors.jira.atlassian_api_fetch import (
    fetch_jira_server_sync_atlassian_api,
)
from services.connectors.jira.connector import _issue_to_document
from services.connectors.jira.field_aliases import load_jira_field_aliases
from services.connectors.jira.issue_type_profiles import load_jira_issue_type_profiles


class JiraConnector(SourceConnector):
    """
    Jira connector implementing unified SourceConnector interface.
    """

    def __init__(self, config: JiraSourceConfig, credential: dict[str, str]):
        """
        Initialize Jira connector.

        Args:
            config: Jira source configuration
            credential: Credential dictionary with username/password/token
        """
        self.config = config
        self.credential = credential
        self.field_aliases = load_jira_field_aliases()
        self.issue_type_profiles = load_jira_issue_type_profiles()

    async def test_connection(self) -> ConnectionTestResult:
        """
        Test Jira connection.

        Returns:
            ConnectionTestResult with success status
        """
        try:
            # Try to fetch a single issue to verify connection
            jql = self._build_jql(max_results=1)

            payload = fetch_jira_server_sync_atlassian_api(
                base_url=self.config.base_url,
                username=self.credential.get("username"),
                password=self.credential.get("password"),
                token=self.credential.get("token"),
                auth_mode="auto",
                jql=jql,
                page_size=1,
                verify_ssl=True,
                include_comments=False,
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
            jql = self._build_jql()

            payload = fetch_jira_server_sync_atlassian_api(
                base_url=self.config.base_url,
                username=self.credential.get("username"),
                password=self.credential.get("password"),
                token=self.credential.get("token"),
                auth_mode="auto",
                jql=jql,
                cursor=cursor,
                page_size=50,
                verify_ssl=True,
                include_comments=True,
                include_attachments=True,
            )

            issues = payload.get("issues", [])

            # Determine next cursor (max updated time from fetched issues)
            next_cursor = None
            if issues:
                updated_times = []
                for issue in issues:
                    fields = issue.get("fields", {})
                    updated = fields.get("updated") or issue.get("updated_at")
                    if updated:
                        updated_times.append(updated)

                if updated_times:
                    next_cursor = max(updated_times)

            has_more = len(issues) >= 50  # If we got a full page, there might be more

            return FetchResult(
                success=True,
                items_fetched=len(issues),
                cursor=next_cursor,
                has_more=has_more,
                raw_data=issues,
            )

        except Exception as e:
            return FetchResult(
                success=False,
                items_fetched=0,
                error_message=f"Initial fetch failed: {str(e)}",
            )

    async def fetch_incremental(self, since: datetime) -> FetchResult:
        """
        Incremental sync based on update time.

        Args:
            since: Fetch items updated since this time

        Returns:
            FetchResult with updated items
        """
        try:
            # Format datetime for JQL
            since_str = since.strftime("%Y-%m-%d %H:%M")

            jql = self._build_jql()
            # Add time filter to JQL
            jql = f"({jql}) AND updated >= '{since_str}'"

            payload = fetch_jira_server_sync_atlassian_api(
                base_url=self.config.base_url,
                username=self.credential.get("username"),
                password=self.credential.get("password"),
                token=self.credential.get("token"),
                auth_mode="auto",
                jql=jql,
                page_size=100,  # Incremental syncs typically have fewer items
                verify_ssl=True,
                include_comments=True,
                include_attachments=True,
            )

            issues = payload.get("issues", [])

            return FetchResult(
                success=True,
                items_fetched=len(issues),
                has_more=False,  # Incremental sync fetches all at once
                raw_data=issues,
            )

        except Exception as e:
            return FetchResult(
                success=False,
                items_fetched=0,
                error_message=f"Incremental fetch failed: {str(e)}",
            )

    def to_canonical(self, raw_data: Any) -> dict[str, Any]:
        """
        Convert Jira issue to canonical document format.

        Args:
            raw_data: Raw Jira issue data

        Returns:
            Canonical document as dictionary
        """
        if not isinstance(raw_data, dict):
            raise ValueError("raw_data must be a dictionary")

        issue_key = raw_data.get("key")
        if not issue_key:
            raise ValueError("Issue must have a 'key' field")

        # Use existing converter
        document = _issue_to_document(
            raw_data,
            source_uri=f"{self.config.base_url.rstrip('/')}/browse/{issue_key}",
            incremental=False,  # Will be set by sync logic
            acl_policy="team:ssd",  # Default policy
            field_name_map=None,
            field_aliases=self.field_aliases,
            issue_type_profiles=self.issue_type_profiles,
        )

        return document

    def _build_jql(self, max_results: Optional[int] = None) -> str:
        """
        Build JQL query based on scope configuration.

        Args:
            max_results: Optional limit for testing

        Returns:
            JQL query string
        """
        from services.connectors.jira.atlassian_api_fetch import _build_jql

        if self.config.scope_type.value == "single_issue":
            if not self.config.issue_key:
                raise ValueError("issue_key is required for single_issue scope")
            jql = _build_jql(issue_key=self.config.issue_key)

        elif self.config.scope_type.value == "project":
            if not self.config.project:
                raise ValueError("project is required for project scope")
            jql = _build_jql(project_key=self.config.project)

        elif self.config.scope_type.value == "jql":
            if not self.config.jql:
                raise ValueError("jql is required for jql scope")
            jql = self.config.jql

        else:
            raise ValueError(f"Unknown scope type: {self.config.scope_type}")

        # Add ordering for consistent pagination
        if "order by" not in jql.lower():
            jql = f"{jql} ORDER BY updated ASC"

        return jql

"""
Abstract base class for source connectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from .models import ConnectionTestResult, FetchResult


class SourceConnector(ABC):
    """
    Abstract base class for all source connectors.

    All connectors (Jira, Confluence, FileUpload) must implement this interface.
    """

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """
        Verify credentials and connectivity.

        Returns:
            ConnectionTestResult with success status and message
        """
        pass

    @abstractmethod
    async def fetch_initial(self, cursor: Optional[str] = None) -> FetchResult:
        """
        Initial sync with cursor-based pagination.

        Args:
            cursor: Optional cursor for resuming pagination

        Returns:
            FetchResult with fetched items and next cursor
        """
        pass

    @abstractmethod
    async def fetch_incremental(self, since: datetime) -> FetchResult:
        """
        Incremental sync based on update time.

        Args:
            since: Fetch items updated since this time

        Returns:
            FetchResult with updated items
        """
        pass

    @abstractmethod
    def to_canonical(self, raw_data: Any) -> dict[str, Any]:
        """
        Convert source-specific format to canonical document.

        Args:
            raw_data: Raw data from source

        Returns:
            Canonical document as dictionary
        """
        pass

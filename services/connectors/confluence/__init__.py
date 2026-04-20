"""
Confluence connector module.

Exports:
- fetch_confluence_page_sync: Legacy function for backward compatibility
- load_confluence_sync: Load Confluence sync from fixture file
- ConfluenceConnector: Unified connector implementing SourceConnector interface
"""

from .connector import fetch_confluence_page_sync, load_confluence_sync
from .unified_connector import ConfluenceConnector

__all__ = ["fetch_confluence_page_sync", "load_confluence_sync", "ConfluenceConnector"]

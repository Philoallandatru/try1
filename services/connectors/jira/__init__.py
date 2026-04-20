"""
Jira connector module.

Exports:
- fetch_jira_server_sync: Legacy function for backward compatibility
- load_jira_sync: Load Jira sync from fixture file
- JiraConnector: Unified connector implementing SourceConnector interface
"""

from .connector import fetch_jira_server_sync, load_jira_sync
from .unified_connector import JiraConnector

__all__ = ["fetch_jira_server_sync", "load_jira_sync", "JiraConnector"]

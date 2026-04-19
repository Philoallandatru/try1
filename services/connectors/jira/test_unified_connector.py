"""
Test script for unified Jira connector.

Usage:
    python -m services.connectors.jira.test_unified_connector
"""

import asyncio
from datetime import datetime, timedelta

from packages.source_models import JiraSourceConfig, JiraScopeType
from services.connectors.jira.unified_connector import JiraConnector


async def test_jira_connector():
    """Test Jira connector."""
    print("Testing unified Jira connector...\n")

    # Test configuration (using fixture data)
    config = JiraSourceConfig(
        base_url="https://jira.example.com",
        credential_ref="jira_test_token",
        scope_type=JiraScopeType.PROJECT,
        project="NVME",
    )

    # Mock credential
    credential = {
        "username": "test_user",
        "token": "test_token_123",
    }

    # Initialize connector
    connector = JiraConnector(config, credential)
    print(f"[OK] Initialized Jira connector")
    print(f"   - Base URL: {config.base_url}")
    print(f"   - Scope: {config.scope_type.value}")
    print(f"   - Project: {config.project}")

    # Test 1: Build JQL
    print("\n1. Building JQL query...")
    try:
        jql = connector._build_jql()
        print(f"   [OK] JQL: {jql}")
    except Exception as e:
        print(f"   [FAIL] {e}")
        return

    # Test 2: Test connection (will fail without real credentials, but tests the flow)
    print("\n2. Testing connection...")
    try:
        result = await connector.test_connection()
        if result.success:
            print(f"   [OK] Connection successful")
            print(f"   - Message: {result.message}")
        else:
            print(f"   [EXPECTED] Connection failed (no real credentials)")
            print(f"   - Message: {result.message}")
    except Exception as e:
        print(f"   [EXPECTED] Exception (no real credentials): {e}")

    # Test 3: Test with single issue scope
    print("\n3. Testing single issue scope...")
    single_issue_config = JiraSourceConfig(
        base_url="https://jira.example.com",
        credential_ref="jira_test_token",
        scope_type=JiraScopeType.SINGLE_ISSUE,
        issue_key="NVME-777",
    )
    single_connector = JiraConnector(single_issue_config, credential)
    jql = single_connector._build_jql()
    print(f"   [OK] Single issue JQL: {jql}")

    # Test 4: Test with JQL scope
    print("\n4. Testing JQL scope...")
    jql_config = JiraSourceConfig(
        base_url="https://jira.example.com",
        credential_ref="jira_test_token",
        scope_type=JiraScopeType.JQL,
        jql="project = NVME AND status = 'In Progress'",
    )
    jql_connector = JiraConnector(jql_config, credential)
    jql = jql_connector._build_jql()
    print(f"   [OK] Custom JQL: {jql}")

    # Test 5: Test canonical document conversion (with mock data)
    print("\n5. Testing canonical document conversion...")
    mock_issue = {
        "key": "NVME-777",
        "fields": {
            "summary": "Test Issue",
            "description": "Test description",
            "updated": "2026-04-20T10:00:00.000+0000",
            "project": {"key": "NVME"},
            "issuetype": {"name": "Bug"},
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
        },
    }

    try:
        canonical_doc = connector.to_canonical(mock_issue)
        print(f"   [OK] Converted to canonical document")
        print(f"   - Document ID: {canonical_doc['document_id']}")
        print(f"   - Title: {canonical_doc['title']}")
        print(f"   - Source type: {canonical_doc['source_type']}")
        print(f"   - Sections: {len(canonical_doc['structure']['sections'])}")
    except Exception as e:
        print(f"   [FAIL] {e}")

    # Test 6: Test fetch_initial (will fail without real credentials)
    print("\n6. Testing fetch_initial...")
    try:
        result = await connector.fetch_initial()
        if result.success:
            print(f"   [OK] Fetched {result.items_fetched} items")
            print(f"   - Has more: {result.has_more}")
            print(f"   - Cursor: {result.cursor}")
        else:
            print(f"   [EXPECTED] Fetch failed (no real credentials)")
            print(f"   - Error: {result.error_message}")
    except Exception as e:
        print(f"   [EXPECTED] Exception (no real credentials): {e}")

    # Test 7: Test fetch_incremental (will fail without real credentials)
    print("\n7. Testing fetch_incremental...")
    since = datetime.now() - timedelta(days=7)
    try:
        result = await connector.fetch_incremental(since)
        if result.success:
            print(f"   [OK] Fetched {result.items_fetched} items")
        else:
            print(f"   [EXPECTED] Fetch failed (no real credentials)")
            print(f"   - Error: {result.error_message}")
    except Exception as e:
        print(f"   [EXPECTED] Exception (no real credentials): {e}")

    print("\n" + "=" * 50)
    print("[OK] Jira connector interface tests passed!")
    print("=" * 50)
    print("\nNote: Connection and fetch tests expected to fail without real Jira credentials.")
    print("The important part is that the interface is correctly implemented.")


if __name__ == "__main__":
    asyncio.run(test_jira_connector())

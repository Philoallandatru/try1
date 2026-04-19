"""
Test script for unified Source API.

Usage:
    python -m apps.portal_runner.test_source_api
"""

import os
import tempfile
from pathlib import Path

from apps.portal_runner.source_api import SourceAPI


def test_source_api():
    """Test Source API."""
    print("Testing unified Source API...\n")

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir) / "test_workspace"
        workspace_dir.mkdir()

        print(f"[OK] Created test workspace: {workspace_dir}")

        # Initialize API
        api = SourceAPI(workspace_dir)
        print(f"[OK] Initialized API")

        # Test 1: Create Jira source
        print("\n1. Creating Jira source...")
        jira_payload = {
            "name": "Production Jira",
            "type": "jira",
            "config": {
                "base_url": "https://jira.example.com",
                "credential_ref": "jira_prod_token",
                "scope_type": "project",
                "project": "NVME",
            },
            "enabled": True,
        }

        jira_source = api.create_source(jira_payload)
        print(f"   [OK] Created Jira source: {jira_source['id']}")
        print(f"   - Name: {jira_source['name']}")
        print(f"   - Type: {jira_source['type']}")
        print(f"   - Sync status: {jira_source['sync_state']['sync_status']}")

        jira_id = jira_source["id"]

        # Test 2: Create Confluence source
        print("\n2. Creating Confluence source...")
        confluence_payload = {
            "name": "Engineering Wiki",
            "type": "confluence",
            "config": {
                "base_url": "https://confluence.example.com",
                "credential_ref": "confluence_token",
                "scope_type": "space",
                "space_key": "ENG",
            },
            "enabled": True,
        }

        confluence_source = api.create_source(confluence_payload)
        print(f"   [OK] Created Confluence source: {confluence_source['id']}")
        print(f"   - Name: {confluence_source['name']}")
        print(f"   - Type: {confluence_source['type']}")

        confluence_id = confluence_source["id"]

        # Test 3: Create File Upload source
        print("\n3. Creating File Upload source...")
        file_payload = {
            "name": "NVMe Spec",
            "type": "file_upload",
            "config": {
                "file_path": "/tmp/nvme-spec-1.4.pdf",
                "file_type": "pdf",
                "parser": "mineru",
                "original_filename": "nvme-spec-1.4.pdf",
            },
            "enabled": True,
        }

        file_source = api.create_source(file_payload)
        print(f"   [OK] Created File Upload source: {file_source['id']}")
        print(f"   - Name: {file_source['name']}")
        print(f"   - Type: {file_source['type']}")

        file_id = file_source["id"]

        # Test 4: List all sources
        print("\n4. Listing all sources...")
        sources_list = api.list_sources()
        print(f"   [OK] Found {sources_list['total']} sources")
        for source in sources_list["sources"]:
            print(f"   - {source['name']} ({source['type']})")

        # Test 5: Get source by ID
        print("\n5. Getting Jira source by ID...")
        retrieved = api.get_source(jira_id)
        assert retrieved["id"] == jira_id
        assert retrieved["name"] == "Production Jira"
        print(f"   [OK] Retrieved: {retrieved['name']}")

        # Test 6: Update source
        print("\n6. Updating Jira source...")
        update_payload = {
            "name": "Production Jira (Updated)",
            "enabled": False,
        }
        updated = api.update_source(jira_id, update_payload)
        assert updated["name"] == "Production Jira (Updated)"
        assert updated["enabled"] is False
        print(f"   [OK] Updated name: {updated['name']}")
        print(f"   [OK] Disabled source")

        # Test 7: List enabled sources only
        print("\n7. Listing enabled sources...")
        enabled_sources = api.list_sources(enabled_only=True)
        print(f"   [OK] Found {enabled_sources['total']} enabled sources")
        assert enabled_sources["total"] == 2  # Confluence and File Upload

        # Test 8: Get sync status
        print("\n8. Getting sync status...")
        sync_status = api.get_sync_status(jira_id)
        print(f"   [OK] Sync status: {sync_status['sync_state']['sync_status']}")
        print(f"   [OK] Total items: {sync_status['sync_state']['total_items']}")

        # Test 9: Update config
        print("\n9. Updating Jira config...")
        config_update_payload = {
            "config": {
                "base_url": "https://jira.example.com",
                "credential_ref": "jira_prod_token",
                "scope_type": "jql",
                "jql": "project = NVME AND updated >= -7d",
            }
        }
        updated_config = api.update_source(jira_id, config_update_payload)
        assert updated_config["config"]["scope_type"] == "jql"
        assert updated_config["config"]["jql"] == "project = NVME AND updated >= -7d"
        print(f"   [OK] Updated scope to JQL")
        print(f"   [OK] JQL: {updated_config['config']['jql']}")

        # Test 10: Delete source
        print("\n10. Deleting Confluence source...")
        delete_result = api.delete_source(confluence_id)
        assert delete_result["success"] is True
        print(f"   [OK] Deleted source: {confluence_id}")

        # Verify deletion
        remaining_sources = api.list_sources()
        assert remaining_sources["total"] == 2  # Jira and File Upload
        print(f"   [OK] Verified deletion (remaining: {remaining_sources['total']})")

        # Test 11: Error handling - Get non-existent source
        print("\n11. Testing error handling...")
        try:
            api.get_source("non-existent-id")
            print("   [FAIL] Should have raised ValueError")
        except ValueError as e:
            print(f"   [OK] Caught expected error: {e}")

        # Test 12: Error handling - Invalid source type
        print("\n12. Testing invalid source type...")
        try:
            invalid_payload = {
                "name": "Invalid Source",
                "type": "invalid_type",
                "config": {},
            }
            api.create_source(invalid_payload)
            print("   [FAIL] Should have raised ValueError")
        except ValueError as e:
            print(f"   [OK] Caught expected error: {e}")

        print("\n" + "=" * 50)
        print("[OK] All API tests passed!")
        print("=" * 50)

        # Cleanup
        api.storage.db.engine.dispose()
        print(f"\n[OK] Cleaned up test workspace")


if __name__ == "__main__":
    test_source_api()

"""
Test script for unified Source models.

Usage:
    python -m packages.source_models.test_models
"""

import os
import tempfile
from datetime import datetime

from packages.source_models import (
    JiraSourceConfig,
    JiraScopeType,
    Source,
    SourceStorage,
    SourceType,
    SyncState,
    SyncStatus,
)


def test_source_models():
    """Test source models and storage."""
    print("Testing unified Source models...\n")

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Initialize storage
        storage = SourceStorage(db_path)
        print(f"[OK] Initialized storage at {db_path}")

        # Test 1: Create Jira source
        print("\n1. Creating Jira source...")
        jira_config = JiraSourceConfig(
            base_url="https://jira.example.com",
            credential_ref="jira_cred_1",
            scope_type=JiraScopeType.PROJECT,
            project="NVME",
        )

        jira_source = storage.create_source(
            name="NVMe Project Tracker",
            type=SourceType.JIRA,
            config=jira_config,
        )

        print(f"   [OK] Created source: {jira_source.id}")
        print(f"   - Name: {jira_source.name}")
        print(f"   - Type: {jira_source.type}")
        print(f"   - Config: {jira_config.model_dump()}")
        print(f"   - Sync status: {jira_source.sync_state.sync_status}")

        # Test 2: Get source
        print("\n2. Retrieving source...")
        retrieved = storage.get_source(jira_source.id)
        assert retrieved is not None
        assert retrieved.id == jira_source.id
        print(f"   [OK] Retrieved source: {retrieved.name}")

        # Test 3: Update sync state
        print("\n3. Updating sync state...")
        new_sync_state = SyncState(
            sync_status=SyncStatus.INITIAL,
            started_at=datetime.utcnow(),
            cursor="page_1",
            total_items=0,
        )

        updated = storage.update_sync_state(jira_source.id, new_sync_state)
        assert updated is not None
        assert updated.sync_state.sync_status == SyncStatus.INITIAL
        assert updated.sync_state.cursor == "page_1"
        print(f"   [OK] Updated sync state: {updated.sync_state.sync_status}")

        # Test 4: Simulate sync completion
        print("\n4. Simulating sync completion...")
        completed_sync_state = SyncState(
            sync_status=SyncStatus.COMPLETED,
            started_at=new_sync_state.started_at,
            completed_at=datetime.utcnow(),
            last_sync_time=datetime.utcnow(),
            cursor=None,
            total_items=42,
        )

        completed = storage.update_sync_state(jira_source.id, completed_sync_state)
        assert completed is not None
        assert completed.sync_state.sync_status == SyncStatus.COMPLETED
        assert completed.sync_state.total_items == 42
        print(f"   [OK] Sync completed: {completed.sync_state.total_items} items")

        # Test 5: List sources
        print("\n5. Listing all sources...")
        all_sources = storage.list_sources()
        assert len(all_sources) == 1
        print(f"   [OK] Found {len(all_sources)} source(s)")

        # Test 6: Update source
        print("\n6. Updating source name...")
        updated_source = storage.update_source(
            jira_source.id,
            name="NVMe Project Tracker (Updated)",
        )
        assert updated_source is not None
        assert updated_source.name == "NVMe Project Tracker (Updated)"
        print(f"   [OK] Updated name: {updated_source.name}")

        # Test 7: Disable source
        print("\n7. Disabling source...")
        disabled = storage.update_source(jira_source.id, enabled=False)
        assert disabled is not None
        assert disabled.enabled is False
        print(f"   [OK] Source disabled")

        # Test 8: List enabled sources only
        print("\n8. Listing enabled sources...")
        enabled_sources = storage.list_sources(enabled_only=True)
        assert len(enabled_sources) == 0
        print(f"   [OK] Found {len(enabled_sources)} enabled source(s)")

        # Test 9: Delete source
        print("\n9. Deleting source...")
        deleted = storage.delete_source(jira_source.id)
        assert deleted is True
        print(f"   [OK] Source deleted")

        # Verify deletion
        retrieved_after_delete = storage.get_source(jira_source.id)
        assert retrieved_after_delete is None
        print(f"   [OK] Verified deletion")

        print("\n" + "=" * 50)
        print("[OK] All tests passed!")
        print("=" * 50)

    finally:
        # Close database connections
        storage.db.engine.dispose()

        # Cleanup
        import time
        time.sleep(0.1)  # Give Windows time to release file handle

        try:
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"\n[OK] Cleaned up test database")
        except PermissionError:
            print(f"\n[WARN] Could not delete test database (file in use): {db_path}")


if __name__ == "__main__":
    test_source_models()

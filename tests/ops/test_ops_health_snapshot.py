from __future__ import annotations

import unittest

from services.ops.health import build_ops_health
from services.connectors.jira.connector import load_jira_sync
from services.retrieval.persistence.snapshot_store import create_snapshot, refresh_snapshot
from services.retrieval.toolkit import load_document_snapshot
from tests.temp_utils import temporary_directory as TemporaryDirectory


class OpsHealthSnapshotTest(unittest.TestCase):
    def test_ops_health_can_read_snapshot_state(self) -> None:
        documents = load_document_snapshot("fixtures/retrieval/pageindex_corpus.json")
        jira_incremental = load_jira_sync("fixtures/connectors/jira/incremental_sync.json")

        with TemporaryDirectory() as temp_dir:
            create_snapshot(temp_dir, documents=documents, source_name="manual")
            refresh_snapshot(temp_dir, sync_payload=jira_incremental, source_name="jira")
            report = build_ops_health(
                snapshot_dir=temp_dir,
                reference_time_iso="2026-04-06T09:10:00Z",
            )

        self.assertEqual(report["backup_restore"]["backup"]["status"], "healthy")
        self.assertEqual(report["backup_restore"]["restore"]["status"], "validated")
        self.assertEqual(report["freshness"]["sources"][0]["source_type"], "jira")
        self.assertEqual(report["freshness"]["sources"][0]["status"], "healthy")


if __name__ == "__main__":
    unittest.main()

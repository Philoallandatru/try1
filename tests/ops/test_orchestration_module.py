from __future__ import annotations

import unittest

from services.ops.orchestration import run_multi_sync_health, run_sync_health
from tests.temp_utils import temporary_directory as TemporaryDirectory


class OpsOrchestrationModuleTest(unittest.TestCase):
    def test_run_sync_health_supports_fixture_source(self) -> None:
        with TemporaryDirectory() as temp_dir:
            payload = run_sync_health(
                snapshot_dir=temp_dir,
                corpus="fixtures/retrieval/pageindex_corpus.json",
                kind="jira",
                path="fixtures/connectors/jira/incremental_sync.json",
                live=False,
                reference_time_iso="2026-04-06T09:10:00Z",
            )
        self.assertEqual(payload["sync"]["source_name"], "jira")
        self.assertEqual(payload["ops_health"]["backup_restore"]["backup"]["status"], "healthy")
        self.assertEqual(payload["ops_health"]["backup_restore"]["restore"]["status"], "validated")

    def test_run_multi_sync_health_supports_fixture_sources(self) -> None:
        with TemporaryDirectory() as temp_dir:
            payload = run_multi_sync_health(
                {
                    "snapshot_dir": temp_dir,
                    "corpus": "fixtures/retrieval/pageindex_corpus.json",
                    "freshness_budget_minutes": 30,
                    "reference_time_iso": "2026-04-06T09:10:00Z",
                    "sources": [
                        {
                            "source_name": "jira",
                            "kind": "jira",
                            "path": "fixtures/connectors/jira/incremental_sync.json",
                            "live": False,
                            "page_size": 50,
                            "jql": "order by updated asc",
                            "auth_mode": "auto",
                            "insecure": False,
                        },
                        {
                            "source_name": "confluence",
                            "kind": "confluence",
                            "path": "fixtures/connectors/confluence/incremental_sync.json",
                            "live": False,
                            "page_size": 25,
                            "auth_mode": "auto",
                            "insecure": False,
                        },
                    ],
                }
            )
        self.assertEqual(len(payload["sources"]), 2)
        source_types = {entry["source_type"] for entry in payload["ops_health"]["freshness"]["sources"]}
        self.assertEqual(source_types, {"jira", "confluence"})


if __name__ == "__main__":
    unittest.main()

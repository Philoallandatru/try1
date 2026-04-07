from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.ops.profile import build_multi_sync_profile, load_json_file, validate_multi_sync_profile


class OpsProfileModuleTest(unittest.TestCase):
    def test_validate_multi_sync_profile_accepts_fixture_profile(self) -> None:
        profile = load_json_file("fixtures/ops/multi_sync_health_profile.json")
        self.assertEqual(validate_multi_sync_profile(profile), [])

    def test_validate_multi_sync_profile_rejects_missing_live_base_url(self) -> None:
        profile = {
            "jira": {"live": True},
            "confluence": {"path": "fixtures/connectors/confluence/incremental_sync.json"},
        }
        errors = validate_multi_sync_profile(profile)
        self.assertIn("profile.jira.base_url is required when live is true", errors)

    def test_build_multi_sync_profile_applies_cli_override_precedence(self) -> None:
        with TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "profile.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "snapshot_dir": ".tmp/from-profile",
                        "reference_time_iso": "2026-04-06T09:10:00Z",
                        "jira": {"path": "fixtures/connectors/jira/incremental_sync.json"},
                        "confluence": {"path": "fixtures/connectors/confluence/incremental_sync.json"},
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                profile=str(profile_path),
                snapshot_dir=".tmp/from-cli",
                corpus="fixtures/retrieval/pageindex_corpus.json",
                freshness_budget_minutes=30,
                reference_time_iso=None,
                jira_path=None,
                jira_live=False,
                jira_base_url=None,
                jira_username=None,
                jira_password=None,
                jira_token=None,
                jira_auth_mode="auto",
                jira_cursor=None,
                jira_page_size=50,
                jira_jql="order by updated asc",
                jira_insecure=False,
                confluence_path=None,
                confluence_live=False,
                confluence_base_url=None,
                confluence_username=None,
                confluence_password=None,
                confluence_token=None,
                confluence_auth_mode="auto",
                confluence_cursor=None,
                confluence_page_size=25,
                confluence_cql=None,
                confluence_space_key=None,
                confluence_insecure=False,
            )
            profile = build_multi_sync_profile(args)

        self.assertEqual(profile["snapshot_dir"], ".tmp/from-cli")
        self.assertEqual(profile["sources"][0]["path"], "fixtures/connectors/jira/incremental_sync.json")
        self.assertEqual(profile["sources"][1]["path"], "fixtures/connectors/confluence/incremental_sync.json")


if __name__ == "__main__":
    unittest.main()

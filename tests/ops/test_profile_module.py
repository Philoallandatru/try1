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

    def test_validate_multi_sync_profile_requires_image_download_dir_when_download_enabled(self) -> None:
        profile = {
            "jira": {
                "live": True,
                "base_url": "https://jira.example.com",
                "fetch_backend": "atlassian-api",
                "download_images": True,
            },
            "confluence": {
                "path": "fixtures/connectors/confluence/incremental_sync.json",
            },
        }
        errors = validate_multi_sync_profile(profile)
        self.assertIn("profile.jira.image_download_dir is required when download_images is true", errors)

    def test_build_multi_sync_profile_carries_confluence_page_tree_overrides(self) -> None:
        args = argparse.Namespace(
            profile=None,
            snapshot_dir=".tmp/workspace",
            corpus="fixtures/retrieval/pageindex_corpus.json",
            freshness_budget_minutes=30,
            reference_time_iso=None,
            jira_path="fixtures/connectors/jira/incremental_sync.json",
            jira_live=False,
            jira_base_url=None,
            jira_username=None,
            jira_password=None,
            jira_token=None,
            jira_auth_mode="auto",
            jira_cursor=None,
            jira_page_size=50,
            jira_jql="order by updated asc",
            jira_fetch_backend="native",
            jira_issue_key=None,
            jira_issue_keys=None,
            jira_project_key=None,
            jira_project_keys=None,
            jira_issue_type=None,
            jira_status=None,
            jira_label=None,
            jira_updated_from=None,
            jira_updated_to=None,
            jira_no_include_comments=False,
            jira_no_include_attachments=False,
            jira_no_include_image_metadata=False,
            jira_download_images=False,
            jira_image_download_dir=None,
            jira_insecure=False,
            confluence_path=None,
            confluence_live=True,
            confluence_base_url="https://confluence.example.com",
            confluence_username=None,
            confluence_password=None,
            confluence_token="secret",
            confluence_auth_mode="auto",
            confluence_cursor=None,
            confluence_page_size=25,
            confluence_cql=None,
            confluence_space_key=None,
            confluence_page_id=None,
            confluence_page_ids=None,
            confluence_root_page_id="CONF-ROOT",
            confluence_include_descendants=True,
            confluence_max_depth=2,
            confluence_title=None,
            confluence_label=None,
            confluence_ancestor_id=None,
            confluence_modified_from=None,
            confluence_modified_to=None,
            confluence_no_include_attachments=False,
            confluence_no_include_image_metadata=False,
            confluence_download_images=False,
            confluence_image_download_dir=None,
            confluence_fetch_backend="atlassian-api",
            confluence_insecure=False,
        )

        profile = build_multi_sync_profile(args)
        confluence = profile["sources"][1]
        self.assertEqual(confluence["root_page_id"], "CONF-ROOT")
        self.assertTrue(confluence["include_descendants"])
        self.assertEqual(confluence["max_depth"], 2)
        self.assertEqual(confluence["fetch_backend"], "atlassian-api")

    def test_validate_multi_sync_profile_rejects_confluence_max_depth_without_descendants(self) -> None:
        profile = {
            "jira": {"path": "fixtures/connectors/jira/incremental_sync.json"},
            "confluence": {
                "live": True,
                "base_url": "https://confluence.example.com",
                "fetch_backend": "atlassian-api",
                "root_page_id": "CONF-ROOT",
                "max_depth": 1,
            },
        }
        errors = validate_multi_sync_profile(profile)
        self.assertIn("profile.confluence.include_descendants must be true when max_depth is set", errors)


if __name__ == "__main__":
    unittest.main()

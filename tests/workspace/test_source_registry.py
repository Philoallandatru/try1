from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

import yaml

from services.workspace.source_registry import (
    build_fetch_request,
    config_hash,
    list_sources,
    load_run_profile,
    load_selector_profile,
    load_source,
    resolve_credential,
    selector_hash,
    write_run_profile,
    write_selector_profile,
    write_source,
)
from tests.temp_utils import temporary_directory as TemporaryDirectory


class SourceRegistryTest(unittest.TestCase):
    def test_source_selector_and_profile_round_trip(self) -> None:
        with TemporaryDirectory() as workspace:
            source_path = write_source(
                workspace,
                {
                    "version": 1,
                    "name": "jira_lab",
                    "kind": "jira",
                    "connector_type": "jira.atlassian_api",
                    "credential_ref": "jira_lab_token",
                    "config": {"base_url": "https://jira.example.com", "auth_mode": "auto"},
                    "defaults": {"include_comments": True, "include_attachments": True},
                    "selector_defaults": {"type": "project_slice", "project_key": "SSD"},
                    "policies": ["team:ssd", "public"],
                    "metadata": {"description": "SSD team Jira server", "tags": ["jira", "ssd"]},
                },
            )
            selector_path = write_selector_profile(
                workspace,
                {
                    "version": 1,
                    "name": "jira_one_issue",
                    "source": "jira_lab",
                    "selector": {"type": "issue", "issue_key": "SSD-777"},
                },
            )
            profile_path = write_run_profile(
                workspace,
                {
                    "version": 1,
                    "name": "ssd_deep_analysis_default",
                    "inputs": {
                        "jira": {
                            "source": "jira_lab",
                            "selector_profile": "jira_one_issue",
                        }
                    },
                    "analysis": {
                        "top_k": 5,
                        "llm_backend": "none",
                        "llm_prompt_mode": "strict",
                        "policies": ["team:ssd", "public"],
                    },
                },
            )

            self.assertTrue(Path(source_path).exists())
            self.assertTrue(Path(selector_path).exists())
            self.assertTrue(Path(profile_path).exists())
            self.assertEqual(load_source(workspace, "jira_lab")["name"], "jira_lab")
            self.assertEqual(load_selector_profile(workspace, "jira_one_issue")["source"], "jira_lab")
            self.assertEqual(load_run_profile(workspace, "ssd_deep_analysis_default")["analysis"]["top_k"], 5)
            self.assertEqual([source["name"] for source in list_sources(workspace)], ["jira_lab"])

    def test_hashes_are_stable_and_ignore_description_metadata(self) -> None:
        source = {
            "version": 1,
            "name": "jira_lab",
            "kind": "jira",
            "connector_type": "jira.atlassian_api",
            "credential_ref": "jira_lab_token",
            "config": {"base_url": "https://jira.example.com", "auth_mode": "auto"},
            "defaults": {"include_comments": True},
            "metadata": {"description": "before"},
        }
        changed_description = dict(source)
        changed_description["metadata"] = {"description": "after"}
        changed_base_url = json.loads(json.dumps(source))
        changed_base_url["config"]["base_url"] = "https://jira2.example.com"

        self.assertEqual(config_hash(source), config_hash(changed_description))
        self.assertNotEqual(config_hash(source), config_hash(changed_base_url))
        self.assertEqual(
            selector_hash({"selector": {"type": "issue", "issue_key": "SSD-777"}}),
            selector_hash({"selector": {"issue_key": "SSD-777", "type": "issue"}}),
        )

    def test_env_credential_resolution_does_not_persist_secret_value(self) -> None:
        with TemporaryDirectory() as workspace:
            credential_path = Path(workspace) / ".local" / "credentials.yaml"
            credential_path.parent.mkdir(parents=True, exist_ok=True)
            credential_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "credentials": {
                            "jira_lab_token": {"type": "bearer_env", "env": "JIRA_TOKEN"}
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            previous = os.environ.get("JIRA_TOKEN")
            os.environ["JIRA_TOKEN"] = "secret-token"
            try:
                credential = resolve_credential(workspace, "jira_lab_token")
            finally:
                if previous is None:
                    os.environ.pop("JIRA_TOKEN", None)
                else:
                    os.environ["JIRA_TOKEN"] = previous

            self.assertEqual(credential["auth_mode"], "bearer")
            self.assertEqual(credential["token"], "secret-token")
            stored = credential_path.read_text(encoding="utf-8")
            self.assertNotIn("secret-token", stored)

    def test_inline_bearer_credential_resolution(self) -> None:
        with TemporaryDirectory() as workspace:
            credential_path = Path(workspace) / ".local" / "credentials.yaml"
            credential_path.parent.mkdir(parents=True, exist_ok=True)
            credential_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "credentials": {
                            "jira_lab_pat": {"type": "bearer_inline", "value": "inline-token"}
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            credential = resolve_credential(workspace, "jira_lab_pat")

            self.assertEqual(credential["auth_mode"], "bearer")
            self.assertEqual(credential["token"], "inline-token")

    def test_pdf_local_file_source_and_selector_round_trip(self) -> None:
        with TemporaryDirectory() as workspace:
            source_path = write_source(
                workspace,
                {
                    "version": 1,
                    "name": "nvme_pdf",
                    "kind": "pdf",
                    "mode": "local",
                    "connector_type": "pdf.local_file",
                    "config": {"path": "fixtures/corpus/pdf/sample.pdf"},
                    "defaults": {"preferred_parser": "pypdf"},
                    "policies": ["team:ssd"],
                },
            )
            selector_path = write_selector_profile(
                workspace,
                {
                    "version": 1,
                    "name": "nvme_pdf_file",
                    "source": "nvme_pdf",
                    "selector": {"type": "file"},
                },
            )

            self.assertTrue(Path(source_path).exists())
            self.assertTrue(Path(selector_path).exists())
            request = build_fetch_request(workspace, source_name="nvme_pdf", selector_profile="nvme_pdf_file")
            self.assertEqual(request["kwargs"]["kind"], "pdf")
            self.assertFalse(request["kwargs"]["live"])
            self.assertEqual(request["kwargs"]["path"], "fixtures/corpus/pdf/sample.pdf")

    def test_fetch_request_merges_source_defaults_and_selector(self) -> None:
        with TemporaryDirectory() as workspace:
            write_source(
                workspace,
                {
                    "version": 1,
                    "name": "jira_lab",
                    "kind": "jira",
                    "connector_type": "jira.atlassian_api",
                    "config": {"base_url": "https://jira.example.com", "auth_mode": "auto"},
                    "defaults": {"include_comments": True, "include_attachments": False},
                    "selector_defaults": {"type": "project_slice", "project_key": "SSD"},
                    "policies": ["team:ssd"],
                },
            )
            write_selector_profile(
                workspace,
                {
                    "version": 1,
                    "name": "jira_one_issue",
                    "source": "jira_lab",
                    "selector": {"type": "issue", "issue_key": "SSD-777"},
                },
            )

            request = build_fetch_request(workspace, source_name="jira_lab", selector_profile="jira_one_issue")

            self.assertEqual(request["kwargs"]["kind"], "jira")
            self.assertTrue(request["kwargs"]["live"])
            self.assertEqual(request["kwargs"]["base_url"], "https://jira.example.com")
            self.assertEqual(request["kwargs"]["issue_key"], "SSD-777")
            self.assertTrue(request["kwargs"]["include_comments"])
            self.assertFalse(request["kwargs"]["include_attachments"])
            self.assertEqual(request["manifest"]["source_name"], "jira_lab")
            self.assertEqual(request["manifest"]["selector_profile"], "jira_one_issue")
            self.assertTrue(request["manifest"]["config_hash"].startswith("sha256:"))
            self.assertTrue(request["manifest"]["selector_hash"].startswith("sha256:"))

    def test_run_profile_accepts_registered_spec_assets(self) -> None:
        with TemporaryDirectory() as workspace:
            write_source(
                workspace,
                {
                    "version": 1,
                    "name": "jira_lab",
                    "kind": "jira",
                    "connector_type": "jira.atlassian_api",
                    "config": {"base_url": "https://jira.example.com", "auth_mode": "auto"},
                    "defaults": {"include_comments": True},
                    "policies": ["team:ssd"],
                },
            )
            write_selector_profile(
                workspace,
                {
                    "version": 1,
                    "name": "jira_one_issue",
                    "source": "jira_lab",
                    "selector": {"type": "issue", "issue_key": "SSD-777"},
                },
            )
            spec_asset_registry = Path(workspace) / "raw" / "files" / "spec_assets" / "registry.json"
            spec_asset_registry.parent.mkdir(parents=True, exist_ok=True)
            spec_asset_registry.write_text(
                json.dumps(
                    {
                        "assets": [
                            {
                                "asset_id": "nvme_2_1",
                                "display_name": "NVMe 2.1",
                                "version": "v1",
                                "document_id": "sample",
                                "asset_root": str(Path(workspace) / "raw" / "files" / "spec_assets" / "nvme_2_1" / "v1"),
                            }
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            profile_path = write_run_profile(
                workspace,
                {
                    "version": 1,
                    "name": "ssd_default",
                    "inputs": {
                        "jira": {"source": "jira_lab", "selector_profile": "jira_one_issue"},
                        "spec_assets": ["nvme_2_1"],
                    },
                    "analysis": {"top_k": 5, "llm_backend": "none", "llm_prompt_mode": "strict"},
                },
            )

            self.assertTrue(Path(profile_path).exists())
            profile = load_run_profile(workspace, "ssd_default")
            self.assertEqual(profile["inputs"]["spec_assets"], ["nvme_2_1"])

    def test_run_profile_rejects_unknown_spec_assets(self) -> None:
        with TemporaryDirectory() as workspace:
            write_source(
                workspace,
                {
                    "version": 1,
                    "name": "jira_lab",
                    "kind": "jira",
                    "connector_type": "jira.atlassian_api",
                    "config": {"base_url": "https://jira.example.com", "auth_mode": "auto"},
                    "defaults": {"include_comments": True},
                    "policies": ["team:ssd"],
                },
            )
            write_selector_profile(
                workspace,
                {
                    "version": 1,
                    "name": "jira_one_issue",
                    "source": "jira_lab",
                    "selector": {"type": "issue", "issue_key": "SSD-777"},
                },
            )

            with self.assertRaisesRegex(ValueError, "Unknown spec asset ids"):
                write_run_profile(
                    workspace,
                    {
                        "version": 1,
                        "name": "ssd_default",
                        "inputs": {
                            "jira": {"source": "jira_lab", "selector_profile": "jira_one_issue"},
                            "spec_assets": ["missing_asset"],
                        },
                        "analysis": {"top_k": 5, "llm_backend": "none", "llm_prompt_mode": "strict"},
                    },
                )


if __name__ == "__main__":
    unittest.main()

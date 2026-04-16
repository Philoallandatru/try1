from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import unittest

from services.connectors.confluence.connector import load_confluence_sync
from services.connectors.jira.connector import load_jira_sync
from services.retrieval.indexing.page_index import load_documents, load_page_index
from services.retrieval.persistence.snapshot_store import write_snapshot
from services.workspace.task_manifest import build_artifact_record, build_run_manifest, update_checkpoint, write_run_manifest
from services.workspace.workspace import _run_dir, init_workspace, workspace_paths
from tests.temp_utils import temporary_directory as TemporaryDirectory


class WorkspaceCliTest(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def _prepare_workspace_snapshot(self, workspace_dir: str) -> None:
        init_workspace(workspace_dir)
        snapshot_dir = workspace_paths(workspace_dir)["snapshot_root"]
        jira_documents = load_jira_sync(Path("fixtures/connectors/jira/incremental_sync.json"))["documents"]
        confluence_documents = load_confluence_sync(Path("fixtures/connectors/confluence/page_sync.json"))["documents"]
        spec_documents = load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
        write_snapshot(
            snapshot_dir,
            documents=[*jira_documents, *confluence_documents, *spec_documents],
            sources={
                "jira": {
                    "cursor": "jira-test",
                    "last_sync": "2026-04-15T00:00:00Z",
                    "sync_type": "incremental",
                    "document_count": len(jira_documents),
                },
                "confluence": {
                    "cursor": "conf-test",
                    "last_sync": "2026-04-15T00:00:00Z",
                    "sync_type": "full",
                    "document_count": len(confluence_documents),
                },
                "spec": {
                    "cursor": "spec-test",
                    "last_sync": "2026-04-15T00:00:00Z",
                    "sync_type": "manual",
                    "document_count": len(spec_documents),
                },
            },
        )

    def test_workspace_cli_init_creates_layout(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(Path(payload["config_path"]).exists())
            self.assertTrue(Path(temp_dir, "raw", "jira", "specs").exists())
            self.assertTrue(Path(temp_dir, "raw", "confluence", "specs").exists())
            self.assertTrue(Path(temp_dir, "snapshots", "current").exists())
            self.assertTrue(Path(temp_dir, "wiki", "topics.json").exists())
            self.assertTrue(Path(temp_dir, "wiki", "routes.json").exists())
            self.assertTrue(Path(temp_dir, "wiki", "compilation-manifest.json").exists())

    def test_workspace_cli_supports_fetch_build_export_query_and_lint(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/full_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-101"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            confluence_spec = Path(temp_dir, "raw", "confluence", "specs", "fixture-confluence.json")
            confluence_spec.write_text(
                json.dumps(
                    {
                        "kind": "confluence",
                        "mode": "fixture",
                        "path": "fixtures/connectors/confluence/page_sync.json",
                        "scope": {"type": "page", "page_id": "CONF-001"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            jira_fetch = self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec))
            self.assertEqual(jira_fetch.returncode, 0, jira_fetch.stderr)
            confluence_fetch = self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(confluence_spec))
            self.assertEqual(confluence_fetch.returncode, 0, confluence_fetch.stderr)

            build = self._run("scripts/workspace_cli.py", "build", temp_dir)
            self.assertEqual(build.returncode, 0, build.stderr)
            build_payload = json.loads(build.stdout)
            self.assertGreater(build_payload["document_count"], 0)
            self.assertGreater(build_payload["page_index_count"], 0)

            status = self._run("scripts/workspace_cli.py", "status", temp_dir)
            self.assertEqual(status.returncode, 0, status.stderr)
            status_payload = json.loads(status.stdout)
            self.assertEqual(status_payload["payload_counts"]["total"], 2)
            self.assertGreater(status_payload["snapshot"]["document_count"], 0)

            export = self._run("scripts/workspace_cli.py", "export", temp_dir)
            self.assertEqual(export.returncode, 0, export.stderr)
            export_payload = json.loads(export.stdout)
            self.assertGreater(export_payload["tree_document_count"], 0)

            query = self._run("scripts/workspace_cli.py", "query", temp_dir, "black screen")
            self.assertEqual(query.returncode, 0, query.stderr)
            query_payload = json.loads(query.stdout)
            self.assertGreaterEqual(query_payload["result_count"], 1)
            self.assertEqual(query_payload["answer"]["mode"], "extractive")
            self.assertIn("comparison", query_payload)
            self.assertEqual(query_payload["comparison"]["engine"], "pageindex")

            lint = self._run("scripts/workspace_cli.py", "lint", temp_dir)
            self.assertEqual(lint.returncode, 0, lint.stderr)
            lint_payload = json.loads(lint.stdout)
            self.assertTrue(lint_payload["ok"], lint_payload)

            llm_query = self._run(
                "scripts/workspace_cli.py",
                "query",
                temp_dir,
                "black screen",
                "--llm-backend",
                "mock",
                "--llm-mock-response",
                "Mock workspace answer",
                "--output-answer-md",
                str(Path(temp_dir) / "answer.md"),
            )
            self.assertEqual(llm_query.returncode, 0, llm_query.stderr)
            llm_query_payload = json.loads(llm_query.stdout)
            self.assertEqual(llm_query_payload["answer"]["mode"], "local-llm")
            self.assertEqual(llm_query_payload["answer"]["backend"], "mock")
            self.assertEqual(llm_query_payload["answer"]["text"], "Mock workspace answer")
            self.assertTrue(Path(llm_query_payload["output_answer_md"]).exists())

    def test_workspace_cli_ingest_spec_asset_writes_versioned_reusable_outputs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            self.assertEqual(self._run("scripts/workspace_cli.py", "init", temp_dir).returncode, 0)

            first = self._run(
                "scripts/workspace_cli.py",
                "ingest-spec-asset",
                temp_dir,
                "--spec-pdf",
                "fixtures/corpus/pdf/sample.pdf",
                "--asset-id",
                "nvme-base",
                "--display-name",
                "NVMe Base Spec",
                "--preferred-parser",
                "pypdf",
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            first_payload = json.loads(first.stdout)
            self.assertEqual(first_payload["asset_id"], "nvme-base")
            self.assertEqual(first_payload["version"], "v1")
            self.assertTrue(Path(first_payload["metadata_json"]).exists())
            self.assertTrue(Path(first_payload["document_json"]).exists())
            self.assertTrue(Path(first_payload["corpus_json"]).exists())
            self.assertTrue(Path(first_payload["markdown"]).exists())
            self.assertTrue(Path(first_payload["page_index_json"]).exists())

            page_index = load_page_index(first_payload["page_index_json"])
            self.assertGreaterEqual(len(page_index), 1)
            documents = load_documents(first_payload["corpus_json"])
            self.assertEqual(documents[0]["document_id"], "sample")

            second = self._run(
                "scripts/workspace_cli.py",
                "ingest-spec-asset",
                temp_dir,
                "--spec-pdf",
                "fixtures/corpus/pdf/sample.pdf",
                "--asset-id",
                "nvme-base",
                "--preferred-parser",
                "pypdf",
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            second_payload = json.loads(second.stdout)
            self.assertEqual(second_payload["version"], "v2")

            registry = json.loads(Path(second_payload["registry_json"]).read_text(encoding="utf-8"))
            matching = [entry for entry in registry["assets"] if entry["asset_id"] == "nvme-base"]
            self.assertEqual([entry["version"] for entry in matching], ["v1", "v2"])

    def test_workspace_cli_build_uses_latest_numeric_spec_asset_version(self) -> None:
        with TemporaryDirectory() as temp_dir:
            self.assertEqual(self._run("scripts/workspace_cli.py", "init", temp_dir).returncode, 0)
            registry_path = workspace_paths(temp_dir)["spec_assets_registry"]
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text(
                json.dumps(
                    {
                        "assets": [
                            {
                                "asset_id": "nvme-base",
                                "display_name": "NVMe Base",
                                "version": "v9",
                                "document_id": "sample-v9",
                                "created_at": "2026-04-15T00:00:00Z",
                                "source_pdf": "fixtures/corpus/pdf/sample.pdf",
                                "parser_used": "pypdf",
                                "asset_root": str(workspace_paths(temp_dir)["spec_assets_root"] / "nvme-base" / "v9"),
                            },
                            {
                                "asset_id": "nvme-base",
                                "display_name": "NVMe Base",
                                "version": "v10",
                                "document_id": "sample-v10",
                                "created_at": "2026-04-15T00:01:00Z",
                                "source_pdf": "fixtures/corpus/pdf/sample.pdf",
                                "parser_used": "pypdf",
                                "asset_root": str(workspace_paths(temp_dir)["spec_assets_root"] / "nvme-base" / "v10"),
                            }
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            for version, document_id in (("v9", "sample-v9"), ("v10", "sample-v10")):
                asset_root = workspace_paths(temp_dir)["spec_assets_root"] / "nvme-base" / version
                asset_root.mkdir(parents=True, exist_ok=True)
                (asset_root / "spec-corpus.json").write_text(
                    json.dumps(
                        {
                            "documents": [
                                {
                                    "document_id": document_id,
                                    "source_type": "pdf",
                                    "authority_level": "canonical",
                                    "version": version,
                                    "language": "en",
                                    "title": f"Spec {version}",
                                    "provenance": {"source_uri": "fixtures/corpus/pdf/sample.pdf", "parser": "pypdf"},
                                    "acl": {"allow": ["team:ssd"], "deny": [], "inherit": False},
                                    "structure": {"pages": [{"page": 1}], "sections": [{"page": 1, "heading": f"Section {version}"}]},
                                    "terminology": {"terms": []},
                                    "content_blocks": [{"id": f"block-{version}", "page": 1, "text": f"Spec content {version}"}],
                                    "markdown": f"# Spec {version}\n\nSpec content {version}",
                                }
                            ]
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/incremental_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-102"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec)).returncode, 0)

            build = self._run("scripts/workspace_cli.py", "build", temp_dir)
            self.assertEqual(build.returncode, 0, build.stderr)

            snapshot_documents = json.loads(
                (workspace_paths(temp_dir)["snapshot_root"] / "documents.json").read_text(encoding="utf-8")
            )["documents"]
            snapshot_ids = {document["document_id"] for document in snapshot_documents}
            self.assertIn("sample-v10", snapshot_ids)
            self.assertNotIn("sample-v9", snapshot_ids)

    def test_workspace_cli_build_includes_latest_spec_assets_in_snapshot(self) -> None:
        with TemporaryDirectory() as temp_dir:
            self.assertEqual(self._run("scripts/workspace_cli.py", "init", temp_dir).returncode, 0)

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/incremental_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-102"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec)).returncode, 0)
            self.assertEqual(
                self._run(
                    "scripts/workspace_cli.py",
                    "ingest-spec-asset",
                    temp_dir,
                    "--spec-pdf",
                    "fixtures/corpus/pdf/sample.pdf",
                    "--asset-id",
                    "nvme-base",
                    "--preferred-parser",
                    "pypdf",
                ).returncode,
                0,
            )

            build = self._run("scripts/workspace_cli.py", "build", temp_dir)
            self.assertEqual(build.returncode, 0, build.stderr)
            build_payload = json.loads(build.stdout)
            self.assertIn("spec_asset:nvme-base", build_payload["sources"])

            snapshot_documents = json.loads(
                (workspace_paths(temp_dir)["snapshot_root"] / "documents.json").read_text(encoding="utf-8")
            )["documents"]
            snapshot_ids = {document["document_id"] for document in snapshot_documents}
            self.assertIn("SSD-102", snapshot_ids)
            self.assertIn("sample", snapshot_ids)

            status = self._run("scripts/workspace_cli.py", "status", temp_dir)
            self.assertEqual(status.returncode, 0, status.stderr)
            status_payload = json.loads(status.stdout)
            self.assertEqual(status_payload["spec_counts"]["spec_assets"], 1)

    def test_workspace_cli_watch_run_once_fetches_specs_and_builds_snapshot(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            watch = self._run(
                "scripts/workspace_cli.py",
                "watch",
                temp_dir,
                "--run-once",
                "--max-cycles",
                "1",
                "--interval-seconds",
                "0.01",
            )
            self.assertEqual(watch.returncode, 0, watch.stderr)
            payload = json.loads(watch.stdout)
            self.assertTrue(payload["built"])
            self.assertGreater(payload["fetched_spec_count"], 0)
            snapshot_manifest = Path(temp_dir, "snapshots", "current", "manifest.json")
            self.assertTrue(snapshot_manifest.exists())

    def test_workspace_cli_route_and_inbox_manage_topic_control_plane(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/full_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-101"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            confluence_spec = Path(temp_dir, "raw", "confluence", "specs", "fixture-confluence.json")
            confluence_spec.write_text(
                json.dumps(
                    {
                        "kind": "confluence",
                        "mode": "fixture",
                        "path": "fixtures/connectors/confluence/page_sync.json",
                        "scope": {"type": "page", "page_id": "CONF-001"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            jira_fetch = self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec))
            self.assertEqual(jira_fetch.returncode, 0, jira_fetch.stderr)
            confluence_fetch = self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(confluence_spec))
            self.assertEqual(confluence_fetch.returncode, 0, confluence_fetch.stderr)
            build = self._run("scripts/workspace_cli.py", "build", temp_dir)
            self.assertEqual(build.returncode, 0, build.stderr)

            route_manifest = Path(temp_dir, "route-manifest.json")
            route_manifest.write_text(
                json.dumps(
                    {
                        "topics": [
                            {
                                "slug": "nvme-reliability",
                                "title": "NVMe Reliability",
                                "description": "Reliability learnings and issue-driven guidance.",
                            }
                        ],
                        "confluence": [
                            {
                                "document_id": "CONF-201",
                                "topic": "nvme-reliability",
                                "mode": "summarize",
                            }
                        ],
                        "jira": [
                            {
                                "document_id": "SSD-101",
                                "topic": "nvme-reliability",
                                "mode": "analyze",
                                "promote": True,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            route = self._run("scripts/workspace_cli.py", "route", temp_dir, "--manifest", str(route_manifest))
            self.assertEqual(route.returncode, 0, route.stderr)
            route_payload = json.loads(route.stdout)
            self.assertEqual(route_payload["topic_count"], 1)
            self.assertEqual(route_payload["route_counts"]["confluence"], 1)
            self.assertEqual(route_payload["route_counts"]["jira"], 1)

            topics_payload = json.loads(Path(temp_dir, "wiki", "topics.json").read_text(encoding="utf-8"))
            routes_payload = json.loads(Path(temp_dir, "wiki", "routes.json").read_text(encoding="utf-8"))
            compilation_payload = json.loads(Path(temp_dir, "wiki", "compilation-manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(topics_payload["topics"][0]["slug"], "nvme-reliability")
            self.assertEqual(routes_payload["confluence"][0]["document_id"], "CONF-201")
            self.assertEqual(routes_payload["jira"][0]["document_id"], "SSD-101")
            self.assertEqual(len(compilation_payload["items"]), 2)
            self.assertTrue(any(item["publish_state"] == "unprocessed" for item in compilation_payload["items"]))

            inbox = self._run("scripts/workspace_cli.py", "inbox", temp_dir)
            self.assertEqual(inbox.returncode, 0, inbox.stderr)
            inbox_payload = json.loads(inbox.stdout)
            self.assertEqual(inbox_payload["candidate_counts"]["total"], 2)
            routed_items = {
                item["document_id"]: item
                for item in inbox_payload["items"]
                if item["routed"]
            }
            self.assertEqual(routed_items["CONF-201"]["topic"], "nvme-reliability")
            self.assertEqual(routed_items["SSD-101"]["publish_state"], "unprocessed")
            self.assertTrue(routed_items["SSD-101"]["promote"])

    def test_workspace_cli_compile_wiki_summarizes_routed_confluence_items(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/full_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-101"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            confluence_spec = Path(temp_dir, "raw", "confluence", "specs", "fixture-confluence.json")
            confluence_spec.write_text(
                json.dumps(
                    {
                        "kind": "confluence",
                        "mode": "fixture",
                        "path": "fixtures/connectors/confluence/page_sync.json",
                        "scope": {"type": "page", "page_id": "CONF-001"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec)).returncode, 0)
            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(confluence_spec)).returncode, 0)
            build = self._run("scripts/workspace_cli.py", "build", temp_dir)
            self.assertEqual(build.returncode, 0, build.stderr)

            route_manifest = Path(temp_dir, "route-manifest.json")
            route_manifest.write_text(
                json.dumps(
                    {
                        "topics": [
                            {
                                "slug": "nvme-reliability",
                                "title": "NVMe Reliability",
                                "description": "Reliability learnings and issue-driven guidance.",
                            }
                        ],
                        "confluence": [
                            {
                                "document_id": "CONF-201",
                                "topic": "nvme-reliability",
                                "mode": "summarize",
                            }
                        ],
                        "jira": [
                            {
                                "document_id": "SSD-101",
                                "topic": "nvme-reliability",
                                "mode": "analyze",
                                "promote": True,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            route = self._run("scripts/workspace_cli.py", "route", temp_dir, "--manifest", str(route_manifest))
            self.assertEqual(route.returncode, 0, route.stderr)

            compile_result = self._run(
                "scripts/workspace_cli.py",
                "compile-wiki",
                temp_dir,
                "--llm-backend",
                "mock",
                "--llm-mock-response",
                "Mock compiled summary",
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            compile_payload = json.loads(compile_result.stdout)
            self.assertEqual(compile_payload["summary_count"], 1)
            self.assertEqual(compile_payload["processed_counts"]["confluence"], 1)
            self.assertEqual(compile_payload["processed_counts"]["jira"], 1)
            self.assertEqual(compile_payload["topic_page_count"], 1)

            summary_path = Path(temp_dir, "wiki", "summaries", "confluence", "CONF-201.md")
            self.assertTrue(summary_path.exists())
            summary_markdown = summary_path.read_text(encoding="utf-8")
            self.assertIn("# Telemetry Architecture", summary_markdown)
            self.assertIn("NVMe Reliability", summary_markdown)
            self.assertIn("Mock compiled summary", summary_markdown)
            self.assertIn("fixtures/connectors/confluence/page_sync.json", summary_markdown)
            self.assertIn("page-hero", summary_markdown)
            self.assertIn("breadcrumb-bar", summary_markdown)
            self.assertIn("page-layout", summary_markdown)
            self.assertIn("page-aside", summary_markdown)
            self.assertIn("status-pill", summary_markdown)
            self.assertIn("updated-timestamp", summary_markdown)
            self.assertIn("source-type-badge", summary_markdown)
            self.assertIn("evidence-card", summary_markdown)
            self.assertIn("## Narrative Summary", summary_markdown)
            self.assertIn("Back to Topic Hub", summary_markdown)
            self.assertIn("## Source Trace", summary_markdown)

            topic_path = Path(temp_dir, "wiki", "compiled", "topics", "nvme-reliability.md")
            self.assertTrue(topic_path.exists())
            topic_markdown = topic_path.read_text(encoding="utf-8")
            self.assertIn("# NVMe Reliability", topic_markdown)
            self.assertIn("Telemetry Architecture", topic_markdown)
            self.assertIn("Mock compiled summary", topic_markdown)
            self.assertIn("breadcrumb-bar", topic_markdown)
            self.assertIn("page-layout", topic_markdown)
            self.assertIn("page-aside", topic_markdown)
            self.assertIn("hero-metrics", topic_markdown)
            self.assertIn("status-pill", topic_markdown)
            self.assertIn("updated-timestamp", topic_markdown)
            self.assertIn("source-type-badge", topic_markdown)
            self.assertIn("evidence-card", topic_markdown)
            self.assertIn("## Evidence Trail", topic_markdown)
            self.assertIn("Open Questions", topic_markdown)
            self.assertIn("Review freshness and conflict indicators during the next compile cycle.", topic_markdown)
            self.assertIn("surface-card", topic_markdown)

            compilation_payload = json.loads(Path(temp_dir, "wiki", "compilation-manifest.json").read_text(encoding="utf-8"))
            manifest_items = {item["document_id"]: item for item in compilation_payload["items"]}
            self.assertEqual(manifest_items["CONF-201"]["publish_state"], "summarized")
            self.assertTrue(manifest_items["CONF-201"]["output_path"].endswith("wiki\\summaries\\confluence\\CONF-201.md") or manifest_items["CONF-201"]["output_path"].endswith("wiki/summaries/confluence/CONF-201.md"))
            self.assertTrue(manifest_items["CONF-201"]["topic_published"])
            self.assertEqual(manifest_items["SSD-101"]["publish_state"], "promoted")
            self.assertTrue(manifest_items["SSD-101"]["topic_published"])

            inbox = self._run("scripts/workspace_cli.py", "inbox", temp_dir)
            self.assertEqual(inbox.returncode, 0, inbox.stderr)
            inbox_payload = json.loads(inbox.stdout)
            by_id = {item["document_id"]: item for item in inbox_payload["items"]}
            self.assertEqual(by_id["CONF-201"]["publish_state"], "summarized")
            self.assertEqual(by_id["SSD-101"]["publish_state"], "promoted")

    def test_workspace_cli_compile_wiki_promotes_only_after_analysis_when_jira_route_requests_promotion(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/full_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-101"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            confluence_spec = Path(temp_dir, "raw", "confluence", "specs", "fixture-confluence.json")
            confluence_spec.write_text(
                json.dumps(
                    {
                        "kind": "confluence",
                        "mode": "fixture",
                        "path": "fixtures/connectors/confluence/page_sync.json",
                        "scope": {"type": "page", "page_id": "CONF-001"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec)).returncode, 0)
            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(confluence_spec)).returncode, 0)
            build = self._run("scripts/workspace_cli.py", "build", temp_dir)
            self.assertEqual(build.returncode, 0, build.stderr)

            route_manifest = Path(temp_dir, "route-manifest.json")
            route_manifest.write_text(
                json.dumps(
                    {
                        "topics": [
                            {
                                "slug": "nvme-reliability",
                                "title": "NVMe Reliability",
                                "description": "Reliability learnings and issue-driven guidance.",
                            }
                        ],
                        "confluence": [],
                        "jira": [
                            {
                                "document_id": "SSD-101",
                                "topic": "nvme-reliability",
                                "mode": "analyze",
                                "promote": True,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            route = self._run("scripts/workspace_cli.py", "route", temp_dir, "--manifest", str(route_manifest))
            self.assertEqual(route.returncode, 0, route.stderr)

            compile_result = self._run(
                "scripts/workspace_cli.py",
                "compile-wiki",
                temp_dir,
                "--llm-backend",
                "mock",
                "--llm-mock-response",
                "Mock Jira analysis",
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            compile_payload = json.loads(compile_result.stdout)
            self.assertEqual(compile_payload["analysis_count"], 1)
            self.assertEqual(compile_payload["processed_counts"]["jira"], 1)
            self.assertEqual(compile_payload["topic_page_count"], 1)

            analysis_path = Path(temp_dir, "wiki", "compiled", "analyses", "jira", "SSD-101.md")
            self.assertTrue(analysis_path.exists())
            analysis_markdown = analysis_path.read_text(encoding="utf-8")
            self.assertIn("# [SV][FwVersion880] xx平台进入S4后黑屏", analysis_markdown)
            self.assertIn("NVMe Reliability", analysis_markdown)
            self.assertIn("Mock Jira analysis", analysis_markdown)
            self.assertIn("defect", analysis_markdown)
            self.assertIn("fw_bug_rca", analysis_markdown)
            self.assertIn("page-hero", analysis_markdown)
            self.assertIn("breadcrumb-bar", analysis_markdown)
            self.assertIn("page-layout", analysis_markdown)
            self.assertIn("page-aside", analysis_markdown)
            self.assertIn("status-pill", analysis_markdown)
            self.assertIn("updated-timestamp", analysis_markdown)
            self.assertIn("source-type-badge", analysis_markdown)
            self.assertIn("evidence-card", analysis_markdown)
            self.assertIn("## Analysis Narrative", analysis_markdown)
            self.assertIn("Back to Topic Hub", analysis_markdown)
            self.assertIn("Related Links", analysis_markdown)

            compilation_payload = json.loads(Path(temp_dir, "wiki", "compilation-manifest.json").read_text(encoding="utf-8"))
            manifest_items = {item["document_id"]: item for item in compilation_payload["items"]}
            self.assertEqual(manifest_items["SSD-101"]["publish_state"], "promoted")
            self.assertTrue(manifest_items["SSD-101"]["promote"])
            self.assertTrue(manifest_items["SSD-101"].get("topic_published", False))
            self.assertTrue(manifest_items["SSD-101"]["output_path"].endswith("wiki\\compiled\\analyses\\jira\\SSD-101.md") or manifest_items["SSD-101"]["output_path"].endswith("wiki/compiled/analyses/jira/SSD-101.md"))

            topic_path = Path(temp_dir, "wiki", "compiled", "topics", "nvme-reliability.md")
            self.assertTrue(topic_path.exists())
            topic_markdown = topic_path.read_text(encoding="utf-8")
            self.assertIn("# NVMe Reliability", topic_markdown)
            self.assertIn("Mock Jira analysis", topic_markdown)
            self.assertIn("SSD-101", topic_markdown)

            inbox = self._run("scripts/workspace_cli.py", "inbox", temp_dir)
            self.assertEqual(inbox.returncode, 0, inbox.stderr)
            inbox_payload = json.loads(inbox.stdout)
            by_id = {item["document_id"]: item for item in inbox_payload["items"]}
            self.assertEqual(by_id["SSD-101"]["publish_state"], "promoted")
            self.assertTrue(by_id["SSD-101"]["promote"])

    def test_workspace_cli_build_site_generates_vitepress_ready_output(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/full_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-101"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            confluence_spec = Path(temp_dir, "raw", "confluence", "specs", "fixture-confluence.json")
            confluence_spec.write_text(
                json.dumps(
                    {
                        "kind": "confluence",
                        "mode": "fixture",
                        "path": "fixtures/connectors/confluence/page_sync.json",
                        "scope": {"type": "page", "page_id": "CONF-001"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec)).returncode, 0)
            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(confluence_spec)).returncode, 0)
            self.assertEqual(self._run("scripts/workspace_cli.py", "build", temp_dir).returncode, 0)

            route_manifest = Path(temp_dir, "route-manifest.json")
            route_manifest.write_text(
                json.dumps(
                    {
                        "topics": [
                            {
                                "slug": "nvme-reliability",
                                "title": "NVMe Reliability",
                                "description": "Reliability learnings and issue-driven guidance.",
                            }
                        ],
                        "confluence": [
                            {
                                "document_id": "CONF-201",
                                "topic": "nvme-reliability",
                                "mode": "summarize",
                            }
                        ],
                        "jira": [
                            {
                                "document_id": "SSD-101",
                                "topic": "nvme-reliability",
                                "mode": "analyze",
                                "promote": True,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.assertEqual(self._run("scripts/workspace_cli.py", "route", temp_dir, "--manifest", str(route_manifest)).returncode, 0)
            self.assertEqual(
                self._run(
                    "scripts/workspace_cli.py",
                    "compile-wiki",
                    temp_dir,
                    "--llm-backend",
                    "mock",
                    "--llm-mock-response",
                    "Mock compiled wiki content",
                ).returncode,
                0,
            )

            build_site = self._run("scripts/workspace_cli.py", "build-site", temp_dir, "--renderer", "vitepress")
            self.assertEqual(build_site.returncode, 0, build_site.stderr)
            build_payload = json.loads(build_site.stdout)
            self.assertEqual(build_payload["renderer"], "vitepress")

            site_root = Path(temp_dir, "wiki", "vitepress_site")
            self.assertTrue((site_root / "docs" / "index.md").exists())
            self.assertTrue((site_root / "docs" / "topics" / "nvme-reliability.md").exists())
            self.assertTrue((site_root / "docs" / "topics" / "index.md").exists())
            self.assertTrue((site_root / "docs" / "summaries" / "confluence" / "index.md").exists())
            self.assertTrue((site_root / "docs" / "analyses" / "jira" / "index.md").exists())
            self.assertTrue((site_root / "docs" / "summaries" / "confluence" / "CONF-201.md").exists())
            self.assertTrue((site_root / "docs" / "analyses" / "jira" / "SSD-101.md").exists())
            self.assertTrue((site_root / ".vitepress" / "config.mts").exists())
            self.assertTrue((site_root / ".vitepress" / "theme" / "index.ts").exists())
            self.assertTrue((site_root / ".vitepress" / "theme" / "custom.css").exists())
            self.assertTrue((site_root / "package.json").exists())
            self.assertTrue((site_root / "README.md").exists())

            index_markdown = (site_root / "docs" / "index.md").read_text(encoding="utf-8")
            vitepress_config = (site_root / ".vitepress" / "config.mts").read_text(encoding="utf-8")
            custom_css = (site_root / ".vitepress" / "theme" / "custom.css").read_text(encoding="utf-8")
            package_json = json.loads((site_root / "package.json").read_text(encoding="utf-8"))
            readme = (site_root / "README.md").read_text(encoding="utf-8")

            self.assertIn("NVMe Reliability", index_markdown)
            self.assertIn("hero-panel", index_markdown)
            self.assertIn("metric-grid", index_markdown)
            self.assertIn("/topics/nvme-reliability", vitepress_config)
            self.assertIn("/summaries/confluence/CONF-201", vitepress_config)
            self.assertIn("/analyses/jira/SSD-101", vitepress_config)
            self.assertIn("IBM Plex Sans", custom_css)
            self.assertIn("JetBrains Mono", custom_css)
            self.assertIn("--vp-c-brand-1", custom_css)
            self.assertIn(".breadcrumb-bar", custom_css)
            self.assertIn(".page-hero", custom_css)
            self.assertIn(".page-layout", custom_css)
            self.assertIn(".page-aside", custom_css)
            self.assertIn(".meta-strip", custom_css)
            self.assertIn(".status-pill", custom_css)
            self.assertIn(".source-type-badge", custom_css)
            self.assertIn(".evidence-card", custom_css)
            self.assertEqual(package_json["name"], "ssd-topic-wiki")
            self.assertIn("vitepress", package_json["devDependencies"])
            self.assertIn("npm install", readme)
            self.assertIn("npm run docs:dev", readme)
            self.assertIn("npm run docs:build", readme)

    def test_workspace_cli_publish_wiki_runs_compile_build_and_writes_reports(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/full_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-101"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            confluence_spec = Path(temp_dir, "raw", "confluence", "specs", "fixture-confluence.json")
            confluence_spec.write_text(
                json.dumps(
                    {
                        "kind": "confluence",
                        "mode": "fixture",
                        "path": "fixtures/connectors/confluence/page_sync.json",
                        "scope": {"type": "page", "page_id": "CONF-001"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec)).returncode, 0)
            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(confluence_spec)).returncode, 0)
            self.assertEqual(self._run("scripts/workspace_cli.py", "build", temp_dir).returncode, 0)

            route_manifest = Path(temp_dir, "route-manifest.json")
            route_manifest.write_text(
                json.dumps(
                    {
                        "topics": [
                            {
                                "slug": "nvme-reliability",
                                "title": "NVMe Reliability",
                                "description": "Reliability learnings and issue-driven guidance.",
                            },
                            {
                                "slug": "idle-topic",
                                "title": "Idle Topic",
                                "description": "No routed content yet.",
                            }
                        ],
                        "confluence": [
                            {
                                "document_id": "CONF-201",
                                "topic": "nvme-reliability",
                                "mode": "summarize",
                            }
                        ],
                        "jira": [
                            {
                                "document_id": "SSD-101",
                                "topic": "nvme-reliability",
                                "mode": "analyze",
                                "promote": False,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            publish = self._run(
                "scripts/workspace_cli.py",
                "publish-wiki",
                temp_dir,
                "--manifest",
                str(route_manifest),
                "--renderer",
                "vitepress",
                "--llm-backend",
                "mock",
                "--llm-mock-response",
                "Mock publish content",
            )
            self.assertEqual(publish.returncode, 0, publish.stderr)
            payload = json.loads(publish.stdout)
            self.assertEqual(payload["renderer"], "vitepress")
            self.assertEqual(payload["compile"]["summary_count"], 1)
            self.assertEqual(payload["compile"]["analysis_count"], 1)

            report_path = Path(temp_dir, "wiki", "reports", "compilation-report.json")
            self.assertTrue(report_path.exists())
            report_payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report_payload["counts"]["topics_total"], 2)
            self.assertEqual(report_payload["counts"]["topics_built"], 1)
            self.assertIn("idle-topic", report_payload["empty_topics"])
            self.assertIn("SSD-101", report_payload["unpromoted_jira_document_ids"])

            topic_path = Path(temp_dir, "wiki", "compiled", "topics", "nvme-reliability.md")
            topic_markdown = topic_path.read_text(encoding="utf-8")
            self.assertIn("Telemetry Architecture", topic_markdown)
            self.assertNotIn("SSD-101", topic_markdown)
            self.assertIn("No promoted Jira analysis is published into this topic yet.", topic_markdown)
            self.assertIn("A routed Jira analysis exists but is not promoted yet.", topic_markdown)

    def test_workspace_cli_publish_wiki_can_verify_site_build_with_custom_command(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_result = self._run("scripts/workspace_cli.py", "init", temp_dir)
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            jira_spec = Path(temp_dir, "raw", "jira", "specs", "fixture-jira.json")
            jira_spec.write_text(
                json.dumps(
                    {
                        "kind": "jira",
                        "mode": "fixture",
                        "path": "fixtures/connectors/jira/full_sync.json",
                        "scope": {"type": "issue", "issue_key": "SSD-101"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            confluence_spec = Path(temp_dir, "raw", "confluence", "specs", "fixture-confluence.json")
            confluence_spec.write_text(
                json.dumps(
                    {
                        "kind": "confluence",
                        "mode": "fixture",
                        "path": "fixtures/connectors/confluence/page_sync.json",
                        "scope": {"type": "page", "page_id": "CONF-001"},
                        "fetch": {"fetch_backend": "atlassian-api"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(jira_spec)).returncode, 0)
            self.assertEqual(self._run("scripts/workspace_cli.py", "fetch", temp_dir, str(confluence_spec)).returncode, 0)
            self.assertEqual(self._run("scripts/workspace_cli.py", "build", temp_dir).returncode, 0)

            route_manifest = Path(temp_dir, "route-manifest.json")
            route_manifest.write_text(
                json.dumps(
                    {
                        "topics": [
                            {
                                "slug": "nvme-reliability",
                                "title": "NVMe Reliability",
                                "description": "Reliability learnings and issue-driven guidance.",
                            }
                        ],
                        "confluence": [
                            {
                                "document_id": "CONF-201",
                                "topic": "nvme-reliability",
                                "mode": "summarize",
                            }
                        ],
                        "jira": [
                            {
                                "document_id": "SSD-101",
                                "topic": "nvme-reliability",
                                "mode": "analyze",
                                "promote": True,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            publish = self._run(
                "scripts/workspace_cli.py",
                "publish-wiki",
                temp_dir,
                "--manifest",
                str(route_manifest),
                "--renderer",
                "vitepress",
                "--verify-site-build",
                f"--site-build-command={sys.executable}",
                "--site-build-command=-c",
                "--site-build-command=print('verify ok')",
                "--llm-backend",
                "mock",
                "--llm-mock-response",
                "Mock publish content",
            )
            self.assertEqual(publish.returncode, 0, publish.stderr)
            payload = json.loads(publish.stdout)
            self.assertIn("site_verification", payload)
            self.assertTrue(payload["site_verification"]["ok"])
            self.assertEqual(payload["site_verification"]["command"], [sys.executable, "-c", "print('verify ok')"])
            self.assertIn("verify ok", payload["site_verification"]["stdout"])

            verify_report = Path(temp_dir, "wiki", "reports", "vitepress-build-report.json")
            self.assertTrue(verify_report.exists())

    def test_workspace_cli_deep_analyze_reads_workspace_snapshot(self) -> None:
        with TemporaryDirectory() as temp_dir:
            self._prepare_workspace_snapshot(temp_dir)
            output_answer_md = Path(temp_dir) / "deep-analysis-answer.md"

            result = self._run(
                "scripts/workspace_cli.py",
                "deep-analyze",
                temp_dir,
                "SSD-102",
                "--policies",
                "team:ssd",
                "--output-answer-md",
                str(output_answer_md),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["issue_id"], "SSD-102")
            self.assertIn("analysis_profile", payload)
            self.assertIn("run_dir", payload)
            self.assertIn("run_manifest_path", payload)
            self.assertEqual(payload["output_answer_md"], str(output_answer_md))
            self.assertEqual(output_answer_md.read_text(encoding="utf-8"), payload["answer"]["text"])
            self.assertTrue((Path(payload["run_dir"]) / "result.json").exists())
            self.assertTrue((Path(payload["run_dir"]) / "shared_retrieval_bundle.json").exists())
            self.assertTrue((Path(payload["run_dir"]) / "section_outputs" / "rca.json").exists())
            self.assertTrue((Path(payload["run_dir"]) / "section_outputs" / "spec_impact.json").exists())
            self.assertTrue((Path(payload["run_dir"]) / "report" / "report.md").exists())
            self.assertTrue((Path(payload["run_dir"]) / "knowledge" / "confluence_update_proposal.json").exists())
            self.assertTrue((Path(payload["run_dir"]) / "knowledge" / "concept_cards.json").exists())
            self.assertTrue((Path(payload["run_dir"]) / "knowledge" / "wiki_draft.md").exists())
            manifest = json.loads(Path(payload["run_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["task_type"], "jira_deep_analysis")
            self.assertEqual(manifest["owner"], "workspace-operator")
            self.assertIn("snapshot_files", manifest["input_config"])
            self.assertIn("documents", manifest["input_config"]["snapshot_files"])
            self.assertIn("page_index", manifest["input_config"]["snapshot_files"])
            self.assertTrue(manifest["checkpoints"]["retrieval_ready"]["reached"])
            self.assertTrue(manifest["checkpoints"]["analysis_ready"]["reached"])
            self.assertTrue(manifest["checkpoints"]["knowledge_ready"]["reached"])
            artifact_types = {artifact["artifact_type"] for artifact in manifest["artifacts"]}
            self.assertIn("shared_retrieval_bundle", artifact_types)
            self.assertIn("section_output_rca", artifact_types)
            self.assertIn("composite_report", artifact_types)
            self.assertIn("confluence_update_proposal", artifact_types)
            self.assertIn("concept_cards", artifact_types)
            self.assertIn("wiki_draft", artifact_types)
            artifacts_by_type = {artifact["artifact_type"]: artifact for artifact in manifest["artifacts"]}
            self.assertIn("shared_retrieval_bundle", artifacts_by_type["confluence_update_proposal"]["depends_on"])
            self.assertIn("shared_retrieval_bundle", artifacts_by_type["concept_cards"]["depends_on"])
            rca_payload = json.loads((Path(payload["run_dir"]) / "section_outputs" / "rca.json").read_text(encoding="utf-8"))
            self.assertEqual(rca_payload["followup_retrieval"]["base_bundle"], "shared_retrieval_bundle")
            report_markdown = (Path(payload["run_dir"]) / "report" / "report.md").read_text(encoding="utf-8")
            self.assertIn("### Evidence", report_markdown)
            self.assertIn("section_outputs/rca.json", report_markdown)
            proposal = json.loads((Path(payload["run_dir"]) / "knowledge" / "confluence_update_proposal.json").read_text(encoding="utf-8"))
            self.assertEqual(proposal["status"], "draft")

    def test_workspace_run_dir_uses_subsecond_uniqueness(self) -> None:
        with TemporaryDirectory() as temp_dir:
            paths = workspace_paths(temp_dir)
            first = _run_dir(paths, source_name="workspace", command="deep-analyze")
            second = _run_dir(paths, source_name="workspace", command="deep-analyze")
            self.assertNotEqual(first.name, second.name)

    def test_workspace_cli_deep_analyze_rejects_non_jira_ids(self) -> None:
        with TemporaryDirectory() as temp_dir:
            self._prepare_workspace_snapshot(temp_dir)

            result = self._run(
                "scripts/workspace_cli.py",
                "deep-analyze",
                temp_dir,
                "CONF-201",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Document is not a Jira issue: CONF-201", result.stderr)

    def test_workspace_cli_control_run_supports_stop_resume_and_rerun(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_workspace(temp_dir)
            run_dir = workspace_paths(temp_dir)["runs"] / "run-control"
            manifest = build_run_manifest(
                task_type="jira_deep_analysis",
                owner="alice",
                input_config={"issue_key": "SSD-102"},
                run_id="run-control",
                status="running",
            )
            manifest = update_checkpoint(
                manifest,
                "retrieval_ready",
                reached=True,
                artifact_types=["shared_retrieval_bundle"],
            )
            write_run_manifest(run_dir, manifest)

            stop = self._run(
                "scripts/workspace_cli.py",
                "control-run",
                temp_dir,
                "run-control",
                "--action",
                "stop",
                "--step-name",
                "analysis",
                "--requested-by",
                "alice",
            )
            self.assertEqual(stop.returncode, 0, stop.stderr)
            stop_payload = json.loads(stop.stdout)
            self.assertEqual(stop_payload["status"], "stopping")
            self.assertEqual(stop_payload["control_event"]["action"], "stop")

            resume = self._run(
                "scripts/workspace_cli.py",
                "control-run",
                temp_dir,
                "run-control",
                "--action",
                "resume",
                "--requested-by",
                "alice",
            )
            self.assertEqual(resume.returncode, 0, resume.stderr)
            resume_payload = json.loads(resume.stdout)
            self.assertEqual(resume_payload["status"], "queued")
            self.assertEqual(resume_payload["control_event"]["result"]["resume_from_step"], "analysis")

            rerun = self._run(
                "scripts/workspace_cli.py",
                "control-run",
                temp_dir,
                "run-control",
                "--action",
                "rerun",
                "--requested-by",
                "alice",
                "--reason",
                "prompt update",
            )
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            rerun_payload = json.loads(rerun.stdout)
            self.assertEqual(rerun_payload["run_version"], 2)
            self.assertTrue(rerun_payload["run_id"].startswith("run-control-rerun-v2-"))
            self.assertEqual(rerun_payload["control_event"]["action"], "rerun")
            self.assertTrue((Path(rerun_payload["run_dir"]) / "run_manifest.json").exists())

    def test_workspace_cli_control_run_supports_section_rerun_invalidation(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_workspace(temp_dir)
            run_dir = workspace_paths(temp_dir)["runs"] / "run-section"
            section_artifacts = [
                build_artifact_record(
                    artifact_type=f"section_output_{section_name}",
                    path=f"runs/run-section/section_outputs/{section_name}.json",
                    step_name=f"section_runner_{section_name}",
                    step_version="v1",
                    input_hash="snapshot-hash",
                    depends_on=["shared_retrieval_bundle"],
                )
                for section_name in ("rca", "spec_impact", "decision_brief", "general_summary")
            ]
            manifest = build_run_manifest(
                task_type="jira_deep_analysis",
                owner="alice",
                input_config={"issue_key": "SSD-102"},
                run_id="run-section",
                status="completed",
                artifacts=[
                    build_artifact_record(
                        artifact_type="shared_retrieval_bundle",
                        path="runs/run-section/shared_retrieval_bundle.json",
                        step_name="shared_retrieval",
                        step_version="v1",
                        input_hash="snapshot-hash",
                    ),
                    *section_artifacts,
                    build_artifact_record(
                        artifact_type="composite_report",
                        path="runs/run-section/report/report.md",
                        step_name="composite_report_builder",
                        step_version="v1",
                        input_hash="snapshot-hash",
                        depends_on=[artifact["artifact_type"] for artifact in section_artifacts],
                    ),
                ],
            )
            write_run_manifest(run_dir, manifest)

            result = self._run(
                "scripts/workspace_cli.py",
                "control-run",
                temp_dir,
                "run-section",
                "--action",
                "rerun-section",
                "--step-name",
                "rca",
                "--requested-by",
                "alice",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "queued")
            self.assertEqual(payload["control_event"]["action"], "rerun_section")
            self.assertIn("section_output_rca", payload["control_event"]["result"]["stale_artifact_types"])
            self.assertIn("composite_report", payload["control_event"]["result"]["stale_artifact_types"])

    def test_workspace_cli_control_run_can_execute_section_rerun(self) -> None:
        with TemporaryDirectory() as temp_dir:
            self._prepare_workspace_snapshot(temp_dir)
            deep = self._run("scripts/workspace_cli.py", "deep-analyze", temp_dir, "SSD-102", "--policies", "team:ssd")
            self.assertEqual(deep.returncode, 0, deep.stderr)
            deep_payload = json.loads(deep.stdout)
            run_dir = Path(deep_payload["run_dir"])
            rca_path = run_dir / "section_outputs" / "rca.json"
            report_path = run_dir / "report" / "report.md"
            rca_path.write_text(json.dumps({"sentinel": True}), encoding="utf-8")
            report_path.write_text("SENTINEL", encoding="utf-8")

            result = self._run(
                "scripts/workspace_cli.py",
                "control-run",
                temp_dir,
                run_dir.name,
                "--action",
                "rerun-section",
                "--step-name",
                "rca",
                "--execute",
                "--requested-by",
                "alice",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "completed")
            self.assertTrue(payload["control_event"]["result"]["executed"])
            self.assertEqual(json.loads(rca_path.read_text(encoding="utf-8"))["section_name"], "rca")
            self.assertIn("## RCA", report_path.read_text(encoding="utf-8"))
            manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
            artifacts_by_type = {artifact["artifact_type"]: artifact for artifact in manifest["artifacts"]}
            self.assertFalse(artifacts_by_type["section_output_rca"]["stale"])
            self.assertFalse(artifacts_by_type["composite_report"]["stale"])
            self.assertFalse(artifacts_by_type["confluence_update_proposal"]["stale"])

    def test_workspace_cli_sync_prefect_state_updates_manifest_runtime(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_workspace(temp_dir)
            run_dir = workspace_paths(temp_dir)["runs"] / "run-prefect"
            manifest = build_run_manifest(
                task_type="jira_deep_analysis",
                owner="alice",
                input_config={"issue_key": "SSD-102"},
                run_id="run-prefect",
                status="queued",
            )
            write_run_manifest(run_dir, manifest)

            result = self._run(
                "scripts/workspace_cli.py",
                "sync-prefect-state",
                temp_dir,
                "run-prefect",
                "--prefect-state",
                "Completed",
                "--flow-run-id",
                "flow-run-789",
                "--deployment-name",
                "jira-analysis",
                "--requested-by",
                "alice",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["control_event"]["action"], "sync_adapter_state")
            updated_manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(updated_manifest["runtime"]["prefect"]["flow_run_id"], "flow-run-789")
            self.assertEqual(updated_manifest["runtime"]["prefect"]["adapter_state"], "succeeded")
            event_lines = Path(payload["control_event_log"]).read_text(encoding="utf-8").splitlines()
            self.assertEqual(json.loads(event_lines[0])["action"], "sync_adapter_state")

    def test_workspace_cli_submit_prefect_run_reports_missing_runtime_cleanly(self) -> None:
        with TemporaryDirectory() as temp_dir:
            init_workspace(temp_dir)
            run_dir = workspace_paths(temp_dir)["runs"] / "run-prefect-submit"
            manifest = build_run_manifest(
                task_type="jira_deep_analysis",
                owner="alice",
                input_config={"issue_key": "SSD-102"},
                run_id="run-prefect-submit",
                status="queued",
            )
            write_run_manifest(run_dir, manifest)

            result = self._run(
                "scripts/workspace_cli.py",
                "submit-prefect-run",
                temp_dir,
                "run-prefect-submit",
                "--deployment-name",
                "analysis-prod",
            )

            if result.returncode == 0:
                payload = json.loads(result.stdout)
                self.assertEqual(payload["control_event"]["action"], "sync_adapter_state")
            else:
                self.assertIn("Prefect is not installed", result.stderr)

    def test_workspace_cli_can_query_run_detail_and_artifacts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            self._prepare_workspace_snapshot(temp_dir)
            deep = self._run("scripts/workspace_cli.py", "deep-analyze", temp_dir, "SSD-102", "--policies", "team:ssd")
            self.assertEqual(deep.returncode, 0, deep.stderr)
            deep_payload = json.loads(deep.stdout)
            run_name = Path(deep_payload["run_dir"]).name

            runs = self._run("scripts/workspace_cli.py", "runs", temp_dir)
            self.assertEqual(runs.returncode, 0, runs.stderr)
            runs_payload = json.loads(runs.stdout)
            self.assertGreaterEqual(runs_payload["run_count"], 1)
            self.assertEqual(runs_payload["runs"][0]["run_id"], run_name)
            self.assertEqual(runs_payload["runs"][0]["issue_key"], "SSD-102")

            detail = self._run("scripts/workspace_cli.py", "run-detail", temp_dir, run_name)
            self.assertEqual(detail.returncode, 0, detail.stderr)
            detail_payload = json.loads(detail.stdout)
            self.assertEqual(detail_payload["run"]["run_id"], run_name)
            self.assertEqual(detail_payload["result_summary"]["issue_id"], "SSD-102")
            self.assertIn("section_output_rca", {row["artifact_type"] for row in detail_payload["artifact_inventory"]})

            section = self._run("scripts/workspace_cli.py", "run-artifact", temp_dir, run_name, "section_output_rca")
            self.assertEqual(section.returncode, 0, section.stderr)
            section_payload = json.loads(section.stdout)
            self.assertEqual(section_payload["format"], "json")
            self.assertEqual(section_payload["payload"]["section_name"], "rca")

            report = self._run("scripts/workspace_cli.py", "run-artifact", temp_dir, run_name, "composite_report")
            self.assertEqual(report.returncode, 0, report.stderr)
            report_payload = json.loads(report.stdout)
            self.assertEqual(report_payload["format"], "text")
            self.assertIn("## RCA", report_payload["content"])

    def test_workspace_cli_can_write_portal_state_from_workspace_runs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            self._prepare_workspace_snapshot(temp_dir)
            deep = self._run("scripts/workspace_cli.py", "deep-analyze", temp_dir, "SSD-102", "--policies", "team:ssd")
            self.assertEqual(deep.returncode, 0, deep.stderr)
            run_name = Path(json.loads(deep.stdout)["run_dir"]).name
            output_path = Path(temp_dir) / "portal_state.json"

            result = self._run(
                "scripts/workspace_cli.py",
                "portal-state",
                temp_dir,
                "--output",
                str(output_path),
                "--query",
                "nvme flush",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["portal_state_path"], str(output_path))
            self.assertEqual(payload["selected_task_id"], run_name)
            state = json.loads(output_path.read_text(encoding="utf-8"))
            selected = next(task for task in state["task_workbench"]["tasks"] if task["selected"])
            self.assertEqual(selected["task_id"], run_name)
            self.assertEqual(selected["issue_key"], "SSD-102")

    def test_workspace_cli_smoke_deep_analysis_runs_jira_confluence_and_pdf_flow(self) -> None:
        with TemporaryDirectory() as temp_dir:
            portal_state_path = Path(temp_dir) / "portal_state.json"

            result = self._run(
                "scripts/workspace_cli.py",
                "smoke-deep-analysis",
                temp_dir,
                "--jira-spec",
                "project-slice",
                "--confluence-spec",
                "page-tree",
                "--issue-key",
                "SSD-102",
                "--spec-pdf",
                "fixtures/corpus/pdf/sample.pdf",
                "--spec-asset-id",
                "nvme-smoke",
                "--preferred-parser",
                "pypdf",
                "--policies",
                "team:ssd",
                "--portal-state-output",
                str(portal_state_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["fetches"]["jira"]["document_count"], 1)
            self.assertGreaterEqual(payload["fetches"]["confluence"]["document_count"], 1)
            self.assertEqual(payload["spec_asset"]["asset_id"], "nvme-smoke")
            self.assertEqual(payload["deep_analysis"]["issue_id"], "SSD-102")
            self.assertTrue(Path(payload["deep_analysis"]["run_dir"]).exists())
            self.assertTrue(portal_state_path.exists())
            portal_state = json.loads(portal_state_path.read_text(encoding="utf-8"))
            self.assertEqual(portal_state["task_workbench"]["tasks"][0]["issue_key"], "SSD-102")


if __name__ == "__main__":
    unittest.main()

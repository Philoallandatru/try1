import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


class WorkspaceCliTest(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            capture_output=True,
            text=True,
            check=False,
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


if __name__ == "__main__":
    unittest.main()

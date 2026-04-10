import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from services.retrieval.search.hybrid_search import search_page_index


class PlatformCliTest(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/platform_cli.py", *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def _assert_source_contracts_persisted(self, snapshot_dir: str) -> None:
        snapshot_documents = json.loads((Path(snapshot_dir) / "documents.json").read_text(encoding="utf-8"))["documents"]
        snapshot_by_source = {document["source_type"]: document for document in snapshot_documents}
        self.assertEqual(snapshot_by_source["jira"]["metadata"]["issue_fields"]["Priority"], "Medium")
        self.assertIn("NAND write", snapshot_by_source["jira"]["metadata"]["issue_fields"]["Root Cause"])
        self.assertIn("TLC write", snapshot_by_source["jira"]["metadata"]["issue_fields"]["Root Cause"])
        self.assertIn("## Root Cause", snapshot_by_source["jira"]["markdown"])
        self.assertEqual(snapshot_by_source["confluence"]["metadata"]["space"], "SSDREQ")
        self.assertIn("## Changes", snapshot_by_source["confluence"]["markdown"])
        self.assertIn("[latency-budget.xlsx](/download/attachments/202/latency-budget.xlsx)", snapshot_by_source["confluence"]["markdown"])
        page_index = json.loads((Path(snapshot_dir) / "page_index.json").read_text(encoding="utf-8"))["entries"]
        jira_results = search_page_index(page_index, "NAND TLC write", {"team:ssd"})
        confluence_results = search_page_index(page_index, "queue wait", {"team:ssd"})
        self.assertTrue(any(result["document_id"] == "SSD-102" for result in jira_results))
        self.assertTrue(any(result["document_id"] == "CONF-202" for result in confluence_results))

    def test_cli_eval_outputs_metrics(self) -> None:
        result = self._run("eval")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("aggregate", payload)
        self.assertIn("recall@10", payload["aggregate"])

    def test_cli_connector_can_write_utf8_json_output(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_json = Path(temp_dir) / "jira-live.json"
            result = self._run(
                "connector",
                "jira",
                "fixtures/connectors/jira/full_sync.json",
                "--output-json",
                str(output_json),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["output_json"], str(output_json))
            written = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(written["documents"][0]["document_id"], "SSD-101")

    def test_cli_citation_outputs_contract_payload(self) -> None:
        result = self._run("citation", "flush command")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["citation"]["document"], "nvme-spec-v1")
        self.assertIn("inspection", payload)

    def test_cli_search_and_citation_can_read_page_index_artifact(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_page_index = Path(temp_dir) / "page-index.json"
            index_result = subprocess.run(
                [
                    sys.executable,
                    "scripts/retrieval/toolkit_cli.py",
                    "index",
                    "--corpus",
                    "fixtures/retrieval/pageindex_corpus.json",
                    "--output-page-index",
                    str(output_page_index),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(index_result.returncode, 0, index_result.stderr)

            search_result = self._run("search", "flush command", "--page-index", str(output_page_index))
            self.assertEqual(search_result.returncode, 0, search_result.stderr)
            search_payload = json.loads(search_result.stdout)
            self.assertEqual(search_payload[0]["document_id"], "nvme-spec-v1")

            citation_result = self._run("citation", "flush command", "--page-index", str(output_page_index))
            self.assertEqual(citation_result.returncode, 0, citation_result.stderr)
            citation_payload = json.loads(citation_result.stdout)
            self.assertEqual(citation_payload["citation"]["document"], "nvme-spec-v1")

    def test_cli_search_and_citation_can_read_snapshot_page_index(self) -> None:
        with TemporaryDirectory() as temp_dir:
            snapshot_create = subprocess.run(
                [
                    sys.executable,
                    "scripts/retrieval/snapshot_cli.py",
                    "create",
                    "--snapshot-dir",
                    temp_dir,
                    "--corpus",
                    "fixtures/retrieval/pageindex_corpus.json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(snapshot_create.returncode, 0, snapshot_create.stderr)

            search_result = self._run("search", "flush command", "--snapshot-dir", temp_dir)
            self.assertEqual(search_result.returncode, 0, search_result.stderr)
            search_payload = json.loads(search_result.stdout)
            self.assertEqual(search_payload[0]["document_id"], "nvme-spec-v1")

            citation_result = self._run("citation", "flush command", "--snapshot-dir", temp_dir)
            self.assertEqual(citation_result.returncode, 0, citation_result.stderr)
            citation_payload = json.loads(citation_result.stdout)
            self.assertEqual(citation_payload["citation"]["document"], "nvme-spec-v1")

    def test_cli_jira_report_filters_by_time_and_renders_custom_prompt(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_md = Path(temp_dir) / "jira-report.md"
            result = self._run(
                "jira-report",
                "--jira-path",
                "fixtures/connectors/jira/incremental_sync.json",
                "--updated-from-iso",
                "2026-04-05T09:00:00Z",
                "--updated-to-iso",
                "2026-04-05T10:00:00Z",
                "--prompt-template",
                "REPORT {time_filter} COUNT={issue_count}\n{summaries}",
                "--output-md",
                str(output_md),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["issue_ids"], ["SSD-102"])
            self.assertEqual(payload["issue_count"], 1)
            self.assertEqual(payload["output_md"], str(output_md))
            self.assertIn("REPORT 2026-04-05T09:00:00Z..2026-04-05T10:00:00Z COUNT=1", payload["prompt"])
            self.assertIn("- Issue: SSD-102", payload["markdown"])
            written_markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("- Issue: SSD-102", written_markdown)
            self.assertIn("## Issue Fields", written_markdown)

    def test_cli_jira_report_can_use_mock_local_llm_backend(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_answer_md = Path(temp_dir) / "jira-report-answer.md"
            result = self._run(
                "jira-report",
                "--jira-path",
                "fixtures/connectors/jira/incremental_sync.json",
                "--updated-from-iso",
                "2026-04-05T09:00:00Z",
                "--updated-to-iso",
                "2026-04-05T10:00:00Z",
                "--llm-backend",
                "mock",
                "--llm-mock-response",
                "Mock Jira report summary",
                "--llm-prompt-mode",
                "strict",
                "--output-answer-md",
                str(output_answer_md),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["answer"]["mode"], "local-llm")
            self.assertEqual(payload["answer"]["backend"], "mock")
            self.assertEqual(payload["answer"]["text"], "Mock Jira report summary")
            self.assertEqual(payload["answer"]["issue_count"], 1)
            self.assertEqual(payload["output_answer_md"], str(output_answer_md))
            self.assertIn("Mode: strict Jira report summarization.", payload["prompt"])
            self.assertEqual(output_answer_md.read_text(encoding="utf-8"), "Mock Jira report summary")

    def test_cli_jira_report_filters_by_calendar_date(self) -> None:
        result = self._run(
            "jira-report",
            "--jira-path",
            "fixtures/connectors/jira/full_sync.json",
            "--updated-on-date",
            "2026-04-05",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["time_filter"], "date:2026-04-05")
        self.assertEqual(payload["issue_ids"], ["SSD-101"])

    def test_cli_jira_report_filters_by_exact_timestamp(self) -> None:
        result = self._run(
            "jira-report",
            "--jira-path",
            "fixtures/connectors/jira/incremental_sync.json",
            "--updated-at-iso",
            "2026-04-05T09:30:00Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["time_filter"], "at:2026-04-05T09:30:00Z")
        self.assertEqual(payload["issue_ids"], ["SSD-102"])

    def test_cli_jira_spec_qa_builds_retrieval_prompt_for_selected_spec(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_answer_md = Path(temp_dir) / "jira-spec-answer.md"
            result = self._run(
                "jira-spec-qa",
                "--jira-path",
                "fixtures/connectors/jira/incremental_sync.json",
                "--jira-issue-id",
                "SSD-102",
                "--spec-corpus",
                "fixtures/retrieval/pageindex_corpus.json",
                "--spec-document-id",
                "nvme-spec-v1",
                "--question",
                "Does the NAND TLC write issue relate to NVMe flush command evidence?",
                "--prompt-template",
                "CUSTOM {jira_issue_id}\nQ={question}\nE={evidence}",
                "--output-answer-md",
                str(output_answer_md),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["jira_issue_id"], "SSD-102")
            self.assertTrue(payload["retrieval"]["has_jira_evidence"])
            self.assertTrue(payload["retrieval"]["has_spec_evidence"])
            cited_documents = {citation["document"] for citation in payload["retrieval"]["citations"]}
            self.assertIn("SSD-102", cited_documents)
            self.assertIn("nvme-spec-v1", cited_documents)
            self.assertTrue(payload["ai_prompt"].startswith("CUSTOM SSD-102"))
            self.assertIn("nvme-spec-v1", payload["ai_prompt"])
            self.assertEqual(payload["answer"]["mode"], "extractive")
            self.assertEqual(payload["output_answer_md"], str(output_answer_md))
            written_answer = output_answer_md.read_text(encoding="utf-8")
            self.assertIn("Question: Does the NAND TLC write issue relate to NVMe flush command evidence?", written_answer)
            self.assertIn("SSD-102", written_answer)
            self.assertIn("nvme-spec-v1", written_answer)

    def test_cli_jira_spec_qa_can_use_mock_local_llm_backend(self) -> None:
        result = self._run(
            "jira-spec-qa",
            "--jira-path",
            "fixtures/connectors/jira/incremental_sync.json",
            "--jira-issue-id",
            "SSD-102",
            "--spec-corpus",
            "fixtures/retrieval/pageindex_corpus.json",
            "--spec-document-id",
            "nvme-spec-v1",
            "--question",
            "Does the NAND TLC write issue relate to NVMe flush command evidence?",
            "--llm-backend",
            "mock",
            "--llm-mock-response",
            "Mock local model answer",
            "--llm-prompt-mode",
            "balanced",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["answer"]["mode"], "local-llm")
        self.assertEqual(payload["answer"]["backend"], "mock")
        self.assertEqual(payload["answer"]["text"], "Mock local model answer")
        self.assertIn("Separate direct evidence from reasonable inference", payload["ai_prompt"])

    def test_cli_retrieval_consume_supports_pdf_source(self) -> None:
        result = self._run(
            "retrieval-consume",
            "--source-kind",
            "pdf",
            "--source-path",
            "fixtures/corpus/pdf/sample.pdf",
            "--question",
            "What document covers flush semantics?",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["retrieval"]["citations"][0]["document"], "sample")
        self.assertEqual(payload["answer"]["mode"], "extractive")

    def test_cli_retrieval_consume_supports_confluence_with_mock_llm(self) -> None:
        result = self._run(
            "retrieval-consume",
            "--source-kind",
            "confluence-sync",
            "--source-path",
            "fixtures/connectors/confluence/page_sync.json",
            "--question",
            "Which page mentions telemetry architecture?",
            "--llm-backend",
            "mock",
            "--llm-mock-response",
            "Mock confluence answer",
            "--llm-prompt-mode",
            "balanced",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["retrieval"]["citations"][0]["document"], "CONF-201")
        self.assertEqual(payload["answer"]["mode"], "local-llm")
        self.assertEqual(payload["answer"]["text"], "Mock confluence answer")

    def test_cli_retrieval_consume_can_write_answer_markdown(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_answer_md = Path(temp_dir) / "retrieval-consume-answer.md"
            result = self._run(
                "retrieval-consume",
                "--source-kind",
                "confluence-sync",
                "--source-path",
                "fixtures/connectors/confluence/page_sync.json",
                "--question",
                "Which page mentions telemetry architecture?",
                "--llm-backend",
                "mock",
                "--llm-mock-response",
                "Mock written answer",
                "--output-answer-md",
                str(output_answer_md),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["output_answer_md"], str(output_answer_md))
            self.assertEqual(output_answer_md.read_text(encoding="utf-8"), "Mock written answer")

    def test_cli_retrieval_consume_can_read_snapshot_documents(self) -> None:
        with TemporaryDirectory() as temp_dir:
            snapshot_create = subprocess.run(
                [
                    sys.executable,
                    "scripts/retrieval/snapshot_cli.py",
                    "create",
                    "--snapshot-dir",
                    temp_dir,
                    "--corpus",
                    "fixtures/retrieval/pageindex_corpus.json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(snapshot_create.returncode, 0, snapshot_create.stderr)

            result = self._run(
                "retrieval-consume",
                "--snapshot-dir",
                temp_dir,
                "--question",
                "What document covers flush semantics?",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["retrieval"]["citations"][0]["document"], "nvme-spec-v1")

    def test_cli_retrieval_consume_can_write_utf8_json_output(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_json = Path(temp_dir) / "consume.json"
            result = self._run(
                "retrieval-consume",
                "--source-kind",
                "confluence-sync",
                "--source-path",
                "fixtures/connectors/confluence/page_sync.json",
                "--question",
                "Which page mentions telemetry architecture?",
                "--output-json",
                str(output_json),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["output_json"], str(output_json))
            written = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(written["retrieval"]["citations"][0]["document"], "CONF-201")

    def test_cli_jira_batch_spec_report_filters_and_writes_markdown(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_md = Path(temp_dir) / "batch-report.md"
            result = self._run(
                "jira-batch-spec-report",
                "--jira-path",
                "fixtures/connectors/jira/incremental_sync.json",
                "--updated-from-iso",
                "2026-04-05T09:00:00Z",
                "--updated-to-iso",
                "2026-04-05T10:00:00Z",
                "--spec-corpus",
                "fixtures/retrieval/pageindex_corpus.json",
                "--spec-document-id",
                "nvme-spec-v1",
                "--question-template",
                "Analyze Jira {jira_issue_id} against the selected spec.",
                "--output-md",
                str(output_md),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["issue_ids"], ["SSD-102"])
            self.assertEqual(payload["issue_count"], 1)
            self.assertEqual(payload["has_spec_evidence_count"], 1)
            self.assertEqual(payload["output_md"], str(output_md))
            self.assertEqual(payload["issues"][0]["jira_issue_id"], "SSD-102")
            written_report = output_md.read_text(encoding="utf-8")
            self.assertIn("- Issue: SSD-102", written_report)
            self.assertIn("Analyze Jira SSD-102 against the selected spec.", written_report)
            self.assertIn("nvme-spec-v1", written_report)

    def test_cli_jira_batch_spec_report_can_use_mock_local_llm_backend(self) -> None:
        result = self._run(
            "jira-batch-spec-report",
            "--jira-path",
            "fixtures/connectors/jira/incremental_sync.json",
            "--updated-from-iso",
            "2026-04-05T09:00:00Z",
            "--updated-to-iso",
            "2026-04-05T10:00:00Z",
            "--spec-corpus",
            "fixtures/retrieval/pageindex_corpus.json",
            "--spec-document-id",
            "nvme-spec-v1",
            "--question-template",
            "Analyze Jira {jira_issue_id} against the selected spec.",
            "--llm-backend",
            "mock",
            "--llm-mock-response",
            "Batch mock local answer",
            "--llm-prompt-mode",
            "exploratory",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["issues"][0]["answer"]["mode"], "local-llm")
        self.assertEqual(payload["issues"][0]["answer"]["backend"], "mock")
        self.assertEqual(payload["issues"][0]["answer"]["text"], "Batch mock local answer")
        self.assertIn("Label hypotheses explicitly", payload["issues"][0]["ai_prompt"])

    def test_cli_jira_batch_spec_report_forwards_prompt_template(self) -> None:
        result = self._run(
            "jira-batch-spec-report",
            "--jira-path",
            "fixtures/connectors/jira/incremental_sync.json",
            "--updated-from-iso",
            "2026-04-05T09:00:00Z",
            "--updated-to-iso",
            "2026-04-05T10:00:00Z",
            "--spec-corpus",
            "fixtures/retrieval/pageindex_corpus.json",
            "--spec-document-id",
            "nvme-spec-v1",
            "--question-template",
            "Analyze Jira {jira_issue_id} against the selected spec.",
            "--prompt-template",
            "BATCH {jira_issue_id}\nQ={question}\nE={evidence}",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["issues"][0]["ai_prompt"].startswith("BATCH SSD-102"))

    def test_cli_live_connector_requires_base_url(self) -> None:
        result = self._run("connector", "jira", "--live")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--base-url is required when --live is set", result.stderr)

    def test_cli_live_connector_validates_positive_page_size(self) -> None:
        result = self._run("connector", "confluence", "--live", "--base-url", "https://example.invalid", "--page-size", "0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--page-size must be greater than 0", result.stderr)

    def test_cli_ops_health_can_read_snapshot_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            snapshot_create = subprocess.run(
                [
                    sys.executable,
                    "scripts/retrieval/snapshot_cli.py",
                    "create",
                    "--snapshot-dir",
                    temp_dir,
                    "--corpus",
                    "fixtures/retrieval/pageindex_corpus.json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(snapshot_create.returncode, 0, snapshot_create.stderr)

            snapshot_refresh = subprocess.run(
                [
                    sys.executable,
                    "scripts/retrieval/snapshot_cli.py",
                    "refresh",
                    "--snapshot-dir",
                    temp_dir,
                    "--sync-payload",
                    "fixtures/connectors/jira/incremental_sync.json",
                    "--source-name",
                    "jira",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(snapshot_refresh.returncode, 0, snapshot_refresh.stderr)

            result = self._run(
                "ops-health",
                "--snapshot-dir",
                temp_dir,
                "--reference-time-iso",
                "2026-04-06T09:10:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["freshness"]["sources"][0]["source_type"], "jira")
            self.assertEqual(payload["backup_restore"]["backup"]["status"], "healthy")
            self.assertEqual(payload["backup_restore"]["restore"]["status"], "validated")

    def test_cli_sync_health_runs_connector_refresh_and_ops_health(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = self._run(
                "sync-health",
                "jira",
                "fixtures/connectors/jira/incremental_sync.json",
                "--snapshot-dir",
                temp_dir,
                "--reference-time-iso",
                "2026-04-06T09:10:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["sync"]["source_name"], "jira")
            self.assertEqual(payload["sync"]["sync_type"], "incremental")
            self.assertEqual(payload["sync"]["document_count"], 1)
            self.assertEqual(payload["refresh"]["manifest"]["sources"]["jira"]["cursor"], "jira-incr-002")
            self.assertEqual(payload["ops_health"]["backup_restore"]["backup"]["status"], "healthy")
            self.assertEqual(payload["ops_health"]["backup_restore"]["restore"]["status"], "validated")
            self.assertEqual(payload["ops_health"]["freshness"]["sources"][0]["status"], "healthy")

    def test_cli_multi_sync_health_runs_both_sources(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = self._run(
                "multi-sync-health",
                "--snapshot-dir",
                temp_dir,
                "--jira-path",
                "fixtures/connectors/jira/incremental_sync.json",
                "--confluence-path",
                "fixtures/connectors/confluence/incremental_sync.json",
                "--reference-time-iso",
                "2026-04-06T09:10:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload["sources"]), 2)
            self.assertEqual(payload["sources"][0]["source_name"], "jira")
            self.assertEqual(payload["sources"][1]["source_name"], "confluence")
            self.assertEqual(payload["sources"][0]["sync"]["document_count"], 1)
            self.assertEqual(payload["sources"][1]["sync"]["document_count"], 1)
            source_types = {entry["source_type"] for entry in payload["ops_health"]["freshness"]["sources"]}
            self.assertEqual(source_types, {"jira", "confluence"})
            self.assertEqual(payload["ops_health"]["backup_restore"]["backup"]["status"], "healthy")
            self.assertEqual(payload["ops_health"]["backup_restore"]["restore"]["status"], "validated")
            self._assert_source_contracts_persisted(temp_dir)

    def test_cli_sync_export_writes_incoming_markdown_and_page_index(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_md = Path(temp_dir) / "sync-export.md"
            output_page_index = Path(temp_dir) / "sync-export-page-index.json"

            result = self._run(
                "sync-export",
                "--snapshot-dir",
                temp_dir,
                "--jira-path",
                "fixtures/connectors/jira/incremental_sync.json",
                "--confluence-path",
                "fixtures/connectors/confluence/incremental_sync.json",
                "--output-md",
                str(output_md),
                "--output-page-index",
                str(output_page_index),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["export_scope"], "incoming")
            self.assertEqual(payload["document_count"], 2)
            self.assertEqual(payload["output_md"], str(output_md))
            self.assertEqual(payload["output_page_index"], str(output_page_index))
            self.assertEqual([document["document_id"] for document in payload["documents"]], ["SSD-102", "CONF-202"])

            written_markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("SSD-102", written_markdown)
            self.assertIn("## Issue Type", written_markdown)
            self.assertIn("- **Family**: defect", written_markdown)
            self.assertIn("Latency Budget Update", written_markdown)

            written_index = json.loads(output_page_index.read_text(encoding="utf-8"))["entries"]
            indexed_documents = {entry["document_id"] for entry in written_index}
            self.assertEqual(indexed_documents, {"SSD-102", "CONF-202"})

            manifest = json.loads((Path(temp_dir) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["sources"]["jira"]["cursor"], "jira-incr-002")
            self.assertEqual(manifest["sources"]["confluence"]["cursor"], "conf-incr-003")

    def test_cli_sync_export_can_write_markdown_tree(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_md_dir = Path(temp_dir) / "documents"

            result = self._run(
                "sync-export",
                "--snapshot-dir",
                temp_dir,
                "--jira-path",
                "fixtures/connectors/jira/incremental_sync.json",
                "--confluence-path",
                "fixtures/connectors/confluence/incremental_sync.json",
                "--output-md-dir",
                str(output_md_dir),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["output_md_dir"], str(output_md_dir))
            matches = list(output_md_dir.rglob("document.md"))
            self.assertEqual(len(matches), 2)

    def test_cli_sync_export_can_export_snapshot_scope(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_md = Path(temp_dir) / "snapshot-export.md"

            result = self._run(
                "sync-export",
                "--snapshot-dir",
                temp_dir,
                "--jira-path",
                "fixtures/connectors/jira/incremental_sync.json",
                "--confluence-path",
                "fixtures/connectors/confluence/incremental_sync.json",
                "--export-scope",
                "snapshot",
                "--output-md",
                str(output_md),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["export_scope"], "snapshot")
            self.assertGreater(payload["document_count"], 2)
            exported_documents = {document["document_id"] for document in payload["documents"]}
            self.assertIn("SSD-102", exported_documents)
            self.assertIn("CONF-202", exported_documents)
            self.assertIn("nvme-spec-v1", exported_documents)
            written_markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("SSD-102", written_markdown)
            self.assertIn("Latency Budget Update", written_markdown)
            self.assertIn("NVMe Flush Command", written_markdown)

    def test_cli_multi_sync_health_validates_live_jira_base_url(self) -> None:
        result = self._run(
            "multi-sync-health",
            "--snapshot-dir",
            ".tmp/multi-sync-health-test",
            "--jira-live",
            "--confluence-path",
            "fixtures/connectors/confluence/incremental_sync.json",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--jira-base-url is required when --jira-live is set", result.stderr)

    def test_cli_multi_sync_health_can_load_profile(self) -> None:
        with TemporaryDirectory() as temp_dir:
            profile = {
                "snapshot_dir": temp_dir,
                "reference_time_iso": "2026-04-06T09:10:00Z",
                "jira": {"path": "fixtures/connectors/jira/incremental_sync.json"},
                "confluence": {"path": "fixtures/connectors/confluence/incremental_sync.json"},
            }
            profile_path = Path(temp_dir) / "profile.json"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")

            result = self._run(
                "multi-sync-health",
                "--profile",
                str(profile_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["profile"], str(profile_path))
            self.assertEqual(len(payload["sources"]), 2)
            source_types = {entry["source_type"] for entry in payload["ops_health"]["freshness"]["sources"]}
            self.assertEqual(source_types, {"jira", "confluence"})
            self._assert_source_contracts_persisted(temp_dir)

    def test_cli_multi_sync_health_cli_overrides_profile_snapshot_dir(self) -> None:
        with TemporaryDirectory() as profile_dir, TemporaryDirectory() as snapshot_dir:
            profile = {
                "snapshot_dir": profile_dir,
                "reference_time_iso": "2026-04-06T09:10:00Z",
                "jira": {"path": "fixtures/connectors/jira/incremental_sync.json"},
                "confluence": {"path": "fixtures/connectors/confluence/incremental_sync.json"},
            }
            profile_path = Path(profile_dir) / "profile.json"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")

            result = self._run(
                "multi-sync-health",
                "--profile",
                str(profile_path),
                "--snapshot-dir",
                snapshot_dir,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["snapshot_dir"], snapshot_dir)

    def test_cli_multi_sync_health_rejects_invalid_profile(self) -> None:
        with TemporaryDirectory() as temp_dir:
            profile = {
                "snapshot_dir": temp_dir,
                "jira": {"live": True},
                "confluence": {"path": "fixtures/connectors/confluence/incremental_sync.json"},
            }
            profile_path = Path(temp_dir) / "invalid-profile.json"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")

            result = self._run(
                "multi-sync-health",
                "--profile",
                str(profile_path),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("profile.jira.base_url is required when live is true", result.stderr)


if __name__ == "__main__":
    unittest.main()

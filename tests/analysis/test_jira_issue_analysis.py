from pathlib import Path
import unittest

from services.analysis.jira_issue_analysis import (
    build_confluence_wiki_summary_payload,
    build_jira_pm_daily_report,
    build_jira_batch_spec_report,
    build_jira_spec_question_payload,
    build_spec_section_explain_payload,
    build_jira_time_report,
    summarize_jira_issue_markdown,
)
from services.analysis.llm_backends import MockLLMBackend
from services.connectors.confluence.connector import load_confluence_sync
from services.connectors.jira.connector import load_jira_sync
from services.retrieval.indexing.page_index import load_documents


class JiraIssueAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.jira_document = load_jira_sync(Path("fixtures/connectors/jira/incremental_sync.json"))["documents"][0]
        cls.jira_documents = [
            *load_jira_sync(Path("fixtures/connectors/jira/full_sync.json"))["documents"],
            cls.jira_document,
        ]
        cls.spec_documents = [
            document
            for document in load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
            if document["document_id"] == "nvme-spec-v1"
        ]
        cls.confluence_document = load_confluence_sync(Path("fixtures/connectors/confluence/page_sync.json"))["documents"][0]

    def test_jira_issue_summary_markdown_preserves_bug_fields_and_comments(self) -> None:
        markdown = summarize_jira_issue_markdown(self.jira_document)

        self.assertIn(f"# {self.jira_document['title']}", markdown)
        self.assertIn("- Issue: SSD-102", markdown)
        self.assertIn("## Issue Fields", markdown)
        self.assertIn("- Priority: Medium", markdown)
        self.assertIn("- Fix Version/s: FwVersion1100", markdown)
        self.assertIn("## Root Cause", markdown)
        self.assertIn("NAND write", markdown)
        self.assertIn("TLC write", markdown)
        self.assertIn("## Comments", markdown)

    def test_jira_spec_question_payload_retrieves_jira_and_spec_evidence(self) -> None:
        payload = build_jira_spec_question_payload(
            jira_document=self.jira_document,
            spec_documents=self.spec_documents,
            question="Does the NAND TLC write issue relate to NVMe flush command evidence?",
            allowed_policies={"team:ssd"},
        )

        self.assertEqual(payload["jira_issue_id"], "SSD-102")
        self.assertTrue(payload["retrieval"]["has_jira_evidence"])
        self.assertTrue(payload["retrieval"]["has_spec_evidence"])
        cited_documents = {citation["document"] for citation in payload["retrieval"]["citations"]}
        self.assertIn("SSD-102", cited_documents)
        self.assertIn("nvme-spec-v1", cited_documents)
        self.assertIn("Answer the Jira question using only the retrieved Jira and spec evidence.", payload["ai_prompt"])
        self.assertIn("If the evidence does not directly support a conclusion", payload["ai_prompt"])
        self.assertIn("## Jira Issue Summary", payload["ai_prompt"])
        self.assertIn("Root Cause", payload["ai_prompt"])
        self.assertIn("SSD-102", payload["ai_prompt"])
        self.assertIn("nvme-spec-v1", payload["ai_prompt"])
        self.assertEqual(payload["answer"]["mode"], "extractive")
        self.assertIn("Jira issue context and spec evidence", payload["answer"]["text"])
        self.assertIn("SSD-102", payload["answer"]["text"])
        self.assertIn("nvme-spec-v1", payload["answer"]["text"])

    def test_jira_spec_question_payload_supports_custom_prompt_template(self) -> None:
        payload = build_jira_spec_question_payload(
            jira_document=self.jira_document,
            spec_documents=self.spec_documents,
            question="Check NAND write against spec evidence",
            allowed_policies={"team:ssd"},
            prompt_template="CUSTOM {jira_issue_id}\nQ={question}\nE={evidence}",
        )

        self.assertTrue(payload["ai_prompt"].startswith("CUSTOM SSD-102"))
        self.assertIn("Q=Check NAND write against spec evidence", payload["ai_prompt"])
        self.assertIn("SSD-102", payload["ai_prompt"])

    def test_jira_spec_question_payload_supports_prompt_modes(self) -> None:
        balanced_payload = build_jira_spec_question_payload(
            jira_document=self.jira_document,
            spec_documents=self.spec_documents,
            question="Check NAND write against spec evidence",
            allowed_policies={"team:ssd"},
            prompt_mode="balanced",
        )
        exploratory_payload = build_jira_spec_question_payload(
            jira_document=self.jira_document,
            spec_documents=self.spec_documents,
            question="Check NAND write against spec evidence",
            allowed_policies={"team:ssd"},
            prompt_mode="exploratory",
        )

        self.assertIn("Separate direct evidence from reasonable inference", balanced_payload["ai_prompt"])
        self.assertIn("Label hypotheses explicitly", exploratory_payload["ai_prompt"])

    def test_jira_spec_question_payload_can_use_local_llm_backend(self) -> None:
        payload = build_jira_spec_question_payload(
            jira_document=self.jira_document,
            spec_documents=self.spec_documents,
            question="Check NAND write against spec evidence",
            allowed_policies={"team:ssd"},
            llm_backend=MockLLMBackend(response_text="Mock local analysis"),
        )

        self.assertEqual(payload["answer"]["mode"], "local-llm")
        self.assertEqual(payload["answer"]["backend"], "mock")
        self.assertEqual(payload["answer"]["text"], "Mock local analysis")
        self.assertEqual(payload["answer"]["citation_count"], payload["retrieval"]["result_count"])

    def test_jira_time_report_filters_by_updated_window_and_renders_custom_prompt(self) -> None:
        report = build_jira_time_report(
            self.jira_documents,
            updated_from_iso="2026-04-05T09:00:00Z",
            updated_to_iso="2026-04-05T10:00:00Z",
            prompt_template="REPORT {time_filter} COUNT={issue_count}\n{summaries}",
        )

        self.assertEqual(report["issue_ids"], ["SSD-102"])
        self.assertEqual(report["issue_count"], 1)
        self.assertEqual(report["time_filter"], "2026-04-05T09:00:00Z..2026-04-05T10:00:00Z")
        self.assertIn("REPORT 2026-04-05T09:00:00Z..2026-04-05T10:00:00Z COUNT=1", report["prompt"])
        self.assertIn("- Issue: SSD-102", report["markdown"])
        self.assertNotIn("- Issue: SSD-101", report["markdown"])

    def test_jira_time_report_can_use_local_llm_backend(self) -> None:
        report = build_jira_time_report(
            self.jira_documents,
            updated_from_iso="2026-04-05T09:00:00Z",
            updated_to_iso="2026-04-05T10:00:00Z",
            llm_backend=MockLLMBackend(response_text="Mock Jira report summary"),
            prompt_mode="strict",
        )

        self.assertEqual(report["answer"]["mode"], "local-llm")
        self.assertEqual(report["answer"]["backend"], "mock")
        self.assertEqual(report["answer"]["text"], "Mock Jira report summary")
        self.assertEqual(report["answer"]["issue_count"], 1)
        self.assertIn("Mode: strict Jira report summarization.", report["prompt"])
        self.assertIn("If evidence is missing", report["prompt"])
        self.assertIn("Do not say no follow-up is needed", report["prompt"])

    def test_jira_time_report_filters_by_calendar_date(self) -> None:
        report = build_jira_time_report(
            self.jira_documents,
            updated_on_date="2026-04-05",
        )

        self.assertEqual(report["time_filter"], "date:2026-04-05")
        self.assertEqual(report["issue_ids"], ["SSD-101", "SSD-102"])

    def test_jira_time_report_filters_by_exact_timestamp(self) -> None:
        report = build_jira_time_report(
            self.jira_documents,
            updated_at_iso="2026-04-05T09:30:00Z",
        )

        self.assertEqual(report["time_filter"], "at:2026-04-05T09:30:00Z")
        self.assertEqual(report["issue_ids"], ["SSD-102"])

    def test_jira_pm_daily_report_splits_updated_and_stale_in_progress(self) -> None:
        report = build_jira_pm_daily_report(
            self.jira_documents,
            reference_date="2026-04-05",
        )

        self.assertEqual(report["report_profile"], "pm-daily")
        self.assertEqual(report["updated_issue_ids"], ["SSD-101", "SSD-102"])
        self.assertEqual(report["stale_issue_ids"], [])
        self.assertIn("## Updated Today", report["markdown"])

    def test_jira_pm_daily_report_can_use_local_llm_backend(self) -> None:
        report = build_jira_pm_daily_report(
            self.jira_documents,
            reference_date="2026-04-05",
            llm_backend=MockLLMBackend(response_text="Mock PM daily"),
        )

        self.assertEqual(report["answer"]["mode"], "local-llm")
        self.assertEqual(report["answer"]["text"], "Mock PM daily")
        self.assertIn("Mode: strict project-manager status reporting.", report["prompt"])

    def test_jira_batch_spec_report_runs_qa_for_filtered_issues(self) -> None:
        report = build_jira_batch_spec_report(
            jira_documents=self.jira_documents,
            spec_documents=self.spec_documents,
            question_template="Analyze Jira {jira_issue_id} against the selected spec.",
            allowed_policies={"team:ssd"},
            updated_from_iso="2026-04-05T09:00:00Z",
            updated_to_iso="2026-04-05T10:00:00Z",
        )

        self.assertEqual(report["issue_ids"], ["SSD-102"])
        self.assertEqual(report["issue_count"], 1)
        self.assertEqual(len(report["issues"]), 1)
        self.assertEqual(report["issues"][0]["jira_issue_id"], "SSD-102")
        self.assertTrue(report["issues"][0]["retrieval"]["has_spec_evidence"])
        self.assertEqual(report["has_spec_evidence_count"], 1)

    def test_jira_batch_spec_report_can_use_local_llm_backend(self) -> None:
        report = build_jira_batch_spec_report(
            jira_documents=self.jira_documents,
            spec_documents=self.spec_documents,
            question_template="Analyze Jira {jira_issue_id} against the selected spec.",
            allowed_policies={"team:ssd"},
            updated_from_iso="2026-04-05T09:00:00Z",
            updated_to_iso="2026-04-05T10:00:00Z",
            llm_backend=MockLLMBackend(response_text="Batch mock analysis"),
        )

        self.assertEqual(report["issues"][0]["answer"]["mode"], "local-llm")
        self.assertEqual(report["issues"][0]["answer"]["text"], "Batch mock analysis")

    def test_jira_batch_spec_report_forwards_prompt_template_to_issue_qa(self) -> None:
        report = build_jira_batch_spec_report(
            jira_documents=self.jira_documents,
            spec_documents=self.spec_documents,
            question_template="Analyze Jira {jira_issue_id} against the selected spec.",
            allowed_policies={"team:ssd"},
            updated_from_iso="2026-04-05T09:00:00Z",
            updated_to_iso="2026-04-05T10:00:00Z",
            prompt_template="BATCH {jira_issue_id}\nQ={question}\nE={evidence}",
        )

        self.assertTrue(report["issues"][0]["ai_prompt"].startswith("BATCH SSD-102"))

    def test_spec_section_explain_payload_retrieves_selected_section_and_jira(self) -> None:
        payload = build_spec_section_explain_payload(
            spec_document=self.spec_documents[0],
            jira_documents=self.jira_documents,
            allowed_policies={"team:ssd"},
            clause="1.1",
        )

        self.assertEqual(payload["section"]["clause"], "1.1")
        self.assertEqual(payload["section"]["heading"], "Flush Semantics")
        self.assertIn("Flush ordering is preserved", payload["section"]["markdown"])
        self.assertIn("Explain the selected spec section using only the section text and retrieved Jira evidence.", payload["ai_prompt"])
        self.assertIn("SSD-102", {issue["document_id"] for issue in payload["related_issues"]})

    def test_confluence_wiki_summary_payload_supports_mock_llm(self) -> None:
        payload = build_confluence_wiki_summary_payload(
            document=self.confluence_document,
            llm_backend=MockLLMBackend(response_text="Mock wiki summary"),
        )

        self.assertEqual(payload["answer"]["mode"], "local-llm")
        self.assertEqual(payload["answer"]["text"], "Mock wiki summary")


if __name__ == "__main__":
    unittest.main()

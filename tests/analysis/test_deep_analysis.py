from __future__ import annotations

from pathlib import Path
import unittest

from services.analysis.deep_analysis import (
    build_deep_analysis_payload,
    _extract_search_keywords,
    _build_search_query,
    _select_analysis_profile,
)
from services.analysis.llm_backends import MockLLMBackend
from services.connectors.confluence.connector import load_confluence_sync
from services.connectors.jira.connector import load_jira_sync
from services.retrieval.indexing.page_index import load_documents


class DeepAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.jira_document = load_jira_sync(Path("fixtures/connectors/jira/incremental_sync.json"))["documents"][0]
        cls.jira_documents = load_jira_sync(Path("fixtures/connectors/jira/full_sync.json"))["documents"]
        cls.spec_documents = [
            document
            for document in load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
            if document["document_id"] == "nvme-spec-v1"
        ]
        cls.confluence_documents = load_confluence_sync(Path("fixtures/connectors/confluence/page_sync.json"))["documents"]

    def test_extract_search_keywords_returns_title(self) -> None:
        keywords = _extract_search_keywords(self.jira_document)
        self.assertTrue(len(keywords) > 0)
        self.assertEqual(keywords[0], self.jira_document["title"])

    def test_build_search_query_produces_non_empty_string(self) -> None:
        query = _build_search_query(self.jira_document)
        self.assertIsInstance(query, str)
        self.assertTrue(len(query) > 0)
        self.assertIn(self.jira_document["title"], query)

    def test_select_analysis_profile_routes_defect(self) -> None:
        defect_doc = {
            "document_id": "TEST-1",
            "metadata": {"issue_fields": {"Issue Type": "FW Bug"}},
        }
        profile = _select_analysis_profile(defect_doc)
        self.assertEqual(profile["label"], "Root Cause Analysis")

    def test_select_analysis_profile_routes_requirement(self) -> None:
        req_doc = {
            "document_id": "TEST-2",
            "metadata": {"issue_fields": {"Issue Type": "DAS/PRD"}},
        }
        profile = _select_analysis_profile(req_doc)
        self.assertEqual(profile["label"], "Requirement Traceability Analysis")

    def test_select_analysis_profile_routes_change_control(self) -> None:
        change_doc = {
            "document_id": "TEST-3",
            "metadata": {"issue_fields": {"Issue Type": "Component Change"}},
        }
        profile = _select_analysis_profile(change_doc)
        self.assertEqual(profile["label"], "Change Impact Analysis")

    def test_select_analysis_profile_defaults_for_unknown(self) -> None:
        unknown_doc = {
            "document_id": "TEST-4",
            "metadata": {"issue_fields": {"Issue Type": "UnknownType"}},
        }
        profile = _select_analysis_profile(unknown_doc)
        self.assertEqual(profile["label"], "General Deep Analysis")

    def test_deep_analysis_payload_extractive_mode(self) -> None:
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            confluence_documents=self.confluence_documents,
            spec_documents=self.spec_documents,
            allowed_policies={"team:ssd"},
        )

        self.assertEqual(payload["issue_id"], self.jira_document["document_id"])
        self.assertIn("title", payload)
        self.assertIn("issue_summary", payload)
        self.assertIn("routing", payload)
        self.assertIn("analysis_profile", payload)
        self.assertIn("search_query", payload)
        self.assertIn("shared_retrieval_bundle", payload)
        self.assertIn("section_retrieval_hooks", payload)
        self.assertIn("section_outputs", payload)
        self.assertIn("composite_report", payload)
        self.assertIn("knowledge_artifacts", payload)
        self.assertIn("image_evidence", payload)
        self.assertIn("confluence_evidence", payload)
        self.assertIn("spec_evidence", payload)
        self.assertIn("cross_source_citations", payload)
        self.assertIn("analysis_prompt", payload)
        self.assertIn("answer", payload)
        self.assertEqual(payload["answer"]["mode"], "extractive")
        self.assertIn(self.jira_document["document_id"], payload["answer"]["text"])
        self.assertEqual(payload["shared_retrieval_bundle"]["engine"], "pageindex")
        self.assertIn("comparison", payload["shared_retrieval_bundle"])
        self.assertIn("rca", payload["section_retrieval_hooks"])
        self.assertIn("rca", payload["section_outputs"])
        self.assertIn("Spec Impact", payload["composite_report"]["content"])
        self.assertIn("confluence_update_proposal", payload["knowledge_artifacts"])
        self.assertEqual(payload["shared_retrieval_bundle"]["allowed_policies"], ["team:ssd"])
        self.assertEqual(payload["shared_retrieval_bundle"]["top_k"], 5)

    def test_deep_analysis_tracks_image_evidence_degraded_states(self) -> None:
        jira_document = {
            **self.jira_document,
            "visual_assets": [
                {
                    "asset_id": "jira-ssd-102-screenshot",
                    "source_type": "jira",
                    "document_id": "SSD-102",
                    "filename": "screenshot.png",
                    "media_type": "image/png",
                    "ocr_text": "FTL assert during write path",
                    "vision_caption": "Firmware failure screenshot.",
                    "provenance": {"ocr_engine": "provided-metadata"},
                }
            ],
        }
        confluence_document = {
            **self.confluence_documents[0],
            "visual_assets": [
                {
                    "asset_id": "conf-diagram",
                    "source_type": "confluence",
                    "document_id": "CONF-201",
                    "filename": "diagram.png",
                    "media_type": "image/png",
                    "provenance": {"extractor": "fixture"},
                }
            ],
        }

        payload = build_deep_analysis_payload(
            jira_document=jira_document,
            confluence_documents=[confluence_document],
            spec_documents=self.spec_documents,
            allowed_policies={"team:ssd"},
        )

        image_evidence = payload["image_evidence"]
        self.assertEqual(image_evidence["asset_count"], 2)
        self.assertEqual(image_evidence["indexed_asset_count"], 1)
        self.assertEqual(image_evidence["degraded_asset_count"], 1)
        self.assertEqual(image_evidence["assets"][0]["ocr_status"], "provided")
        self.assertEqual(image_evidence["assets"][1]["enrichment_state"], "degraded")
        self.assertIn("missing_ocr", image_evidence["assets"][1]["gaps"])
        self.assertIn("## Image Evidence Status", payload["analysis_prompt"])
        self.assertIn("conf-diagram", payload["analysis_prompt"])

    def test_deep_analysis_payload_has_spec_evidence(self) -> None:
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            spec_documents=self.spec_documents,
            allowed_policies={"team:ssd"},
        )

        self.assertGreaterEqual(payload["spec_evidence"]["citation_count"], 0)
        if payload["spec_evidence"]["citation_count"] > 0:
            cited_docs = {c["document"] for c in payload["spec_evidence"]["citations"]}
            self.assertTrue(len(cited_docs) > 0)

    def test_deep_analysis_shared_bundle_tracks_source_breakdown(self) -> None:
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            confluence_documents=self.confluence_documents,
            spec_documents=self.spec_documents,
            allowed_policies={"team:ssd"},
        )

        bundle = payload["shared_retrieval_bundle"]
        self.assertIn("source_breakdown", bundle)
        self.assertIn("confluence", bundle["source_breakdown"])
        self.assertIn("pdf", bundle["source_breakdown"])
        self.assertEqual(
            bundle["source_breakdown"]["confluence"]["document_ids"],
            ["CONF-201"],
        )
        hook = payload["section_retrieval_hooks"]["spec_impact"]
        self.assertEqual(hook["status"], "completed")
        self.assertEqual(hook["allowed_policies"], ["team:ssd"])
        self.assertEqual(hook["top_k"], 3)
        self.assertIn("spec clause", hook["scope_hint"])
        self.assertIn("enhanced_query", hook)
        self.assertGreaterEqual(len(hook["followup_results"]), 1)
        self.assertGreaterEqual(len(hook["followup_citations"]), 1)

    def test_deep_analysis_spec_evidence_excludes_contextual_non_spec_documents(self) -> None:
        mixed_spec_documents = load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            confluence_documents=self.confluence_documents,
            spec_documents=[
                document
                for document in mixed_spec_documents
                if document["source_type"] != "confluence"
            ],
            allowed_policies={"team:ssd", "public"},
        )

        cited_docs = {citation["document"] for citation in payload["spec_evidence"]["citations"]}
        self.assertNotIn("press-release", cited_docs)

    def test_deep_analysis_builds_four_section_outputs(self) -> None:
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            confluence_documents=self.confluence_documents,
            spec_documents=self.spec_documents,
            allowed_policies={"team:ssd"},
        )

        self.assertEqual(
            set(payload["section_outputs"].keys()),
            {"rca", "spec_impact", "decision_brief", "general_summary"},
        )
        self.assertEqual(payload["section_outputs"]["rca"]["runner_version"], "v1")
        self.assertEqual(payload["section_outputs"]["rca"]["followup_retrieval"]["status"], "completed")
        self.assertEqual(payload["section_outputs"]["rca"]["followup_retrieval"]["base_bundle"], "shared_retrieval_bundle")
        self.assertEqual(payload["section_outputs"]["rca"]["followup_retrieval"]["allowed_policies"], ["team:ssd"])
        self.assertGreaterEqual(payload["section_outputs"]["rca"]["answer"]["citation_count"], 1)
        self.assertIn("## RCA", payload["composite_report"]["content"])
        self.assertIn("## General Summary", payload["composite_report"]["content"])
        self.assertIn("### Evidence", payload["composite_report"]["content"])
        self.assertIn("section_outputs/rca.json", payload["composite_report"]["content"])

    def test_deep_analysis_builds_knowledge_artifacts(self) -> None:
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            confluence_documents=self.confluence_documents,
            spec_documents=self.spec_documents,
            allowed_policies={"team:ssd"},
        )

        proposal = payload["knowledge_artifacts"]["confluence_update_proposal"]
        self.assertEqual(proposal["source_issue_key"], self.jira_document["document_id"])
        self.assertEqual(proposal["knowledge_action"], "revise")
        self.assertGreaterEqual(len(proposal["supporting_evidence"]), 1)
        concept_cards = payload["knowledge_artifacts"]["concept_cards"]
        self.assertIn("cards", concept_cards)
        self.assertIn("Composite Report", payload["knowledge_artifacts"]["wiki_draft"]["content"])

    def test_deep_analysis_payload_with_llm_backend(self) -> None:
        mock_backend = MockLLMBackend(response_text="Mock deep analysis result")
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            confluence_documents=self.confluence_documents,
            spec_documents=self.spec_documents,
            allowed_policies={"team:ssd"},
            llm_backend=mock_backend,
        )

        self.assertEqual(payload["answer"]["mode"], "local-llm")
        self.assertEqual(payload["answer"]["backend"], "mock")
        self.assertEqual(payload["answer"]["text"], "Mock deep analysis result")
        self.assertIn("profile", payload["answer"])

    def test_deep_analysis_prompt_contains_evidence_sections(self) -> None:
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            confluence_documents=self.confluence_documents,
            spec_documents=self.spec_documents,
            allowed_policies={"team:ssd"},
        )

        prompt = payload["analysis_prompt"]
        self.assertIn("## Jira Issue Context", prompt)
        self.assertIn("## Confluence Evidence", prompt)
        self.assertIn("## Specification Evidence", prompt)
        self.assertIn(self.jira_document["document_id"], prompt)

    def test_deep_analysis_with_no_cross_source_documents(self) -> None:
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            confluence_documents=[],
            spec_documents=[],
            allowed_policies={"team:ssd"},
        )

        self.assertEqual(payload["confluence_evidence"]["citation_count"], 0)
        self.assertEqual(payload["spec_evidence"]["citation_count"], 0)
        self.assertEqual(payload["section_retrieval_hooks"]["rca"]["status"], "no-corpus")
        self.assertIn("No cross-source evidence", payload["answer"]["text"])
        proposal = payload["knowledge_artifacts"]["confluence_update_proposal"]
        self.assertEqual(proposal["knowledge_action"], "no_change")
        self.assertGreaterEqual(len(proposal["candidate_pages"]), 1)
        self.assertTrue(proposal["candidate_pages"][0]["page_id"].startswith("candidate-"))
        self.assertEqual(proposal["supporting_evidence"], [])
        self.assertIn("No secondary evidence", proposal["open_questions"][0])

    def test_deep_analysis_supports_prompt_modes(self) -> None:
        for mode in ("strict", "balanced", "exploratory"):
            payload = build_deep_analysis_payload(
                jira_document=self.jira_document,
                spec_documents=self.spec_documents,
                allowed_policies={"team:ssd"},
                prompt_mode=mode,
            )
            self.assertIn(f"Mode: {mode}", payload["analysis_prompt"])

    def test_deep_analysis_routing_preserves_issue_family(self) -> None:
        payload = build_deep_analysis_payload(
            jira_document=self.jira_document,
            allowed_policies={"team:ssd"},
        )

        routing = payload["routing"]
        self.assertIn("issue_type_raw", routing)
        self.assertIn("issue_family", routing)
        self.assertIn("issue_route", routing)


if __name__ == "__main__":
    unittest.main()

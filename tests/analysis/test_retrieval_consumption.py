from pathlib import Path
import unittest

from services.analysis.llm_backends import MockLLMBackend
from services.analysis.retrieval_consumption import build_retrieval_consumption_payload
from services.connectors.confluence.connector import load_confluence_sync
from services.connectors.jira.connector import load_jira_sync
from services.ingest.adapters.office.adapter import parse_pptx
from services.retrieval.indexing.page_index import load_documents


class RetrievalConsumptionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.jira_documents = load_jira_sync(Path("fixtures/connectors/jira/incremental_sync.json"))["documents"]
        cls.confluence_documents = load_confluence_sync(Path("fixtures/connectors/confluence/page_sync.json"))["documents"]
        cls.pdf_documents = [
            document
            for document in load_documents(Path("fixtures/retrieval/pageindex_corpus.json"))
            if document["document_id"] == "nvme-spec-v1"
        ]
        cls.pptx_documents = [parse_pptx(Path("fixtures/corpus/office/sample.pptx"))]

    def test_payload_works_for_jira_documents(self) -> None:
        payload = build_retrieval_consumption_payload(
            documents=self.jira_documents,
            question="Which issue mentions medium priority?",
            allowed_policies={"team:ssd"},
        )

        self.assertEqual(payload["retrieval"]["citations"][0]["document"], "SSD-102")
        self.assertEqual(payload["answer"]["mode"], "extractive")
        self.assertIn("SSD-102", payload["ai_prompt"])

    def test_payload_works_for_confluence_documents(self) -> None:
        payload = build_retrieval_consumption_payload(
            documents=self.confluence_documents,
            question="Which page mentions telemetry architecture?",
            allowed_policies={"team:ssd"},
        )

        self.assertEqual(payload["retrieval"]["citations"][0]["document"], "CONF-201")
        self.assertIn("Telemetry Architecture", payload["retrieval"]["citations"][0]["title"])

    def test_payload_works_for_pdf_documents(self) -> None:
        payload = build_retrieval_consumption_payload(
            documents=self.pdf_documents,
            question="What document covers flush semantics?",
            allowed_policies={"team:ssd", "public"},
            prompt_mode="balanced",
        )

        self.assertEqual(payload["retrieval"]["citations"][0]["document"], "nvme-spec-v1")
        self.assertIn("Separate direct evidence from reasonable inference.", payload["ai_prompt"])

    def test_payload_works_for_pptx_documents_with_local_llm(self) -> None:
        payload = build_retrieval_consumption_payload(
            documents=self.pptx_documents,
            question="Which slide mentions latency targets?",
            allowed_policies={"team:ssd"},
            llm_backend=MockLLMBackend(response_text="Mock slide answer"),
        )

        self.assertEqual(payload["retrieval"]["citations"][0]["document"], "sample")
        self.assertEqual(payload["answer"]["mode"], "local-llm")
        self.assertEqual(payload["answer"]["text"], "Mock slide answer")


if __name__ == "__main__":
    unittest.main()

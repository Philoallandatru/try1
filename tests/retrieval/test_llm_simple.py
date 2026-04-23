"""LLM-Assisted Retrieval Tests - Simplified Version.

Tests retrieval with LLM-based enhancements using mock LLM.
"""
import tempfile
import unittest
from pathlib import Path

from packages.retrieval.index_manager import IndexManager
from packages.retrieval.bm25_retriever import BM25Retriever


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self):
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        """Mock LLM generation."""
        self.call_count += 1

        if "reformulate" in prompt.lower():
            return "NVMe flush command specification"
        elif "relevant" in prompt.lower():
            return "yes" if "nvme" in prompt.lower() else "no"
        elif "answer" in prompt.lower():
            return "The NVMe flush command ensures data persistence."
        elif "summarize" in prompt.lower():
            return "Summary of the document content."
        else:
            return "mock response"


class TestLLMRetrievalSimple(unittest.TestCase):
    """Simplified tests for LLM-assisted retrieval."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Initialize index
        cls.db_path = cls.workspace_dir / "documents.db"
        cls.index_dir = cls.workspace_dir / ".index"
        cls.index_manager = IndexManager(
            db_path=str(cls.db_path),
            index_dir=str(cls.index_dir)
        )

        # Add test documents
        test_docs = [
            {
                "id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "content": "The NVMe Flush command commits data to non-volatile media.",
                "source_type": "pdf"
            },
            {
                "id": "SSD-777",
                "title": "NVMe flush failure",
                "content": "NVMe flush command fails under high load.",
                "source_type": "jira"
            },
        ]

        for doc in test_docs:
            cls.index_manager.db.create_document(
                id=doc["id"],
                source_id=doc["id"],
                source_type=doc["source_type"],
                title=doc["title"],
                content=doc["content"],
                url="",
                metadata={}
            )

        cls.index_manager.build_full_index()

    def test_llm_query_reformulation(self):
        """Test LLM-based query reformulation."""
        llm = MockLLMClient()

        # Reformulate query
        original = "nvme flush not working"
        reformulated = llm.generate(f"Reformulate: {original}")

        self.assertIsInstance(reformulated, str)
        self.assertGreater(len(reformulated), 0)

        # Search with reformulated query
        retriever = BM25Retriever(self.index_manager.index)
        results = retriever.search(reformulated, top_k=3)
        self.assertGreater(len(results), 0)

    def test_llm_relevance_assessment(self):
        """Test LLM-based relevance assessment."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Search
        results = retriever.search("NVMe flush", top_k=5)

        # Assess relevance
        relevant_count = 0
        for result in results:
            content = result.document.get("content", "")
            assessment = llm.generate(f"Is relevant to NVMe: {content[:100]}")
            if "yes" in assessment.lower():
                relevant_count += 1

        self.assertGreater(relevant_count, 0)

    def test_llm_answer_generation(self):
        """Test LLM-based answer generation."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Search
        results = retriever.search("NVMe flush command", top_k=3)

        # Generate answer
        context = "\n".join([r.document.get("content", "") for r in results])
        answer = llm.generate(f"Answer based on: {context[:200]}")

        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 0)

    def test_llm_reranking(self):
        """Test LLM-based reranking."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Initial retrieval
        results = retriever.search("flush command", top_k=5)

        # Rerank with LLM scores
        reranked = []
        for result in results:
            content = result.document.get("content", "")
            llm.generate(f"Rate relevance: {content[:100]}")

            # Combine scores (mock: use original score)
            reranked.append({
                "doc_id": result.doc_id,
                "original_score": result.score,
                "llm_score": result.score,  # Mock
                "combined_score": result.score
            })

        self.assertEqual(len(reranked), len(results))

    def test_llm_document_summarization(self):
        """Test LLM-based document summarization."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Retrieve documents
        results = retriever.search("NVMe", top_k=3)

        # Summarize
        summaries = []
        for result in results:
            content = result.document.get("content", "")
            summary = llm.generate(f"Summarize: {content}")
            summaries.append({
                "doc_id": result.doc_id,
                "summary": summary
            })

        self.assertEqual(len(summaries), len(results))
        for item in summaries:
            self.assertIn("summary", item)
            self.assertGreater(len(item["summary"]), 0)

    def test_llm_multi_hop_reasoning(self):
        """Test LLM multi-hop reasoning."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # First hop
        results1 = retriever.search("NVMe flush failure", top_k=2)

        # Second hop
        results2 = retriever.search("NVMe flush fix", top_k=2)

        # Combine and synthesize
        all_results = results1 + results2
        context = "\n".join([r.document.get("content", "")[:100] for r in all_results])
        answer = llm.generate(f"Answer using: {context}")

        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 0)

    def test_llm_call_tracking(self):
        """Test that LLM calls are tracked."""
        llm = MockLLMClient()

        initial_count = llm.call_count
        llm.generate("test prompt")

        self.assertEqual(llm.call_count, initial_count + 1)


if __name__ == "__main__":
    unittest.main()

"""LLM-Assisted Retrieval Tests.

Tests retrieval with LLM-based enhancements:
1. Query understanding and reformulation
2. Result relevance assessment
3. Answer generation from retrieved documents
4. Hybrid retrieval (keyword + semantic)
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from packages.retrieval.index_manager import IndexManager
from packages.retrieval.bm25_retriever import BM25Retriever


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self):
        self.call_count = 0

    def generate(self, prompt: str, **kwargs) -> str:
        """Mock LLM generation."""
        self.call_count += 1

        # Simple mock responses based on prompt content
        if "reformulate" in prompt.lower() or "rewrite" in prompt.lower():
            # Query reformulation
            if "nvme flush" in prompt.lower():
                return "NVMe flush command specification implementation"
            elif "ssd slow" in prompt.lower():
                return "SSD performance degradation troubleshooting"
            else:
                return "reformulated query"

        elif "relevant" in prompt.lower() or "assess" in prompt.lower():
            # Relevance assessment
            return "yes" if "nvme" in prompt.lower() or "flush" in prompt.lower() else "no"

        elif "answer" in prompt.lower() or "summarize" in prompt.lower():
            # Answer generation
            return "Based on the retrieved documents, the NVMe flush command ensures data persistence."

        elif "extract" in prompt.lower() and "keywords" in prompt.lower():
            # Keyword extraction
            return json.dumps(["nvme", "flush", "command", "data", "persistence"])

        else:
            return "mock llm response"


class TestLLMAssistedRetrieval(unittest.TestCase):
    """Tests for LLM-assisted retrieval."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "test_workspace"
        cls.workspace_dir.mkdir(parents=True)

        # Create test documents
        cls.test_documents = [
            {
                "doc_id": "nvme-spec-1.4",
                "title": "NVMe Specification 1.4",
                "content": "The NVMe Flush command commits data and metadata to non-volatile media. "
                          "This ensures data persistence across power cycles. "
                          "The command is mandatory for all NVMe devices.",
                "metadata": {"document_type": "spec", "source_type": "pdf"}
            },
            {
                "doc_id": "SSD-777",
                "title": "NVMe flush command failure",
                "content": "NVMe flush command fails intermittently under high load. "
                          "Error code 0x02 returned. Affects firmware version 2.1.3. "
                          "Workaround: reduce queue depth to 32.",
                "metadata": {"document_type": "issue", "source_type": "jira"}
            },
            {
                "doc_id": "CONF-123",
                "title": "NVMe Flush Implementation Guide",
                "content": "Best practices for implementing NVMe flush command. "
                          "Includes queue management, timeout handling, and error recovery. "
                          "Recommended timeout: 30 seconds.",
                "metadata": {"document_type": "guide", "source_type": "confluence"}
            },
            {
                "doc_id": "SSD-888",
                "title": "SSD performance degradation",
                "content": "SSD shows performance degradation after prolonged use. "
                          "IOPS drops from 100K to 50K. Garbage collection suspected. "
                          "Recommend firmware update to version 3.0.",
                "metadata": {"document_type": "issue", "source_type": "jira"}
            }
        ]

        # Initialize index
        cls.db_path = cls.workspace_dir / "documents.db"
        cls.index_dir = cls.workspace_dir / ".index"
        cls.index_manager = IndexManager(
            db_path=str(cls.db_path),
            index_dir=str(cls.index_dir)
        )

        # Add documents to database
        for doc in cls.test_documents:
            cls.index_manager.db.create_document(
                id=doc["doc_id"],
                source_id=doc["doc_id"],
                source_type=doc["metadata"].get("source_type", "test"),
                title=doc["title"],
                content=doc["content"],
                url="",
                metadata=doc.get("metadata", {})
            )

        cls.index_manager.build_full_index()

    def test_llm_query_reformulation(self):
        """Test LLM-based query reformulation."""
        llm = MockLLMClient()

        # Original query
        original_query = "nvme flush not working"

        # Reformulate with LLM
        prompt = f"Reformulate this search query to be more specific: '{original_query}'"
        reformulated_query = llm.generate(prompt)

        # Verify reformulation
        self.assertIsInstance(reformulated_query, str)
        self.assertGreater(len(reformulated_query), 0)
        self.assertNotEqual(reformulated_query, original_query)

        # Search with reformulated query
        retriever = BM25Retriever(self.index_manager.index)
        results = retriever.search(reformulated_query, top_k=3)

        # Should return relevant results
        self.assertGreater(len(results), 0)

    def test_llm_relevance_assessment(self):
        """Test LLM-based relevance assessment of retrieved documents."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Search
        query = "NVMe flush command"
        results = retriever.search(query, top_k=5)

        # Assess relevance with LLM
        relevant_results = []
        for result in results:
            prompt = f"Is this document relevant to the query '{query}'?\n\nDocument: {result['content'][:200]}"
            assessment = llm.generate(prompt)

            if "yes" in assessment.lower():
                relevant_results.append(result)

        # Should have some relevant results
        self.assertGreater(len(relevant_results), 0)
        self.assertLessEqual(len(relevant_results), len(results))

    def test_llm_answer_generation(self):
        """Test LLM-based answer generation from retrieved documents."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Search
        query = "What does the NVMe flush command do?"
        results = retriever.search(query, top_k=3)

        # Generate answer with LLM
        context = "\n\n".join([f"Document {i+1}: {r['content']}" for i, r in enumerate(results)])
        prompt = f"Answer this question based on the provided documents:\n\nQuestion: {query}\n\nDocuments:\n{context}"
        answer = llm.generate(prompt)

        # Verify answer
        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 0)
        self.assertIn("flush", answer.lower())

    def test_llm_keyword_extraction(self):
        """Test LLM-based keyword extraction for query expansion."""
        llm = MockLLMClient()

        # Extract keywords
        query = "NVMe flush command ensures data persistence"
        prompt = f"Extract the most important keywords from this query: '{query}'"
        keywords_json = llm.generate(prompt)

        # Parse keywords
        keywords = json.loads(keywords_json)

        # Verify keywords
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)

        # Use keywords for expanded search
        retriever = BM25Retriever(self.index_manager.index)
        expanded_query = " ".join(keywords)
        results = retriever.search(expanded_query, top_k=3)

        self.assertGreater(len(results), 0)

    def test_llm_query_intent_classification(self):
        """Test LLM-based query intent classification."""
        llm = MockLLMClient()

        test_queries = [
            ("What is NVMe flush command?", "knowledge"),
            ("NVMe flush command not working", "troubleshooting"),
            ("NVMe specification section 5.3", "specification"),
        ]

        for query, expected_intent in test_queries:
            prompt = f"Classify the intent of this query (knowledge/troubleshooting/specification): '{query}'"
            response = llm.generate(prompt)

            # Intent classification helps route queries to appropriate retrieval strategies
            self.assertIsInstance(response, str)

    def test_hybrid_retrieval_with_llm_reranking(self):
        """Test hybrid retrieval with LLM-based reranking."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Initial retrieval
        query = "flush command implementation"
        results = retriever.search(query, top_k=5)

        # Rerank with LLM
        reranked_results = []
        for result in results:
            # Ask LLM to score relevance
            prompt = f"Rate the relevance (0-10) of this document to query '{query}':\n\n{result['content'][:200]}"
            score_text = llm.generate(prompt)

            # Parse score (mock: use original score)
            llm_score = result["score"]  # In real implementation, parse LLM response

            reranked_results.append({
                **result,
                "llm_score": llm_score,
                "combined_score": result["score"] * 0.5 + llm_score * 0.5
            })

        # Sort by combined score
        reranked_results.sort(key=lambda x: x["combined_score"], reverse=True)

        # Verify reranking
        self.assertEqual(len(reranked_results), len(results))
        for result in reranked_results:
            self.assertIn("llm_score", result)
            self.assertIn("combined_score", result)

    def test_llm_query_expansion_with_context(self):
        """Test LLM-based query expansion with domain context."""
        llm = MockLLMClient()

        # Provide domain context
        domain_context = "NVMe storage technology, SSD firmware, PCIe interface"
        query = "flush fails"

        # Expand query with LLM
        prompt = f"Expand this query with relevant technical terms from the domain:\n\nDomain: {domain_context}\nQuery: {query}"
        expanded_query = llm.generate(prompt)

        # Search with expanded query
        retriever = BM25Retriever(self.index_manager.index)
        results = retriever.search(expanded_query, top_k=3)

        self.assertGreater(len(results), 0)

    def test_llm_document_summarization(self):
        """Test LLM-based summarization of retrieved documents."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Retrieve documents
        query = "NVMe flush"
        results = retriever.search(query, top_k=3)

        # Summarize each document
        summaries = []
        for result in results:
            prompt = f"Summarize this document in one sentence:\n\n{result['content']}"
            summary = llm.generate(prompt)
            summaries.append({
                "doc_id": result["doc_id"],
                "summary": summary
            })

        # Verify summaries
        self.assertEqual(len(summaries), len(results))
        for summary_item in summaries:
            self.assertIn("doc_id", summary_item)
            self.assertIn("summary", summary_item)
            self.assertGreater(len(summary_item["summary"]), 0)

    def test_llm_multi_hop_reasoning(self):
        """Test LLM-assisted multi-hop reasoning over retrieved documents."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Complex query requiring multiple documents
        query = "What causes NVMe flush failures and how to fix them?"

        # First hop: retrieve documents about flush failures
        results1 = retriever.search("NVMe flush failure", top_k=3)

        # Second hop: retrieve documents about fixes
        results2 = retriever.search("NVMe flush fix workaround", top_k=3)

        # Combine results
        all_results = results1 + results2

        # Use LLM to synthesize answer
        context = "\n\n".join([f"Doc {i+1}: {r['content']}" for i, r in enumerate(all_results)])
        prompt = f"Answer this question using the provided documents:\n\nQuestion: {query}\n\nDocuments:\n{context}"
        answer = llm.generate(prompt)

        # Verify answer
        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 0)

    def test_llm_retrieval_with_conversation_context(self):
        """Test LLM-assisted retrieval with conversation history."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Conversation history
        conversation = [
            {"role": "user", "content": "Tell me about NVMe"},
            {"role": "assistant", "content": "NVMe is a storage protocol..."},
            {"role": "user", "content": "What about the flush command?"}
        ]

        # Use LLM to understand query in context
        context_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
        prompt = f"Given this conversation, reformulate the last query:\n\n{context_text}"
        contextualized_query = llm.generate(prompt)

        # Search with contextualized query
        results = retriever.search(contextualized_query, top_k=3)

        self.assertGreater(len(results), 0)


class TestLLMRetrievalIntegration(unittest.TestCase):
    """Integration tests for LLM-assisted retrieval in the full pipeline."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_dir = Path(self.temp_dir) / "test_workspace"
        self.workspace_dir.mkdir(parents=True)

        # Initialize components
        self.db_path = self.workspace_dir / "documents.db"
        self.index_dir = self.workspace_dir / ".index"
        self.index_manager = IndexManager(
            db_path=str(self.db_path),
            index_dir=str(self.index_dir)
        )

        # Add sample document to database
        self.index_manager.db.create_document(
            id="test-doc-1",
            source_id="test-doc-1",
            source_type="test",
            title="Test Document",
            content="This is a test document about NVMe flush command.",
            url="",
            metadata={"type": "test"}
        )
        self.index_manager.build_full_index()

    @patch('builtins.print')
    def test_llm_retrieval_pipeline_with_mock(self, mock_print):
        """Test complete LLM retrieval pipeline with mocked LLM."""
        llm = MockLLMClient()
        retriever = BM25Retriever(self.index_manager.index)

        # Step 1: Query reformulation
        original_query = "flush not working"
        reformulated = llm.generate(f"Reformulate: {original_query}")

        # Step 2: Retrieval
        results = retriever.search(reformulated, top_k=3)

        # Step 3: Relevance filtering
        filtered_results = []
        for result in results:
            assessment = llm.generate(f"Is relevant: {result['content'][:100]}")
            if "yes" in assessment.lower() or "nvme" in result['content'].lower():
                filtered_results.append(result)

        # Step 4: Answer generation
        if filtered_results:
            context = "\n".join([r['content'] for r in filtered_results])
            answer = llm.generate(f"Answer based on: {context[:200]}")

            # Verify pipeline
            self.assertGreater(len(filtered_results), 0)
            self.assertIsInstance(answer, str)
            self.assertGreater(len(answer), 0)

    def test_llm_retrieval_error_handling(self):
        """Test error handling in LLM-assisted retrieval."""
        llm = MockLLMClient()

        # Test with empty query
        try:
            response = llm.generate("")
            self.assertIsInstance(response, str)
        except Exception as e:
            self.fail(f"Should handle empty query gracefully: {e}")

        # Test with very long query
        long_query = "test " * 1000
        try:
            response = llm.generate(long_query)
            self.assertIsInstance(response, str)
        except Exception as e:
            self.fail(f"Should handle long query gracefully: {e}")


if __name__ == "__main__":
    unittest.main()

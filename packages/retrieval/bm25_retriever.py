"""
BM25 Retriever for document search.

Provides search functionality on top of BM25Index.
"""

from typing import List, Dict, Any, Optional
import numpy as np

from .bm25_index import BM25Index
from .tokenizer import Tokenizer


class SearchResult:
    """Search result for a single document."""

    def __init__(self, doc_id: str, score: float, document: Dict[str, Any], rank: int):
        self.doc_id = doc_id
        self.score = score
        self.document = document
        self.rank = rank

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "doc_id": self.doc_id,
            "score": float(self.score),
            "rank": self.rank,
            "document": self.document,
        }


class BM25Retriever:
    """BM25-based document retriever."""

    def __init__(self, index: BM25Index):
        """
        Initialize retriever.

        Args:
            index: BM25Index instance
        """
        self.index = index
        self.tokenizer = index.tokenizer

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        document_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Search for documents matching the query.

        Args:
            query: Search query
            top_k: Number of top results to return
            min_score: Minimum score threshold
            document_types: Optional list of document types to filter by (e.g., ["spec", "policy"])

        Returns:
            List of SearchResult objects, sorted by score (descending)
        """
        if not self.index.bm25:
            return []

        # Tokenize query
        query_tokens = self.tokenizer.tokenize(query)
        if not query_tokens:
            return []

        # Get BM25 scores
        scores = self.index.bm25.get_scores(query_tokens)

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1]

        # Build results with filtering
        results = []
        for idx in top_indices:
            score = scores[idx]
            if score < min_score:
                continue

            doc = self.index.documents[idx]

            # Filter by document type if specified
            if document_types:
                doc_type = doc.get("metadata", {}).get("document_type")
                if doc_type not in document_types:
                    continue

            result = SearchResult(
                doc_id=doc.get("id", str(idx)),
                score=score,
                document=doc,
                rank=len(results) + 1
            )
            results.append(result)

            # Stop when we have enough results
            if len(results) >= top_k:
                break

        return results

    def search_with_highlights(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        text_field: str = "content",
        document_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search and return results with highlighted matching terms.

        Args:
            query: Search query
            top_k: Number of top results to return
            min_score: Minimum score threshold
            text_field: Field name containing text content
            document_types: Optional list of document types to filter by

        Returns:
            List of result dicts with highlights
        """
        results = self.search(query, top_k, min_score, document_types)
        query_tokens = set(self.tokenizer.tokenize(query))

        highlighted_results = []
        for result in results:
            result_dict = result.to_dict()

            # Find matching tokens in document
            doc_text = result.document.get(text_field, "")
            doc_tokens = self.tokenizer.tokenize(doc_text)
            matching_tokens = [t for t in doc_tokens if t in query_tokens]

            result_dict["matching_tokens"] = matching_tokens
            result_dict["match_count"] = len(matching_tokens)

            highlighted_results.append(result_dict)

        return highlighted_results

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document dict or None if not found
        """
        for doc in self.index.documents:
            if doc.get("id") == doc_id:
                return doc
        return None

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents in the index."""
        return self.index.documents

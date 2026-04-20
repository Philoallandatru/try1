"""
BM25 Index for document retrieval.

Uses the rank-bm25 library for efficient BM25 scoring.
"""

import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

from .tokenizer import Tokenizer


class BM25Index:
    """BM25 index for document retrieval."""

    def __init__(self, tokenizer: Optional[Tokenizer] = None):
        """
        Initialize BM25 index.

        Args:
            tokenizer: Tokenizer instance (creates default if None)
        """
        self.tokenizer = tokenizer or Tokenizer()
        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []

    def build(self, documents: List[Dict[str, Any]], text_field: str = "content"):
        """
        Build BM25 index from documents.

        Args:
            documents: List of document dicts with at least {id, content}
            text_field: Field name containing text content
        """
        self.documents = documents
        self.tokenized_corpus = []

        # Tokenize all documents
        for doc in documents:
            text = doc.get(text_field, "")
            tokens = self.tokenizer.tokenize(text)
            self.tokenized_corpus.append(tokens)

        # Build BM25 index
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

    def add_documents(self, new_documents: List[Dict[str, Any]], text_field: str = "content"):
        """
        Add new documents to existing index (incremental update).

        Args:
            new_documents: List of new document dicts
            text_field: Field name containing text content
        """
        # Add to document list
        self.documents.extend(new_documents)

        # Tokenize new documents
        for doc in new_documents:
            text = doc.get(text_field, "")
            tokens = self.tokenizer.tokenize(text)
            self.tokenized_corpus.append(tokens)

        # Rebuild BM25 index (rank-bm25 doesn't support incremental updates)
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

    def remove_documents(self, doc_ids: List[str]):
        """
        Remove documents from index.

        Args:
            doc_ids: List of document IDs to remove
        """
        # Find indices to remove
        remove_indices = set()
        for i, doc in enumerate(self.documents):
            if doc.get("id") in doc_ids:
                remove_indices.add(i)

        # Remove documents and tokenized corpus
        self.documents = [doc for i, doc in enumerate(self.documents) if i not in remove_indices]
        self.tokenized_corpus = [tokens for i, tokens in enumerate(self.tokenized_corpus) if i not in remove_indices]

        # Rebuild BM25 index
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

    def get_document_count(self) -> int:
        """Get number of documents in index."""
        return len(self.documents)

    def save(self, index_path: Path):
        """
        Save index to disk.

        Args:
            index_path: Path to save index file
        """
        index_path.parent.mkdir(parents=True, exist_ok=True)

        index_data = {
            "documents": self.documents,
            "tokenized_corpus": self.tokenized_corpus,
        }

        with open(index_path, "wb") as f:
            pickle.dump(index_data, f)

    def load(self, index_path: Path):
        """
        Load index from disk.

        Args:
            index_path: Path to index file
        """
        with open(index_path, "rb") as f:
            index_data = pickle.load(f)

        self.documents = index_data["documents"]
        self.tokenized_corpus = index_data["tokenized_corpus"]

        # Rebuild BM25 index
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Dict with index stats
        """
        return {
            "document_count": len(self.documents),
            "avg_doc_length": sum(len(tokens) for tokens in self.tokenized_corpus) / len(self.tokenized_corpus) if self.tokenized_corpus else 0,
            "total_tokens": sum(len(tokens) for tokens in self.tokenized_corpus),
        }

"""
SPLADE (Sparse Lexical and Expansion) Retriever.

SPLADE is a neural retrieval model that learns sparse representations
for queries and documents, combining the benefits of:
- Sparse representations (like BM25)
- Neural semantic understanding (like dense embeddings)

This implementation provides a simplified SPLADE-like approach using:
- Term importance weighting
- Query expansion with learned weights
- Sparse vector representations
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import defaultdict
import math

from .bm25_retriever import SearchResult
from .tokenizer import Tokenizer


class SPLADERetriever:
    """
    SPLADE-inspired sparse retrieval with term importance weighting.

    This is a simplified implementation that captures the key ideas:
    1. Learn term importance weights
    2. Expand queries with weighted terms
    3. Use sparse representations for efficient retrieval
    """

    def __init__(
        self,
        tokenizer: Tokenizer,
        use_idf: bool = True,
        expansion_terms: int = 10,
        alpha: float = 0.5
    ):
        """
        Initialize SPLADE retriever.

        Args:
            tokenizer: Tokenizer for text processing
            use_idf: Whether to use IDF for term weighting
            expansion_terms: Number of expansion terms to add
            alpha: Balance between original and expanded terms (0-1)
        """
        self.tokenizer = tokenizer
        self.use_idf = use_idf
        self.expansion_terms = expansion_terms
        self.alpha = alpha

        # Document collection
        self.documents = []
        self.doc_vectors = []  # Sparse vectors for documents

        # Term statistics
        self.term_doc_freq = defaultdict(int)  # Document frequency per term
        self.term_weights = {}  # Learned term importance weights
        self.vocab = set()
        self.num_docs = 0

    def build_index(self, documents: List[Dict[str, Any]]):
        """
        Build SPLADE index from documents.

        Args:
            documents: List of document dicts with 'id' and 'content'
        """
        self.documents = documents
        self.num_docs = len(documents)

        # First pass: collect vocabulary and document frequencies
        for doc in documents:
            content = doc.get("content", "")
            tokens = set(self.tokenizer.tokenize(content))
            self.vocab.update(tokens)

            for token in tokens:
                self.term_doc_freq[token] += 1

        # Compute IDF weights
        if self.use_idf:
            for term in self.vocab:
                df = self.term_doc_freq[term]
                idf = math.log((self.num_docs + 1) / (df + 1)) + 1
                self.term_weights[term] = idf
        else:
            # Uniform weights
            for term in self.vocab:
                self.term_weights[term] = 1.0

        # Second pass: build sparse document vectors
        self.doc_vectors = []
        for doc in documents:
            content = doc.get("content", "")
            doc_vector = self._compute_sparse_vector(content)
            self.doc_vectors.append(doc_vector)

    def _compute_sparse_vector(self, text: str) -> Dict[str, float]:
        """
        Compute sparse vector representation for text.

        Args:
            text: Input text

        Returns:
            Sparse vector as dict {term: weight}
        """
        tokens = self.tokenizer.tokenize(text)
        term_freq = defaultdict(int)

        for token in tokens:
            term_freq[token] += 1

        # Compute weighted sparse vector
        sparse_vector = {}
        for term, freq in term_freq.items():
            # TF-IDF style weighting
            tf = math.log(1 + freq)
            weight = self.term_weights.get(term, 1.0)
            sparse_vector[term] = tf * weight

        # Normalize
        norm = math.sqrt(sum(v ** 2 for v in sparse_vector.values()))
        if norm > 0:
            sparse_vector = {k: v / norm for k, v in sparse_vector.items()}

        return sparse_vector

    def _expand_query(self, query_vector: Dict[str, float]) -> Dict[str, float]:
        """
        Expand query with related terms based on co-occurrence.

        Args:
            query_vector: Original query sparse vector

        Returns:
            Expanded query vector
        """
        # Find candidate expansion terms based on co-occurrence
        expansion_candidates = defaultdict(float)

        for term in query_vector.keys():
            # Find documents containing this term
            for doc_idx, doc_vector in enumerate(self.doc_vectors):
                if term in doc_vector:
                    # Add all terms from this document as candidates
                    for doc_term, doc_weight in doc_vector.items():
                        if doc_term not in query_vector:
                            expansion_candidates[doc_term] += doc_weight

        # Select top expansion terms
        sorted_candidates = sorted(
            expansion_candidates.items(),
            key=lambda x: x[1],
            reverse=True
        )[:self.expansion_terms]

        # Create expanded vector
        expanded_vector = query_vector.copy()

        for term, score in sorted_candidates:
            # Weight expansion terms lower than original terms
            expanded_vector[term] = score * (1 - self.alpha)

        # Re-normalize
        norm = math.sqrt(sum(v ** 2 for v in expanded_vector.values()))
        if norm > 0:
            expanded_vector = {k: v / norm for k, v in expanded_vector.items()}

        return expanded_vector

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        enable_expansion: bool = True
    ) -> List[SearchResult]:
        """
        Search documents using SPLADE-style sparse retrieval.

        Args:
            query: Search query
            top_k: Number of results to return
            min_score: Minimum score threshold
            enable_expansion: Whether to expand query

        Returns:
            List of SearchResult objects
        """
        if not self.documents:
            return []

        # Compute query vector
        query_vector = self._compute_sparse_vector(query)

        # Expand query if enabled
        if enable_expansion:
            query_vector = self._expand_query(query_vector)

        # Compute scores for all documents
        scores = []
        for doc_idx, doc_vector in enumerate(self.doc_vectors):
            score = self._compute_similarity(query_vector, doc_vector)
            scores.append((doc_idx, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        # Build results
        results = []
        for rank, (doc_idx, score) in enumerate(scores[:top_k], 1):
            if score < min_score:
                break

            doc = self.documents[doc_idx]
            result = SearchResult(
                doc_id=doc.get("id", str(doc_idx)),
                score=score,
                document=doc,
                rank=rank
            )
            results.append(result)

        return results

    def _compute_similarity(
        self,
        vec1: Dict[str, float],
        vec2: Dict[str, float]
    ) -> float:
        """
        Compute cosine similarity between two sparse vectors.

        Args:
            vec1: First sparse vector
            vec2: Second sparse vector

        Returns:
            Cosine similarity score
        """
        # Compute dot product
        dot_product = 0.0
        for term in vec1.keys():
            if term in vec2:
                dot_product += vec1[term] * vec2[term]

        return dot_product

    def get_query_expansion(self, query: str) -> List[Tuple[str, float]]:
        """
        Get expansion terms for a query.

        Args:
            query: Search query

        Returns:
            List of (term, weight) tuples
        """
        query_vector = self._compute_sparse_vector(query)
        expanded_vector = self._expand_query(query_vector)

        # Find expansion terms (not in original query)
        original_terms = set(query_vector.keys())
        expansion_terms = [
            (term, weight)
            for term, weight in expanded_vector.items()
            if term not in original_terms
        ]

        # Sort by weight
        expansion_terms.sort(key=lambda x: x[1], reverse=True)

        return expansion_terms

    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Statistics dict
        """
        return {
            "num_documents": self.num_docs,
            "vocab_size": len(self.vocab),
            "avg_doc_vector_size": np.mean([len(v) for v in self.doc_vectors]) if self.doc_vectors else 0,
            "use_idf": self.use_idf,
            "expansion_terms": self.expansion_terms,
            "alpha": self.alpha
        }


class HybridRetriever:
    """
    Hybrid retriever combining BM25 and SPLADE.

    Combines sparse lexical matching (BM25) with learned sparse
    representations (SPLADE) for improved retrieval quality.
    """

    def __init__(
        self,
        bm25_retriever,
        splade_retriever: SPLADERetriever,
        bm25_weight: float = 0.5,
        splade_weight: float = 0.5
    ):
        """
        Initialize hybrid retriever.

        Args:
            bm25_retriever: BM25 retriever instance
            splade_retriever: SPLADE retriever instance
            bm25_weight: Weight for BM25 scores (0-1)
            splade_weight: Weight for SPLADE scores (0-1)
        """
        self.bm25_retriever = bm25_retriever
        self.splade_retriever = splade_retriever
        self.bm25_weight = bm25_weight
        self.splade_weight = splade_weight

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        Hybrid search combining BM25 and SPLADE.

        Args:
            query: Search query
            top_k: Number of results to return
            min_score: Minimum score threshold

        Returns:
            List of SearchResult objects
        """
        # Get results from both retrievers
        bm25_results = self.bm25_retriever.search(query, top_k=top_k * 2)
        splade_results = self.splade_retriever.search(query, top_k=top_k * 2)

        # Normalize scores to [0, 1]
        bm25_scores = self._normalize_scores(bm25_results)
        splade_scores = self._normalize_scores(splade_results)

        # Combine scores
        combined_scores = {}
        for result in bm25_results:
            doc_id = result.doc_id
            combined_scores[doc_id] = {
                "bm25_score": bm25_scores.get(doc_id, 0.0),
                "splade_score": 0.0,
                "document": result.document
            }

        for result in splade_results:
            doc_id = result.doc_id
            if doc_id not in combined_scores:
                combined_scores[doc_id] = {
                    "bm25_score": 0.0,
                    "splade_score": splade_scores.get(doc_id, 0.0),
                    "document": result.document
                }
            else:
                combined_scores[doc_id]["splade_score"] = splade_scores.get(doc_id, 0.0)

        # Compute final scores
        final_results = []
        for doc_id, scores in combined_scores.items():
            final_score = (
                self.bm25_weight * scores["bm25_score"] +
                self.splade_weight * scores["splade_score"]
            )

            if final_score >= min_score:
                final_results.append({
                    "doc_id": doc_id,
                    "score": final_score,
                    "bm25_score": scores["bm25_score"],
                    "splade_score": scores["splade_score"],
                    "document": scores["document"]
                })

        # Sort by final score
        final_results.sort(key=lambda x: x["score"], reverse=True)

        # Convert to SearchResult objects
        results = []
        for rank, item in enumerate(final_results[:top_k], 1):
            result = SearchResult(
                doc_id=item["doc_id"],
                score=item["score"],
                document=item["document"],
                rank=rank
            )
            results.append(result)

        return results

    def _normalize_scores(self, results: List[SearchResult]) -> Dict[str, float]:
        """
        Normalize scores to [0, 1] range.

        Args:
            results: List of search results

        Returns:
            Dict mapping doc_id to normalized score
        """
        if not results:
            return {}

        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return {r.doc_id: 1.0 for r in results}

        normalized = {}
        for result in results:
            norm_score = (result.score - min_score) / (max_score - min_score)
            normalized[result.doc_id] = norm_score

        return normalized

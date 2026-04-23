"""
Advanced retrieval algorithms and enhancements.

Provides query expansion, reranking, and filtering capabilities.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import re

from .bm25_retriever import BM25Retriever, SearchResult
from .tokenizer import Tokenizer


class QueryExpander:
    """Expand queries with synonyms and related terms."""

    def __init__(self):
        # Domain-specific synonym dictionary
        self.synonyms = {
            # Storage terms
            "ssd": ["固态硬盘", "固态盘", "闪存盘"],
            "固态硬盘": ["ssd", "固态盘"],
            "hdd": ["机械硬盘", "硬盘"],
            "机械硬盘": ["hdd", "硬盘"],

            # NVMe terms
            "nvme": ["非易失性存储", "nvm express"],
            "pcie": ["pci express", "pci-e"],

            # Error terms
            "bsod": ["蓝屏", "蓝屏死机", "系统崩溃"],
            "蓝屏": ["bsod", "蓝屏死机"],
            "黑屏": ["no display", "blank screen", "显示器无信号"],
            "死机": ["hang", "freeze", "卡死"],
            "崩溃": ["crash", "系统崩溃"],

            # Firmware terms
            "固件": ["firmware", "fw"],
            "firmware": ["固件", "fw"],
            "驱动": ["driver", "驱动程序"],
            "driver": ["驱动", "驱动程序"],

            # Performance terms
            "性能": ["performance", "速度"],
            "performance": ["性能", "速度"],
            "延迟": ["latency", "时延"],
            "latency": ["延迟", "时延"],
            "吞吐量": ["throughput", "带宽"],
            "throughput": ["吞吐量", "带宽"],
        }

    def expand(self, query: str, max_expansions: int = 3) -> str:
        """
        Expand query with synonyms.

        Args:
            query: Original query
            max_expansions: Maximum number of synonyms to add per term

        Returns:
            Expanded query
        """
        # Tokenize query (simple split for now)
        tokens = query.lower().split()

        expanded_tokens = []
        for token in tokens:
            expanded_tokens.append(token)

            # Add synonyms
            if token in self.synonyms:
                synonyms = self.synonyms[token][:max_expansions]
                expanded_tokens.extend(synonyms)

        return " ".join(expanded_tokens)

    def add_synonym(self, term: str, synonyms: List[str]):
        """
        Add a synonym mapping.

        Args:
            term: Original term
            synonyms: List of synonyms
        """
        if term not in self.synonyms:
            self.synonyms[term] = []
        self.synonyms[term].extend(synonyms)


class QueryRewriter:
    """Rewrite queries to improve retrieval quality."""

    def __init__(self):
        # Common typos and corrections
        self.corrections = {
            "nvem": "nvme",
            "pci-e": "pcie",
            "固建": "固件",
            "驱动程序": "驱动",
        }

    def rewrite(self, query: str) -> str:
        """
        Rewrite query with corrections.

        Args:
            query: Original query

        Returns:
            Rewritten query
        """
        # Apply corrections
        for typo, correction in self.corrections.items():
            query = query.replace(typo, correction)

        # Normalize whitespace
        query = " ".join(query.split())

        return query

    def add_correction(self, typo: str, correction: str):
        """
        Add a typo correction.

        Args:
            typo: Typo to correct
            correction: Correct form
        """
        self.corrections[typo] = correction


class ResultReranker:
    """Rerank search results based on additional signals."""

    def __init__(self):
        # Document type priorities (higher = more important)
        self.type_priorities = {
            "spec": 1.2,      # Specifications are authoritative
            "policy": 1.1,    # Policies are important
            "jira": 1.0,      # Issues are relevant
            "confluence": 0.9, # Wiki pages are helpful
            "pdf": 1.15,      # PDFs often contain detailed info
        }

    def rerank(
        self,
        results: List[SearchResult],
        query: str,
        boost_recent: bool = True,
        boost_by_type: bool = True
    ) -> List[SearchResult]:
        """
        Rerank search results.

        Args:
            results: Original search results
            query: Search query
            boost_recent: Whether to boost recent documents
            boost_by_type: Whether to boost by document type

        Returns:
            Reranked results
        """
        if not results:
            return results

        # Calculate boosted scores
        boosted_results = []
        for result in results:
            score = result.score

            # Boost by document type
            if boost_by_type:
                doc_type = result.document.get("metadata", {}).get("document_type", "")
                if doc_type in self.type_priorities:
                    score *= self.type_priorities[doc_type]

            # Boost by title match
            title = result.document.get("title", "").lower()
            if query.lower() in title:
                score *= 1.3  # Strong boost for title matches

            # Create new result with boosted score
            boosted_result = SearchResult(
                doc_id=result.doc_id,
                score=score,
                document=result.document,
                rank=result.rank
            )
            boosted_results.append(boosted_result)

        # Sort by boosted score
        boosted_results.sort(key=lambda x: x.score, reverse=True)

        # Update ranks
        for i, result in enumerate(boosted_results):
            result.rank = i + 1

        return boosted_results

    def set_type_priority(self, doc_type: str, priority: float):
        """
        Set priority for a document type.

        Args:
            doc_type: Document type
            priority: Priority multiplier (1.0 = neutral)
        """
        self.type_priorities[doc_type] = priority


class ResultFilter:
    """Filter low-quality search results."""

    def __init__(
        self,
        min_content_length: int = 50,
        max_duplicate_ratio: float = 0.8
    ):
        """
        Initialize filter.

        Args:
            min_content_length: Minimum content length
            max_duplicate_ratio: Maximum ratio of duplicate content
        """
        self.min_content_length = min_content_length
        self.max_duplicate_ratio = max_duplicate_ratio

    def filter(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Filter low-quality results.

        Args:
            results: Search results

        Returns:
            Filtered results
        """
        filtered = []
        seen_content = []

        for result in results:
            # Filter by content length
            content = result.document.get("content", "")
            if len(content) < self.min_content_length:
                continue

            # Filter duplicates
            if self._is_duplicate(content, seen_content):
                continue

            filtered.append(result)
            seen_content.append(content)

        # Update ranks
        for i, result in enumerate(filtered):
            result.rank = i + 1

        return filtered

    def _is_duplicate(self, content: str, seen_content: List[str]) -> bool:
        """
        Check if content is duplicate.

        Args:
            content: Content to check
            seen_content: List of seen content

        Returns:
            True if duplicate
        """
        if not seen_content:
            return False

        # Simple character-level similarity
        for seen in seen_content:
            # Calculate Jaccard similarity
            set1 = set(content.lower())
            set2 = set(seen.lower())

            if not set1 or not set2:
                continue

            intersection = len(set1 & set2)
            union = len(set1 | set2)

            similarity = intersection / union if union > 0 else 0

            if similarity > self.max_duplicate_ratio:
                return True

        return False


class EnhancedRetriever:
    """Enhanced retriever with query expansion, reranking, and filtering."""

    def __init__(
        self,
        base_retriever: BM25Retriever,
        enable_expansion: bool = True,
        enable_reranking: bool = True,
        enable_filtering: bool = True
    ):
        """
        Initialize enhanced retriever.

        Args:
            base_retriever: Base BM25 retriever
            enable_expansion: Enable query expansion
            enable_reranking: Enable result reranking
            enable_filtering: Enable result filtering
        """
        self.base_retriever = base_retriever
        self.enable_expansion = enable_expansion
        self.enable_reranking = enable_reranking
        self.enable_filtering = enable_filtering

        # Initialize components
        self.query_expander = QueryExpander()
        self.query_rewriter = QueryRewriter()
        self.result_reranker = ResultReranker()
        self.result_filter = ResultFilter()

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        document_types: Optional[List[str]] = None,
        expand_query: Optional[bool] = None,
        rerank_results: Optional[bool] = None,
        filter_results: Optional[bool] = None
    ) -> List[SearchResult]:
        """
        Enhanced search with query expansion, reranking, and filtering.

        Args:
            query: Search query
            top_k: Number of results to return
            min_score: Minimum score threshold
            document_types: Optional document type filter
            expand_query: Override expansion setting
            rerank_results: Override reranking setting
            filter_results: Override filtering setting

        Returns:
            Enhanced search results
        """
        # Determine which enhancements to apply
        do_expansion = expand_query if expand_query is not None else self.enable_expansion
        do_reranking = rerank_results if rerank_results is not None else self.enable_reranking
        do_filtering = filter_results if filter_results is not None else self.enable_filtering

        # Step 1: Query rewriting (always enabled)
        processed_query = self.query_rewriter.rewrite(query)

        # Step 2: Query expansion
        if do_expansion:
            processed_query = self.query_expander.expand(processed_query)

        # Step 3: Base retrieval (retrieve more for reranking/filtering)
        retrieve_k = top_k * 3 if (do_reranking or do_filtering) else top_k
        results = self.base_retriever.search(
            processed_query,
            top_k=retrieve_k,
            min_score=min_score,
            document_types=document_types
        )

        # Step 4: Result filtering
        if do_filtering:
            results = self.result_filter.filter(results)

        # Step 5: Result reranking
        if do_reranking:
            results = self.result_reranker.rerank(results, query)

        # Step 6: Return top-k
        return results[:top_k]

    def get_query_expander(self) -> QueryExpander:
        """Get query expander for customization."""
        return self.query_expander

    def get_query_rewriter(self) -> QueryRewriter:
        """Get query rewriter for customization."""
        return self.query_rewriter

    def get_result_reranker(self) -> ResultReranker:
        """Get result reranker for customization."""
        return self.result_reranker

    def get_result_filter(self) -> ResultFilter:
        """Get result filter for customization."""
        return self.result_filter

"""
Retrieval API for Portal Runner.

Provides search and index management functionality.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from packages.retrieval.bm25_retriever import BM25Retriever
from packages.retrieval.index_manager import IndexManager
from packages.retrieval.golden_dataset import load_golden_dataset
from packages.retrieval.evaluator import RetrievalEvaluator
from packages.retrieval.evaluation_manager import EvaluationManager, DatasetInfo, EvaluationRun
from packages.retrieval.debug_tools import QueryAnalyzer, ScoreExplainer, RelevanceAnnotator, ABTestComparator
from packages.retrieval.enhanced_retrieval import EnhancedRetriever
from packages.retrieval.splade_retriever import SPLADERetriever, HybridRetriever


class RetrievalAPI:
    """
    API layer for retrieval and search functionality.
    """

    def __init__(self, workspace_dir: str | Path, storage_dir: str | Path | None = None):
        """
        Initialize Retrieval API.

        Args:
            workspace_dir: Path to workspace directory
            storage_dir: Path to evaluation storage directory (defaults to .local/retrieval)
        """
        self.workspace_dir = Path(workspace_dir)

        # Database path
        db_path = self.workspace_dir / "documents.db"

        # Index directory
        index_dir = self.workspace_dir / ".index"

        # Initialize index manager
        self.index_manager = IndexManager(
            db_path=str(db_path),
            index_dir=str(index_dir),
        )

        # Load index if exists
        self.index_manager.load_index()

        # Initialize evaluation manager
        if storage_dir is None:
            storage_dir = Path(".local/retrieval")
        self.eval_manager = EvaluationManager(storage_dir)

        # Initialize debug tools
        from packages.retrieval.tokenizer import Tokenizer
        self.tokenizer = Tokenizer()
        self.query_analyzer = QueryAnalyzer(self.tokenizer)
        self.relevance_annotator = RelevanceAnnotator(str(storage_dir / "annotations.json"))

        # Initialize enhanced retriever (lazy initialization)
        self._enhanced_retriever = None

        # Initialize SPLADE retriever (lazy initialization)
        self._splade_retriever = None

        # Initialize hybrid retriever (lazy initialization)
        self._hybrid_retriever = None

    def _get_enhanced_retriever(self) -> EnhancedRetriever:
        """Get or create enhanced retriever."""
        if self._enhanced_retriever is None:
            base_retriever = BM25Retriever(self.index_manager.index)
            self._enhanced_retriever = EnhancedRetriever(base_retriever)
        return self._enhanced_retriever

    def _get_splade_retriever(self) -> SPLADERetriever:
        """Get or create SPLADE retriever."""
        if self._splade_retriever is None:
            self._splade_retriever = SPLADERetriever(
                tokenizer=self.tokenizer,
                use_idf=True,
                expansion_terms=10,
                alpha=0.5
            )
            # Build SPLADE index from existing documents
            self._build_splade_index()
        return self._splade_retriever

    def _get_hybrid_retriever(self) -> HybridRetriever:
        """Get or create hybrid retriever."""
        if self._hybrid_retriever is None:
            bm25_retriever = BM25Retriever(self.index_manager.index)
            splade_retriever = self._get_splade_retriever()
            self._hybrid_retriever = HybridRetriever(
                bm25_retriever=bm25_retriever,
                splade_retriever=splade_retriever,
                bm25_weight=0.5,
                splade_weight=0.5
            )
        return self._hybrid_retriever

    def _build_splade_index(self):
        """Build SPLADE index from database documents."""
        if self._splade_retriever is None:
            return

        # Get all documents from database
        all_docs = self.index_manager.db.list_documents(limit=10000)

        # Convert to SPLADE format
        splade_docs = []
        for doc in all_docs:
            splade_docs.append({
                "id": doc.id,
                "content": f"{doc.title} {doc.content}"
            })

        # Build SPLADE index
        if splade_docs:
            self._splade_retriever.build_index(splade_docs)

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        document_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Execute search query.

        Args:
            query: Search query text
            top_k: Number of results to return
            min_score: Minimum relevance score
            document_types: Optional list of document types to filter by

        Returns:
            Search results with metadata
        """
        # Check if index exists
        if self.index_manager.index.bm25 is None:
            return {
                "status": "error",
                "error": "Index not built. Please build index first.",
                "results": [],
            }

        # Create retriever
        retriever = BM25Retriever(self.index_manager.index)

        # Execute search with document type filtering
        results = retriever.search(
            query,
            top_k=top_k,
            min_score=min_score,
            document_types=document_types
        )

        # Get document details from database
        result_list = []
        for result in results:
            doc = self.index_manager.db.get_document(result.doc_id)
            if doc:
                import json
                metadata = json.loads(doc.metadata_json) if doc.metadata_json else {}
                result_list.append({
                    "doc_id": result.doc_id,
                    "score": result.score,
                    "rank": result.rank,
                    "title": doc.title,
                    "content": doc.content[:500],  # First 500 chars
                    "source_id": doc.source_id,
                    "source_type": doc.source_type,
                    "url": doc.url,
                    "metadata": metadata,
                })

        return {
            "status": "success",
            "query": query,
            "total_results": len(result_list),
            "results": result_list,
        }

    def get_index_stats(self) -> dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Index statistics
        """
        stats = self.index_manager.get_stats()

        return {
            "status": "success",
            "stats": stats,
        }

    def build_index(self, batch_size: int = 1000) -> dict[str, Any]:
        """
        Build full index from database.

        Args:
            batch_size: Batch size for processing

        Returns:
            Build result
        """
        try:
            result = self.index_manager.build_full_index(batch_size=batch_size)
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def update_index(self) -> dict[str, Any]:
        """
        Update index incrementally.

        Returns:
            Update result
        """
        try:
            result = self.index_manager.update_index_incremental()
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def rebuild_index(self) -> dict[str, Any]:
        """
        Rebuild index from scratch.

        Returns:
            Rebuild result
        """
        try:
            result = self.index_manager.rebuild_index()
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def health_check(self) -> dict[str, Any]:
        """
        Check index health.

        Returns:
            Health check result
        """
        health = self.index_manager.health_check()

        return {
            "status": "success",
            "health": health,
        }

    def evaluate(
        self,
        golden_dataset_path: str = "data/golden_dataset.yaml",
        top_k: int = 10,
        save_result: bool = True,
    ) -> dict[str, Any]:
        """
        Run evaluation on golden dataset.

        Args:
            golden_dataset_path: Path to golden dataset
            top_k: Number of results to retrieve
            save_result: Whether to save the evaluation result

        Returns:
            Evaluation results
        """
        try:
            # Load golden dataset
            golden_dataset = load_golden_dataset(golden_dataset_path)

            # Create retriever
            retriever = BM25Retriever(self.index_manager.index)

            # Create evaluator
            evaluator = RetrievalEvaluator(retriever, golden_dataset)

            # Run evaluation
            results, aggregate = evaluator.evaluate_all(top_k=top_k)

            # Save result if requested
            run_id = None
            if save_result:
                # Extract dataset_id from path
                dataset_id = Path(golden_dataset_path).stem
                run = self.eval_manager.save_evaluation_result(
                    dataset_id=dataset_id,
                    dataset_name=golden_dataset.name,
                    top_k=top_k,
                    aggregate_metrics=aggregate,
                    per_query_results=results,
                )
                run_id = run.run_id

            # Format results
            return {
                "status": "success",
                "run_id": run_id,
                "aggregate_metrics": {
                    "total_queries": aggregate.total_queries,
                    "mean_average_precision": aggregate.mean_average_precision,
                    "mean_reciprocal_rank": aggregate.mean_reciprocal_rank,
                    "mean_ndcg_at_5": aggregate.mean_ndcg_at_5,
                    "mean_ndcg_at_10": aggregate.mean_ndcg_at_10,
                    "mean_precision_at_1": aggregate.mean_precision_at_1,
                    "mean_precision_at_3": aggregate.mean_precision_at_3,
                    "mean_precision_at_5": aggregate.mean_precision_at_5,
                    "mean_precision_at_10": aggregate.mean_precision_at_10,
                    "mean_recall_at_1": aggregate.mean_recall_at_1,
                    "mean_recall_at_3": aggregate.mean_recall_at_3,
                    "mean_recall_at_5": aggregate.mean_recall_at_5,
                    "mean_recall_at_10": aggregate.mean_recall_at_10,
                },
                "per_query_results": [
                    {
                        "query_id": r.query_id,
                        "query_text": r.query_text,
                        "average_precision": r.average_precision,
                        "reciprocal_rank": r.reciprocal_rank,
                        "ndcg_at_5": r.ndcg_at_5,
                        "precision_at_5": r.precision_at_5,
                        "recall_at_5": r.recall_at_5,
                    }
                    for r in results
                ],
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    # ==================== Dataset Management ====================

    def upload_dataset(self, dataset_content: str, dataset_id: str | None = None) -> dict[str, Any]:
        """
        Upload a golden dataset.

        Args:
            dataset_content: YAML content of the dataset
            dataset_id: Optional dataset ID

        Returns:
            Dataset information
        """
        try:
            info = self.eval_manager.upload_dataset(dataset_content, dataset_id)
            return {
                "status": "success",
                "dataset": {
                    "dataset_id": info.dataset_id,
                    "name": info.name,
                    "description": info.description,
                    "version": info.version,
                    "created_at": info.created_at,
                    "updated_at": info.updated_at,
                    "total_queries": info.total_queries,
                    "total_documents": info.total_documents,
                    "categories": info.categories,
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def list_datasets(self) -> dict[str, Any]:
        """
        List all available datasets.

        Returns:
            List of datasets
        """
        try:
            datasets = self.eval_manager.list_datasets()
            return {
                "status": "success",
                "datasets": [
                    {
                        "dataset_id": d.dataset_id,
                        "name": d.name,
                        "description": d.description,
                        "version": d.version,
                        "created_at": d.created_at,
                        "updated_at": d.updated_at,
                        "total_queries": d.total_queries,
                        "total_documents": d.total_documents,
                        "categories": d.categories,
                    }
                    for d in datasets
                ],
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        """
        Get dataset information and content.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset information and content
        """
        try:
            info = self.eval_manager.get_dataset(dataset_id)
            content = self.eval_manager.get_dataset_content(dataset_id)
            return {
                "status": "success",
                "dataset": {
                    "dataset_id": info.dataset_id,
                    "name": info.name,
                    "description": info.description,
                    "version": info.version,
                    "created_at": info.created_at,
                    "updated_at": info.updated_at,
                    "total_queries": info.total_queries,
                    "total_documents": info.total_documents,
                    "categories": info.categories,
                },
                "content": content,
            }
        except FileNotFoundError as e:
            return {
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def delete_dataset(self, dataset_id: str) -> dict[str, Any]:
        """
        Delete a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            Success status
        """
        try:
            self.eval_manager.delete_dataset(dataset_id)
            return {
                "status": "success",
                "message": f"Dataset {dataset_id} deleted",
            }
        except FileNotFoundError as e:
            return {
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    # ==================== Evaluation Results Management ====================

    def list_evaluation_results(
        self,
        dataset_id: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        List evaluation results.

        Args:
            dataset_id: Optional filter by dataset ID
            limit: Optional limit number of results

        Returns:
            List of evaluation results
        """
        try:
            results = self.eval_manager.list_evaluation_results(dataset_id, limit)
            return {
                "status": "success",
                "results": [
                    {
                        "run_id": r.run_id,
                        "dataset_id": r.dataset_id,
                        "dataset_name": r.dataset_name,
                        "timestamp": r.timestamp,
                        "top_k": r.top_k,
                        "total_queries": r.total_queries,
                        "aggregate_metrics": r.aggregate_metrics,
                    }
                    for r in results
                ],
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_evaluation_result(self, run_id: str) -> dict[str, Any]:
        """
        Get detailed evaluation result.

        Args:
            run_id: Run ID

        Returns:
            Evaluation result
        """
        try:
            run = self.eval_manager.get_evaluation_result(run_id)
            return {
                "status": "success",
                "result": {
                    "run_id": run.run_id,
                    "dataset_id": run.dataset_id,
                    "dataset_name": run.dataset_name,
                    "timestamp": run.timestamp,
                    "top_k": run.top_k,
                    "total_queries": run.total_queries,
                    "aggregate_metrics": run.aggregate_metrics,
                    "per_query_results": run.per_query_results,
                    "config": run.config,
                },
            }
        except FileNotFoundError as e:
            return {
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def delete_evaluation_result(self, run_id: str) -> dict[str, Any]:
        """
        Delete evaluation result.

        Args:
            run_id: Run ID

        Returns:
            Success status
        """
        try:
            self.eval_manager.delete_evaluation_result(run_id)
            return {
                "status": "success",
                "message": f"Evaluation result {run_id} deleted",
            }
        except FileNotFoundError as e:
            return {
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def compare_evaluation_results(self, run_ids: list[str]) -> dict[str, Any]:
        """
        Compare multiple evaluation results.

        Args:
            run_ids: List of run IDs

        Returns:
            Comparison data
        """
        try:
            comparison = self.eval_manager.compare_evaluation_results(run_ids)
            return {
                "status": "success",
                "comparison": comparison,
            }
        except FileNotFoundError as e:
            return {
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    # ==================== Debug Tools ====================

    def analyze_query(self, query: str) -> dict[str, Any]:
        """
        Analyze query tokenization and statistics.

        Args:
            query: Search query

        Returns:
            Query analysis
        """
        try:
            analysis = self.query_analyzer.analyze(query)
            return {
                "status": "success",
                "analysis": analysis,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def explain_score(self, query: str, doc_id: str) -> dict[str, Any]:
        """
        Explain BM25 score for a specific document.

        Args:
            query: Search query
            doc_id: Document ID

        Returns:
            Score explanation
        """
        try:
            retriever = BM25Retriever(self.index_manager.index)
            explainer = ScoreExplainer(retriever)
            explanation = explainer.explain_score(query, doc_id)
            return {
                "status": "success",
                "explanation": explanation,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def compare_document_scores(self, query: str, doc_ids: list[str]) -> dict[str, Any]:
        """
        Compare BM25 scores across multiple documents.

        Args:
            query: Search query
            doc_ids: List of document IDs

        Returns:
            Score comparison
        """
        try:
            retriever = BM25Retriever(self.index_manager.index)
            explainer = ScoreExplainer(retriever)
            comparison = explainer.compare_documents(query, doc_ids)
            return {
                "status": "success",
                "comparison": comparison,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def annotate_relevance(
        self,
        query: str,
        doc_id: str,
        relevance: int,
        notes: str = ""
    ) -> dict[str, Any]:
        """
        Annotate document relevance for a query.

        Args:
            query: Search query
            doc_id: Document ID
            relevance: Relevance score (0-3)
            notes: Optional notes

        Returns:
            Annotation record
        """
        try:
            annotation = self.relevance_annotator.annotate(query, doc_id, relevance, notes)
            return {
                "status": "success",
                "annotation": annotation,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_relevance_annotations(
        self,
        query: str | None = None,
        doc_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get relevance annotations.

        Args:
            query: Optional query filter
            doc_id: Optional doc_id filter

        Returns:
            List of annotations
        """
        try:
            annotations = self.relevance_annotator.get_annotations(query, doc_id)
            return {
                "status": "success",
                "annotations": annotations,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_relevance_stats(self, query: str) -> dict[str, Any]:
        """
        Get relevance statistics for a query.

        Args:
            query: Search query

        Returns:
            Relevance statistics
        """
        try:
            stats = self.relevance_annotator.get_relevance_stats(query)
            return {
                "status": "success",
                "stats": stats,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    # ==================== Enhanced Retrieval ====================

    def enhanced_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        document_types: list[str] | None = None,
        enable_expansion: bool = True,
        enable_reranking: bool = True,
        enable_filtering: bool = True
    ) -> dict[str, Any]:
        """
        Execute enhanced search with query expansion, reranking, and filtering.

        Args:
            query: Search query text
            top_k: Number of results to return
            min_score: Minimum relevance score
            document_types: Optional list of document types to filter by
            enable_expansion: Enable query expansion
            enable_reranking: Enable result reranking
            enable_filtering: Enable result filtering

        Returns:
            Enhanced search results
        """
        # Check if index exists
        if self.index_manager.index.bm25 is None:
            return {
                "status": "error",
                "error": "Index not built. Please build index first.",
                "results": [],
            }

        try:
            # Get enhanced retriever
            enhanced_retriever = self._get_enhanced_retriever()

            # Execute enhanced search
            results = enhanced_retriever.search(
                query,
                top_k=top_k,
                min_score=min_score,
                document_types=document_types,
                expand_query=enable_expansion,
                rerank_results=enable_reranking,
                filter_results=enable_filtering
            )

            # Get document details from database
            result_list = []
            for result in results:
                doc = self.index_manager.db.get_document(result.doc_id)
                if doc:
                    import json
                    metadata = json.loads(doc.metadata_json) if doc.metadata_json else {}
                    result_list.append({
                        "doc_id": result.doc_id,
                        "score": result.score,
                        "rank": result.rank,
                        "title": doc.title,
                        "content": doc.content[:500],  # First 500 chars
                        "source_id": doc.source_id,
                        "source_type": doc.source_type,
                        "url": doc.url,
                        "metadata": metadata,
                    })

            return {
                "status": "success",
                "query": query,
                "total_results": len(result_list),
                "enhancements": {
                    "expansion": enable_expansion,
                    "reranking": enable_reranking,
                    "filtering": enable_filtering,
                },
                "results": result_list,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def splade_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        enable_expansion: bool = True
    ) -> dict[str, Any]:
        """
        Execute SPLADE sparse vector search.

        Args:
            query: Search query text
            top_k: Number of results to return
            min_score: Minimum relevance score
            enable_expansion: Enable query expansion

        Returns:
            SPLADE search results
        """
        # Check if index exists
        if self.index_manager.index.bm25 is None:
            return {
                "status": "error",
                "error": "Index not built. Please build index first.",
                "results": [],
            }

        try:
            # Get SPLADE retriever
            splade_retriever = self._get_splade_retriever()

            # Execute SPLADE search
            results = splade_retriever.search(
                query,
                top_k=top_k,
                min_score=min_score,
                enable_expansion=enable_expansion
            )

            # Get document details from database
            result_list = []
            for result in results:
                doc = self.index_manager.db.get_document(result.doc_id)
                if doc:
                    import json
                    metadata = json.loads(doc.metadata_json) if doc.metadata_json else {}
                    result_list.append({
                        "doc_id": result.doc_id,
                        "score": result.score,
                        "rank": result.rank,
                        "title": doc.title,
                        "content": doc.content[:500],
                        "source_id": doc.source_id,
                        "source_type": doc.source_type,
                        "url": doc.url,
                        "metadata": metadata,
                    })

            # Get query expansion terms
            expansion_terms = []
            if enable_expansion:
                expansion_terms = splade_retriever.get_query_expansion(query)[:5]

            return {
                "status": "success",
                "query": query,
                "total_results": len(result_list),
                "retrieval_method": "splade",
                "expansion_enabled": enable_expansion,
                "expansion_terms": [{"term": t, "weight": float(w)} for t, w in expansion_terms],
                "results": result_list,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        bm25_weight: float = 0.5,
        splade_weight: float = 0.5
    ) -> dict[str, Any]:
        """
        Execute hybrid search combining BM25 and SPLADE.

        Args:
            query: Search query text
            top_k: Number of results to return
            min_score: Minimum relevance score
            bm25_weight: Weight for BM25 scores (0-1)
            splade_weight: Weight for SPLADE scores (0-1)

        Returns:
            Hybrid search results
        """
        # Check if index exists
        if self.index_manager.index.bm25 is None:
            return {
                "status": "error",
                "error": "Index not built. Please build index first.",
                "results": [],
            }

        try:
            # Get hybrid retriever
            hybrid_retriever = self._get_hybrid_retriever()

            # Update weights if provided
            hybrid_retriever.bm25_weight = bm25_weight
            hybrid_retriever.splade_weight = splade_weight

            # Execute hybrid search
            results = hybrid_retriever.search(
                query,
                top_k=top_k,
                min_score=min_score
            )

            # Get document details from database
            result_list = []
            for result in results:
                doc = self.index_manager.db.get_document(result.doc_id)
                if doc:
                    import json
                    metadata = json.loads(doc.metadata_json) if doc.metadata_json else {}
                    result_list.append({
                        "doc_id": result.doc_id,
                        "score": result.score,
                        "rank": result.rank,
                        "title": doc.title,
                        "content": doc.content[:500],
                        "source_id": doc.source_id,
                        "source_type": doc.source_type,
                        "url": doc.url,
                        "metadata": metadata,
                    })

            return {
                "status": "success",
                "query": query,
                "total_results": len(result_list),
                "retrieval_method": "hybrid",
                "weights": {
                    "bm25": bm25_weight,
                    "splade": splade_weight
                },
                "results": result_list,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def add_synonym(self, term: str, synonyms: list[str]) -> dict[str, Any]:
        """
        Add synonym mapping for query expansion.

        Args:
            term: Original term
            synonyms: List of synonyms

        Returns:
            Success status
        """
        try:
            enhanced_retriever = self._get_enhanced_retriever()
            expander = enhanced_retriever.get_query_expander()
            expander.add_synonym(term, synonyms)
            return {
                "status": "success",
                "message": f"Added {len(synonyms)} synonyms for '{term}'",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def add_typo_correction(self, typo: str, correction: str) -> dict[str, Any]:
        """
        Add typo correction for query rewriting.

        Args:
            typo: Typo to correct
            correction: Correct form

        Returns:
            Success status
        """
        try:
            enhanced_retriever = self._get_enhanced_retriever()
            rewriter = enhanced_retriever.get_query_rewriter()
            rewriter.add_correction(typo, correction)
            return {
                "status": "success",
                "message": f"Added correction: '{typo}' -> '{correction}'",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def set_document_type_priority(self, doc_type: str, priority: float) -> dict[str, Any]:
        """
        Set priority for a document type in reranking.

        Args:
            doc_type: Document type
            priority: Priority multiplier (1.0 = neutral)

        Returns:
            Success status
        """
        try:
            enhanced_retriever = self._get_enhanced_retriever()
            reranker = enhanced_retriever.get_result_reranker()
            reranker.set_type_priority(doc_type, priority)
            return {
                "status": "success",
                "message": f"Set priority for '{doc_type}' to {priority}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    # ==================== Debug and Comparison ====================

    def debug_search(
        self,
        query: str,
        strategy: str = "hybrid",
        top_k: int = 5
    ) -> dict[str, Any]:
        """
        Execute search with debug information.

        Args:
            query: Search query text
            strategy: Retrieval strategy (hybrid, semantic, keyword, splade)
            top_k: Number of results to return

        Returns:
            Search results with debug information
        """
        import time

        # Check if index exists
        if self.index_manager.index.bm25 is None:
            return {
                "status": "error",
                "error": "Index not built. Please build index first.",
                "results": [],
            }

        try:
            start_time = time.time()

            # Execute search based on strategy
            if strategy == "hybrid":
                result = self.hybrid_search(query, top_k=top_k)
            elif strategy == "semantic":
                result = self.enhanced_search(
                    query, top_k=top_k,
                    enable_expansion=True,
                    enable_reranking=True,
                    enable_filtering=False
                )
            elif strategy == "keyword":
                result = self.search(query, top_k=top_k)
            elif strategy == "splade":
                result = self.splade_search(query, top_k=top_k)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown strategy: {strategy}",
                }

            retrieval_time_ms = (time.time() - start_time) * 1000

            # Get total document count
            stats = self.index_manager.get_stats()
            total_docs = stats.get("total_documents", 0)

            # Format results with full content and metadata
            results = []
            if result["status"] == "success":
                for doc in result.get("results", []):
                    # Get full document content
                    full_doc = self.index_manager.db.get_document(doc["doc_id"])
                    if full_doc:
                        results.append({
                            "doc_id": doc["doc_id"],
                            "content": full_doc.content,  # Full content
                            "score": doc["score"],
                            "metadata": doc.get("metadata", {})
                        })

            return {
                "status": "success",
                "query": query,
                "results": results,
                "debug_info": {
                    "strategy": strategy,
                    "retrieval_time_ms": retrieval_time_ms,
                    "total_docs": total_docs,
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def compare_strategies(
        self,
        query: str,
        strategies: list[str],
        top_k: int = 5
    ) -> dict[str, Any]:
        """
        Compare multiple retrieval strategies.

        Args:
            query: Search query text
            strategies: List of strategies to compare
            top_k: Number of results per strategy

        Returns:
            Comparison results
        """
        import time

        # Check if index exists
        if self.index_manager.index.bm25 is None:
            return {
                "status": "error",
                "error": "Index not built. Please build index first.",
            }

        # Validate strategies count
        if len(strategies) < 1:
            return {
                "status": "error",
                "error": "At least one strategy is required",
            }

        try:
            strategy_results = []

            # Execute each strategy
            for strategy in strategies:
                start_time = time.time()

                # Execute search
                if strategy == "hybrid":
                    result = self.hybrid_search(query, top_k=top_k)
                elif strategy == "semantic":
                    result = self.enhanced_search(
                        query, top_k=top_k,
                        enable_expansion=True,
                        enable_reranking=True,
                        enable_filtering=False
                    )
                elif strategy == "keyword":
                    result = self.search(query, top_k=top_k)
                elif strategy == "splade":
                    result = self.splade_search(query, top_k=top_k)
                else:
                    continue

                retrieval_time_ms = (time.time() - start_time) * 1000

                # Format results
                results = []
                if result["status"] == "success":
                    for doc in result.get("results", []):
                        results.append({
                            "doc_id": doc["doc_id"],
                            "content": doc["content"],
                            "score": doc["score"]
                        })

                strategy_results.append({
                    "strategy": strategy,
                    "results": results,
                    "metrics": {
                        "retrieval_time_ms": retrieval_time_ms,
                        "total_results": len(results)
                    }
                })

            # Calculate comparison metrics
            if len(strategy_results) >= 2:
                # Calculate overlap rate between first two strategies
                doc_ids_1 = set(r["doc_id"] for r in strategy_results[0]["results"])
                doc_ids_2 = set(r["doc_id"] for r in strategy_results[1]["results"])
                overlap = len(doc_ids_1 & doc_ids_2)
                total = len(doc_ids_1 | doc_ids_2)
                overlap_rate = overlap / total if total > 0 else 0.0

                # Calculate average score difference
                common_docs = doc_ids_1 & doc_ids_2
                score_diffs = []
                for doc_id in common_docs:
                    score_1 = next((r["score"] for r in strategy_results[0]["results"] if r["doc_id"] == doc_id), 0)
                    score_2 = next((r["score"] for r in strategy_results[1]["results"] if r["doc_id"] == doc_id), 0)
                    score_diffs.append(abs(score_1 - score_2))
                avg_score_diff = sum(score_diffs) / len(score_diffs) if score_diffs else 0.0
            else:
                overlap_rate = 0.0
                avg_score_diff = 0.0

            return {
                "status": "success",
                "query": query,
                "strategies": strategy_results,
                "comparison_metrics": {
                    "overlap_rate": overlap_rate,
                    "avg_score_diff": avg_score_diff
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

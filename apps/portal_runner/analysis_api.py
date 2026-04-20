"""Analysis API business logic for Portal Runner.

Provides deep analysis and daily report generation functionality.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.analysis.deep_analysis import build_deep_analysis_from_documents
from services.analysis.llm_backends import LLMBackend, build_llm_backend


class AnalysisAPI:
    """Business logic for analysis operations."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.knowledge_root = self.workspace_root / "knowledge"
        self.knowledge_root.mkdir(parents=True, exist_ok=True)

    def deep_analyze_issue(
        self,
        *,
        workspace_dir: str,
        issue_id: str,
        llm_backend: str = "none",
        llm_base_url: str | None = None,
        llm_model: str | None = None,
        prompt_mode: str = "strict",
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Perform deep analysis on a single Jira issue.

        Args:
            workspace_dir: Path to workspace directory
            issue_id: Jira issue ID (e.g., "SSD-777")
            llm_backend: LLM backend type ("none", "mock", "openai-compatible")
            llm_base_url: Base URL for LLM API
            llm_model: Model name for LLM
            prompt_mode: Prompt mode ("strict", "balanced", "exploratory")
            top_k: Number of top results to retrieve

        Returns:
            Deep analysis result with citations and recommendations
        """
        workspace_path = Path(workspace_dir)

        # Load workspace snapshot
        snapshot_dir = workspace_path / "snapshot"
        documents_file = snapshot_dir / "documents.json"

        if not documents_file.exists():
            raise ValueError(f"Workspace snapshot not found: {documents_file}")

        with open(documents_file, encoding="utf-8") as f:
            documents = json.load(f)

        # Create LLM backend if requested
        backend: LLMBackend | None = None
        if llm_backend != "none":
            backend = build_llm_backend(
                backend=llm_backend,
                base_url=llm_base_url,
                model=llm_model,
            )

        # Perform deep analysis
        allowed_policies = {"public", "internal"}
        result = build_deep_analysis_from_documents(
            documents=documents,
            issue_id=issue_id,
            allowed_policies=allowed_policies,
            top_k=top_k,
            prompt_mode=prompt_mode,
            llm_backend=backend,
        )

        # Save to knowledge base
        self._save_analysis_to_knowledge_base(
            workspace_dir=workspace_dir,
            issue_id=issue_id,
            analysis_result=result,
        )

        return result

    def _save_analysis_to_knowledge_base(
        self,
        *,
        workspace_dir: str,
        issue_id: str,
        analysis_result: dict[str, Any],
    ) -> None:
        """Save analysis result to knowledge base."""
        workspace_path = Path(workspace_dir)
        issue_dir = workspace_path / "knowledge" / "issues" / issue_id
        issue_dir.mkdir(parents=True, exist_ok=True)

        # Save analysis markdown
        analysis_md = issue_dir / "analysis.md"
        composite_report = analysis_result.get("composite_report", {})
        content = composite_report.get("content", "")

        with open(analysis_md, "w", encoding="utf-8") as f:
            f.write(content)

        # Save metadata
        metadata = {
            "issue_id": issue_id,
            "title": analysis_result.get("title", issue_id),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "analysis_profile": analysis_result.get("analysis_profile"),
            "citation_count": len(analysis_result.get("cross_source_citations", [])),
            "confluence_citations": len(analysis_result.get("confluence_evidence", {}).get("citations", [])),
            "spec_citations": len(analysis_result.get("spec_evidence", {}).get("citations", [])),
        }

        metadata_file = issue_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def get_analysis_result(
        self,
        *,
        workspace_dir: str,
        issue_id: str,
    ) -> dict[str, Any]:
        """Get saved analysis result from knowledge base.

        Args:
            workspace_dir: Path to workspace directory
            issue_id: Jira issue ID

        Returns:
            Analysis result with markdown content and metadata
        """
        workspace_path = Path(workspace_dir)
        issue_dir = workspace_path / "knowledge" / "issues" / issue_id

        if not issue_dir.exists():
            raise ValueError(f"Analysis not found for issue: {issue_id}")

        # Load analysis markdown
        analysis_md = issue_dir / "analysis.md"
        if not analysis_md.exists():
            raise ValueError(f"Analysis markdown not found: {analysis_md}")

        with open(analysis_md, encoding="utf-8") as f:
            content = f.read()

        # Load metadata
        metadata_file = issue_dir / "metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)

        return {
            "issue_id": issue_id,
            "content": content,
            "metadata": metadata,
        }

    def search_knowledge_base(
        self,
        *,
        workspace_dir: str,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search knowledge base for relevant analyses.

        Args:
            workspace_dir: Path to workspace directory
            query: Search query
            limit: Maximum number of results

        Returns:
            Search results with issue IDs and metadata
        """
        workspace_path = Path(workspace_dir)
        knowledge_dir = workspace_path / "knowledge" / "issues"

        if not knowledge_dir.exists():
            return {"query": query, "results": []}

        results = []
        for issue_dir in knowledge_dir.iterdir():
            if not issue_dir.is_dir():
                continue

            metadata_file = issue_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)

            # Simple keyword matching (can be improved with BM25)
            title = metadata.get("title", "").lower()
            issue_id = metadata.get("issue_id", "").lower()

            if query.lower() in title or query.lower() in issue_id:
                results.append({
                    "issue_id": metadata.get("issue_id"),
                    "title": metadata.get("title"),
                    "analyzed_at": metadata.get("analyzed_at"),
                    "citation_count": metadata.get("citation_count", 0),
                })

        # Sort by analyzed_at (most recent first)
        results.sort(key=lambda x: x.get("analyzed_at", ""), reverse=True)

        return {
            "query": query,
            "total": len(results),
            "results": results[:limit],
        }

    def generate_daily_report(
        self,
        *,
        workspace_dir: str,
        date: str | None = None,
        mode: str = "fast",
    ) -> dict[str, Any]:
        """Generate daily report from knowledge base.

        Args:
            workspace_dir: Path to workspace directory
            date: Report date (YYYY-MM-DD), defaults to today
            mode: Generation mode - "fast" (< 5s) or "full" (< 30s)

        Returns:
            Daily report with sections and metadata
        """
        workspace_path = Path(workspace_dir)
        knowledge_dir = workspace_path / "knowledge" / "issues"

        if not knowledge_dir.exists():
            return {
                "date": date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "mode": mode,
                "sections": [],
                "total_issues": 0,
            }

        # Get target date
        target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Collect all analyzed issues
        all_issues = []
        for issue_dir in knowledge_dir.iterdir():
            if not issue_dir.is_dir():
                continue

            metadata_file = issue_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            with open(metadata_file, encoding="utf-8") as f:
                metadata = json.load(f)

            all_issues.append({
                "issue_id": metadata.get("issue_id"),
                "title": metadata.get("title"),
                "analyzed_at": metadata.get("analyzed_at"),
                "citation_count": metadata.get("citation_count", 0),
                "analysis_profile": metadata.get("analysis_profile"),
            })

        # Sort by analyzed_at (most recent first)
        all_issues.sort(key=lambda x: x.get("analyzed_at", ""), reverse=True)

        # Generate report sections
        sections = []

        # Section 1: Summary
        sections.append({
            "title": "Summary",
            "content": f"Total analyzed issues: {len(all_issues)}",
            "order": 1,
        })

        # Section 2: Recent Analyses (fast mode: top 5, full mode: top 20)
        limit = 5 if mode == "fast" else 20
        recent_issues = all_issues[:limit]

        recent_content = []
        for issue in recent_issues:
            recent_content.append(
                f"- **{issue['issue_id']}**: {issue['title']} "
                f"({issue['citation_count']} citations)"
            )

        sections.append({
            "title": "Recent Analyses",
            "content": "\n".join(recent_content),
            "order": 2,
        })

        # Section 3: Top Issues by Citations (only in full mode)
        if mode == "full":
            top_issues = sorted(all_issues, key=lambda x: x.get("citation_count", 0), reverse=True)[:10]
            top_content = []
            for issue in top_issues:
                top_content.append(
                    f"- **{issue['issue_id']}**: {issue['title']} "
                    f"({issue['citation_count']} citations)"
                )

            sections.append({
                "title": "Top Issues by Citations",
                "content": "\n".join(top_content),
                "order": 3,
            })

        # Save report to knowledge base
        self._save_daily_report(
            workspace_dir=workspace_dir,
            date=target_date,
            sections=sections,
            metadata={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "mode": mode,
                "total_issues": len(all_issues),
            },
        )

        return {
            "date": target_date,
            "mode": mode,
            "sections": sections,
            "total_issues": len(all_issues),
        }

    def _save_daily_report(
        self,
        *,
        workspace_dir: str,
        date: str,
        sections: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> None:
        """Save daily report to knowledge base."""
        workspace_path = Path(workspace_dir)
        report_dir = workspace_path / "knowledge" / "reports" / "daily" / date
        report_dir.mkdir(parents=True, exist_ok=True)

        # Generate markdown content
        content_lines = [f"# Daily Report - {date}\n"]
        for section in sorted(sections, key=lambda x: x.get("order", 0)):
            content_lines.append(f"\n## {section['title']}\n")
            content_lines.append(section["content"])

        report_md = report_dir / "report.md"
        with open(report_md, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))

        # Save metadata
        metadata_file = report_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)


def deep_analyze_issue_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle deep analysis request.

    Args:
        payload: Request payload with workspace_dir, issue_id, etc.

    Returns:
        Deep analysis result
    """
    workspace_dir = payload.get("workspace_dir")
    if not workspace_dir:
        raise ValueError("workspace_dir is required")

    issue_id = payload.get("issue_id")
    if not issue_id:
        raise ValueError("issue_id is required")

    api = AnalysisAPI(workspace_root=Path(workspace_dir).parent)

    result = api.deep_analyze_issue(
        workspace_dir=workspace_dir,
        issue_id=issue_id,
        llm_backend=payload.get("llm_backend", "none"),
        llm_base_url=payload.get("llm_base_url"),
        llm_model=payload.get("llm_model"),
        prompt_mode=payload.get("prompt_mode", "strict"),
        top_k=payload.get("top_k", 5),
    )

    return {
        "status": "completed",
        "issue_id": issue_id,
        "result": result,
    }


def get_analysis_result_response(workspace_dir: str, issue_id: str) -> dict[str, Any]:
    """Get saved analysis result.

    Args:
        workspace_dir: Path to workspace directory
        issue_id: Jira issue ID

    Returns:
        Analysis result with content and metadata
    """
    api = AnalysisAPI(workspace_root=Path(workspace_dir).parent)
    return api.get_analysis_result(workspace_dir=workspace_dir, issue_id=issue_id)


def search_knowledge_base_response(workspace_dir: str, query: str, limit: int = 10) -> dict[str, Any]:
    """Search knowledge base.

    Args:
        workspace_dir: Path to workspace directory
        query: Search query
        limit: Maximum number of results

    Returns:
        Search results
    """
    api = AnalysisAPI(workspace_root=Path(workspace_dir).parent)
    return api.search_knowledge_base(workspace_dir=workspace_dir, query=query, limit=limit)


def generate_daily_report_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate daily report.

    Args:
        payload: Request payload with workspace_dir, date, mode

    Returns:
        Daily report with sections and metadata
    """
    workspace_dir = payload.get("workspace_dir")
    if not workspace_dir:
        raise ValueError("workspace_dir is required")

    api = AnalysisAPI(workspace_root=Path(workspace_dir).parent)

    return api.generate_daily_report(
        workspace_dir=workspace_dir,
        date=payload.get("date"),
        mode=payload.get("mode", "fast"),
    )


class BatchAnalysisAPI:
    """Business logic for batch analysis operations."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.batch_root = self.workspace_root / "knowledge" / "batches"
        self.batch_root.mkdir(parents=True, exist_ok=True)
        self.analysis_api = AnalysisAPI(workspace_root)

    async def batch_analyze_issues(
        self,
        *,
        workspace_dir: str,
        issue_ids: list[str],
        llm_backend: str = "none",
        llm_base_url: str | None = None,
        llm_model: str | None = None,
        prompt_mode: str = "strict",
        top_k: int = 5,
        max_concurrent: int = 3,
        progress_callback: callable | None = None,
    ) -> dict[str, Any]:
        """Perform batch deep analysis on multiple Jira issues.

        Args:
            workspace_dir: Path to workspace directory
            issue_ids: List of Jira issue IDs
            llm_backend: LLM backend type
            llm_base_url: Base URL for LLM API
            llm_model: Model name for LLM
            prompt_mode: Prompt mode
            top_k: Number of top results to retrieve
            max_concurrent: Maximum concurrent analyses
            progress_callback: Optional callback for progress updates

        Returns:
            Batch analysis result with individual results and summary
        """
        batch_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        results = []
        errors = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_one(issue_id: str, index: int) -> dict[str, Any]:
            async with semaphore:
                try:
                    if progress_callback:
                        await progress_callback(
                            batch_id=batch_id,
                            stage="analyzing",
                            progress=(index / len(issue_ids)) * 100,
                            message=f"Analyzing {issue_id}",
                        )

                    # Run synchronous analysis in thread pool
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: self.analysis_api.deep_analyze_issue(
                            workspace_dir=workspace_dir,
                            issue_id=issue_id,
                            llm_backend=llm_backend,
                            llm_base_url=llm_base_url,
                            llm_model=llm_model,
                            prompt_mode=prompt_mode,
                            top_k=top_k,
                        ),
                    )

                    return {
                        "issue_id": issue_id,
                        "status": "success",
                        "result": result,
                    }
                except Exception as exc:
                    return {
                        "issue_id": issue_id,
                        "status": "error",
                        "error": str(exc),
                    }

        # Analyze all issues concurrently
        tasks = [analyze_one(issue_id, i) for i, issue_id in enumerate(issue_ids)]
        results = await asyncio.gather(*tasks)

        # Separate successes and errors
        successes = [r for r in results if r["status"] == "success"]
        errors = [r for r in results if r["status"] == "error"]

        completed_at = datetime.now(timezone.utc)
        duration = (completed_at - started_at).total_seconds()

        # Save batch result
        batch_result = {
            "batch_id": batch_id,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": duration,
            "total_issues": len(issue_ids),
            "successful": len(successes),
            "failed": len(errors),
            "results": results,
        }

        self._save_batch_result(workspace_dir, batch_id, batch_result)

        if progress_callback:
            await progress_callback(
                batch_id=batch_id,
                stage="complete",
                progress=100,
                message=f"Completed {len(successes)}/{len(issue_ids)} analyses",
            )

        return batch_result

    def _save_batch_result(
        self,
        workspace_dir: str,
        batch_id: str,
        batch_result: dict[str, Any],
    ) -> None:
        """Save batch analysis result."""
        workspace_path = Path(workspace_dir)
        batch_dir = workspace_path / "knowledge" / "batches" / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        result_file = batch_dir / "result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(batch_result, f, indent=2)

    def get_batch_result(
        self,
        *,
        workspace_dir: str,
        batch_id: str,
    ) -> dict[str, Any]:
        """Get saved batch analysis result.

        Args:
            workspace_dir: Path to workspace directory
            batch_id: Batch ID

        Returns:
            Batch analysis result
        """
        workspace_path = Path(workspace_dir)
        batch_dir = workspace_path / "knowledge" / "batches" / batch_id

        if not batch_dir.exists():
            raise ValueError(f"Batch not found: {batch_id}")

        result_file = batch_dir / "result.json"
        if not result_file.exists():
            raise ValueError(f"Batch result not found: {batch_id}")

        with open(result_file, encoding="utf-8") as f:
            return json.load(f)

    def list_batches(
        self,
        *,
        workspace_dir: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List recent batch analyses.

        Args:
            workspace_dir: Path to workspace directory
            limit: Maximum number of batches to return

        Returns:
            List of batch summaries
        """
        workspace_path = Path(workspace_dir)
        batch_dir = workspace_path / "knowledge" / "batches"

        if not batch_dir.exists():
            return {"batches": []}

        batches = []
        for batch_path in batch_dir.iterdir():
            if not batch_path.is_dir():
                continue

            result_file = batch_path / "result.json"
            if not result_file.exists():
                continue

            with open(result_file, encoding="utf-8") as f:
                result = json.load(f)

            batches.append({
                "batch_id": result.get("batch_id"),
                "started_at": result.get("started_at"),
                "completed_at": result.get("completed_at"),
                "duration_seconds": result.get("duration_seconds"),
                "total_issues": result.get("total_issues"),
                "successful": result.get("successful"),
                "failed": result.get("failed"),
            })

        # Sort by started_at (most recent first)
        batches.sort(key=lambda x: x.get("started_at", ""), reverse=True)

        return {
            "total": len(batches),
            "batches": batches[:limit],
        }


async def batch_analyze_issues_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle batch analysis request.

    Args:
        payload: Request payload with workspace_dir, issue_ids, etc.

    Returns:
        Batch analysis result
    """
    workspace_dir = payload.get("workspace_dir")
    if not workspace_dir:
        raise ValueError("workspace_dir is required")

    issue_ids = payload.get("issue_ids")
    if not issue_ids or not isinstance(issue_ids, list):
        raise ValueError("issue_ids must be a non-empty list")

    api = BatchAnalysisAPI(workspace_root=Path(workspace_dir).parent)

    result = await api.batch_analyze_issues(
        workspace_dir=workspace_dir,
        issue_ids=issue_ids,
        llm_backend=payload.get("llm_backend", "none"),
        llm_base_url=payload.get("llm_base_url"),
        llm_model=payload.get("llm_model"),
        prompt_mode=payload.get("prompt_mode", "strict"),
        top_k=payload.get("top_k", 5),
        max_concurrent=payload.get("max_concurrent", 3),
    )

    return result


def get_batch_result_response(workspace_dir: str, batch_id: str) -> dict[str, Any]:
    """Get saved batch analysis result.

    Args:
        workspace_dir: Path to workspace directory
        batch_id: Batch ID

    Returns:
        Batch analysis result
    """
    api = BatchAnalysisAPI(workspace_root=Path(workspace_dir).parent)
    return api.get_batch_result(workspace_dir=workspace_dir, batch_id=batch_id)


def list_batches_response(workspace_dir: str, limit: int = 20) -> dict[str, Any]:
    """List recent batch analyses.

    Args:
        workspace_dir: Path to workspace directory
        limit: Maximum number of batches to return

    Returns:
        List of batch summaries
    """
    api = BatchAnalysisAPI(workspace_root=Path(workspace_dir).parent)
    return api.list_batches(workspace_dir=workspace_dir, limit=limit)


"""
Generic report generation service.

This module provides source-agnostic report generation capabilities that can be
used with any document type (Jira, Confluence, PDF, etc.).
"""
from __future__ import annotations

from services.analysis.llm_backends import LLMBackend


def build_time_filtered_report(
    *,
    documents: list[dict],
    time_filter_label: str,
    document_summarizer: callable,
    prompt_builder: callable | None = None,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    """
    Build a report for time-filtered documents.

    Args:
        documents: List of filtered documents
        time_filter_label: Human-readable time filter description
        document_summarizer: Function to summarize a single document
        prompt_builder: Function to build LLM prompt (if llm_backend is provided)
        prompt_template: Optional custom prompt template
        prompt_mode: Prompt mode (strict/balanced/exploratory)
        llm_backend: Optional LLM backend for generating answers

    Returns:
        Report dictionary with markdown, prompt, and optional answer
    """
    summaries = [document_summarizer(document) for document in documents]
    summary_text = "\n\n---\n\n".join(summaries)

    if prompt_template:
        prompt = prompt_template.format(
            issue_count=len(documents),
            time_filter=time_filter_label,
            summaries=summary_text,
            prompt_mode=prompt_mode,
        )
    elif llm_backend and prompt_builder:
        prompt = prompt_builder(
            issue_count=len(documents),
            time_filter=time_filter_label,
            summaries=summary_text,
            prompt_mode=prompt_mode,
        )
    else:
        prompt = "Summarize {issue_count} document(s) for time filter {time_filter}.\n\n{summaries}".format(
            issue_count=len(documents),
            time_filter=time_filter_label,
            summaries=summary_text,
        )

    report = {
        "time_filter": time_filter_label,
        "issue_count": len(documents),
        "issue_ids": [document["document_id"] for document in documents],
        "markdown": summary_text,
        "prompt": prompt,
    }

    if llm_backend:
        report["answer"] = build_llm_answer(prompt, llm_backend, len(documents))

    return report


def build_daily_status_report(
    *,
    documents: list[dict],
    reference_date: str,
    status_filter: str,
    fact_builder: callable,
    issue_renderer: callable,
    attention_renderer: callable,
    executive_summary_builder: callable,
    prompt_builder: callable,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
    **filter_params,
) -> dict:
    """
    Build a daily status report (e.g., PM daily report).

    Args:
        documents: All documents to analyze
        reference_date: Reference date for the report
        status_filter: Status to filter by (e.g., "In Progress")
        fact_builder: Function to build facts from a document
        issue_renderer: Function to render an issue line
        attention_renderer: Function to render an attention item
        executive_summary_builder: Function to build executive summary
        prompt_builder: Function to build LLM prompt
        prompt_template: Optional custom prompt template
        prompt_mode: Prompt mode (strict/balanced/exploratory)
        llm_backend: Optional LLM backend
        **filter_params: Additional filter parameters

    Returns:
        Report dictionary with structured data and markdown
    """
    issue_facts = [
        fact_builder(document, **filter_params)
        for document in documents
    ]

    active_today = [issue for issue in issue_facts if issue.get("updated_today")]
    in_progress_no_update = [issue for issue in issue_facts if not issue.get("updated_today")]
    stale_in_progress = [issue for issue in in_progress_no_update if issue.get("stale")]
    manager_attention_items = [issue for issue in issue_facts if issue.get("attention_signals")]

    executive_summary = executive_summary_builder(
        reference_date=reference_date,
        active_today=active_today,
        in_progress_no_update=in_progress_no_update,
        attention_items=manager_attention_items,
    )

    issue_summaries = "\n\n".join(
        [
            "## Active Today",
            *(issue_renderer(issue) for issue in active_today),
            "",
            "## In Progress But No Update",
            *(issue_renderer(issue) for issue in in_progress_no_update),
            "",
            "## Manager Attention",
            *(attention_renderer(issue) for issue in manager_attention_items),
        ]
    ).strip()

    if prompt_template:
        prompt = prompt_template.format(
            reference_date=reference_date,
            status_filter=status_filter,
            updated_issue_count=len(active_today),
            stale_issue_count=len(stale_in_progress),
            issue_summaries=issue_summaries,
            prompt_mode=prompt_mode,
        )
    else:
        prompt = prompt_builder(
            reference_date=reference_date,
            status_filter=status_filter,
            updated_issue_count=len(active_today),
            stale_issue_count=len(stale_in_progress),
            issue_summaries=issue_summaries,
            prompt_mode=prompt_mode,
        )

    markdown_sections = [
        f"# Daily Status Report ({reference_date})",
        "",
        "## Executive Summary",
        *(f"- {line}" for line in executive_summary),
        "",
        "## Active Today",
        *(issue_renderer(issue) for issue in active_today),
        "",
        "## In Progress But No Update",
        *(issue_renderer(issue) for issue in in_progress_no_update),
        "",
        "## Manager Attention",
        *([f"- {attention_renderer(issue)}" for issue in manager_attention_items] or ["- None"]),
    ]

    payload = {
        "report_profile": "daily-status",
        "reference_date": reference_date,
        "status_filter": status_filter,
        "executive_summary": executive_summary,
        "active_today": active_today,
        "in_progress_no_update": in_progress_no_update,
        "updated_issue_ids": [issue["document_id"] for issue in active_today],
        "stale_issue_ids": [issue["document_id"] for issue in stale_in_progress],
        "issue_count": len(issue_facts),
        "updated_issue_count": len(active_today),
        "stale_issue_count": len(stale_in_progress),
        "manager_attention": [attention_renderer(issue) for issue in manager_attention_items],
        "manager_attention_items": manager_attention_items,
        "markdown": "\n".join(markdown_sections).strip(),
        "prompt": prompt,
    }

    if llm_backend:
        payload["answer"] = build_llm_answer(prompt, llm_backend, len(issue_facts))

    return payload


def build_llm_answer(prompt: str, llm_backend: LLMBackend, document_count: int) -> dict:
    """
    Generate an LLM answer for a report.

    Args:
        prompt: The prompt to send to the LLM
        llm_backend: LLM backend to use
        document_count: Number of documents in the report

    Returns:
        Answer dictionary with mode, backend, text, and document count
    """
    return {
        "mode": "local-llm",
        "backend": llm_backend.name,
        "text": llm_backend.generate(prompt).strip(),
        "issue_count": document_count,
    }

from __future__ import annotations

from datetime import date, datetime, time, timezone
from html import escape
from pathlib import Path

from services.analysis.demo_profiles import (
    build_confluence_wiki_summary_prompt,
    build_jira_pm_daily_prompt,
    build_spec_section_explain_prompt,
)
from services.analysis.llm_backends import LLMBackend
from services.analysis.jira_profiles import (
    build_jira_report_prompt,
    build_jira_spec_extractive_answer,
    build_spec_section_extractive_answer,
)
from services.analysis.retrieval_consumption import build_retrieval_consumption_payload


def _parse_iso(value: str | None) -> datetime | None:
    if not value or value == "fixture":
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _document_updated_at(document: dict) -> datetime | None:
    return _parse_iso(document.get("version")) or _parse_iso(document.get("provenance", {}).get("ingested_at"))


def _resolve_time_filter(
    *,
    updated_from_iso: str | None = None,
    updated_to_iso: str | None = None,
    updated_on_date: str | None = None,
    updated_at_iso: str | None = None,
) -> tuple[str | None, str | None, str]:
    if updated_on_date:
        selected_date = date.fromisoformat(updated_on_date)
        start = datetime.combine(selected_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(selected_date, time.max, tzinfo=timezone.utc)
        return (
            start.isoformat().replace("+00:00", "Z"),
            end.isoformat().replace("+00:00", "Z"),
            f"date:{updated_on_date}",
        )
    if updated_at_iso:
        parsed = _parse_iso(updated_at_iso)
        if parsed is None:
            return None, None, "all"
        normalized = parsed.isoformat().replace("+00:00", "Z")
        return normalized, normalized, f"at:{normalized}"
    return updated_from_iso, updated_to_iso, _format_time_filter(updated_from_iso, updated_to_iso)


def _format_time_filter(updated_from_iso: str | None, updated_to_iso: str | None) -> str:
    if updated_from_iso and updated_to_iso:
        return f"{updated_from_iso}..{updated_to_iso}"
    if updated_from_iso:
        return f">={updated_from_iso}"
    if updated_to_iso:
        return f"<={updated_to_iso}"
    return "all"


def summarize_jira_issue_markdown(document: dict) -> str:
    issue_fields = document.get("metadata", {}).get("issue_fields", {})
    comments = document.get("comments", [])
    lines = [
        f"# {document.get('title', document['document_id'])}",
        "",
        f"- Issue: {document['document_id']}",
        f"- Version: {document.get('version')}",
        f"- Source: {document.get('source_type')}",
        "",
        "## Issue Fields",
    ]
    for key in sorted(issue_fields):
        value = issue_fields[key]
        if value not in (None, "", []):
            lines.append(f"- {key}: {value}")

    lines.extend(["", "## Jira Markdown", document.get("markdown", "").strip() or "No markdown."])
    if comments:
        lines.extend(["", "## Comments"])
        for comment in comments:
            if isinstance(comment, dict):
                author = comment.get("author", {}).get("displayName") or comment.get("author") or "unknown"
                body = comment.get("body", "")
                lines.append(f"- {author}: {body}")
            else:
                lines.append(f"- {comment}")
    return "\n".join(lines).strip()


def _issue_field(document: dict, label: str) -> str:
    return str(document.get("metadata", {}).get("issue_fields", {}).get(label, "") or "").strip()


def _comment_records(document: dict) -> list[dict]:
    records = []
    for comment in document.get("comments", []):
        if isinstance(comment, dict):
            author = comment.get("author", {}) or {}
            records.append(
                {
                    "author": author.get("displayName") or author.get("name") or comment.get("author") or "unknown",
                    "created": comment.get("created"),
                    "body": comment.get("body", ""),
                }
            )
    return records


def _latest_comment(document: dict) -> dict | None:
    records = _comment_records(document)
    if not records:
        return None
    records.sort(key=lambda item: item.get("created") or "", reverse=True)
    return records[0]


def _render_pm_issue_line(document: dict, reference_date: str, stale_threshold_hours: int) -> str:
    latest_comment = _latest_comment(document)
    latest_comment_text = "No comment update."
    if latest_comment:
        body = str(latest_comment.get("body") or "").strip() or "No comment body."
        latest_comment_text = f"{latest_comment['author']} ({latest_comment.get('created') or 'unknown'}): {body}"
    return "\n".join(
        [
            f"- Issue: {document['document_id']}",
            f"  Summary: {document.get('title', document['document_id'])}",
            f"  Priority: {_issue_field(document, 'Priority') or 'unknown'}",
            f"  Status: {_issue_field(document, 'Status') or 'unknown'}",
            f"  Updated: {document.get('version')}",
            f"  Reference date: {reference_date}",
            f"  Stale threshold hours: {stale_threshold_hours}",
            f"  Latest comment: {latest_comment_text}",
        ]
    )


def _pm_attention_items(document: dict, stale: bool) -> list[str]:
    items = []
    latest_comment = _latest_comment(document)
    if stale:
        items.append(f"{document['document_id']}: still In Progress but no update in the selected day")
    if latest_comment is None:
        items.append(f"{document['document_id']}: no comments available")
    else:
        body = str(latest_comment.get("body") or "").lower()
        if any(term in body for term in ("retest", "validation", "blocked", "pending")):
            items.append(f"{document['document_id']}: latest comment mentions retest/validation/blocking signal")
    return items


def filter_jira_documents_by_updated_time(
    documents: list[dict],
    *,
    updated_from_iso: str | None = None,
    updated_to_iso: str | None = None,
    updated_on_date: str | None = None,
    updated_at_iso: str | None = None,
) -> list[dict]:
    updated_from_iso, updated_to_iso, _ = _resolve_time_filter(
        updated_from_iso=updated_from_iso,
        updated_to_iso=updated_to_iso,
        updated_on_date=updated_on_date,
        updated_at_iso=updated_at_iso,
    )
    updated_from = _parse_iso(updated_from_iso)
    updated_to = _parse_iso(updated_to_iso)
    filtered = []
    for document in documents:
        updated_at = _document_updated_at(document)
        if updated_at is None:
            continue
        if updated_from and updated_at < updated_from:
            continue
        if updated_to and updated_at > updated_to:
            continue
        filtered.append(document)
    return filtered


def build_jira_time_report(
    documents: list[dict],
    *,
    updated_from_iso: str | None = None,
    updated_to_iso: str | None = None,
    updated_on_date: str | None = None,
    updated_at_iso: str | None = None,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    updated_from_iso, updated_to_iso, time_filter = _resolve_time_filter(
        updated_from_iso=updated_from_iso,
        updated_to_iso=updated_to_iso,
        updated_on_date=updated_on_date,
        updated_at_iso=updated_at_iso,
    )
    filtered = filter_jira_documents_by_updated_time(
        documents,
        updated_from_iso=updated_from_iso,
        updated_to_iso=updated_to_iso,
    )
    summaries = [summarize_jira_issue_markdown(document) for document in filtered]
    summary_text = "\n\n---\n\n".join(summaries)
    if prompt_template:
        prompt = prompt_template.format(
            issue_count=len(filtered),
            time_filter=time_filter,
            summaries=summary_text,
            prompt_mode=prompt_mode,
        )
    elif llm_backend:
        prompt = build_jira_report_prompt(
            issue_count=len(filtered),
            time_filter=time_filter,
            summaries=summary_text,
            prompt_mode=prompt_mode,
        )
    else:
        prompt = "Summarize {issue_count} Jira issue(s) for time filter {time_filter}.\n\n{summaries}".format(
            issue_count=len(filtered),
            time_filter=time_filter,
            summaries=summary_text,
        )
    report = {
        "time_filter": time_filter,
        "issue_count": len(filtered),
        "issue_ids": [document["document_id"] for document in filtered],
        "markdown": summary_text,
        "prompt": prompt,
    }
    if llm_backend:
        report["answer"] = _build_report_llm_answer(prompt, llm_backend, len(filtered))
    return report


def build_jira_pm_daily_report(
    documents: list[dict],
    *,
    reference_date: str,
    status_filter: str = "In Progress",
    stale_threshold_hours: int = 24,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    target_date = date.fromisoformat(reference_date)
    in_progress_documents = [
        document
        for document in documents
        if _issue_field(document, "Status") == status_filter
    ]
    updated_today = []
    stale_in_progress = []
    manager_attention: list[str] = []
    for document in in_progress_documents:
        updated_at = _document_updated_at(document)
        updated_on_target_date = updated_at is not None and updated_at.date() == target_date
        if updated_on_target_date:
            updated_today.append(document)
        else:
            stale_in_progress.append(document)
        manager_attention.extend(_pm_attention_items(document, stale=not updated_on_target_date))

    issue_summaries = "\n\n".join(
        [
            "## Updated Today",
            *(_render_pm_issue_line(document, reference_date, stale_threshold_hours) for document in updated_today),
            "",
            "## In Progress But No Update",
            *(_render_pm_issue_line(document, reference_date, stale_threshold_hours) for document in stale_in_progress),
        ]
    ).strip()
    if prompt_template:
        prompt = prompt_template.format(
            reference_date=reference_date,
            status_filter=status_filter,
            updated_issue_count=len(updated_today),
            stale_issue_count=len(stale_in_progress),
            issue_summaries=issue_summaries,
            prompt_mode=prompt_mode,
        )
    else:
        prompt = build_jira_pm_daily_prompt(
            reference_date=reference_date,
            status_filter=status_filter,
            updated_issue_count=len(updated_today),
            stale_issue_count=len(stale_in_progress),
            issue_summaries=issue_summaries,
            prompt_mode=prompt_mode,
        )
    markdown_sections = [
        f"# Jira PM Daily Report ({reference_date})",
        "",
        "## Updated Today",
        *(_render_pm_issue_line(document, reference_date, stale_threshold_hours) for document in updated_today),
        "",
        "## In Progress But No Update",
        *(_render_pm_issue_line(document, reference_date, stale_threshold_hours) for document in stale_in_progress),
        "",
        "## Manager Attention",
        *(f"- {item}" for item in manager_attention or ["None"]),
    ]
    payload = {
        "report_profile": "pm-daily",
        "reference_date": reference_date,
        "status_filter": status_filter,
        "updated_issue_ids": [document["document_id"] for document in updated_today],
        "stale_issue_ids": [document["document_id"] for document in stale_in_progress],
        "issue_count": len(in_progress_documents),
        "updated_issue_count": len(updated_today),
        "stale_issue_count": len(stale_in_progress),
        "manager_attention": manager_attention,
        "markdown": "\n".join(markdown_sections).strip(),
        "prompt": prompt,
    }
    if llm_backend:
        payload["answer"] = _build_report_llm_answer(prompt, llm_backend, len(in_progress_documents))
    return payload

def _build_report_llm_answer(prompt: str, llm_backend: LLMBackend, issue_count: int) -> dict:
    return {
        "mode": "local-llm",
        "backend": llm_backend.name,
        "text": llm_backend.generate(prompt).strip(),
        "issue_count": issue_count,
    }

def build_jira_spec_question_payload(
    *,
    jira_document: dict,
    spec_documents: list[dict],
    question: str,
    allowed_policies: set[str],
    top_k: int = 5,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    documents = [jira_document, *spec_documents]
    summary_markdown = summarize_jira_issue_markdown(jira_document)
    retrieval_payload = build_retrieval_consumption_payload(
        documents=documents,
        question=question,
        allowed_policies=allowed_policies,
        top_k=top_k,
        prompt_template=prompt_template,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
        assistant_intro="You are an SSD firmware/spec triage assistant.",
        task_instruction="Answer the Jira question using only the retrieved Jira and spec evidence.",
        context_heading="Jira Issue Summary",
        context_markdown=summary_markdown,
        extra_template_values={
            "jira_issue_id": jira_document["document_id"],
            "summary_markdown": summary_markdown,
        },
    )
    citations = retrieval_payload["retrieval"]["citations"]
    jira_citations = [citation for citation in citations if citation["document"] == jira_document["document_id"]]
    spec_citations = [citation for citation in citations if citation["document"] != jira_document["document_id"]]

    return {
        "question": question,
        "jira_issue_id": jira_document["document_id"],
        "summary_markdown": summary_markdown,
        "retrieval": {
            "result_count": retrieval_payload["retrieval"]["result_count"],
            "citations": citations,
            "has_jira_evidence": bool(jira_citations),
            "has_spec_evidence": bool(spec_citations),
        },
        "ai_prompt": retrieval_payload["ai_prompt"],
        "answer": (
            retrieval_payload["answer"]
            if llm_backend
            else build_jira_spec_extractive_answer(question, citations)
        ),
    }


def build_jira_batch_spec_report(
    *,
    jira_documents: list[dict],
    spec_documents: list[dict],
    question_template: str,
    allowed_policies: set[str],
    updated_from_iso: str | None = None,
    updated_to_iso: str | None = None,
    updated_on_date: str | None = None,
    updated_at_iso: str | None = None,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    time_report = build_jira_time_report(
        jira_documents,
        updated_from_iso=updated_from_iso,
        updated_to_iso=updated_to_iso,
        updated_on_date=updated_on_date,
        updated_at_iso=updated_at_iso,
    )
    selected_documents = [
        document
        for document in jira_documents
        if document["document_id"] in set(time_report["issue_ids"])
    ]
    issue_reports = []
    for document in selected_documents:
        question = question_template.format(
            jira_issue_id=document["document_id"],
            title=document.get("title", document["document_id"]),
        )
        issue_reports.append(
            build_jira_spec_question_payload(
                jira_document=document,
                spec_documents=spec_documents,
                question=question,
                allowed_policies=allowed_policies,
                prompt_template=prompt_template,
                prompt_mode=prompt_mode,
                llm_backend=llm_backend,
            )
        )

    return {
        "time_filter": time_report["time_filter"],
        "issue_count": time_report["issue_count"],
        "issue_ids": time_report["issue_ids"],
        "summary_markdown": time_report["markdown"],
        "issues": issue_reports,
        "has_spec_evidence_count": sum(1 for report in issue_reports if report["retrieval"]["has_spec_evidence"]),
    }


def _resolve_spec_section(spec_document: dict, *, clause: str | None = None, section_heading: str | None = None) -> dict:
    sections = spec_document.get("structure", {}).get("sections", [])
    for section in sections:
        if clause and str(section.get("clause")) == clause:
            return section
        if section_heading and str(section.get("heading")) == section_heading:
            return section
    if clause:
        raise ValueError(f"Spec clause not found: {clause}")
    if section_heading:
        raise ValueError(f"Spec section not found: {section_heading}")
    raise ValueError("Either clause or section_heading is required")


def _spec_section_markdown(spec_document: dict, section: dict) -> tuple[str, str]:
    page = section.get("page")
    heading = section.get("heading") or "Untitled Section"
    clause = section.get("clause")
    blocks = [
        block.get("text", "")
        for block in spec_document.get("content_blocks", [])
        if page is None or block.get("page") == page
    ]
    section_label = f"{clause} {heading}".strip() if clause else heading
    markdown = "\n".join([f"# {section_label}", "", *(block for block in blocks if block)]).strip()
    return section_label, markdown


def build_spec_section_explain_payload(
    *,
    spec_document: dict,
    jira_documents: list[dict],
    allowed_policies: set[str],
    clause: str | None = None,
    section_heading: str | None = None,
    question: str | None = None,
    top_k: int = 5,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    section = _resolve_spec_section(spec_document, clause=clause, section_heading=section_heading)
    section_label, section_markdown = _spec_section_markdown(spec_document, section)
    query = question or f"Which Jira issues help explain {section_label} in {spec_document['title']}?"
    retrieval_payload = build_retrieval_consumption_payload(
        documents=jira_documents,
        question=query,
        allowed_policies=allowed_policies,
        top_k=top_k,
        prompt_template=prompt_template,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
        assistant_intro="You are an SSD firmware and specification explanation assistant.",
        task_instruction="Explain the selected spec section using only the section text and retrieved Jira evidence.",
        context_heading="Spec Section",
        context_markdown=section_markdown,
        extra_template_values={
            "spec_document_id": spec_document["document_id"],
            "section_label": section_label,
            "section_markdown": section_markdown,
        },
    )
    if not prompt_template:
        cited_jira_ids = {
            citation["document"]
            for citation in retrieval_payload["retrieval"]["citations"]
            if citation["document"] != spec_document["document_id"]
        }
        related_jira_documents = [
            document for document in jira_documents if document["document_id"] in cited_jira_ids
        ]
        evidence_text = "\n\n---\n\n".join(
            summarize_jira_issue_markdown(document) for document in related_jira_documents
        )
        retrieval_payload["ai_prompt"] = build_spec_section_explain_prompt(
            spec_document_id=spec_document["document_id"],
            section_label=section_label,
            section_markdown=section_markdown,
            evidence_text=evidence_text,
            prompt_mode=prompt_mode,
        )
        if llm_backend:
            retrieval_payload["answer"] = {
                "mode": "local-llm",
                "backend": llm_backend.name,
                "text": llm_backend.generate(retrieval_payload["ai_prompt"]).strip(),
                "citation_count": len(retrieval_payload["retrieval"]["citations"]),
            }
    citations = retrieval_payload["retrieval"]["citations"]
    jira_citations = citations
    return {
        "spec_document_id": spec_document["document_id"],
        "section": {
            "heading": section.get("heading"),
            "clause": section.get("clause"),
            "page": section.get("page"),
            "label": section_label,
            "markdown": section_markdown,
        },
        "question": query,
        "retrieval": {
            "result_count": retrieval_payload["retrieval"]["result_count"],
            "citations": citations,
            "has_jira_evidence": bool(jira_citations),
        },
        "related_issues": [
            {
                "document_id": document["document_id"],
                "title": document.get("title", document["document_id"]),
                "summary_markdown": summarize_jira_issue_markdown(document),
            }
            for document in jira_documents
            if document["document_id"] in {citation["document"] for citation in citations}
        ],
        "ai_prompt": retrieval_payload["ai_prompt"],
        "answer": retrieval_payload["answer"] if llm_backend else build_spec_section_extractive_answer(
            spec_document_id=spec_document["document_id"],
            section_label=section_label,
            citations=citations,
        ),
    }


def build_confluence_wiki_summary_payload(
    *,
    document: dict,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    page_markdown = document.get("markdown", "").strip()
    if prompt_template:
        prompt = prompt_template.format(
            title=document.get("title", document["document_id"]),
            source_uri=document.get("provenance", {}).get("source_uri", ""),
            markdown=page_markdown,
            prompt_mode=prompt_mode,
        )
    else:
        prompt = build_confluence_wiki_summary_prompt(
            title=document.get("title", document["document_id"]),
            source_uri=document.get("provenance", {}).get("source_uri", ""),
            page_markdown=page_markdown,
            prompt_mode=prompt_mode,
        )

    if llm_backend:
        answer = {
            "mode": "local-llm",
            "backend": llm_backend.name,
            "text": llm_backend.generate(prompt).strip(),
        }
    else:
        headings = [section.get("heading", "") for section in document.get("structure", {}).get("sections", []) if section.get("heading")]
        blocks = [block.get("text", "") for block in document.get("content_blocks", []) if block.get("text")]
        summary_lines = [
            f"Title: {document.get('title', document['document_id'])}",
            "",
            "Key headings:",
            *(f"- {heading}" for heading in headings[:5] or ["- None"]),
            "",
            "Extractive highlights:",
            *(f"- {block}" for block in blocks[:5] or ["- None"]),
        ]
        answer = {"mode": "extractive", "text": "\n".join(summary_lines).strip()}

    return {
        "document_id": document["document_id"],
        "title": document.get("title", document["document_id"]),
        "source_uri": document.get("provenance", {}).get("source_uri"),
        "version": document.get("version"),
        "prompt": prompt,
        "answer": answer,
    }


def render_confluence_static_wiki(
    *,
    page_payloads: list[dict],
    output_dir: str | Path,
) -> dict:
    root = Path(output_dir)
    pages_dir = root / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    written_pages = []
    index_items = []
    for payload in page_payloads:
        page_path = pages_dir / f"{payload['document_id']}.html"
        answer_text = escape(payload["answer"]["text"]).replace("\n", "<br/>\n")
        page_html = "\n".join(
            [
                "<!doctype html>",
                "<html><head><meta charset=\"utf-8\"><title>{}</title></head><body>".format(escape(payload["title"])),
                f"<h1>{escape(payload['title'])}</h1>",
                f"<p><strong>Document ID:</strong> {escape(payload['document_id'])}</p>",
                f"<p><strong>Version:</strong> {escape(str(payload.get('version') or ''))}</p>",
                f"<p><strong>Source:</strong> {escape(str(payload.get('source_uri') or ''))}</p>",
                "<p><strong>Derived page:</strong> This page is a summary and does not replace source truth.</p>",
                "<h2>Summary</h2>",
                f"<p>{answer_text}</p>",
                "</body></html>",
            ]
        )
        page_path.write_text(page_html, encoding="utf-8")
        written_pages.append(str(page_path))
        first_line = payload["answer"]["text"].splitlines()[0] if payload["answer"]["text"] else payload["title"]
        index_items.append(
            f"<li><a href=\"pages/{escape(payload['document_id'])}.html\">{escape(payload['title'])}</a> - {escape(first_line)}</li>"
        )

    index_html = "\n".join(
        [
            "<!doctype html>",
            "<html><head><meta charset=\"utf-8\"><title>Confluence Wiki Demo</title></head><body>",
            "<h1>Confluence Wiki Demo</h1>",
            "<p>Derived summaries generated from Confluence documents.</p>",
            "<ul>",
            *index_items,
            "</ul>",
            "</body></html>",
        ]
    )
    index_path = root / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    return {"output_dir": str(root), "index_html": str(index_path), "pages": written_pages}

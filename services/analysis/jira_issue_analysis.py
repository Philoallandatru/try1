from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from services.analysis.demo_profiles import (
    build_jira_pm_daily_prompt,
    build_spec_section_explain_prompt,
)
from services.analysis.llm_backends import LLMBackend
from services.analysis.jira_profiles import (
    build_jira_report_prompt,
    build_jira_spec_extractive_answer,
    build_spec_section_extractive_answer,
)
from services.analysis.report_generation import (
    build_time_filtered_report,
    build_daily_status_report,
)
from services.analysis.jira_report_profiles import (
    build_jira_pm_issue_fact,
    render_jira_pm_issue_line,
    render_jira_pm_attention_item,
    build_jira_pm_executive_summary,
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


def _first_issue_field(document: dict, labels: list[str]) -> str:
    for label in labels:
        value = _issue_field(document, label)
        if value:
            return value
    return ""


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


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _pm_attention_signals(document: dict, *, stale: bool) -> list[str]:
    signals: list[str] = []
    latest_comment = _latest_comment(document)
    owner = _first_issue_field(document, ["Assignee", "Owner"])
    if stale:
        signals.append("stale_in_progress")
    if not owner:
        signals.append("unclear_ownership")
    if latest_comment is None:
        signals.append("no_comment")
        return signals

    body = str(latest_comment.get("body") or "").lower()
    if any(term in body for term in ("blocked", "blocking", "阻塞")):
        signals.append("blocked")
    if any(term in body for term in ("retest", "复测", "待复测")):
        signals.append("retest_pending")
    if any(term in body for term in ("validation", "验证", "待验证", "pending")):
        signals.append("validation_pending")
    return _dedupe(signals)


# PM report helper functions moved to jira_report_profiles.py


def _format_latest_comment(comment: dict | None) -> str:
    """Format a comment for display in reports."""
    if not comment:
        return "No comment update."
    body = str(comment.get("body") or "").strip() or "No comment body."
    return f"{comment.get('author') or 'unknown'} ({comment.get('created') or 'unknown'}): {body}"


def _structured_jira_summary(document: dict, *, evidence_spans: list[str] | None = None) -> str:
    latest_comment = _latest_comment(document)
    lines = [
        f"### {document['document_id']} - {document.get('title', document['document_id'])}",
        f"- Owner: {_first_issue_field(document, ['Assignee', 'Owner']) or 'unknown'}",
        f"- Priority: {_issue_field(document, 'Priority') or 'unknown'}",
        f"- Status: {_issue_field(document, 'Status') or 'unknown'}",
        f"- Updated: {document.get('version') or 'unknown'}",
        f"- Latest comment: {_format_latest_comment(latest_comment)}",
    ]
    if evidence_spans:
        lines.append("- Evidence spans:")
        lines.extend(f"  - {span}" for span in evidence_spans if span)
    return "\n".join(lines)


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
    """
    Build a time-filtered Jira report.

    Uses the generic report generation service with Jira-specific configuration.
    """
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

    return build_time_filtered_report(
        documents=filtered,
        time_filter_label=time_filter,
        document_summarizer=summarize_jira_issue_markdown,
        prompt_builder=build_jira_report_prompt if llm_backend else None,
        prompt_template=prompt_template,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
    )


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
    """
    Build a PM daily report for Jira issues.

    Uses the generic daily status report service with Jira-specific configuration.
    """
    target_date = date.fromisoformat(reference_date)

    # Filter documents by status
    filtered_documents = [
        document for document in documents
        if _issue_field(document, "Status") == status_filter
    ]

    # Use generic daily status report builder
    report = build_daily_status_report(
        documents=filtered_documents,
        reference_date=reference_date,
        status_filter=status_filter,
        fact_builder=lambda doc, **kwargs: build_jira_pm_issue_fact(
            doc,
            target_date=target_date,
            stale_threshold_hours=stale_threshold_hours,
        ),
        issue_renderer=render_jira_pm_issue_line,
        attention_renderer=render_jira_pm_attention_item,
        executive_summary_builder=build_jira_pm_executive_summary,
        prompt_builder=build_jira_pm_daily_prompt,
        prompt_template=prompt_template,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
    )

    # Override report_profile to match expected value
    report["report_profile"] = "pm-daily"

    return report


# _build_report_llm_answer moved to report_generation.build_llm_answer


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


def _build_section_anchor(spec_document: dict, section: dict) -> dict:
    clause = str(section.get("clause") or "").strip() or None
    page = section.get("page")
    heading = str(section.get("heading") or "").strip() or "Untitled Section"
    raw_section_id = str(section.get("id") or "").strip() or None
    if clause and page is not None:
        section_anchor_id = f"{spec_document['document_id']}:{clause}:{page}"
    elif raw_section_id:
        section_anchor_id = f"{spec_document['document_id']}:{raw_section_id}"
    elif page is not None:
        section_anchor_id = f"{spec_document['document_id']}:{heading}:{page}"
    else:
        section_anchor_id = f"{spec_document['document_id']}:{heading}"
    return {
        "heading": heading,
        "clause": clause,
        "page": page,
        "raw_section_id": raw_section_id,
        "section_anchor_id": section_anchor_id,
    }


def _section_blocks(spec_document: dict, section: dict) -> list[dict]:
    content_blocks = spec_document.get("content_blocks", [])
    section_id = section.get("id")
    clause = section.get("clause")
    heading = section.get("heading")
    page = section.get("page")

    direct_matches = [
        block
        for block in content_blocks
        if (section_id and block.get("section_id") == section_id)
        or (clause and str(block.get("clause")) == str(clause))
        or (heading and str(block.get("section_heading")) == str(heading))
    ]
    if direct_matches:
        return direct_matches
    if page is not None:
        return [block for block in content_blocks if block.get("page") == page]
    return list(content_blocks)


def _spec_section_context(spec_document: dict, section: dict) -> dict:
    anchor = _build_section_anchor(spec_document, section)
    block_texts = [str(block.get("text") or "").strip() for block in _section_blocks(spec_document, section) if str(block.get("text") or "").strip()]
    section_label = f"{anchor['clause']} {anchor['heading']}".strip() if anchor["clause"] else anchor["heading"]
    markdown_lines = [
        f"# {section_label}",
        "",
        f"- Section Anchor: {anchor['section_anchor_id']}",
        f"- Page: {anchor['page'] if anchor['page'] is not None else 'unknown'}",
        "",
        *(block_texts or ["No section text available."]),
    ]
    return {
        "heading": anchor["heading"],
        "clause": anchor["clause"],
        "page": anchor["page"],
        "label": section_label,
        "markdown": "\n".join(markdown_lines).strip(),
        "section_anchor_id": anchor["section_anchor_id"],
        "context_blocks": block_texts,
    }


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
    section_context = _spec_section_context(spec_document, section)
    section_label = section_context["label"]
    section_markdown = section_context["markdown"]
    section_excerpt = " ".join(section_context["context_blocks"][:2]).strip()
    query = question or f"Which Jira issues help explain {section_label} in {spec_document['title']}? {section_excerpt}".strip()
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
    citation_rank: dict[str, int] = {}
    citation_evidence: dict[str, list[str]] = {}
    for index, citation in enumerate(retrieval_payload["retrieval"]["citations"]):
        document_id = citation["document"]
        citation_rank.setdefault(document_id, index)
        evidence_text = citation.get("evidence_span", "").strip()
        if evidence_text:
            citation_evidence.setdefault(document_id, []).append(evidence_text)

    related_jira_documents = sorted(
        [
            document
            for document in jira_documents
            if document["document_id"] in citation_rank
        ],
        key=lambda document: citation_rank.get(document["document_id"], 10**6),
    )
    related_issues = [
        {
            "document_id": document["document_id"],
            "title": document.get("title", document["document_id"]),
            "owner": _first_issue_field(document, ["Assignee", "Owner"]) or "unknown",
            "priority": _issue_field(document, "Priority") or "unknown",
            "status": _issue_field(document, "Status") or "unknown",
            "updated_at": document.get("version") or "unknown",
            "latest_comment": _latest_comment(document),
            "evidence_spans": citation_evidence.get(document["document_id"], []),
            "summary_markdown": summarize_jira_issue_markdown(document),
        }
        for document in related_jira_documents
    ]
    if not prompt_template:
        jira_summary_text = "\n\n".join(
            _structured_jira_summary(
                document,
                evidence_spans=citation_evidence.get(document["document_id"], []),
            )
            for document in related_jira_documents
        )
        evidence_text = "\n".join(
            f"- {citation['document']} v{citation['version']}: {citation.get('evidence_span', '')}"
            for citation in retrieval_payload["retrieval"]["citations"]
        )
        retrieval_payload["ai_prompt"] = build_spec_section_explain_prompt(
            spec_document_id=spec_document["document_id"],
            section_label=section_label,
            section_markdown=section_markdown,
            jira_summary_text=jira_summary_text,
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
        "section": section_context,
        "question": query,
        "retrieval": {
            "result_count": retrieval_payload["retrieval"]["result_count"],
            "citations": citations,
            "has_jira_evidence": bool(jira_citations),
        },
        "related_issues": related_issues,
        "ai_prompt": retrieval_payload["ai_prompt"],
        "answer": retrieval_payload["answer"] if llm_backend else build_spec_section_extractive_answer(
            spec_document_id=spec_document["document_id"],
            section_label=section_label,
            citations=citations,
        ),
    }


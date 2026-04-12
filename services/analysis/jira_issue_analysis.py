from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
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


def _build_pm_issue_fact(document: dict, *, target_date: date, stale_threshold_hours: int) -> dict:
    updated_at = _document_updated_at(document)
    latest_comment = _latest_comment(document)
    reference_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
    stale_cutoff = reference_end - timedelta(hours=stale_threshold_hours)
    updated_today = updated_at is not None and updated_at.date() == target_date
    stale = updated_at is None or updated_at < stale_cutoff
    attention_signals = _pm_attention_signals(document, stale=stale)
    return {
        "document_id": document["document_id"],
        "title": document.get("title", document["document_id"]),
        "owner": _first_issue_field(document, ["Assignee", "Owner"]) or "unknown",
        "priority": _issue_field(document, "Priority") or "unknown",
        "status": _issue_field(document, "Status") or "unknown",
        "updated_at": document.get("version") or "unknown",
        "updated_today": updated_today,
        "stale": stale,
        "latest_comment": latest_comment,
        "attention_signals": attention_signals,
    }


def _format_latest_comment(comment: dict | None) -> str:
    if not comment:
        return "No comment update."
    body = str(comment.get("body") or "").strip() or "No comment body."
    return f"{comment.get('author') or 'unknown'} ({comment.get('created') or 'unknown'}): {body}"


def _render_pm_issue_line(issue: dict) -> str:
    return "\n".join(
        [
            f"- Issue: {issue['document_id']}",
            f"  Summary: {issue['title']}",
            f"  Owner: {issue['owner']}",
            f"  Priority: {issue['priority']}",
            f"  Status: {issue['status']}",
            f"  Updated: {issue['updated_at']}",
            f"  Latest comment: {_format_latest_comment(issue['latest_comment'])}",
            f"  Attention signals: {', '.join(issue['attention_signals']) or 'none'}",
        ]
    )


def _render_pm_attention_item(issue: dict) -> str:
    signals = ", ".join(issue["attention_signals"]) or "none"
    return f"{issue['document_id']}: {issue['title']} | owner={issue['owner']} | signals={signals}"


def _build_pm_executive_summary(
    *,
    reference_date: str,
    active_today: list[dict],
    in_progress_no_update: list[dict],
    attention_items: list[dict],
) -> list[str]:
    summary = [
        f"{len(active_today)} In Progress issue(s) were updated on {reference_date}.",
        f"{len(in_progress_no_update)} In Progress issue(s) had no same-day update.",
    ]
    if attention_items:
        summary.append(
            f"{len(attention_items)} issue(s) need manager attention: "
            + ", ".join(issue["document_id"] for issue in attention_items[:5])
            + "."
        )
    else:
        summary.append("No manager-attention signals were detected from deterministic rules.")
    return summary


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
    issue_facts = [
        _build_pm_issue_fact(document, target_date=target_date, stale_threshold_hours=stale_threshold_hours)
        for document in documents
        if _issue_field(document, "Status") == status_filter
    ]
    active_today = [issue for issue in issue_facts if issue["updated_today"]]
    in_progress_no_update = [issue for issue in issue_facts if not issue["updated_today"]]
    stale_in_progress = [issue for issue in in_progress_no_update if issue["stale"]]
    manager_attention_items = [issue for issue in issue_facts if issue["attention_signals"]]
    executive_summary = _build_pm_executive_summary(
        reference_date=reference_date,
        active_today=active_today,
        in_progress_no_update=in_progress_no_update,
        attention_items=manager_attention_items,
    )

    issue_summaries = "\n\n".join(
        [
            "## Active Today",
            *(_render_pm_issue_line(issue) for issue in active_today),
            "",
            "## In Progress But No Update",
            *(_render_pm_issue_line(issue) for issue in in_progress_no_update),
            "",
            "## Manager Attention",
            *(_render_pm_attention_item(issue) for issue in manager_attention_items),
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
        prompt = build_jira_pm_daily_prompt(
            reference_date=reference_date,
            status_filter=status_filter,
            updated_issue_count=len(active_today),
            stale_issue_count=len(stale_in_progress),
            issue_summaries=issue_summaries,
            prompt_mode=prompt_mode,
        )
    markdown_sections = [
        f"# Jira PM Daily Report ({reference_date})",
        "",
        "## Executive Summary",
        *(f"- {line}" for line in executive_summary),
        "",
        "## Active Today",
        *(_render_pm_issue_line(issue) for issue in active_today),
        "",
        "## In Progress But No Update",
        *(_render_pm_issue_line(issue) for issue in in_progress_no_update),
        "",
        "## Manager Attention",
        *([f"- {_render_pm_attention_item(issue)}" for issue in manager_attention_items] or ["- None"]),
    ]
    payload = {
        "report_profile": "pm-daily",
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
        "manager_attention": [_render_pm_attention_item(issue) for issue in manager_attention_items],
        "manager_attention_items": manager_attention_items,
        "markdown": "\n".join(markdown_sections).strip(),
        "prompt": prompt,
    }
    if llm_backend:
        payload["answer"] = _build_report_llm_answer(prompt, llm_backend, len(issue_facts))
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
        evidence_text = " ".join(citation.get("evidence_span", [])).strip()
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
            f"- {citation['document']} v{citation['version']}: {' '.join(citation.get('evidence_span', []))}"
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
        "space": document.get("metadata", {}).get("space") or document.get("provenance", {}).get("space") or "General",
        "derived_marker": "Derived page - canonical source remains Confluence.",
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
    index_groups: dict[str, list[str]] = {}
    shared_style = """
<style>
:root {
  color-scheme: light;
  --bg: #f5f1e8;
  --paper: #fffdf8;
  --ink: #1f2933;
  --muted: #5b6570;
  --line: #d6cfbf;
  --accent: #a4471c;
  --accent-soft: #f4dfd3;
}
body {
  margin: 0;
  padding: 40px;
  background: linear-gradient(180deg, #f7f3eb 0%, #efe6d8 100%);
  color: var(--ink);
  font-family: Georgia, "Times New Roman", serif;
}
.shell {
  max-width: 1100px;
  margin: 0 auto;
}
.hero,
.page-shell,
.card {
  background: var(--paper);
  border: 1px solid var(--line);
  box-shadow: 0 12px 30px rgba(31, 41, 51, 0.08);
}
.hero,
.page-shell {
  padding: 28px;
}
.eyebrow,
.badge {
  display: inline-block;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: var(--accent-soft);
  color: var(--accent);
}
.group-title {
  margin-top: 28px;
  margin-bottom: 14px;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
}
.card {
  padding: 20px;
}
.card h3,
.page-shell h1 {
  margin-top: 0;
}
.meta {
  color: var(--muted);
  font-size: 14px;
}
.summary {
  margin-top: 14px;
  line-height: 1.6;
}
.traceability {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
a {
  color: var(--accent);
}
</style>
""".strip()
    for payload in page_payloads:
        page_path = pages_dir / f"{payload['document_id']}.html"
        answer_text = escape(payload["answer"]["text"]).replace("\n", "<br/>\n")
        page_html = "\n".join(
            [
                "<!doctype html>",
                "<html><head><meta charset=\"utf-8\"><title>{}</title>{}</head><body><div class=\"shell\">".format(
                    escape(payload["title"]),
                    shared_style,
                ),
                "<article class=\"page-shell\">",
                f"<span class=\"badge\">Derived page</span>",
                f"<h1>{escape(payload['title'])}</h1>",
                f"<p class=\"meta\"><strong>Document ID:</strong> {escape(payload['document_id'])}</p>",
                f"<p class=\"meta\"><strong>Version:</strong> {escape(str(payload.get('version') or ''))}</p>",
                f"<p class=\"meta\"><strong>Space:</strong> {escape(str(payload.get('space') or 'General'))}</p>",
                f"<div class=\"summary\"><h2>Summary</h2><p>{answer_text}</p></div>",
                "<section class=\"traceability\">",
                "<h2>Source Traceability</h2>",
                f"<p><strong>Source:</strong> {escape(str(payload.get('source_uri') or ''))}</p>",
                f"<p><strong>Derived marker:</strong> {escape(str(payload.get('derived_marker') or 'Derived page'))}</p>",
                "</section>",
                "</article>",
                "</div>",
                "</body></html>",
            ]
        )
        page_path.write_text(page_html, encoding="utf-8")
        written_pages.append(str(page_path))
        first_line = payload["answer"]["text"].splitlines()[0] if payload["answer"]["text"] else payload["title"]
        card_html = "\n".join(
            [
                "<article class=\"card\">",
                f"<span class=\"eyebrow\">{escape(str(payload.get('space') or 'General'))}</span>",
                f"<h3><a href=\"pages/{escape(payload['document_id'])}.html\">{escape(payload['title'])}</a></h3>",
                f"<p class=\"meta\">Version {escape(str(payload.get('version') or ''))}</p>",
                f"<p class=\"summary\">{escape(first_line)}</p>",
                "<p class=\"meta\">Derived Confluence Wiki entry with source traceability.</p>",
                "</article>",
            ]
        )
        index_groups.setdefault(str(payload.get("space") or "General"), []).append(card_html)

    grouped_sections = []
    for group_name, cards in index_groups.items():
        grouped_sections.extend(
            [
                f"<h2 class=\"group-title\">{escape(group_name)}</h2>",
                "<section class=\"card-grid\">",
                *cards,
                "</section>",
            ]
        )
    index_html = "\n".join(
        [
            "<!doctype html>",
            f"<html><head><meta charset=\"utf-8\"><title>Derived Confluence Wiki</title>{shared_style}</head><body><div class=\"shell\">",
            "<section class=\"hero\">",
            "<span class=\"eyebrow\">Static export</span>",
            "<h1>Derived Confluence Wiki</h1>",
            "<p>Document-level summaries generated from Confluence sources. These pages are derived views and do not replace canonical source truth.</p>",
            "</section>",
            *grouped_sections,
            "</div>",
            "</body></html>",
        ]
    )
    index_path = root / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    return {"output_dir": str(root), "index_html": str(index_path), "pages": written_pages}

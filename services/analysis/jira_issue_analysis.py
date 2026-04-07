from __future__ import annotations

from datetime import date, datetime, time, timezone

from services.retrieval.citations.assembler import assemble_citation
from services.retrieval.indexing.page_index import build_page_index
from services.retrieval.search.hybrid_search import search_page_index


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
    default_prompt = "Summarize {issue_count} Jira issue(s) for time filter {time_filter}.\n\n{summaries}"
    prompt = (prompt_template or default_prompt).format(
        issue_count=len(filtered),
        time_filter=time_filter,
        summaries="\n\n---\n\n".join(summaries),
    )
    return {
        "time_filter": time_filter,
        "issue_count": len(filtered),
        "issue_ids": [document["document_id"] for document in filtered],
        "markdown": "\n\n---\n\n".join(summaries),
        "prompt": prompt,
    }


def _build_extractive_answer(question: str, citations: list[dict]) -> dict:
    jira_citations = [citation for citation in citations if str(citation["document"]).startswith("SSD-")]
    spec_citations = [citation for citation in citations if not str(citation["document"]).startswith("SSD-")]
    evidence_lines = []
    for citation in citations:
        evidence = " ".join(citation.get("evidence_span", []))
        evidence_lines.append(f"- {citation['document']} v{citation['version']}: {evidence}")

    if jira_citations and spec_citations:
        conclusion = "The retrieved evidence includes both Jira issue context and spec evidence, so the question can be reviewed against the selected spec."
    elif jira_citations:
        conclusion = "The retrieved evidence includes Jira issue context but no selected spec evidence."
    elif spec_citations:
        conclusion = "The retrieved evidence includes selected spec evidence but no Jira issue context."
    else:
        conclusion = "No supporting Jira or spec evidence was retrieved."

    return {
        "mode": "extractive",
        "text": "\n".join(
            [
                f"Question: {question}",
                "",
                conclusion,
                "",
                "Evidence:",
                *evidence_lines,
            ]
        ).strip(),
        "citation_count": len(citations),
    }


def build_jira_spec_question_payload(
    *,
    jira_document: dict,
    spec_documents: list[dict],
    question: str,
    allowed_policies: set[str],
    top_k: int = 5,
    prompt_template: str | None = None,
) -> dict:
    documents = [jira_document, *spec_documents]
    results = search_page_index(build_page_index(documents), question, allowed_policies, top_k=top_k)
    citations = [assemble_citation(result) for result in results]
    jira_citations = [citation for citation in citations if citation["document"] == jira_document["document_id"]]
    spec_citations = [citation for citation in citations if citation["document"] != jira_document["document_id"]]
    evidence_lines = []
    for citation in citations:
        evidence = " ".join(citation.get("evidence_span", []))
        evidence_lines.append(f"- {citation['document']} v{citation['version']}: {evidence}")
    evidence_text = "\n".join(evidence_lines)
    summary_markdown = summarize_jira_issue_markdown(jira_document)
    default_prompt = "\n".join(
        [
            "Answer the Jira question using only the retrieved Jira and spec evidence.",
            "Question: {question}",
            "Evidence:",
            "{evidence}",
        ]
    ).strip()
    prompt = (prompt_template or default_prompt).format(
        question=question,
        jira_issue_id=jira_document["document_id"],
        summary_markdown=summary_markdown,
        evidence=evidence_text,
    )

    return {
        "question": question,
        "jira_issue_id": jira_document["document_id"],
        "summary_markdown": summary_markdown,
        "retrieval": {
            "result_count": len(results),
            "citations": citations,
            "has_jira_evidence": bool(jira_citations),
            "has_spec_evidence": bool(spec_citations),
        },
        "ai_prompt": prompt,
        "answer": _build_extractive_answer(question, citations),
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
) -> dict:
    time_report = build_jira_time_report(
        jira_documents,
        updated_from_iso=updated_from_iso,
        updated_to_iso=updated_to_iso,
        updated_on_date=updated_on_date,
        updated_at_iso=updated_at_iso,
        prompt_template=prompt_template,
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

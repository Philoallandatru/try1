from __future__ import annotations

from datetime import date, datetime, time, timezone

from services.analysis.llm_backends import LLMBackend
from services.analysis.jira_profiles import build_jira_report_prompt, build_jira_spec_extractive_answer
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

from __future__ import annotations

from services.analysis.llm_backends import LLMBackend


SECTION_RUNNERS: dict[str, dict[str, str]] = {
    "rca": {
        "label": "RCA",
        "version": "v1",
        "instruction": "Explain likely root cause, failure mechanism, and what evidence supports or weakens the root-cause hypothesis.",
    },
    "spec_impact": {
        "label": "Spec Impact",
        "version": "v1",
        "instruction": "Explain which specifications, clauses, or requirements appear affected and what evidence anchors that impact.",
    },
    "decision_brief": {
        "label": "Decision Brief",
        "version": "v1",
        "instruction": "Summarize decision-ready takeaways, key risks, and what needs confirmation before action.",
    },
    "general_summary": {
        "label": "General Summary",
        "version": "v1",
        "instruction": "Summarize the issue and the most important cross-source evidence for a broad engineering audience.",
    },
}


def _section_evidence_text(citations: list[dict]) -> str:
    if not citations:
        return "No evidence retrieved."
    lines: list[str] = []
    for citation in citations:
        evidence = " ".join(citation.get("evidence_span", []))
        lines.append(f"- {citation['document']} v{citation['version']}: {evidence}")
    return "\n".join(lines)


def _combined_citations(shared_citations: list[dict], followup_citations: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    combined: list[dict] = []
    for citation in [*shared_citations, *followup_citations]:
        key = (
            citation.get("document"),
            citation.get("version"),
            citation.get("page"),
            citation.get("section"),
            tuple(citation.get("evidence_span", [])),
        )
        if key in seen:
            continue
        seen.add(key)
        combined.append(citation)
    return combined


def _section_prompt(
    *,
    section_name: str,
    issue_summary: str,
    citations: list[dict],
) -> str:
    section = SECTION_RUNNERS[section_name]
    return "\n".join(
        [
            f"Section: {section['label']}",
            f"Section version: {section['version']}",
            section["instruction"],
            "",
            "## Jira Issue Context",
            issue_summary,
            "",
            "## Shared Retrieval Evidence",
            _section_evidence_text(citations),
        ]
    ).strip()


def _extractive_section_answer(section_name: str, citations: list[dict]) -> dict:
    section = SECTION_RUNNERS[section_name]
    if not citations:
        summary = "No shared evidence is available for this section yet."
    else:
        summary = f"{len(citations)} shared evidence citation(s) are available for {section['label']}."
    return {
        "mode": "extractive",
        "text": summary,
        "citation_count": len(citations),
    }


def build_section_outputs(
    *,
    issue_summary: str,
    shared_citations: list[dict],
    section_retrieval_hooks: dict[str, dict],
    llm_backend: LLMBackend | None = None,
) -> dict[str, dict]:
    outputs: dict[str, dict] = {}
    for section_name in SECTION_RUNNERS:
        citations = _combined_citations(
            shared_citations,
            section_retrieval_hooks[section_name].get("followup_citations", []),
        )
        prompt = _section_prompt(
            section_name=section_name,
            issue_summary=issue_summary,
            citations=citations,
        )
        if llm_backend:
            answer = {
                "mode": "local-llm",
                "backend": llm_backend.name,
                "text": llm_backend.generate(prompt).strip(),
                "citation_count": len(citations),
            }
        else:
            answer = _extractive_section_answer(section_name, citations)
        outputs[section_name] = {
            "section_name": section_name,
            "label": SECTION_RUNNERS[section_name]["label"],
            "runner_version": SECTION_RUNNERS[section_name]["version"],
            "followup_retrieval": section_retrieval_hooks[section_name],
            "citations": citations,
            "prompt": prompt,
            "answer": answer,
        }
    return outputs


def build_composite_report_markdown(
    *,
    issue_id: str,
    title: str,
    section_outputs: dict[str, dict],
) -> str:
    lines = [f"# Deep Analysis Report: {title}", "", f"Issue ID: {issue_id}", ""]
    for section_name in ("rca", "spec_impact", "decision_brief", "general_summary"):
        section = section_outputs[section_name]
        citation_lines = []
        for citation in section.get("citations", []):
            evidence = " ".join(citation.get("evidence_span", []))
            citation_lines.append(f"- `{citation['document']}` v{citation['version']}: {evidence}")
        lines.extend(
            [
                f"## {section['label']}",
                "",
                section["answer"]["text"],
                "",
                "### Evidence",
                "",
                *(citation_lines or ["- No shared evidence retrieved."]),
                "",
                f"Section artifact: `section_outputs/{section_name}.json`",
                "",
            ]
        )
    return "\n".join(lines).strip()

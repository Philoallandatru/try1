from __future__ import annotations


def build_jira_report_prompt(
    *,
    issue_count: int,
    time_filter: str,
    summaries: str,
    prompt_mode: str,
) -> str:
    mode_instructions = {
        "strict": [
            "Mode: strict Jira report summarization.",
            "If evidence is missing, state the gap instead of guessing impact or root cause.",
            "Do not infer release risk beyond the Jira fields and comments shown below.",
            "Do not say no follow-up is needed when the Jira text mentions validation, retest, or unresolved status.",
        ],
        "balanced": [
            "Mode: balanced Jira report summarization.",
            "Separate direct Jira facts from engineering interpretation.",
            "Call out uncertainty where fields or comments are incomplete.",
        ],
        "exploratory": [
            "Mode: exploratory Jira report triage.",
            "Label hypotheses explicitly and keep them separate from known Jira facts.",
            "Use hypotheses only to propose follow-up checks.",
        ],
    }[prompt_mode]

    return "\n".join(
        [
            "You are an SSD firmware triage reporter.",
            "Summarize the Jira issues using only the Jira issue summaries below.",
            *mode_instructions,
            "",
            "Output format:",
            "1. Executive summary: 2-4 bullets.",
            "2. Issue table: issue, priority, status, root cause, fix, evidence gap.",
            "3. Follow-up actions: only actions explicitly supported by the Jira text; preserve retest or validation needs.",
            "",
            f"Time filter: {time_filter}",
            f"Issue count: {issue_count}",
            "",
            "## Jira Issue Summaries",
            summaries or "No Jira issues matched the selected filter.",
        ]
    ).strip()


def build_jira_spec_extractive_answer(question: str, citations: list[dict]) -> dict:
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

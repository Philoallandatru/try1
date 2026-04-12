from __future__ import annotations


def build_jira_pm_daily_prompt(
    *,
    reference_date: str,
    status_filter: str,
    updated_issue_count: int,
    stale_issue_count: int,
    issue_summaries: str,
    prompt_mode: str,
) -> str:
    mode_instructions = {
        "strict": [
            "Mode: strict project-manager status reporting.",
            "Do not change issue status, timestamps, ownership, or priority.",
            "Use the latest comment only as an observed progress signal, not as a guarantee of completion.",
            "If the evidence does not support a risk or next step, state the gap instead of guessing.",
        ],
        "balanced": [
            "Mode: balanced project-manager status reporting.",
            "Separate direct Jira facts from lightweight manager interpretation.",
            "Call out uncertainty when the latest comment is unclear or absent.",
        ],
        "exploratory": [
            "Mode: exploratory project-manager status reporting.",
            "Label hypotheses explicitly and keep them separate from Jira facts.",
            "Use hypotheses only for follow-up suggestions.",
        ],
    }[prompt_mode]
    return "\n".join(
        [
            "You are an SSD program reporting assistant.",
            "Summarize today's In Progress Jira state for a project manager using only the prepared issue evidence below.",
            *mode_instructions,
            "",
            "Output format:",
            "## Executive Summary",
            "- 3 to 5 bullets for managers",
            "",
            "## Active Today",
            "- issue: one sentence",
            "- latest signal: one sentence",
            "- risk or next step: one sentence only if directly supported",
            "",
            "## In Progress But No Update",
            "- list stale in-progress issues and why they need attention",
            "",
            "## Manager Attention",
            "- blocked, retest pending, validation pending, or unclear ownership only when supported",
            "",
            f"Reference date: {reference_date}",
            f"Status filter: {status_filter}",
            f"Updated today: {updated_issue_count}",
            f"Stale in progress: {stale_issue_count}",
            "",
            "## Prepared Issue Evidence",
            issue_summaries or "No matching issues.",
        ]
    ).strip()


def build_spec_section_explain_prompt(
    *,
    spec_document_id: str,
    section_label: str,
    section_markdown: str,
    evidence_text: str,
    prompt_mode: str,
) -> str:
    mode_instructions = {
        "strict": [
            "Mode: strict section explanation.",
            "Treat the spec as authoritative and Jira as supporting engineering context.",
            "Do not say Jira changes or overrides the spec.",
            "If Jira evidence is weak or absent, say so explicitly.",
        ],
        "balanced": [
            "Mode: balanced section explanation.",
            "Separate direct section meaning from engineering interpretation.",
            "Call out uncertainty and missing issue support.",
        ],
        "exploratory": [
            "Mode: exploratory section explanation.",
            "Label hypotheses explicitly and keep them separate from spec text.",
            "Use weak Jira signals only to suggest follow-up checks.",
        ],
    }[prompt_mode]
    return "\n".join(
        [
            "You are an SSD firmware and specification explanation assistant.",
            "Explain the selected spec section using only the section text and retrieved Jira evidence.",
            *mode_instructions,
            "",
            "Output format:",
            "## Section Intent",
            "- 2 to 4 sentences describing what the section directly says",
            "",
            "## Jira Evidence",
            "- related issues with one-sentence relevance each",
            "",
            "## Engineering Interpretation",
            "- explain how the Jira issues help interpret the section in practice",
            "",
            "## Evidence Gaps",
            "- explicit missing proof or weak linkage",
            "",
            f"Spec document: {spec_document_id}",
            f"Section: {section_label}",
            "",
            "## Spec Section",
            section_markdown,
            "",
            "## Retrieved Jira Evidence",
            evidence_text or "No Jira evidence.",
        ]
    ).strip()


def build_confluence_wiki_summary_prompt(
    *,
    title: str,
    source_uri: str,
    page_markdown: str,
    prompt_mode: str,
) -> str:
    mode_instructions = {
        "strict": [
            "Mode: strict derived wiki summary.",
            "Use only the provided Confluence page content.",
            "Do not invent decisions, action items, or ownership.",
        ],
        "balanced": [
            "Mode: balanced derived wiki summary.",
            "Separate direct page content from concise interpretation.",
            "Call out unclear or missing decisions.",
        ],
        "exploratory": [
            "Mode: exploratory derived wiki summary.",
            "Label hypotheses explicitly and do not present them as established facts.",
        ],
    }[prompt_mode]
    return "\n".join(
        [
            "You are an internal knowledge distillation assistant.",
            "Summarize the Confluence page into a derived wiki entry without replacing source truth.",
            *mode_instructions,
            "",
            "Output format:",
            "## Summary",
            "- 3 to 5 sentences",
            "",
            "## Key Points",
            "- flat bullets of important facts",
            "",
            "## Decisions",
            "- only explicit decisions from the page",
            "",
            "## Open Questions / Risks",
            "- only explicit unresolved items or clear evidence gaps",
            "",
            f"Title: {title}",
            f"Source URI: {source_uri}",
            "",
            "## Page Content",
            page_markdown or "No page content.",
        ]
    ).strip()

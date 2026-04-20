from __future__ import annotations

from services.analysis.llm_backends import LLMBackend
from services.analysis.jira_issue_analysis import summarize_jira_issue_markdown
from services.analysis.image_evidence import build_image_evidence_summary, format_image_evidence_summary
from services.analysis.knowledge_compiler import build_knowledge_artifacts
from services.analysis.search_enhancer import build_enhanced_search_query
from services.analysis.section_analysis import build_composite_report_markdown, build_section_outputs
from services.connectors.jira.issue_type_profiles import route_jira_issue_type
from services.retrieval.citations.assembler import assemble_citation
from services.retrieval.engine import BM25_ENGINE, build_shared_retrieval_bundle
from services.retrieval.indexing.page_index import build_page_index
from services.retrieval.search.bm25_search import build_bm25_index, search_bm25


ANALYSIS_PROFILES: dict[str, dict[str, str]] = {
    "defect": {
        "label": "Root Cause Analysis",
        "assistant_intro": "You are an SSD firmware defect root cause analysis assistant.",
        "task_instruction": (
            "Perform a deep root cause analysis of this Jira defect issue using "
            "the retrieved Confluence and spec evidence. Focus on: root cause identification, "
            "impact assessment, and fix suggestions."
        ),
    },
    "requirement": {
        "label": "Requirement Traceability Analysis",
        "assistant_intro": "You are an SSD requirement traceability and gap analysis assistant.",
        "task_instruction": (
            "Perform a requirement traceability analysis of this Jira requirement issue using "
            "the retrieved Confluence and spec evidence. Focus on: spec coverage, "
            "gap analysis, and requirement completeness."
        ),
    },
    "requirement_change": {
        "label": "Requirement Change Impact Analysis",
        "assistant_intro": "You are an SSD requirement change impact analysis assistant.",
        "task_instruction": (
            "Analyze the impact of this requirement change using the retrieved Confluence "
            "and spec evidence. Focus on: affected specifications, change scope, and risk assessment."
        ),
    },
    "change_control": {
        "label": "Change Impact Analysis",
        "assistant_intro": "You are an SSD component change impact analysis assistant.",
        "task_instruction": (
            "Analyze the impact of this component change using the retrieved Confluence "
            "and spec evidence. Focus on: affected components, risk assessment, "
            "and downstream dependencies."
        ),
    },
}

DEFAULT_PROFILE: dict[str, str] = {
    "label": "General Deep Analysis",
    "assistant_intro": "You are an SSD engineering deep analysis assistant.",
    "task_instruction": (
        "Perform a deep analysis of this Jira issue using the retrieved Confluence "
        "and spec evidence. Summarize the issue context, cross-source evidence, and key insights."
    ),
}

SECTION_RETRIEVAL_NAMES = (
    "rca",
    "spec_impact",
    "decision_brief",
    "general_summary",
)

SECTION_SCOPE_HINTS = {
    "rca": "failure mechanism, error-code, and root-cause evidence",
    "spec_impact": "spec clause, requirement, and component impact evidence",
    "decision_brief": "decision, risk, and tradeoff evidence",
    "general_summary": "broad cross-source overview evidence",
}


def build_deep_analysis_from_documents(
    *,
    documents: list[dict],
    issue_id: str,
    allowed_policies: set[str],
    top_k: int = 5,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    """Build a deep-analysis payload from a mixed document snapshot."""
    matching_documents = [document for document in documents if document["document_id"] == issue_id]
    if not matching_documents:
        raise ValueError(f"Issue not found in snapshot: {issue_id}")

    jira_document = next(
        (document for document in matching_documents if document.get("source_type") == "jira"),
        None,
    )
    if jira_document is None:
        raise ValueError(f"Document is not a Jira issue: {issue_id}")

    confluence_documents = [document for document in documents if document.get("source_type") == "confluence"]
    spec_documents = [
        document
        for document in documents
        if document.get("source_type") not in ("jira", "confluence")
        and document.get("authority_level") in {"canonical", "supporting"}
    ]
    return build_deep_analysis_payload(
        jira_document=jira_document,
        confluence_documents=confluence_documents,
        spec_documents=spec_documents,
        allowed_policies=allowed_policies,
        top_k=top_k,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
    )


def _extract_search_keywords(document: dict) -> list[str]:
    """Extract meaningful search keywords from a Jira document."""
    keywords: list[str] = []
    title = document.get("title", "")
    if title:
        keywords.append(title)

    issue_fields = document.get("metadata", {}).get("issue_fields", {})
    for field_name in ("Summary", "Component/s", "Labels", "Fix Version/s"):
        value = issue_fields.get(field_name)
        if value and value not in (None, "", []):
            if isinstance(value, list):
                keywords.extend(str(v) for v in value if v)
            else:
                keywords.append(str(value))

    markdown = document.get("markdown", "")
    if markdown:
        first_lines = " ".join(markdown.splitlines()[:3]).strip()
        if first_lines:
            keywords.append(first_lines[:200])

    return keywords


def _build_search_query(document: dict) -> str:
    """Build a combined search query from the document keywords."""
    keywords = _extract_search_keywords(document)
    return " ".join(keywords[:5]).strip() or document.get("document_id", "unknown")


def _search_cross_source(
    *,
    source_documents: list[dict],
    query: str,
    allowed_policies: set[str],
    top_k: int = 5,
) -> list[dict]:
    """Search across a set of source documents and return citations."""
    if not source_documents:
        return []
    page_index = build_page_index(source_documents)
    bm25_index = build_bm25_index(page_index)
    results = search_bm25(bm25_index, query, allowed_policies, top_k=top_k)
    return [assemble_citation(result) for result in results]


def _build_shared_secondary_retrieval_bundle(
    *,
    confluence_documents: list[dict],
    spec_documents: list[dict],
    query: str,
    allowed_policies: set[str],
    top_k: int,
) -> dict:
    documents = [*confluence_documents, *spec_documents]
    entries = build_page_index(documents)
    bundle = build_shared_retrieval_bundle(
        engine=BM25_ENGINE,
        entries=entries,
        query=query,
        allowed_policies=allowed_policies,
        top_k=top_k,
    )
    document_source_types = {
        document["document_id"]: document.get("source_type")
        for document in documents
    }
    citations = [assemble_citation(result) for result in bundle["results"]]
    source_breakdown: dict[str, dict] = {
        source_type: {"result_count": 0, "document_ids": []}
        for source_type in sorted(set(document_source_types.values()))
    }
    for result in bundle["results"]:
        source_type = document_source_types.get(result["document_id"], "unknown")
        bucket = source_breakdown.setdefault(
            source_type,
            {"result_count": 0, "document_ids": []},
        )
        bucket["result_count"] += 1
        if result["document_id"] not in bucket["document_ids"]:
            bucket["document_ids"].append(result["document_id"])
    return {
        **bundle,
        "citations": citations,
        "source_breakdown": source_breakdown,
    }


def _split_bundle_citations_by_source_type(bundle: dict, source_type: str) -> list[dict]:
    return [
        citation
        for citation, result in zip(bundle.get("citations", []), bundle.get("results", []), strict=False)
        if result.get("source_type") == source_type
    ]


def _json_safe(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _build_section_retrieval_hooks_with_context(
    *,
    jira_document: dict,
    entries: list[dict],
    query: str,
    allowed_policies: set[str],
    top_k: int,
) -> dict[str, dict]:
    hooks: dict[str, dict] = {}
    followup_top_k = max(1, min(3, top_k))
    for section_name in SECTION_RETRIEVAL_NAMES:
        scope_hint = SECTION_SCOPE_HINTS[section_name]
        enhanced = build_enhanced_search_query(
            base_query=query,
            jira_document=jira_document,
            section_name=section_name,
            scope_hint=scope_hint,
        )
        followup_results = (
            BM25_ENGINE.search(
                entries,
                enhanced["query"],
                allowed_policies,
                top_k=followup_top_k,
            )
            if entries
            else []
        )
        followup_citations = [assemble_citation(result) for result in followup_results]
        hooks[section_name] = {
            "mode": "append-only",
            "status": "completed" if entries else "no-corpus",
            "base_bundle": "shared_retrieval_bundle",
            "base_query": query,
            "enhanced_query": enhanced["query"],
            "enhancement": enhanced,
            "allowed_policies": sorted(allowed_policies),
            "top_k": followup_top_k,
            "scope_hint": scope_hint,
            "followup_results": _json_safe(followup_results),
            "followup_citations": followup_citations,
        }
    return hooks


def _select_analysis_profile(document: dict) -> dict[str, str]:
    """Select the analysis profile based on issue_family routing."""
    issue_type_raw = document.get("metadata", {}).get("issue_fields", {}).get("Issue Type")
    if not issue_type_raw:
        issue_type_raw = document.get("metadata", {}).get("issue_type_raw")
    routing = route_jira_issue_type(issue_type_raw)
    issue_family = routing.get("issue_family", "unknown")
    return ANALYSIS_PROFILES.get(issue_family, DEFAULT_PROFILE)


def _build_evidence_text(citations: list[dict]) -> str:
    """Format citations into an evidence text block."""
    if not citations:
        return "No evidence retrieved."
    lines: list[str] = []
    for citation in citations:
        evidence = " ".join(citation.get("evidence_span", []))
        lines.append(f"- {citation['document']} v{citation['version']}: {evidence}")
    return "\n".join(lines)


def _build_deep_analysis_prompt(
    *,
    issue_summary: str,
    confluence_evidence_text: str,
    spec_evidence_text: str,
    image_evidence_text: str,
    profile: dict[str, str],
    prompt_mode: str = "strict",
) -> str:
    """Assemble the deep analysis prompt from all evidence sources."""
    mode_instructions = {
        "strict": [
            "Mode: strict evidence review.",
            "If the evidence does not directly support a conclusion, say the evidence is insufficient.",
            "Do not infer facts that are not grounded in the retrieved evidence.",
        ],
        "balanced": [
            "Mode: balanced evidence review.",
            "Separate direct evidence from reasonable inference.",
            "Call out uncertainty and the missing evidence needed to strengthen the conclusion.",
        ],
        "exploratory": [
            "Mode: exploratory evidence review.",
            "Label hypotheses explicitly and do not present them as established facts.",
            "Use hypotheses only to suggest follow-up checks, not to claim final conclusions.",
        ],
    }
    if prompt_mode not in mode_instructions:
        raise ValueError(f"Unsupported prompt mode: {prompt_mode}")

    return "\n".join(
        [
            profile["assistant_intro"],
            profile["task_instruction"],
            *mode_instructions[prompt_mode],
            "",
            "Output format:",
            "1. Summary: concise issue overview.",
            "2. Cross-source evidence: cite Confluence and spec evidence with document IDs.",
            "3. Analysis: root cause / traceability / impact based on issue family.",
            "4. Gaps: missing evidence or unanswered questions.",
            "5. Recommendations: suggested next steps.",
            "",
            "## Jira Issue Context",
            issue_summary,
            "",
            "## Confluence Evidence",
            confluence_evidence_text,
            "",
            "## Specification Evidence",
            spec_evidence_text,
            "",
            "## Image Evidence Status",
            image_evidence_text,
        ]
    ).strip()


def _extractive_deep_answer(
    *,
    issue_id: str,
    profile: dict[str, str],
    confluence_citations: list[dict],
    spec_citations: list[dict],
) -> dict:
    """Build a deterministic extractive answer when no LLM is available."""
    all_citations = confluence_citations + spec_citations
    if not all_citations:
        conclusion = "No cross-source evidence found for this issue."
    elif confluence_citations and spec_citations:
        conclusion = (
            f"Cross-source evidence found: {len(confluence_citations)} Confluence hit(s) "
            f"and {len(spec_citations)} spec hit(s). Review cited evidence directly."
        )
    elif confluence_citations:
        conclusion = f"{len(confluence_citations)} Confluence hit(s) found. No spec evidence."
    else:
        conclusion = f"{len(spec_citations)} spec hit(s) found. No Confluence evidence."

    evidence_lines: list[str] = []
    for citation in all_citations:
        evidence = " ".join(citation.get("evidence_span", []))
        evidence_lines.append(f"- {citation['document']} v{citation['version']}: {evidence}")

    return {
        "mode": "extractive",
        "profile": profile["label"],
        "text": "\n".join(
            [
                f"Deep analysis ({profile['label']}) for {issue_id}",
                "",
                conclusion,
                "",
                "Evidence:",
                *(evidence_lines or ["- None"]),
            ]
        ).strip(),
        "citation_count": len(all_citations),
    }


def build_deep_analysis_payload(
    *,
    jira_document: dict,
    confluence_documents: list[dict] | None = None,
    spec_documents: list[dict] | None = None,
    allowed_policies: set[str],
    top_k: int = 5,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    """Build a deep analysis payload for a single Jira issue.

    Performs cross-source retrieval against Confluence and spec documents,
    selects an analysis profile based on issue_family routing, and
    assembles a structured report with optional LLM enrichment.
    """
    confluence_documents = confluence_documents or []
    spec_documents = spec_documents or []
    issue_id = jira_document["document_id"]

    # 1. Summarize the issue
    issue_summary = summarize_jira_issue_markdown(jira_document)

    # 2. Build search query from issue content
    search_query = _build_search_query(jira_document)

    # 3. Build one shared secondary retrieval bundle baseline
    secondary_documents = [*confluence_documents, *spec_documents]
    secondary_entries = build_page_index(secondary_documents)
    shared_retrieval_bundle = _build_shared_secondary_retrieval_bundle(
        confluence_documents=confluence_documents,
        spec_documents=spec_documents,
        query=search_query,
        allowed_policies=allowed_policies,
        top_k=top_k,
    )
    confluence_citations = _split_bundle_citations_by_source_type(shared_retrieval_bundle, "confluence")
    spec_citations = [
        citation
        for citation, result in zip(
            shared_retrieval_bundle.get("citations", []),
            shared_retrieval_bundle.get("results", []),
            strict=False,
        )
        if result.get("source_type") != "confluence"
        and result.get("authority_level") in {"canonical", "supporting"}
    ]

    # 5. Select analysis profile based on issue_family
    profile = _select_analysis_profile(jira_document)

    # 6. Build evidence texts
    confluence_evidence_text = _build_evidence_text(confluence_citations)
    spec_evidence_text = _build_evidence_text(spec_citations)
    image_evidence = build_image_evidence_summary(
        [jira_document, *confluence_documents, *spec_documents]
    )
    image_evidence_text = format_image_evidence_summary(image_evidence)

    # 7. Build the analysis prompt
    analysis_prompt = _build_deep_analysis_prompt(
        issue_summary=issue_summary,
        confluence_evidence_text=confluence_evidence_text,
        spec_evidence_text=spec_evidence_text,
        image_evidence_text=image_evidence_text,
        profile=profile,
        prompt_mode=prompt_mode,
    )

    # 8. Generate answer (LLM or extractive)
    all_citations = confluence_citations + spec_citations
    if llm_backend:
        answer = {
            "mode": "local-llm",
            "backend": llm_backend.name,
            "profile": profile["label"],
            "text": llm_backend.generate(analysis_prompt).strip(),
            "citation_count": len(all_citations),
        }
    else:
        answer = _extractive_deep_answer(
            issue_id=issue_id,
            profile=profile,
            confluence_citations=confluence_citations,
            spec_citations=spec_citations,
        )

    # 9. Assemble routing metadata
    issue_type_raw = jira_document.get("metadata", {}).get("issue_fields", {}).get("Issue Type")
    if not issue_type_raw:
        issue_type_raw = jira_document.get("metadata", {}).get("issue_type_raw")
    routing = route_jira_issue_type(issue_type_raw)

    section_retrieval_hooks = _build_section_retrieval_hooks_with_context(
        jira_document=jira_document,
        entries=secondary_entries,
        query=search_query,
        allowed_policies=allowed_policies,
        top_k=top_k,
    )
    section_outputs = build_section_outputs(
        issue_summary=issue_summary,
        shared_citations=shared_retrieval_bundle["citations"],
        section_retrieval_hooks=section_retrieval_hooks,
        llm_backend=llm_backend,
    )
    composite_report = build_composite_report_markdown(
        issue_id=issue_id,
        title=jira_document.get("title", issue_id),
        section_outputs=section_outputs,
    )
    composite_report_payload = {
        "format": "markdown",
        "content": composite_report,
    }
    knowledge_artifacts = build_knowledge_artifacts(
        jira_document=jira_document,
        shared_citations=shared_retrieval_bundle["citations"],
        confluence_citations=confluence_citations,
        composite_report=composite_report_payload,
    )

    return {
        "issue_id": issue_id,
        "title": jira_document.get("title", issue_id),
        "issue_summary": issue_summary,
        "routing": routing,
        "analysis_profile": profile["label"],
        "search_query": search_query,
        "shared_retrieval_bundle": shared_retrieval_bundle,
        "section_retrieval_hooks": section_retrieval_hooks,
        "section_outputs": section_outputs,
        "composite_report": composite_report_payload,
        "knowledge_artifacts": knowledge_artifacts,
        "image_evidence": image_evidence,
        "confluence_evidence": {
            "citation_count": len(confluence_citations),
            "citations": confluence_citations,
        },
        "spec_evidence": {
            "citation_count": len(spec_citations),
            "citations": spec_citations,
        },
        "cross_source_citations": all_citations,
        "analysis_prompt": analysis_prompt,
        "answer": answer,
    }

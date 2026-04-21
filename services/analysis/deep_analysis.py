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
        "label": "根因分析",
        "assistant_intro": "你是一位SSD固件缺陷根因分析专家。",
        "task_instruction": (
            "基于检索到的Confluence文档和规格说明证据，对此Jira缺陷问题进行深度根因分析。\n"
            "分析要求：\n"
            "1. 根因识别：分析可能的根本原因，包括代码逻辑、配置错误、时序问题、资源竞争等\n"
            "2. 失效机制：解释问题是如何发生的，触发条件和传播路径\n"
            "3. 影响评估：评估问题的严重程度、影响范围（功能模块、性能、数据完整性）\n"
            "4. 证据链：引用具体的规格条款、设计文档、测试结果来支撑分析结论\n"
            "5. 修复建议：提供具体的修复方案，包括代码修改点、配置调整、测试验证方法\n"
            "6. 预防措施：建议如何避免类似问题再次发生"
        ),
    },
    "requirement": {
        "label": "需求追溯分析",
        "assistant_intro": "你是一位SSD需求追溯和差距分析专家。",
        "task_instruction": (
            "基于检索到的Confluence文档和规格说明证据，对此Jira需求问题进行需求追溯分析。\n"
            "分析要求：\n"
            "1. 规格覆盖：识别需求对应的规格条款（NVMe、SATA、PCIe等标准）\n"
            "2. 实现状态：评估需求的实现完整性，是否完全满足规格要求\n"
            "3. 差距分析：指出当前实现与规格要求之间的差距\n"
            "4. 依赖关系：分析需求的上下游依赖，包括硬件依赖、固件模块依赖\n"
            "5. 测试覆盖：评估测试用例是否充分覆盖需求的各个方面\n"
            "6. 风险评估：识别需求实现中的潜在风险和不确定性"
        ),
    },
    "requirement_change": {
        "label": "需求变更影响分析",
        "assistant_intro": "你是一位SSD需求变更影响分析专家。",
        "task_instruction": (
            "基于检索到的Confluence文档和规格说明证据，分析此需求变更的影响。\n"
            "分析要求：\n"
            "1. 变更范围：明确变更涉及的功能模块、接口、数据结构\n"
            "2. 规格影响：分析变更对相关规格条款的影响，是否引入新的合规性要求\n"
            "3. 架构影响：评估对系统架构、模块交互、性能的影响\n"
            "4. 兼容性：分析向后兼容性、与其他功能的兼容性\n"
            "5. 测试影响：识别需要新增或修改的测试用例\n"
            "6. 风险评估：评估变更引入的风险，包括回归风险、性能风险、稳定性风险\n"
            "7. 实施建议：提供分阶段实施方案和验证策略"
        ),
    },
    "change_control": {
        "label": "变更影响分析",
        "assistant_intro": "你是一位SSD组件变更影响分析专家。",
        "task_instruction": (
            "基于检索到的Confluence文档和规格说明证据，分析此组件变更的影响。\n"
            "分析要求：\n"
            "1. 受影响组件：识别所有直接和间接受影响的固件模块、硬件组件\n"
            "2. 接口影响：分析对内部接口、外部接口（Host、NAND）的影响\n"
            "3. 性能影响：评估对IOPS、延迟、带宽、功耗的影响\n"
            "4. 下游依赖：分析对依赖此组件的其他模块的影响\n"
            "5. 验证策略：提供完整的验证方案，包括单元测试、集成测试、系统测试\n"
            "6. 风险评估：识别高风险区域，提供风险缓解措施\n"
            "7. 回滚方案：提供变更失败时的回滚策略"
        ),
    },
}

DEFAULT_PROFILE: dict[str, str] = {
    "label": "综合深度分析",
    "assistant_intro": "你是一位SSD工程深度分析专家。",
    "task_instruction": (
        "基于检索到的Confluence文档和规格说明证据，对此Jira问题进行综合深度分析。\n"
        "分析要求：\n"
        "1. 问题概述：总结问题的核心内容和背景\n"
        "2. 跨源证据：整合Confluence文档和规格说明中的相关证据\n"
        "3. 技术分析：从技术角度深入分析问题的本质\n"
        "4. 关键洞察：提供有价值的技术洞察和发现\n"
        "5. 行动建议：提供具体的后续行动建议"
    ),
}

SECTION_RETRIEVAL_NAMES = (
    "rca",
    "spec_impact",
    "decision_brief",
    "general_summary",
)

SECTION_SCOPE_HINTS = {
    "rca": "失效机制、错误代码、根因证据",
    "spec_impact": "规格条款、需求、组件影响证据",
    "decision_brief": "决策、风险、权衡证据",
    "general_summary": "跨源综合概览证据",
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
        return "未检索到相关证据。"
    lines: list[str] = []
    for citation in citations:
        evidence = citation.get("evidence_span", "")
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
            "模式：严格证据审查",
            "如果证据不能直接支持结论，请明确说明证据不足。",
            "不要推断未在检索证据中明确体现的事实。",
        ],
        "balanced": [
            "模式：平衡证据审查",
            "区分直接证据和合理推断。",
            "指出不确定性以及需要哪些额外证据来加强结论。",
        ],
        "exploratory": [
            "模式：探索性证据审查",
            "明确标注假设，不要将其作为既定事实呈现。",
            "仅使用假设来建议后续检查，而非声称最终结论。",
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
            "输出格式：",
            "1. 概述：简明的问题概览",
            "2. 跨源证据：引用Confluence和规格证据，标注文档ID",
            "3. 分析：根据问题类型进行根因/追溯/影响分析",
            "4. 差距：缺失的证据或未解答的问题",
            "5. 建议：建议的后续步骤",
            "",
            "## Jira问题上下文",
            issue_summary,
            "",
            "## Confluence证据",
            confluence_evidence_text,
            "",
            "## 规格说明证据",
            spec_evidence_text,
            "",
            "## 图像证据状态",
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
        conclusion = "未找到此问题的跨源证据。"
    elif confluence_citations and spec_citations:
        conclusion = (
            f"找到跨源证据：{len(confluence_citations)}条Confluence证据 "
            f"和{len(spec_citations)}条规格证据。请直接查看引用的证据。"
        )
    elif confluence_citations:
        conclusion = f"找到{len(confluence_citations)}条Confluence证据。未找到规格证据。"
    else:
        conclusion = f"找到{len(spec_citations)}条规格证据。未找到Confluence证据。"

    evidence_lines: list[str] = []
    for citation in all_citations:
        evidence = citation.get("evidence_span", "")
        evidence_lines.append(f"- {citation['document']} v{citation['version']}: {evidence}")

    return {
        "mode": "extractive",
        "profile": profile["label"],
        "text": "\n".join(
            [
                f"深度分析（{profile['label']}）- {issue_id}",
                "",
                conclusion,
                "",
                "证据：",
                *(evidence_lines or ["- 无"]),
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

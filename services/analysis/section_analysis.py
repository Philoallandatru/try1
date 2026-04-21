from __future__ import annotations

from services.analysis.llm_backends import LLMBackend


SECTION_RUNNERS: dict[str, dict[str, str]] = {
    "rca": {
        "label": "根因分析",
        "version": "v1",
        "instruction": (
            "解释可能的根本原因、失效机制，以及哪些证据支持或削弱根因假设。\n"
            "要求：\n"
            "- 识别直接原因和根本原因\n"
            "- 分析失效的触发条件和传播路径\n"
            "- 引用具体的日志、错误代码、规格条款\n"
            "- 评估证据的可信度和完整性"
        ),
    },
    "spec_impact": {
        "label": "规格影响",
        "version": "v1",
        "instruction": (
            "解释哪些规格、条款或需求受到影响，以及哪些证据支撑这种影响。\n"
            "要求：\n"
            "- 列出受影响的规格条款（章节号、版本）\n"
            "- 分析对合规性的影响\n"
            "- 评估对功能、性能、兼容性的影响\n"
            "- 引用具体的规格文本和设计文档"
        ),
    },
    "decision_brief": {
        "label": "决策简报",
        "version": "v1",
        "instruction": (
            "总结决策就绪的要点、关键风险，以及在采取行动前需要确认的内容。\n"
            "要求：\n"
            "- 提供清晰的行动建议\n"
            "- 识别高风险区域和不确定性\n"
            "- 列出需要进一步确认的事项\n"
            "- 评估不同方案的利弊"
        ),
    },
    "general_summary": {
        "label": "综合总结",
        "version": "v1",
        "instruction": (
            "为广泛的工程受众总结问题和最重要的跨源证据。\n"
            "要求：\n"
            "- 用简洁的语言概括问题核心\n"
            "- 整合来自不同来源的关键信息\n"
            "- 突出最重要的技术发现\n"
            "- 提供清晰的结论和建议"
        ),
    },
}


def _section_evidence_text(citations: list[dict]) -> str:
    if not citations:
        return "未检索到证据。"
    lines: list[str] = []
    for citation in citations:
        evidence = citation.get("evidence_span", "")
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
            citation.get("evidence_span", ""),
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
            f"章节：{section['label']}",
            f"章节版本：{section['version']}",
            section["instruction"],
            "",
            "## Jira问题上下文",
            issue_summary,
            "",
            "## 共享检索证据",
            _section_evidence_text(citations),
            "",
            "请使用中文输出分析结果。",
        ]
    ).strip()


def _extractive_section_answer(section_name: str, citations: list[dict]) -> dict:
    section = SECTION_RUNNERS[section_name]
    if not citations:
        summary = f"此章节暂无可用的共享证据。"
    else:
        summary = f"{section['label']}有{len(citations)}条共享证据引用可用。"
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
    lines = [f"# 深度分析报告：{title}", "", f"问题ID：{issue_id}", ""]
    for section_name in ("rca", "spec_impact", "decision_brief", "general_summary"):
        section = section_outputs[section_name]
        citation_lines = []
        for citation in section.get("citations", []):
            evidence = citation.get("evidence_span", "")
            citation_lines.append(f"- `{citation['document']}` v{citation['version']}: {evidence}")
        lines.extend(
            [
                f"## {section['label']}",
                "",
                section["answer"]["text"],
                "",
                "### 证据",
                "",
                *(citation_lines or ["- 未检索到共享证据。"]),
                "",
                f"章节产物：`section_outputs/{section_name}.json`",
                "",
            ]
        )
    return "\n".join(lines).strip()

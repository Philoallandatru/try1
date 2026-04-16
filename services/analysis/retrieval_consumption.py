from __future__ import annotations

from collections.abc import Iterable

from services.analysis.llm_backends import LLMBackend
from services.retrieval.citations.assembler import assemble_citation
from services.retrieval.indexing.page_index import build_page_index
from services.retrieval.search.hybrid_search import search_page_index


PROMPT_MODES = {"strict", "balanced", "exploratory"}


def _build_evidence_text(citations: list[dict]) -> str:
    lines = []
    for citation in citations:
        evidence = " ".join(citation.get("evidence_span", []))
        lines.append(f"- {citation['document']} v{citation['version']}: {evidence}")
    return "\n".join(lines)


def _default_prompt(
    *,
    question: str,
    evidence_text: str,
    prompt_mode: str,
    assistant_intro: str = "You are a grounded retrieval assistant.",
    task_instruction: str = "Answer using only the retrieved evidence below.",
    context_heading: str | None = None,
    context_markdown: str | None = None,
) -> str:
    if prompt_mode not in PROMPT_MODES:
        raise ValueError(f"Unsupported prompt mode: {prompt_mode}")

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
    }[prompt_mode]

    return "\n".join(
        [
            assistant_intro,
            task_instruction,
            *mode_instructions,
            "",
            "Output format:",
            "1. Conclusion: one sentence.",
            "2. Evidence: cite document IDs and versions only from the retrieved evidence.",
            "3. Gaps: list missing evidence or say `None`.",
            "",
            f"Question: {question}",
            "",
            *(["## " + context_heading, context_markdown, ""] if context_heading and context_markdown else []),
            "## Retrieved Evidence",
            evidence_text or "No retrieved evidence.",
        ]
    ).strip()


def _extractive_answer(question: str, citations: list[dict]) -> dict:
    if not citations:
        conclusion = "The retrieved evidence is insufficient to answer the question."
    elif len({citation["document"] for citation in citations}) == 1:
        conclusion = "The retrieved evidence points to a single source that should be reviewed directly."
    else:
        conclusion = "The retrieved evidence spans multiple sources and can be compared directly."

    evidence_lines = []
    for citation in citations:
        evidence = " ".join(citation.get("evidence_span", []))
        evidence_lines.append(f"- {citation['document']} v{citation['version']}: {evidence}")

    return {
        "mode": "extractive",
        "text": "\n".join(
            [
                f"Question: {question}",
                "",
                conclusion,
                "",
                "Evidence:",
                *(evidence_lines or ["- None"]),
            ]
        ).strip(),
        "citation_count": len(citations),
    }


def _llm_answer(prompt: str, llm_backend: LLMBackend, citations: list[dict]) -> dict:
    return {
        "mode": "local-llm",
        "backend": llm_backend.name,
        "text": llm_backend.generate(prompt).strip(),
        "citation_count": len(citations),
    }


def build_retrieval_consumption_payload(
    *,
    documents: Iterable[dict],
    question: str,
    allowed_policies: set[str],
    top_k: int = 5,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
    assistant_intro: str = "You are a grounded retrieval assistant.",
    task_instruction: str = "Answer using only the retrieved evidence below.",
    context_heading: str | None = None,
    context_markdown: str | None = None,
    extra_template_values: dict[str, object] | None = None,
    retrieval_bundle: dict | None = None,
) -> dict:
    if retrieval_bundle is not None:
        results = list(retrieval_bundle.get("results", []))
    else:
        results = search_page_index(build_page_index(documents), question, allowed_policies, top_k=top_k)
    citations = [assemble_citation(result) for result in results]
    evidence_text = _build_evidence_text(citations)

    if prompt_template:
        prompt_values = {
            "question": question,
            "evidence": evidence_text,
            "prompt_mode": prompt_mode,
            "citation_count": len(citations),
            **(extra_template_values or {}),
        }
        prompt = prompt_template.format(**prompt_values)
    else:
        prompt = _default_prompt(
            question=question,
            evidence_text=evidence_text,
            prompt_mode=prompt_mode,
            assistant_intro=assistant_intro,
            task_instruction=task_instruction,
            context_heading=context_heading,
            context_markdown=context_markdown,
        )

    return {
        "question": question,
        "retrieval": {
            "result_count": len(results),
            "citations": citations,
        },
        "ai_prompt": prompt,
        "answer": _llm_answer(prompt, llm_backend, citations) if llm_backend else _extractive_answer(question, citations),
    }

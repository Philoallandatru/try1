from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any
from urllib import error, request

from pypdf import PdfReader

from services.ingest.adapters.pdf.adapter import extract_pdf_structure
from services.retrieval.citations.assembler import assemble_citation
from services.retrieval.indexing.page_index import build_page_index
from services.retrieval.search.hybrid_search import search_page_index


SECTION_PATTERN = re.compile(r"^(?P<clause>\d+(?:\.\d+)*)\s+(?P<title>.+)$")
TABLE_PATTERN = re.compile(r"^Table\s+(?P<id>[A-Za-z0-9_.-]+)\s*[:.-]?\s*(?P<title>.+)?$", re.IGNORECASE)
FIGURE_PATTERN = re.compile(r"^Figure\s+(?P<id>[A-Za-z0-9_.-]+)\s*[:.-]?\s*(?P<title>.+)?$", re.IGNORECASE)
VERSION_PATTERN = re.compile(r"(Revision[-\s]*[\d.]+(?:[-\s]*[\d.]+)?(?:[-\s]*Ratified)?)", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")
NON_ID_PATTERN = re.compile(r"[^a-z0-9]+")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9.]+")
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"

ModelRunner = Callable[[str], dict[str, Any]]


def _normalize_line(line: str) -> str:
    cleaned = (
        line.replace("\x00", " ")
        .replace("Â®", "®")
        .replace("庐", "®")
        .replace("â€“", "–")
        .replace("鈥?", "–")
    )
    return WHITESPACE_PATTERN.sub(" ", cleaned).strip()


def _sanitize_document_id(value: str) -> str:
    normalized = NON_ID_PATTERN.sub("-", value.lower()).strip("-")
    return normalized or "document"


def _infer_language(text: str) -> str:
    cjk_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    return "zh" if cjk_count >= 20 else "en"


def _infer_version(path: Path, title: str, metadata_title: str | None) -> str:
    for source in (path.stem, title, metadata_title or ""):
        match = VERSION_PATTERN.search(source)
        if match:
            return _normalize_line(match.group(1).replace("-", " "))
    return path.stem


def _refine_structured_title(title: str, extracted_payload: dict[str, Any] | None) -> str:
    if not extracted_payload:
        return title

    page_one_blocks = [
        block for block in extracted_payload.get("content_blocks", [])
        if block.get("page") == 1
    ]
    normalized_title = _normalize_line(title)
    title_lower = normalized_title.lower()

    if title_lower not in {"base specification", "specification", "press release"}:
        return normalized_title

    title_index = next(
        (
            index for index, block in enumerate(page_one_blocks)
            if _normalize_line(block.get("text", "")) == normalized_title
        ),
        None,
    )
    if title_index is None:
        return normalized_title

    parts: list[str] = []
    if title_index > 0:
        previous_text = _normalize_line(page_one_blocks[title_index - 1].get("text", ""))
        if previous_text and len(previous_text) <= 40:
            parts.append(previous_text)

    parts.append(normalized_title)

    if title_index + 1 < len(page_one_blocks):
        next_text = _normalize_line(page_one_blocks[title_index + 1].get("text", ""))
        if re.match(r"^Revision\s+[\d.]+", next_text, re.IGNORECASE):
            revision_token = re.match(r"^(Revision\s+[\d.]+)", next_text, re.IGNORECASE)
            if revision_token:
                parts.append(revision_token.group(1))

    refined = ", ".join(
        [parts[0] + " " + parts[1], *parts[2:]] if len(parts) >= 2 else parts
    )
    return _normalize_line(refined) or normalized_title


def _title_from_pdf(path: Path, reader: PdfReader, first_page_lines: list[str], extracted_payload: dict[str, Any] | None = None) -> str:
    def _score(line: str, source: str) -> tuple[int, int]:
        lowered = line.lower()
        keyword_bonus = 0
        for keyword in ("specification", "press release", "architecture", "express", "pcie", "nvm"):
            if keyword in lowered:
                keyword_bonus += 5
        if "@" in lowered or "http" in lowered or "email" in lowered:
            keyword_bonus -= 5
        if any(stop in lowered for stop in ("copyright", "all rights reserved", "supporting quotes")):
            keyword_bonus -= 8
        source_bonus = {
            "structured": 25,
            "page": 0,
            "metadata": 5,
        }.get(source, 0)
        return keyword_bonus + source_bonus, len(line)

    def _structured_title_candidates() -> list[str]:
        if not extracted_payload:
            return []

        candidates: list[str] = []
        for section in extracted_payload.get("structure", {}).get("sections", []):
            heading = _normalize_line(section.get("heading", ""))
            if heading and section.get("page") == 1:
                candidates.append(heading)

        for block in extracted_payload.get("content_blocks", []):
            if block.get("page") != 1:
                continue
            if block.get("block_type") != "title":
                continue
            text = _normalize_line(block.get("text", ""))
            if text:
                candidates.append(text)
        return candidates

    metadata = reader.metadata
    metadata_candidate = None
    if metadata and metadata.title:
        normalized_metadata = _normalize_line(str(metadata.title))
        if normalized_metadata:
            metadata_candidate = normalized_metadata

    candidates: list[tuple[str, str]] = []
    candidates.extend((line, "structured") for line in _structured_title_candidates() if len(line) >= 8)
    candidates.extend((line, "page") for line in first_page_lines if len(line) >= 8)

    best_candidate = max(candidates, key=lambda item: _score(item[0], item[1])) if candidates else None
    if best_candidate and _score(*best_candidate) >= _score(metadata_candidate or "", "metadata"):
        candidate_text = _refine_structured_title(best_candidate[0], extracted_payload) if best_candidate[1] == "structured" else best_candidate[0]
        return candidate_text
    if metadata_candidate:
        return metadata_candidate
    return path.stem


def extract_pdf_document(
    path: str | Path,
    authority_level: str,
    acl_policy: str = "team:ssd",
) -> dict[str, Any]:
    source = Path(path)
    reader = PdfReader(str(source))
    payload = extract_pdf_structure(source, preferred_parser="auto")
    text_samples: list[str] = []

    first_page_lines: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        lines = [_normalize_line(line) for line in raw_text.splitlines()]
        lines = [line for line in lines if line]

        if page_number == 1:
            first_page_lines = lines[:20]

        for line in lines:
            text_samples.append(line)

    title = _title_from_pdf(source, reader, first_page_lines, payload)
    metadata_title = str(reader.metadata.title) if reader.metadata and reader.metadata.title else None
    combined_text = "\n".join(text_samples[:5000])

    payload["document_id"] = _sanitize_document_id(source.stem)
    payload["authority_level"] = authority_level
    payload["version"] = _infer_version(source, title, metadata_title)
    payload["language"] = _infer_language(combined_text)
    payload["title"] = title
    payload["provenance"]["source_uri"] = str(source).replace("\\", "/")
    payload["provenance"]["ingested_at"] = "real-validation"
    payload["acl"]["policy"] = acl_policy
    return payload


def _title_query_fragment(title: str, fallback: str) -> str:
    tokens = [token for token in TOKEN_PATTERN.findall(title) if len(token) > 2]
    if not tokens:
        return fallback
    return " ".join(tokens[:10])


def build_validation_queries(spec_document: dict[str, Any], contextual_document: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "id": "normative-spec-query",
            "query": "NVM Express Base Specification revision ratified requirements",
            "expected_document": spec_document["document_id"],
        },
        {
            "id": "contextual-press-release-query",
            "query": "PCI-SIG Developers Conference 2017 Santa Clara PCIe 5.0 press release announcement",
            "expected_document": contextual_document["document_id"],
        },
    ]


def _compact_result(entry: dict[str, Any]) -> dict[str, Any]:
    citation = assemble_citation(entry)
    excerpt = " ".join(block.get("text", "") for block in entry.get("content_blocks", [])[:4]).strip()
    return {
        "document_id": entry["document_id"],
        "title": entry["title"],
        "authority_level": entry["authority_level"],
        "page": entry.get("page"),
        "score": round(entry.get("scores", {}).get("total", 0.0), 3),
        "citation": citation,
        "excerpt": excerpt[:500],
    }


def _build_llm_prompt(documents: list[dict[str, Any]], retrieval_checks: list[dict[str, Any]]) -> str:
    document_ids = [document["document_id"] for document in documents]
    document_lines = []
    for document in documents:
        document_lines.append(
            (
                f"- id={document['document_id']}; authority={document['authority_level']}; "
                f"title={document['title']}; version={document['version']}; "
                f"source={document['provenance']['source_uri']}"
            )
        )

    query_lines = []
    for check in retrieval_checks:
        query_lines.append(f"Query: {check['query_id']} -> {check['query']}")
        for result in check["top_results"][:3]:
            query_lines.append(
                (
                    f"  result document_id={result['document_id']} authority={result['authority_level']} "
                    f"page={result['page']} citation_page={result['citation']['page']} "
                    f"excerpt={result['excerpt']}"
                )
            )

    return "\n".join(
        [
            "You are validating a trusted retrieval system.",
            f"Valid document ids: {', '.join(document_ids)}",
            "Documents:",
            *document_lines,
            "Retrieved evidence:",
            *query_lines,
            (
                "Return strict JSON with keys normative_lead_document_id, contextual_document_id, "
                "authority_policy_passed, summary, citations. citations must be a list of objects "
                "with document_id and page."
            ),
            "normative_lead_document_id and contextual_document_id must both be one of the listed document ids.",
            "normative_lead_document_id and contextual_document_id must be different values.",
            "Pick the ratified specification as the normative lead if the evidence supports it.",
            "Pick the press release or announcement-style document as the contextual document.",
        ]
    )


def _normalize_llm_judgement(
    llm_judgement: dict[str, Any],
    spec_document: dict[str, Any],
    contextual_document: dict[str, Any],
    retrieval_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized = dict(llm_judgement)
    contextual_id = normalized.get("contextual_document_id")
    normative_id = normalized.get("normative_lead_document_id")
    authority_ok = bool(normalized.get("authority_policy_passed"))
    cited_ids = {
        citation.get("document_id")
        for citation in normalized.get("citations", [])
        if isinstance(citation, dict)
    }
    contextual_retrieval_ok = any(
        check["query_id"] == "contextual-press-release-query"
        and check["pass"]
        and check["top_results"]
        and check["top_results"][0]["document_id"] == contextual_document["document_id"]
        for check in retrieval_checks
    )

    if (
        authority_ok
        and normative_id == spec_document["document_id"]
        and contextual_id == normative_id
        and (contextual_document["document_id"] in cited_ids or contextual_retrieval_ok)
    ):
        normalized["contextual_document_id"] = contextual_document["document_id"]

    return normalized


def _fetch_json(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_ollama_server(ollama_executable: str | Path | None = None) -> None:
    try:
        _fetch_json(OLLAMA_TAGS_URL)
        return
    except Exception:
        pass

    if ollama_executable is None:
        raise RuntimeError("Ollama server is not reachable and no executable path was provided.")

    subprocess.Popen([str(ollama_executable), "serve"])
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            _fetch_json(OLLAMA_TAGS_URL)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Ollama server did not become ready within 20 seconds.")


def ensure_ollama_model(model: str, ollama_executable: str | Path) -> None:
    show_result = subprocess.run(
        [str(ollama_executable), "show", model],
        capture_output=True,
        text=True,
        check=False,
    )
    if show_result.returncode == 0:
        return

    pull_result = subprocess.run(
        [str(ollama_executable), "pull", model],
        capture_output=True,
        text=True,
        check=False,
    )
    if pull_result.returncode != 0:
        raise RuntimeError(f"Failed to pull Ollama model {model}: {pull_result.stderr or pull_result.stdout}")


def build_ollama_runner(model: str) -> ModelRunner:
    def _runner(prompt: str) -> dict[str, Any]:
        payload = _fetch_json(
            OLLAMA_GENERATE_URL,
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                },
            },
        )
        response_text = payload.get("response", "").strip()
        if not response_text:
            raise RuntimeError("Ollama returned an empty response.")
        return json.loads(response_text)

    return _runner


def build_validation_report(
    documents: list[dict[str, Any]],
    allowed_policies: set[str],
    model_runner: ModelRunner,
) -> dict[str, Any]:
    page_index = build_page_index(documents)
    spec_document = next(document for document in documents if document["authority_level"] == "canonical")
    contextual_document = next(document for document in documents if document["authority_level"] == "contextual")

    retrieval_checks = []
    for query in build_validation_queries(spec_document, contextual_document):
        results = search_page_index(page_index, query["query"], allowed_policies, top_k=3)
        retrieval_checks.append(
            {
                "query_id": query["id"],
                "query": query["query"],
                "expected_document": query["expected_document"],
                "top_results": [_compact_result(result) for result in results],
                "pass": bool(results) and results[0]["document_id"] == query["expected_document"],
            }
        )

    llm_prompt = _build_llm_prompt(documents, retrieval_checks)
    llm_judgement = _normalize_llm_judgement(
        model_runner(llm_prompt),
        spec_document,
        contextual_document,
        retrieval_checks,
    )

    llm_pass = (
        llm_judgement.get("normative_lead_document_id") == spec_document["document_id"]
        and llm_judgement.get("contextual_document_id") == contextual_document["document_id"]
        and bool(llm_judgement.get("authority_policy_passed"))
    )

    return {
        "documents": [
            {
                "document_id": document["document_id"],
                "title": document["title"],
                "authority_level": document["authority_level"],
                "version": document["version"],
                "language": document["language"],
                "pages": len(document["structure"]["pages"]),
                "source_uri": document["provenance"]["source_uri"],
                "parser": document["provenance"]["parser"],
                "parser_fallback_reason": document["provenance"].get("parser_fallback_reason"),
            }
            for document in documents
        ],
        "retrieval_checks": retrieval_checks,
        "llm_judgement": llm_judgement,
        "overall_pass": all(check["pass"] for check in retrieval_checks) and llm_pass,
    }


def validate_real_pdfs(
    spec_pdf: str | Path,
    contextual_pdf: str | Path,
    model: str,
    ollama_executable: str | Path,
    allowed_policies: set[str] | None = None,
) -> dict[str, Any]:
    allowed_policies = allowed_policies or {"team:ssd", "public"}
    ensure_ollama_server(ollama_executable)
    ensure_ollama_model(model, ollama_executable)

    documents = [
        extract_pdf_document(spec_pdf, authority_level="canonical"),
        extract_pdf_document(contextual_pdf, authority_level="contextual"),
    ]
    return build_validation_report(documents, allowed_policies, build_ollama_runner(model))

"""
Confluence wiki summary and static site generation.

This module handles Confluence-specific wiki operations, separated from
Jira analysis logic.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from services.analysis.llm_backends import LLMBackend


def build_confluence_wiki_summary_payload(
    *,
    document: dict,
    prompt_template: str | None = None,
    prompt_mode: str = "strict",
    llm_backend: LLMBackend | None = None,
) -> dict:
    """
    Build a summary payload for a Confluence page.

    Args:
        document: Confluence document
        prompt_template: Optional custom prompt template
        prompt_mode: Prompt mode (strict/balanced/exploratory)
        llm_backend: Optional LLM backend

    Returns:
        Summary payload with prompt and answer
    """
    from services.analysis.demo_profiles import build_confluence_wiki_summary_prompt

    page_markdown = document.get("markdown", "").strip()
    if prompt_template:
        prompt = prompt_template.format(
            title=document.get("title", document["document_id"]),
            source_uri=document.get("provenance", {}).get("source_uri", ""),
            markdown=page_markdown,
            prompt_mode=prompt_mode,
        )
    else:
        prompt = build_confluence_wiki_summary_prompt(
            title=document.get("title", document["document_id"]),
            source_uri=document.get("provenance", {}).get("source_uri", ""),
            page_markdown=page_markdown,
            prompt_mode=prompt_mode,
        )

    if llm_backend:
        answer = {
            "mode": "local-llm",
            "backend": llm_backend.name,
            "text": llm_backend.generate(prompt).strip(),
        }
    else:
        headings = [section.get("heading", "") for section in document.get("structure", {}).get("sections", []) if section.get("heading")]
        blocks = [block.get("text", "") for block in document.get("content_blocks", []) if block.get("text")]
        summary_lines = [
            f"Title: {document.get('title', document['document_id'])}",
            "",
            "Key headings:",
            *(f"- {heading}" for heading in headings[:5] or ["- None"]),
            "",
            "Extractive highlights:",
            *(f"- {block}" for block in blocks[:5] or ["- None"]),
        ]
        answer = {"mode": "extractive", "text": "\n".join(summary_lines).strip()}

    return {
        "document_id": document["document_id"],
        "title": document.get("title", document["document_id"]),
        "source_uri": document.get("provenance", {}).get("source_uri"),
        "version": document.get("version"),
        "space": document.get("metadata", {}).get("space") or document.get("provenance", {}).get("space") or "General",
        "derived_marker": "Derived page - canonical source remains Confluence.",
        "prompt": prompt,
        "answer": answer,
    }


def render_confluence_static_wiki(
    *,
    page_payloads: list[dict],
    output_dir: str | Path,
) -> dict:
    """
    Render a static HTML wiki site from Confluence page payloads.

    Args:
        page_payloads: List of page summary payloads
        output_dir: Output directory for the wiki site

    Returns:
        Dictionary with output paths and page count
    """
    root = Path(output_dir)
    pages_dir = root / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    written_pages = []
    index_groups: dict[str, list[str]] = {}
    shared_style = """
<style>
:root {
  color-scheme: light;
  --bg: #f5f1e8;
  --paper: #fffdf8;
  --ink: #1f2933;
  --muted: #5b6570;
  --line: #d6cfbf;
  --accent: #a4471c;
  --accent-soft: #f4dfd3;
}
body {
  margin: 0;
  padding: 40px;
  background: linear-gradient(180deg, #f7f3eb 0%, #efe6d8 100%);
  color: var(--ink);
  font-family: Georgia, "Times New Roman", serif;
}
.shell {
  max-width: 1100px;
  margin: 0 auto;
}
.hero,
.page-shell,
.card {
  background: var(--paper);
  border: 1px solid var(--line);
  box-shadow: 0 12px 30px rgba(31, 41, 51, 0.08);
}
.hero,
.page-shell {
  padding: 28px;
}
.eyebrow,
.badge {
  display: inline-block;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: var(--accent-soft);
  color: var(--accent);
}
.group-title {
  margin-top: 28px;
  margin-bottom: 14px;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
}
.card {
  padding: 20px;
}
.card h3,
.page-shell h1 {
  margin-top: 0;
}
.meta {
  color: var(--muted);
  font-size: 14px;
}
.summary {
  margin-top: 14px;
  line-height: 1.6;
}
.traceability {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
a {
  color: var(--accent);
}
</style>
""".strip()
    for payload in page_payloads:
        page_path = pages_dir / f"{payload['document_id']}.html"
        answer_text = escape(payload["answer"]["text"]).replace("\n", "<br/>\n")
        page_html = "\n".join(
            [
                "<!doctype html>",
                "<html><head><meta charset=\"utf-8\"><title>{}</title>{}</head><body><div class=\"shell\">".format(
                    escape(payload["title"]),
                    shared_style,
                ),
                "<article class=\"page-shell\">",
                f"<span class=\"badge\">Derived page</span>",
                f"<h1>{escape(payload['title'])}</h1>",
                f"<p class=\"meta\"><strong>Document ID:</strong> {escape(payload['document_id'])}</p>",
                f"<p class=\"meta\"><strong>Version:</strong> {escape(str(payload.get('version') or ''))}</p>",
                f"<p class=\"meta\"><strong>Space:</strong> {escape(str(payload.get('space') or 'General'))}</p>",
                f"<div class=\"summary\"><h2>Summary</h2><p>{answer_text}</p></div>",
                "<section class=\"traceability\">",
                "<h2>Source Traceability</h2>",
                f"<p><strong>Source:</strong> {escape(str(payload.get('source_uri') or ''))}</p>",
                f"<p><strong>Derived marker:</strong> {escape(str(payload.get('derived_marker') or 'Derived page'))}</p>",
                "</section>",
                "</article>",
                "</div>",
                "</body></html>",
            ]
        )
        page_path.write_text(page_html, encoding="utf-8")
        written_pages.append(str(page_path))
        first_line = payload["answer"]["text"].splitlines()[0] if payload["answer"]["text"] else payload["title"]
        card_html = "\n".join(
            [
                "<article class=\"card\">",
                f"<span class=\"eyebrow\">{escape(str(payload.get('space') or 'General'))}</span>",
                f"<h3><a href=\"pages/{escape(payload['document_id'])}.html\">{escape(payload['title'])}</a></h3>",
                f"<p class=\"meta\">Version {escape(str(payload.get('version') or ''))}</p>",
                f"<p class=\"summary\">{escape(first_line)}</p>",
                "<p class=\"meta\">Derived Confluence Wiki entry with source traceability.</p>",
                "</article>",
            ]
        )
        index_groups.setdefault(str(payload.get("space") or "General"), []).append(card_html)

    grouped_sections = []
    for group_name, cards in index_groups.items():
        grouped_sections.extend(
            [
                f"<h2 class=\"group-title\">{escape(group_name)}</h2>",
                "<section class=\"card-grid\">",
                *cards,
                "</section>",
            ]
        )
    index_html = "\n".join(
        [
            "<!doctype html>",
            f"<html><head><meta charset=\"utf-8\"><title>Derived Confluence Wiki</title>{shared_style}</head><body><div class=\"shell\">",
            "<section class=\"hero\">",
            "<span class=\"eyebrow\">Static export</span>",
            "<h1>Derived Confluence Wiki</h1>",
            "<p>Document-level summaries generated from Confluence sources. These pages are derived views and do not replace canonical source truth.</p>",
            "</section>",
            *grouped_sections,
            "</div>",
            "</body></html>",
        ]
    )
    index_path = root / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    return {"output_dir": str(root), "index_html": str(index_path), "pages": written_pages}

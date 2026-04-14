from __future__ import annotations

from html import escape
from pathlib import Path
import json
import shutil


def _copy_tree(source_root: Path, target_root: Path) -> list[str]:
    written: list[str] = []
    if not source_root.exists():
        return written
    for source_path in sorted(source_root.rglob("*.md")):
        relative_path = source_path.relative_to(source_root)
        target_path = target_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        written.append(str(target_path))
    return written


def _page_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def _page_summaries(paths: list[str], *, relative_root: Path) -> list[dict]:
    pages: list[dict] = []
    for path in paths:
        full_path = Path(path)
        relative_path = full_path.relative_to(relative_root)
        lines = full_path.read_text(encoding="utf-8").splitlines()
        title = _page_title(full_path)
        excerpt = ""
        for line in lines:
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("#")
                or stripped.startswith(">")
                or stripped.startswith("- ")
                or stripped.startswith("<")
            ):
                continue
            excerpt = stripped
            break
        pages.append(
            {
                "path": relative_path,
                "title": title,
                "excerpt": excerpt or "Derived knowledge page.",
            }
        )
    return pages


def _card_list(section_title: str, base_path: str, pages: list[dict]) -> str:
    if not pages:
        return "\n".join(
            [
                f"## {section_title}",
                "",
                '<div class="card-grid">',
                '<article class="surface-card muted-card">',
                "<h3>Nothing published yet</h3>",
                "<p>This section will populate after the next workspace publish cycle.</p>",
                "</article>",
                "</div>",
            ]
        )
    lines = [
        f"## {section_title}",
        "",
        '<div class="card-grid">',
    ]
    for page in pages:
        lines.extend(
            [
                '<article class="surface-card nav-card">',
                f'<h3><a href="{base_path}/{page["path"].name}">{escape(page["title"])}</a></h3>',
                f"<p>{escape(page['excerpt'])}</p>",
                "</article>",
            ]
        )
    lines.append("</div>")
    return "\n".join(lines)


def _topic_links(topic_pages: list[dict]) -> list[str]:
    return [f"- [{page['title']}](topics/{page['path'].name})" for page in topic_pages]


def _index_markdown(
    *,
    site_title: str,
    topic_pages: list[dict],
    summary_pages: list[dict],
    analysis_pages: list[dict],
) -> str:
    lines = [
        "---",
        "layout: home",
        "---",
        "",
        '<div class="hero-panel">',
        f"<p class=\"eyebrow\">Derived Knowledge Hub</p>",
        f"<h1>{site_title}</h1>",
        "<p class=\"hero-copy\">A topic-routed engineering wiki built from curated Confluence summaries, promoted Jira analyses, and evidence-preserving source links.</p>",
        '<div class="hero-actions">',
        '<a class="action-pill action-pill-primary" href="./topics/">Browse Topics</a>',
        '<a class="action-pill action-pill-secondary" href="./summaries/confluence/">Review Summaries</a>',
        "</div>",
        "</div>",
        "",
        '<div class="metric-grid">',
        f'<div class="metric-card"><span class="metric-label">Topics</span><strong>{len(topic_pages)}</strong></div>',
        f'<div class="metric-card"><span class="metric-label">Confluence Summaries</span><strong>{len(summary_pages)}</strong></div>',
        f'<div class="metric-card"><span class="metric-label">Jira Analyses</span><strong>{len(analysis_pages)}</strong></div>',
        "</div>",
        "",
        _card_list("Topic Hubs", "topics", topic_pages),
        "",
        _card_list("Confluence Summaries", "summaries/confluence", summary_pages),
        "",
        _card_list("Jira Analyses", "analyses/jira", analysis_pages),
    ]
    return "\n".join(lines).strip()


def _section_index_markdown(
    *,
    title: str,
    description: str,
    base_path: str,
    pages: list[dict],
) -> str:
    lines = [
        f"# {title}",
        "",
        f"> {description}",
        "",
        _card_list(title, base_path, pages),
    ]
    return "\n".join(lines).strip()


def _vitepress_config(
    *,
    site_title: str,
    topic_pages: list[dict],
    summary_pages: list[dict],
    analysis_pages: list[dict],
) -> str:
    def nav_items(pages: list[dict], prefix: str) -> list[str]:
        lines: list[str] = []
        for page in pages:
            lines.append(f"        {{ text: '{page['title']}', link: '/{prefix}/{page['path'].stem}' }},")
        return lines

    lines = [
        "import { defineConfig } from 'vitepress'",
        "",
        "export default defineConfig({",
        f"  title: '{site_title}',",
        "  description: 'Topic-routed derived wiki',",
        "  cleanUrls: true,",
        "  lastUpdated: true,",
        "  themeConfig: {",
        "    siteTitle: 'SSD Topic Wiki',",
        "    nav: [",
        "      { text: 'Home', link: '/' },",
        "      { text: 'Topics', link: '/topics/' },",
        "      { text: 'Confluence', link: '/summaries/confluence/' },",
        "      { text: 'Jira', link: '/analyses/jira/' },",
        "    ],",
        "    sidebar: [",
        "      {",
        "        text: 'Topic Hubs',",
        "        items: [",
        "          { text: 'Overview', link: '/topics/' },",
        *nav_items(topic_pages, "topics"),
        "        ]",
        "      },",
        "      {",
        "        text: 'Confluence Summaries',",
        "        items: [",
        "          { text: 'Overview', link: '/summaries/confluence/' },",
        *nav_items(summary_pages, "summaries/confluence"),
        "        ]",
        "      },",
        "      {",
        "        text: 'Jira Analyses',",
        "        items: [",
        "          { text: 'Overview', link: '/analyses/jira/' },",
        *nav_items(analysis_pages, "analyses/jira"),
        "        ]",
        "      }",
        "    ]",
        "  }",
        "})",
    ]
    return "\n".join(lines)


def _package_json() -> dict:
    return {
        "name": "ssd-topic-wiki",
        "private": True,
        "type": "module",
        "scripts": {
            "docs:dev": "vitepress dev docs",
            "docs:build": "vitepress build docs",
            "docs:preview": "vitepress preview docs",
        },
        "devDependencies": {
            "vitepress": "^1.6.4",
        },
    }


def _readme() -> str:
    lines = [
        "# SSD Topic Wiki",
        "",
        "This directory is a VitePress-ready derived wiki output.",
        "",
        "## Local preview",
        "",
        "```bash",
        "npm install",
        "npm run docs:dev",
        "```",
        "",
        "## Static build",
        "",
        "```bash",
        "npm install",
        "npm run docs:build",
        "```",
        "",
        "## Notes",
        "",
        "- This site is derived from the workspace topic-routed wiki flow.",
        "- Canonical documents remain the source of truth.",
        "- Re-run the workspace publish/build flow instead of editing generated pages directly.",
        "- Prefer the local npm scripts over npx on Windows to avoid cache-path and unlink issues.",
    ]
    return "\n".join(lines).strip()


def _theme_index() -> str:
    return "\n".join(
        [
            "import DefaultTheme from 'vitepress/theme'",
            "import './custom.css'",
            "",
            "export default {",
            "  extends: DefaultTheme,",
            "}",
        ]
    )


def _custom_css() -> str:
    return """@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --vp-c-brand-1: #3B82F6;
  --vp-c-brand-2: #60A5FA;
  --vp-c-brand-3: #1D4ED8;
  --vp-c-bg: #F8FAFC;
  --vp-c-bg-soft: #EEF4FB;
  --vp-c-text-1: #1E293B;
  --vp-c-text-2: #475569;
  --vp-font-family-base: 'IBM Plex Sans', sans-serif;
  --vp-font-family-mono: 'JetBrains Mono', monospace;
}

.VPDoc,
.VPHome {
  font-family: var(--vp-font-family-base);
}

.VPNavBarTitle .title {
  font-family: var(--vp-font-family-mono);
  letter-spacing: 0.02em;
}

.hero-panel {
  padding: 2rem;
  background: linear-gradient(135deg, rgba(59,130,246,0.10), rgba(96,165,250,0.05));
  border: 1px solid rgba(59,130,246,0.12);
  border-radius: 24px;
  margin: 1rem 0 2rem;
}

.page-hero {
  padding: 1.45rem 1.5rem;
  background: linear-gradient(180deg, rgba(59,130,246,0.08), rgba(248,250,252,0.95));
  border: 1px solid rgba(59,130,246,0.14);
  border-radius: 22px;
  margin: 0.5rem 0 1rem;
}

.page-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(280px, 0.95fr);
  gap: 1.1rem;
  align-items: start;
  margin-bottom: 2rem;
}

.page-main,
.page-aside {
  min-width: 0;
}

.page-aside {
  display: grid;
  gap: 0.9rem;
}

.breadcrumb-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
  margin: 0.5rem 0 0.75rem;
  color: var(--vp-c-text-2);
  font-size: 0.9rem;
}

.breadcrumb-bar a {
  color: var(--vp-c-brand-1);
  text-decoration: none !important;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-family: var(--vp-font-family-mono);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--vp-c-brand-3);
}

.hero-copy {
  max-width: 52rem;
  color: var(--vp-c-text-2);
  font-size: 1.05rem;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.action-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0.75rem 1rem;
  border-radius: 999px;
  text-decoration: none !important;
  transition: transform 220ms ease, box-shadow 220ms ease, background-color 220ms ease;
  cursor: pointer;
}

.action-pill:hover {
  transform: translateY(-1px);
}

.action-pill-primary {
  background: var(--vp-c-brand-1);
  color: white !important;
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.18);
}

.action-pill-secondary {
  background: white;
  color: var(--vp-c-text-1) !important;
  border: 1px solid rgba(59,130,246,0.18);
}

.metric-grid,
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.hero-metrics,
.metric-grid {
  margin: 1rem 0 2rem;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.9rem;
}

.metric-card,
.surface-card {
  background: white;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 20px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.metric-card {
  padding: 1rem 1.1rem;
}

.meta-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin: 0.75rem 0 1.5rem;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: rgba(59,130,246,0.10);
  border: 1px solid rgba(59,130,246,0.14);
  color: var(--vp-c-text-1);
  font-family: var(--vp-font-family-mono);
  font-size: 0.78rem;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-family: var(--vp-font-family-mono);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.status-pill-topic {
  background: rgba(59,130,246,0.14);
  color: #1D4ED8;
}

.status-pill-summary {
  background: rgba(16,185,129,0.14);
  color: #047857;
}

.status-pill-analysis {
  background: rgba(249,115,22,0.14);
  color: #C2410C;
}

.source-type-badge {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: rgba(30, 41, 59, 0.07);
  color: var(--vp-c-text-1);
  font-family: var(--vp-font-family-mono);
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: lowercase;
}

.updated-timestamp {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  border: 1px dashed rgba(148, 163, 184, 0.35);
  color: var(--vp-c-text-2);
  font-family: var(--vp-font-family-mono);
  font-size: 0.78rem;
}

.metric-card strong {
  display: block;
  font-size: 1.8rem;
  line-height: 1.1;
  margin-top: 0.35rem;
  color: var(--vp-c-text-1);
}

.metric-label {
  display: block;
  color: var(--vp-c-text-2);
  font-size: 0.85rem;
}

.surface-card {
  padding: 1.1rem 1.15rem;
}

.info-card {
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
}

.info-card h2 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 1rem;
}

.info-card ul {
  margin: 0;
  padding-left: 1.1rem;
}

.info-card p + p {
  margin-top: 0.55rem;
}

.artifact-card {
  margin-bottom: 1rem;
}

.evidence-card {
  border-style: dashed;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
}

.evidence-card p + p {
  margin-top: 0.45rem;
}

.surface-card h3 {
  margin: 0 0 0.4rem;
  font-size: 1.05rem;
  line-height: 1.35;
}

.surface-card p {
  margin: 0;
  color: var(--vp-c-text-2);
  line-height: 1.65;
}

.nav-card:hover {
  border-color: rgba(59,130,246,0.28);
  box-shadow: 0 20px 40px rgba(59,130,246,0.10);
}

.muted-card {
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
}

.VPDoc .content-container {
  max-width: 900px;
}

.VPContent.is-home {
  max-width: 1200px !important;
}

@media (prefers-reduced-motion: reduce) {
  .action-pill {
    transition: none;
  }

  .action-pill:hover {
    transform: none;
  }
}

@media (max-width: 960px) {
  .page-layout {
    grid-template-columns: 1fr;
  }
}
"""


def build_vitepress_site(
    *,
    compiled_root: str | Path,
    output_root: str | Path,
    site_title: str,
) -> dict:
    compiled_root_path = Path(compiled_root)
    output_root_path = Path(output_root)
    docs_root = output_root_path / "docs"
    config_root = output_root_path / ".vitepress"
    theme_root = config_root / "theme"
    docs_root.mkdir(parents=True, exist_ok=True)
    config_root.mkdir(parents=True, exist_ok=True)
    theme_root.mkdir(parents=True, exist_ok=True)

    topic_paths = _copy_tree(compiled_root_path / "topics", docs_root / "topics")
    summary_paths = _copy_tree(compiled_root_path.parent / "summaries" / "confluence", docs_root / "summaries" / "confluence")
    analysis_paths = _copy_tree(compiled_root_path / "analyses" / "jira", docs_root / "analyses" / "jira")

    topic_pages = _page_summaries(topic_paths, relative_root=docs_root / "topics")
    summary_pages = _page_summaries(summary_paths, relative_root=docs_root / "summaries" / "confluence")
    analysis_pages = _page_summaries(analysis_paths, relative_root=docs_root / "analyses" / "jira")

    index_path = docs_root / "index.md"
    index_path.write_text(
        _index_markdown(
            site_title=site_title,
            topic_pages=topic_pages,
            summary_pages=summary_pages,
            analysis_pages=analysis_pages,
        ),
        encoding="utf-8",
    )
    (docs_root / "topics" / "index.md").write_text(
        _section_index_markdown(
            title="Topic Hubs",
            description="Cross-source knowledge pages curated from Confluence summaries and promoted Jira analyses.",
            base_path=".",
            pages=topic_pages,
        ),
        encoding="utf-8",
    )
    (docs_root / "summaries" / "confluence" / "index.md").write_text(
        _section_index_markdown(
            title="Confluence Summaries",
            description="Derived summaries prepared from selected Confluence sources before they enter topic hubs.",
            base_path=".",
            pages=summary_pages,
        ),
        encoding="utf-8",
    )
    (docs_root / "analyses" / "jira" / "index.md").write_text(
        _section_index_markdown(
            title="Jira Analyses",
            description="Issue-by-issue derived analyses. Only promoted analyses are folded into topic hubs.",
            base_path=".",
            pages=analysis_pages,
        ),
        encoding="utf-8",
    )

    config_path = config_root / "config.mts"
    config_path.write_text(
        _vitepress_config(
            site_title=site_title,
            topic_pages=topic_pages,
            summary_pages=summary_pages,
            analysis_pages=analysis_pages,
        ),
        encoding="utf-8",
    )
    theme_index_path = theme_root / "index.ts"
    theme_index_path.write_text(_theme_index(), encoding="utf-8")
    custom_css_path = theme_root / "custom.css"
    custom_css_path.write_text(_custom_css(), encoding="utf-8")
    package_json_path = output_root_path / "package.json"
    package_json_path.write_text(json.dumps(_package_json(), indent=2), encoding="utf-8")
    readme_path = output_root_path / "README.md"
    readme_path.write_text(_readme(), encoding="utf-8")
    return {
        "output_root": str(output_root_path),
        "docs_root": str(docs_root),
        "config_path": str(config_path),
        "theme_index_path": str(theme_index_path),
        "custom_css_path": str(custom_css_path),
        "package_json_path": str(package_json_path),
        "readme_path": str(readme_path),
        "renderer": "vitepress",
        "topic_page_count": len(topic_paths),
        "summary_page_count": len(summary_paths),
        "analysis_page_count": len(analysis_paths),
    }

# Connectors Service

Connector service for external content sources such as Jira and Confluence.

## Canonicalization Debt

Jira and Confluence currently use a bridge path:

1. source payload
2. source-specific Markdown rendering
3. `normalize_markdown_text(...)`
4. canonical document

This keeps the current fixtures readable and indexable, but it is not the target structure-preserving architecture. The foundation roadmap in `docs/replan-markdown-pageindex-local-llm.md` expects richer direct payload-to-canonical builders for Jira and Confluence after the PageIndex artifact and retrieval-consumption seams are stable.

Do not make Markdown the source of truth for connector data. Markdown is only the readable projection; canonical documents remain the source of truth.

# SSD Knowledge Platform Foundation TODO

## Current Execution Rule

Use this file as the active near-term roadmap. The current milestone is deliberately narrower than the older broad Phase 1 plan:

- Primary target: Markdown + PageIndex + local LLM.
- Priority sources: Jira, Confluence, PPTX, PDF.
- Critical path: conversion foundation, PageIndex artifact contract, source-agnostic retrieval, local LLM consumption.
- Deferred: portal, ops hardening, rollout gates, hosted services, identity-aware ACL, clustering, summarization.

Do not weaken existing ACL, citation, provenance, or PageIndex-first retrieval constraints.

## Phase A: Conversion Foundation

### Goal

Make Jira, Confluence, PPTX, and PDF all produce canonical document + readable Markdown + PageIndex from one canonical document.

### Inputs

- `spec.md`
- `docs/replan-markdown-pageindex-local-llm.md`
- `docs/api-contracts.md`
- Jira and Confluence connector fixtures
- PPTX and PDF corpus fixtures
- Existing canonical normalization helpers and adapters

### Outputs

- Four-source conversion support matrix.
- Tests for source -> canonical document.
- Tests for canonical document -> Markdown.
- Tests for canonical document -> PageIndex.

### Validation

- Run focused tests for ingestion and connector PageIndex behavior.
- Each source has at least one happy-path and one failure-path validation.

### Blockers

- Jira and Confluence currently rely on payload -> Markdown -> `normalize_markdown_text(...)`; this is accepted as temporary behavior but not the target architecture.

### Exit Criteria

- All four priority sources can produce readable Markdown and PageIndex without weakening provenance, ACL, citation, or structure metadata.

## Phase B: PageIndex Artifact Contract

### Goal

Make PageIndex a first-class artifact with one shape and one loader.

### Inputs

- `services/retrieval/indexing/page_index.py`
- `scripts/ingest/normalize_cli.py`
- `scripts/platform_cli.py sync-export`
- `services/retrieval/persistence/snapshot_store.py`

### Outputs

- Canonical artifact shape: `{"entries": [...]}`
- Consistent PageIndex exports from normalize CLI, sync-export, and snapshot persistence.
- Retrieval loader for PageIndex artifact input.

### Validation

- Tests prove all PageIndex writers emit `{"entries": [...]}`.
- Tests prove retrieval can consume exported PageIndex directly.

### Blockers

- `normalize_cli.py --output-page-index` currently writes a bare list while snapshot and sync-export write `{"entries": [...]}`.
- Retrieval toolkit currently prefers document corpus input and rebuilds PageIndex.

### Exit Criteria

- PageIndex artifacts are stable runtime inputs and no longer only derived intermediate outputs.

## Phase C: Unified Retrieval Surface

### Goal

Provide source-agnostic search, citation, and source inspection for Jira, Confluence, PPTX, and PDF.

### Inputs

- Canonical documents.
- PageIndex artifacts.
- Existing hybrid search and citation assembly.

### Outputs

- Retrieval API/CLI supports both document corpus compatibility and direct PageIndex input.
- Source inspection payloads remain evidence-bearing and ACL-safe.

### Validation

- Search and citation tests cover all four priority source types.
- ACL pre-ranking filtering remains covered.
- Ranking default remains `canonical > supporting > contextual`.

### Blockers

- Direct PageIndex artifact input must be settled first.

### Exit Criteria

- One retrieval path can search/cite/inspect across all four source types.

## Phase D: Local LLM Consumption

### Goal

Add a source-generic retrieval -> prompt assembly -> local LLM answer seam.

### Inputs

- Retrieval results.
- Citation payloads.
- Evidence spans.
- `services/analysis/llm_backends.py`

### Outputs

- Generic local LLM retrieval-consumption service.
- Jira-specific analysis implemented as a profile on the generic seam.
- Extractive fallback remains default when no LLM backend is selected.

### Validation

- Mock LLM tests for Jira, Confluence, PPTX, and PDF.
- Tests prove local LLM prompts include retrieved evidence only.

### Blockers

- Current local LLM paths are Jira-specific plus a PDF validation harness.

### Exit Criteria

- One local LLM path can consume retrieved evidence across all four priority sources.

## Phase E: Index Optimization

### Goal

Reduce redundant index rebuilds and define the PageIndex/chunk/embedding relationship.

### Inputs

- Stable canonical document contract.
- Stable PageIndex artifact contract.
- Stable retrieval surface.

### Outputs

- Snapshot/cache-based index reuse plan.
- Contextual chunking plan.
- Decision record for PageIndex vs embedding/chunk index responsibilities.

### Validation

- Regression tests prove optimization does not change ACL filtering, authority ranking, or citation payloads.

### Blockers

- Do not optimize before PageIndex artifact shape and direct retrieval input are stable.

### Exit Criteria

- Index reuse and chunking can be added without changing canonical truth or citation semantics.

## Phase F: Enrichment

### Goal

Add clustering and summarization only after the foundation is stable.

### Inputs

- Stable retrieval surface.
- Stable local LLM consumption seam.
- Optional optimized chunk/index artifacts.

### Outputs

- Topic clusters.
- Document summaries.
- Cluster summaries.

### Validation

- Enrichment artifacts cite source evidence.
- Enrichment artifacts do not overwrite canonical documents, Markdown projections, or PageIndex entries.

### Blockers

- Foundation chain must be complete first.

### Exit Criteria

- Clustering and summarization exist only as derived enrichment.

## Prioritized Roadmap

### P0: Now

1. Done: persist this foundation-first roadmap.
2. Done: standardize PageIndex artifact shape as `{"entries": [...]}` for skill-ready export and retrieval paths.
3. Done: add direct PageIndex artifact input for `scripts/retrieval/toolkit_cli.py` and platform search/citation.
4. Done: add four-source Markdown and PageIndex export tests.
5. Done: document Jira/Confluence Markdown-first canonicalization as temporary technical debt in source-specific docs.

### P1: Foundation Closeout

1. Done for current fixture-backed paths: replace Jira and Confluence Markdown-first canonicalization with direct payload-to-canonical builders.
2. Done: add a source-generic local LLM retrieval-consumption service.
3. In progress: refactor Jira analysis commands into profiles over the generic seam. Jira spec QA and batch spec QA now reuse the generic seam internally, `retrieval-consume` exposes the generic CLI surface, and Jira profile helpers are separated from orchestration code.
4. Done: add mock-backed local LLM tests for Confluence, PPTX, and PDF.
5. Remaining in this lane: fidelity expansion for richer Jira/Confluence source shapes and final small cleanup of Jira orchestration/profile boundaries.

### P2: Later

1. Add snapshot/cache-based index reuse.
2. Add contextual chunking.
3. Define embedding/chunk index relationship to PageIndex.
4. Add clustering and summarization as citation-backed enrichment artifacts.
5. Revisit portal, ops hardening, and rollout gate expansion.

## Handoff Notes

- Canonical document remains truth.
- Markdown remains readable projection.
- PageIndex remains retrieval projection.
- Local LLM consumes retrieved evidence only.
- Clustering and summarization are post-foundation enrichment.

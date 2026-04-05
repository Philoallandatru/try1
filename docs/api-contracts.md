# API Contracts

## Purpose

This document captures the current JSON-level contracts already used inside the repository. These are not yet exposed as hosted HTTP APIs, but they are the effective payload shapes consumed by the portal, rollout gate, and evaluation tooling.

## 1. Normalized Document Contract

Primary source:

- `packages/schema/document-schema.json`

Required top-level fields:

- `document_id`
- `source_type`
- `authority_level`
- `version`
- `language`
- `title`
- `provenance`
- `acl`
- `structure`
- `terminology`
- `content_blocks`

Key invariants:

- `authority_level` is one of `canonical`, `supporting`, `contextual`
- `source_type` is one of `md`, `pdf`, `docx`, `xlsx`, `pptx`, `jira`, `confluence`
- `acl` must always be present
- structural metadata must remain first-class

## 2. Page Index Entry Contract

Produced by:

- `services/retrieval/indexing/page_index.py`

Current shape:

- `document_id`
- `page`
- `source_type`
- `authority_level`
- `version`
- `language`
- `title`
- `provenance`
- `acl`
- `structure`
- `terminology`
- `content_blocks`
- `text`
- `token_counts`
- `tokens`

Key invariants:

- each entry is page-scoped when page information exists
- ACL metadata is preserved at index-entry level
- retrieval consumes page entries, not raw documents

## 3. Search Result Contract

Produced by:

- `services/retrieval/search/hybrid_search.py`

Current shape:

- all page index entry fields
- `scores`

`scores` contains:

- `lexical`
- `semantic`
- `authority`
- `total`

Key invariants:

- ACL filtering happens before any result is scored or returned
- `total` score drives ordering
- authority score is part of the final ranking

## 4. Citation Contract

Produced by:

- `services/retrieval/citations/assembler.py`

Current shape:

- `document`
- `title`
- `version`
- `page`
- `section`
- `clause`
- `table_id`
- `figure_id`
- `source_uri`
- `evidence_span`

Key invariants:

- citations must resolve to evidence-bearing content
- `document`, `version`, `page`, and section or clause are mandatory when available
- `table_id` and `figure_id` are included when available

## 5. Source Inspection Contract

Produced by:

- `services/retrieval/citations/assembler.py`

Current shape:

- `document_id`
- `title`
- `version`
- `authority_level`
- `page`
- `language`
- `source_uri`
- `section`
- `clause`
- `table_id`
- `figure_id`
- `content_blocks`

Key invariants:

- must support operator drilldown from a search result
- must remain aligned with the citation contract

## 6. Evaluation Report Contract

Produced by:

- `services/eval/harness.py`
- `scripts/eval/run_recall_eval.py`

Current shape:

- `thresholds`
- `aggregate`
- `queries`

`aggregate` contains:

- `recall@10`
- `ndcg@10`
- `citation_fidelity`

Each query result contains:

- `id`
- `query`
- `recall`
- `ndcg`
- `citation_fidelity`
- `top_result`
- `citation`

## 7. Ops Health Contract

Produced by:

- `services/ops/health.py`

Current shape:

- `freshness`
- `backup_restore`
- `evaluation`

`freshness` contains:

- `sources`
- `budget_minutes`

Each freshness source contains:

- `source_type`
- `status`
- `last_sync`
- `lag_minutes`

`backup_restore` contains:

- `backup`
- `restore`

## 8. Portal State Contract

Produced by:

- `apps/portal/portal_state.py`

Current shape:

- `ingestion_status`
- `corpus_inventory`
- `search_query`
- `search_workspace`
- `citation_inspection`
- `evaluation_health`

Key invariants:

- portal state is a composition of ingestion, retrieval, citation, and evaluation contracts
- the portal should not invent fields outside the underlying service contracts

## 9. Rollout Gate Contract

Produced by:

- `scripts/gates/run_phase1_gate.py`

Current shape:

- `passed`
- `checks`
- `eval`
- `ops`

`checks` contains:

- `eval`
- `freshness`
- `backup_restore`
- `portal`

Key invariants:

- `passed` is true only when all checks pass
- degraded policy scope must be able to fail the gate


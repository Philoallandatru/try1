# Architecture Overview

## Purpose

This document summarizes the current foundation architecture as implemented in the repository. The active near-term milestone is Markdown + PageIndex + local LLM consumption for Jira, Confluence, PPTX, and PDF.

## Terminology

- `fixture`: a checked-in, deterministic sample input used to exercise the system without relying on live external systems. Fixtures are the contract-test baseline for sources such as Jira sync payloads, Confluence page payloads, and sample Office/PDF files.
- `canonical document`: the normalized internal source-of-truth representation produced by ingestion. It is the authoritative shape that carries provenance, ACL metadata, structure metadata, and content blocks. Markdown, PageIndex, snapshots, and local LLM prompts are downstream projections or consumers of this representation.
- `artifact`: a generated output with a stable shape that can be stored, exchanged, or consumed by later pipeline stages. In the current design this includes exported PageIndex JSON, snapshot files, evaluation outputs, and portal-state JSON. An artifact is usually derived from canonical documents rather than replacing them as truth.

## System Layers

### 1. Contract Layer

- `docs/adr/*`
- `packages/schema/*`
- `packages/acl/*`
- `packages/terminology/*`

This layer defines the product scope, source authority model, success metrics, canonical document shape, and ACL propagation rules. `docs/replan-markdown-pageindex-local-llm.md` is the active roadmap for the current narrower milestone.

### 2. Ingestion Layer

- `services/ingest/adapters/markdown/*`
- `services/ingest/adapters/office/*`
- `services/ingest/adapters/pdf/*`
- `services/connectors/jira/*`
- `services/connectors/confluence/*`

This layer normalizes source content into a shared evidence model while preserving structural metadata such as sections, clauses, pages, worksheets, and slides.

The target model is:

- canonical document is the source of truth
- Markdown is a readable projection from canonical document content
- PageIndex is a retrieval projection from canonical document content

PPTX and PDF currently build canonical-like documents directly. Jira and Confluence currently generate Markdown first and then normalize that Markdown back into canonical documents; that path is acceptable as a temporary bridge but is less structure-preserving than the target payload-to-canonical builders.

### 3. Retrieval Layer

- `services/retrieval/indexing/*`
- `services/retrieval/search/*`
- `services/retrieval/citations/*`

This layer builds page-level retrieval entries, applies ACL-safe filtering before ranking, performs hybrid retrieval, and assembles citations and source inspection payloads.

The current retrieval implementation remains PageIndex-first internally. PageIndex artifacts now use the canonical `{"entries": [...]}` shape in the skill-ready normalizer, sync-export, snapshots, and retrieval toolkit artifact loader. `scripts/retrieval/toolkit_cli.py` and `scripts/platform_cli.py` search/citation can consume PageIndex artifacts directly through `--page-index`, while corpus-backed document loading remains the default.

### 4. Local LLM Consumption Layer

- `services/analysis/*`

This layer currently contains Jira-specific report and spec-QA workflows plus local LLM backend adapters. The target is a source-generic retrieval-consumption seam where local LLM prompts are assembled only from retrieved evidence and citations. Jira-specific analysis should become a profile over that generic seam.

### 5. Evaluation and Ops Layer

- `services/eval/*`
- `services/ops/*`
- `scripts/eval/*`
- `scripts/gates/*`

This layer computes retrieval metrics, validates rollout gates, reports ops health, and enforces readiness checks. It remains useful support infrastructure, but portal/ops hardening and rollout gate expansion are not on the current critical path.

### 6. Portal Layer

- `apps/portal/*`

This layer exposes operator-facing views for ingestion status, corpus inventory, evaluation health, search results, and citation inspection. Hosted portal work and richer portal UX are deferred until the Markdown + PageIndex + local LLM foundation is stable.

## Main Data Flow

1. Source fixtures or source connectors produce canonical documents.
2. Canonical documents export readable Markdown.
3. Canonical documents derive PageIndex retrieval entries.
4. Search requests are ACL-filtered before ordering.
5. Ranked results are converted into citation payloads and source inspection payloads.
6. Local LLM workflows consume only retrieved evidence and citations.

## Trust and Safety Rules

- `canonical > supporting > contextual`
- ACL filtering happens before reranking
- ACL filtering happens before local LLM prompt assembly
- citation payload includes location-level evidence fields
- canonical documents remain truth; Markdown, PageIndex, and LLM outputs are projections or consumers
- clustering and summarization are later enrichment artifacts, not inputs to canonical truth

## Current Implementation Scope

This repo currently implements a fixture-backed foundation. The immediate roadmap is to stabilize the four-source conversion chain, standardize PageIndex artifact input/output, and add a source-generic local LLM consumption seam before returning to portal, ops hardening, clustering, or summarization.

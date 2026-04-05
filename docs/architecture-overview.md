# Architecture Overview

## Purpose

This document summarizes the current Phase 1 architecture as implemented in the repository.

## System Layers

### 1. Contract Layer

- `docs/adr/*`
- `packages/schema/*`
- `packages/acl/*`
- `packages/terminology/*`

This layer defines the product scope, source authority model, success metrics, canonical document shape, and ACL propagation rules.

### 2. Ingestion Layer

- `services/ingest/adapters/markdown/*`
- `services/ingest/adapters/office/*`
- `services/ingest/adapters/pdf/*`
- `services/connectors/jira/*`
- `services/connectors/confluence/*`

This layer normalizes source content into a shared evidence model while preserving structural metadata such as sections, clauses, pages, worksheets, and slides.

### 3. Retrieval Layer

- `services/retrieval/indexing/*`
- `services/retrieval/search/*`
- `services/retrieval/citations/*`

This layer builds page-level retrieval entries, applies ACL-safe filtering before ranking, performs hybrid retrieval, and assembles citations and source inspection payloads.

### 4. Evaluation and Ops Layer

- `services/eval/*`
- `services/ops/*`
- `scripts/eval/*`
- `scripts/gates/*`

This layer computes retrieval metrics, validates rollout gates, reports ops health, and enforces readiness checks.

### 5. Portal Layer

- `apps/portal/*`

This layer exposes operator-facing views for ingestion status, corpus inventory, evaluation health, search results, and citation inspection.

## Main Data Flow

1. Source fixtures or source connectors produce normalized documents.
2. Normalized documents are indexed into page-level entries.
3. Search requests are ACL-filtered before ordering.
4. Ranked results are converted into citation payloads and source inspection payloads.
5. Evaluation and portal layers consume the same retrieval contracts.

## Trust and Safety Rules

- `canonical > supporting > contextual`
- ACL filtering happens before reranking
- citation payload includes location-level evidence fields
- evaluation thresholds are release gates, not advisory metrics

## Current Implementation Scope

This repo currently implements a fixture-backed foundation. It is intentionally structured so that live integrations, service hosting, and reusable skill extraction can be added without changing the core contracts.


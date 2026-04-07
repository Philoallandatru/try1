# Live Integration Plan

## Purpose

This document describes how to evolve the current fixture-backed Phase 1 foundation into a live internal system without breaking the existing contracts.

## Current State

The repository currently uses:

- local fixtures for content sources
- local retrieval corpus snapshots
- static portal state generation
- local evaluation and rollout checks

This is intentional. The current implementation proves the contracts, validation model, and reusable component boundaries first.

## Integration Priorities

### 1. Replace Fixture Connectors with Live Connectors

Target modules:

- `services/connectors/jira/*`
- `services/connectors/confluence/*`

Required changes:

- add authenticated API clients
- support pagination and incremental sync cursors
- preserve version markers and attachment metadata
- map live payloads into the existing normalized document contract

Rules:

- do not change the retrieval or portal contracts first
- keep fixture-based tests as contract tests
- add separate integration tests for live connector behavior

### 2. Replace Minimal PDF Parsing with Production Parser Path

Target modules:

- `services/ingest/adapters/pdf/*`
- `services/ingest/visual_assets.py`

Required changes:

- integrate MinerU or the chosen offline parser
- preserve page, clause, table, figure, and language metadata
- extract image assets from Jira, Confluence, and PDF sources into readable Markdown evidence blocks
- add production OCR and optional local vision captioning for image content
- keep fidelity checks intact

Rules:

- parser swap must not weaken citation fidelity
- parser output must still fit the canonical schema
- image-generated text must be marked as OCR or vision caption metadata, not original source text

### 3. Add Persistent Storage and Real Indexing

Target areas:

- retrieval indexing
- ingestion persistence
- portal data access

Required changes:

- persist normalized documents
- persist page index entries
- support incremental index refresh
- preserve ACL metadata in stored form

Rules:

- page-level retrieval contract stays stable
- evaluation harness remains runnable against a snapshot corpus

### 4. Upgrade Portal to a Hosted Internal Service

Target modules:

- `apps/portal/*`

Required changes:

- replace static JSON generation with request-driven data loading
- expose internal APIs for ingestion status, corpus inventory, search, and citation inspection
- add identity-aware ACL behavior if the portal becomes multi-user

Rules:

- keep the current operator views unchanged unless justified
- keep citation drilldown grounded in the retrieval contract

### 5. Add Identity-Aware ACL Enforcement

Target areas:

- retrieval request handling
- connector ingestion metadata
- portal access control

Required changes:

- map users or groups to allowed policies
- evaluate ACLs per request
- preserve deny-by-default behavior

Rules:

- ACL filtering must still happen before reranking
- unauthorized candidates must never leak into answer assembly

## Recommended Rollout Order

1. Live Jira and Confluence connectors
2. Production visual asset extraction for Jira, Confluence, and PDF images
3. Production PDF parser path
4. Persistent document and page index storage
5. Hosted portal service
6. Identity-aware ACL

## Non-Negotiable Safeguards

- Keep current fixture tests as contract tests.
- Keep rollout gate green throughout each integration step.
- Preserve the canonical schema and citation contract.
- Add live integration tests without deleting local deterministic checks.

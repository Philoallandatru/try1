# ADR 0001: Phase 1 Scope

## Status

Accepted

## Context

Phase 1 defines the retrieval foundation for the SSD knowledge platform. The implementation must preserve evidence fidelity, enforce ACL-aware access, and support operator workflows without expanding into generic AI assistant behavior.

## In Scope

- Internal ingestion for `md`, `pdf`, `docx`, `xlsx`, `pptx`, Jira, and Confluence.
- Layout-preserving preprocessing with a PDF path built around MinerU or an equivalent offline parser.
- Canonical normalized document schema with provenance, ACL metadata, structure metadata, and terminology metadata.
- PageIndex-first retrieval with hybrid search, reranking, and exact citations.
- Internal operations portal for ingestion status, corpus inventory, search, citation inspection, and evaluation health.
- Retrieval evaluation harness with explicit recall and citation fidelity gates.
- Internal deployment only, with self-hosted inference only.

## Out of Scope

- PR review automation.
- Testcase optimization.
- Product design optimization.
- Any Jira or Confluence write-back workflow.
- Broad multi-team workflow orchestration.
- Human annotation product surfaces.

## Decision

Phase 1 is explicitly limited to trusted retrieval infrastructure and operator-facing workflows. Any downstream intelligence modules must remain deferred until the release gates defined for this phase are met.


# SSD Knowledge Platform Foundation Spec

## 1. Current Product Goal

The current milestone is a foundation-first slice for the SSD knowledge platform. Its only primary goal is to make Jira, Confluence, PPTX, and PDF content flow through one stable evidence chain:

1. Source payload or file -> canonical document.
2. Canonical document -> readable Markdown.
3. Canonical document -> PageIndex retrieval projection.
4. PageIndex retrieval results -> local LLM consumption.

This milestone is not a generic assistant, not a portal milestone, and not an ops-hardening milestone. It is the data and retrieval substrate required before higher-order intelligence work.

## 2. Scope

### In Scope

- Stable conversion for Jira, Confluence, PPTX, and PDF.
- Canonical document schema with provenance, ACL metadata, structure metadata, and terminology metadata.
- Readable Markdown exports derived from canonical documents.
- PageIndex-first retrieval derived from canonical documents.
- Exact citation and source inspection payloads from retrieval results.
- Local LLM consumption that uses retrieved evidence only.
- Fixture-backed happy-path and failure-path validation for the four priority sources.

### Out of Scope for the Current Milestone

- Hosted portal work or richer portal UX.
- Ops hardening beyond preserving current snapshot compatibility.
- Rollout gate expansion.
- Hosted services and database-backed storage.
- Request-scoped or identity-aware ACL.
- Jira or Confluence write-back.
- Clustering, topic discovery, document summaries, and cluster summaries.
- Production OCR or local vision caption backends.
- Broad multi-team workflow orchestration.

These items may remain in the longer-term product backlog, but they must not block the current Markdown + PageIndex + local LLM foundation.

## 3. Data Truth Model

- Canonical document is the source of truth.
- Markdown is a readable projection generated from canonical document content.
- PageIndex is a retrieval projection generated from canonical document content.
- Local LLM answers are generated consumers of retrieved evidence and must not define or overwrite canonical truth.
- Clustering and summarization are later enrichment artifacts and must not pollute canonical documents, Markdown projections, or PageIndex entries.

## 4. Source Authority Model

### Authority Levels

- `canonical`
  - normative specifications
  - ratified standards
  - approved design baselines
  - approved product requirements
- `supporting`
  - internal design notes
  - Jira discussions
  - Confluence explanations
  - design reviews
  - derived analyses
- `contextual`
  - press releases
  - announcements
  - background articles
  - non-normative summaries

### Ranking Rule

- Default ranking remains `canonical > supporting > contextual`.
- Contextual content must not outrank canonical content unless the user explicitly asks for background or non-normative context.
- Retrieval and LLM prompt assembly must preserve the source authority level of each evidence item.

## 5. Evidence and Fidelity Requirements

The system must preserve and expose the following first-class structure when available:

- headings
- clause numbering
- page numbers
- tables
- figures
- worksheet names
- slide boundaries
- document versions
- original language

Fidelity requirements:

- Citations must resolve to evidence-bearing content.
- Citations should include `document + version + page + section/clause` when available.
- Citations should include `table_id` or `figure_id` when available.
- Original language evidence must be preserved.
- Protocol and design documents must not be reduced to anonymous plain-text blobs.

## 6. Security and Access Model

ACL metadata must enter the canonical document model and remain present through PageIndex retrieval and answer assembly.

Minimum security constraints:

- ACL filtering happens before ranking.
- ACL filtering happens before local LLM prompt assembly.
- Deny-by-default behavior must be preserved.
- Unauthorized documents must not enter a candidate set and then be trimmed after ranking.

This milestone does not add request-scoped identity-aware ACL, but it must not weaken the existing ACL contract.

## 7. Retrieval and Local LLM Contract

Retrieval must remain PageIndex-first and source-agnostic across Jira, Confluence, PPTX, and PDF.

The retrieval contract includes:

- direct PageIndex artifact consumption
- document-corpus indexing compatibility where needed
- ACL-safe candidate filtering
- authority-aware ordering
- citation assembly
- source inspection

The local LLM contract includes:

- opt-in local LLM backend only
- deterministic extractive fallback when no LLM backend is selected
- prompt assembly from retrieval results and citations only
- explicit evidence gaps instead of unsupported inference
- source-generic behavior, with Jira-specific analysis implemented as a profile rather than a separate foundation path

## 8. Current Milestone Acceptance Checklist

The current milestone is complete only when:

- Jira, Confluence, PPTX, and PDF each have a stable path to canonical document output.
- The same canonical documents can export readable Markdown.
- The same canonical documents can export PageIndex using one artifact shape.
- PageIndex artifacts can be used as retrieval inputs without requiring rebuild from source documents as the only path.
- Retrieval search, citation, and source inspection work across all four priority source families.
- ACL filtering and authority ranking remain intact.
- Local LLM consumption works through one source-generic retrieval-consumption seam.
- Clustering and summarization are documented as later enrichment work, not current foundation requirements.

## 9. Longer-Term Product Context

The broader platform may still include portal, ops health, rollout gates, hosted services, richer indexing, clustering, and summarization. Those areas are deferred until the Markdown + PageIndex + local LLM foundation is stable.

The current roadmap is documented in `docs/replan-markdown-pageindex-local-llm.md`.

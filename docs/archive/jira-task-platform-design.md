# Jira Analysis Task Platform Design

## Status

Design document only. No implementation is implied by this document.

## Purpose

Define a Phase 1 task platform for deep Jira analysis that:

- starts from a Jira issue key
- retrieves grounded evidence from Jira, Confluence, and reusable spec PDF assets
- produces one composite report with four analysis sections
- compiles derived knowledge focused on Confluence knowledge updates
- preserves the repository's existing PageIndex-first, ACL-safe, citation-first contracts

This design is intentionally framework-neutral at the business layer so later execution frameworks can be introduced without rewriting the core model.

## Scope

### In Scope

- Task workbench for `jira_deep_analysis` and `knowledge_compile`
- Prefect-backed task orchestration, status, stop, resume, and rerun
- Reusable spec PDF asset ingestion
- Confluence snapshot reuse with optional sync-before-run
- Shared retrieval plus per-section follow-up retrieval
- Lightweight agentic search as a retrieval enhancer
- OCR-first and optional caption-based image evidence enrichment
- Composite report generation
- Confluence update proposal generation
- Lightweight concept cards

### Out of Scope

- Automatic Confluence write-back
- Topic-level clustering UI
- Vector search or GraphRAG as first-class runtime engines
- Multi-tenant access control beyond existing document ACL propagation
- Arbitrary DAG builders exposed to users

## Understanding Summary

- The primary user journey is entering a Jira issue key and launching an asynchronous deep-analysis task.
- The first-phase UI is task-list driven, not chat-first.
- The core output is one composite report containing `RCA`, `Spec Impact`, `Decision Brief`, and `General Summary`.
- Knowledge outputs are derived artifacts, not source-of-truth replacements.
- The most important knowledge artifact is a Confluence update proposal that describes what should be added, revised, or appended in Confluence.
- Spec PDFs are reusable knowledge assets, not temporary task attachments.
- PageIndex remains the formal retrieval engine in Phase 1, with plugin seams reserved for future engines.

## Assumptions

- The first release is for a single user or small internal team.
- Existing Jira, Confluence, retrieval, citation, and wiki export seams remain the default reusable substrate.
- Tasks have owners even in a small-team environment.
- Knowledge outputs support `draft` and `published` states and default to new versions on rerun.
- OCR and caption backends may be replaceable and may fail independently without failing the full task.

## Decision Log

- `D1` Use Prefect as the task control plane.
- `D2` Keep PageIndex as the only formal retrieval engine in Phase 1.
- `D3` Support retrieval-engine plugins, but defer live vector and GraphRAG integrations.
- `D4` Use shared retrieval plus per-section follow-up retrieval.
- `D5` Use lightweight agentic search only as a search enhancer.
- `D6` Make spec PDFs reusable knowledge assets.
- `D7` Use Confluence snapshots by default, with an optional sync-before-run toggle.
- `D8` Use three business checkpoints: `retrieval_ready`, `analysis_ready`, `knowledge_ready`.
- `D9` Make knowledge compilation center on Confluence update proposals.
- `D10` Use lightweight concept cards instead of full concept pages.
- `D11` Make the main workbench layout `task list + right-side detail`.
- `D12` Track retrieval comparison metrics for `hit quality`, `readability`, and `citation fidelity`.

## Architecture Overview

The platform is organized into five major modules:

1. `Task Control Plane`
   Prefect-based orchestration shell for queueing, run state, stop, resume, rerun, and logs.

2. `Knowledge Asset Layer`
   Versioned assets for Confluence snapshots, Jira snapshots, spec PDF assets, and derived image evidence metadata.

3. `Retrieval Engine Interface`
   Stable search, citation, inspection, and engine-comparison contract.

4. `Analysis Kernel`
   Section-based analysis runners that consume shared evidence and optionally request extra retrieval rounds.

5. `Knowledge Compiler`
   Derived artifact builder for report assembly, Confluence update proposals, and lightweight concept cards.

Framework-specific code must remain limited to adapters around task orchestration and optional agent runners.

## Core Task Types

### `jira_deep_analysis`

Primary task that:

- loads Jira issue context
- optionally syncs Confluence before analysis
- loads selected spec assets
- performs shared retrieval
- runs four section analyzers
- builds the composite report
- emits derived knowledge artifacts

### `knowledge_compile`

Secondary task that:

- consumes previously generated section outputs and report artifacts
- regenerates or upgrades the derived knowledge layer
- avoids rerunning retrieval or analysis unless dependent artifacts are stale

## Input Contract

### `jira_deep_analysis` Request

Required fields:

- `task_type`
- `jira_issue_key`
- `owner`

Optional fields:

- `confluence_sync_before_run: bool`
- `spec_asset_ids: list[str]`
- `image_enrichment`
- `retrieval_profile`
- `section_profile_versions`
- `prompt_profile_versions`
- `comparison_request`

Example:

```json
{
  "task_type": "jira_deep_analysis",
  "jira_issue_key": "SSD-777",
  "owner": "alice",
  "confluence_sync_before_run": true,
  "spec_asset_ids": ["nvme-base-2.1"],
  "image_enrichment": {
    "ocr": true,
    "caption": true
  },
  "retrieval_profile": "default.v1",
  "section_profile_versions": {
    "rca": "v1",
    "spec_impact": "v1",
    "decision_brief": "v1",
    "general_summary": "v1"
  },
  "prompt_profile_versions": {
    "shared_retrieval": "v1",
    "knowledge_compile": "v1"
  }
}
```

## Output And Artifact Contract

Each task writes a run directory with structured artifacts.

Minimum artifacts:

- `run_manifest.json`
- `shared_retrieval_bundle.json`
- `section_outputs/rca.json`
- `section_outputs/spec_impact.json`
- `section_outputs/decision_brief.json`
- `section_outputs/general_summary.json`
- `report/report.md`
- `knowledge/confluence_update_proposal.json`
- `knowledge/concept_cards.json`

Each artifact records:

- `artifact_type`
- `step_name`
- `step_version`
- `input_hash`
- `depends_on`
- `engine`
- `prompt_version`
- `status`
- `created_at`
- `stale`

These fields allow targeted reruns without changing user-visible checkpoint semantics.

## Task State Model

### Run States

- `queued`
- `running`
- `stopping`
- `stopped`
- `failed`
- `completed`

### Business Checkpoints

- `retrieval_ready`
- `analysis_ready`
- `knowledge_ready`

The checkpoints are intentionally stable. Internal step sequences may evolve over time without changing the user-facing recovery model.

## Stop, Resume, And Rerun Semantics

### Stop

User-triggered stop requests move the task to `stopping` and allow the current active step to end cleanly where possible.

### Resume

Resume uses the most recent stable checkpoint and reuses valid artifacts. It does not attempt to continue from arbitrary internal prompt substeps.

### Rerun

Rerun creates a new task version by default. Existing artifacts are preserved for audit and comparison.

### Staleness

If a section prompt, retrieval profile, engine, or compiler rule changes, downstream artifacts are marked `stale` and recomputed from the nearest valid checkpoint.

## Knowledge Asset Layer

### Spec PDF Assets

Each uploaded PDF becomes a reusable asset with:

- canonical document
- Markdown projection
- PageIndex artifact
- provenance and build metadata
- asset version

This supports future spec-focused analysis without redesigning the asset model.

### Confluence Assets

Confluence content continues to come from snapshots. The user may choose to sync before analysis, but the task always consumes a normalized snapshot shape rather than live response payloads directly.

### Image Evidence

Jira and Confluence image evidence is stored with:

- original reference
- OCR text when available
- caption when available
- extraction backend metadata
- extraction status

Failure to extract OCR or caption must not fail the task. The image reference remains in the evidence chain.

## Retrieval Engine Interface

The retrieval interface must be stable across engines:

- `build_index`
- `search`
- `inspect`
- `cite`
- `compare`

### Phase 1 Engine

- `PageIndexEngine`

### Reserved Future Engines

- `VectorEngine`
- `GraphRAGEngine`

The first release only implements `PageIndexEngine`, but comparison payloads should already allow multiple engines later.

## Retrieval Strategy

### Shared Retrieval

Run one shared retrieval stage across Jira, Confluence, and selected spec assets. This produces the shared retrieval bundle used by all sections.

### Section Follow-Up Retrieval

Each section runner may request targeted extra retrieval rounds based on its own needs.

Examples:

- `RCA` may request error-code or stack-trace focused retrieval
- `Spec Impact` may request clause- or component-specific retrieval
- `Decision Brief` may request decision-history or risk-pattern retrieval

## Agentic Search

Phase 1 agentic search is limited to a `Search Enhancer`.

It may:

- rewrite the query
- add terminology or synonym expansion
- inject module, protocol, or issue-type cues
- trigger one or two extra retrieval rounds

It must not become an unconstrained research agent. The final evidence path still flows through the retrieval engine and standard citation contract.

## Analysis Kernel

The analysis kernel runs four section analyzers:

- `RCA`
- `Spec Impact`
- `Decision Brief`
- `General Summary`

All sections consume the shared retrieval bundle. Each may perform follow-up retrieval and then emit a structured section artifact.

Section runners should be independently versioned so prompt or logic changes can invalidate only the affected section outputs.

## Composite Report Model

The user-facing report is one composite artifact with four tabs or sections:

- `RCA`
- `Spec Impact`
- `Decision Brief`
- `General Summary`

The UI may render these as tabs, but the underlying artifact should remain section-addressable for reruns and future extensibility.

## Knowledge Compiler

The compiler generates three derived outputs:

### Confluence Update Proposal

Primary knowledge artifact. Suggested fields:

- `proposal_id`
- `source_issue_key`
- `candidate_pages`
- `knowledge_action`
- `proposed_delta`
- `supporting_evidence`
- `confidence`
- `open_questions`
- `status`
- `version`

Supported `knowledge_action` values:

- `add`
- `revise`
- `append`
- `no_change`

### Wiki Draft

Human-readable draft built from the composite report for review and debugging.

### Lightweight Concept Cards

Evidence-anchored cards for:

- terminology
- modules
- interfaces
- risk points
- rules

Each card must point back to citations or inspected evidence.

## Frontend Workbench

### Layout

- left: task list
- top: new-task entry
- right: task details

### Task List Filters

- status
- owner
- project
- issue key
- updated time

### Detail Panels

- `Overview`
- `Logs`
- `Evidence`
- `Report`
- `Knowledge`

### Report View

Render one report with four tabs:

- `RCA`
- `Spec Impact`
- `Decision Brief`
- `General Summary`

### Knowledge View

- `Confluence Update Proposal`
- `Wiki Draft`
- `Concept Cards`

### Retrieval Comparison View

Even before multiple engines are live, the UI model should reserve comparison fields for:

- engine
- query
- top hits
- hit quality
- readability
- citation fidelity

## Ownership And Versioning

### Task Ownership

Each task has an `owner` field.

### Knowledge Ownership

Knowledge artifacts support:

- `draft`
- `published`

### Versioning

Reruns create new versions by default instead of destructive overwrite.

## Verification Strategy

### Task Contract Tests

Verify:

- submit
- stop
- resume
- rerun
- ownership
- versioning

### Evidence Contract Tests

Verify that retrieval, inspection, citation, ACL preservation, and image enrichment still obey repository constraints.

### Section Contract Tests

Verify:

- shared retrieval bundle generation
- independent section rerun behavior
- stale propagation rules

### Knowledge Contract Tests

Verify:

- Confluence update proposals remain evidence-backed
- concept cards always reference citations
- draft/published and version semantics are preserved

## Framework Readiness

To preserve future flexibility:

- keep Prefect-specific code in task adapters
- keep optional agent-framework code in analysis-runner adapters
- do not embed framework-specific state into business artifacts

Future integrations such as AgentScope, Goose, or Temporal should replace adapters, not the asset model, retrieval contract, or frontend view model.

## Risks And Mitigations

### Risk: Derived knowledge becomes vague or untraceable

Mitigation:

- keep Confluence update proposal as the primary knowledge target
- require citation-backed concept cards

### Risk: Stop/resume semantics become brittle

Mitigation:

- keep only three stable checkpoints
- use artifact versioning and staleness for flexibility

### Risk: Search enhancement drifts into unconstrained agent research

Mitigation:

- restrict agentic search to query enhancement and bounded follow-up retrieval
- require all evidence to resolve through the formal retrieval interface

### Risk: Future engine integrations force a rewrite

Mitigation:

- define a stable retrieval-engine interface now
- keep engine-specific code out of report and knowledge compiler contracts

## Follow-Ups

- Write an implementation plan with vertical slices and acceptance criteria.
- Define the JSON schema for run manifests and section artifacts.
- Define the Confluence update proposal schema in a dedicated contract doc.
- Define the spec asset ingestion flow and upload constraints.
- Design the workbench UI states and task-detail wireframes before implementation.

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
- `scripts/workspace_cli.py portal-state`

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

## 10. Jira Analysis Task Run Manifest Contract

Produced by:

- `services/workspace/task_manifest.py`

Current shape:

- `task_type`
- `owner`
- `input_config`
- `run_id`
- `run_version`
- `status`
- `checkpoints`
- `artifacts`
- `created_at`
- `updated_at`
- `error`

Each checkpoint contains:

- `reached`
- `updated_at`
- `artifact_types`

Each artifact record contains:

- `artifact_type`
- `path`
- `step_name`
- `step_version`
- `input_hash`
- `depends_on`
- `engine`
- `prompt_version`
- `status`
- `created_at`
- `stale`

Key invariants:

- only the business checkpoints `retrieval_ready`, `analysis_ready`, and `knowledge_ready` are exposed
- downstream artifact staleness propagates through `depends_on`
- run and artifact contracts remain dict-first so later orchestration layers can adopt them without adapter-heavy rewrites

## 11. Task Control Adapter Baseline Contract

Produced by:

- `services/workspace/task_control.py`
- `services/workspace/prefect_adapter.py`
- `services/workspace/prefect_flows.py`
- `scripts/workspace_cli.py control-run`
- `scripts/workspace_cli.py sync-prefect-state`
- `scripts/workspace_cli.py submit-prefect-run`

Current control actions:

- `stop`
- `resume`
- `rerun`
- `rerun-section`

Current adapter state mapping:

- `scheduled` -> `queued`
- `running` -> `running`
- `cancelling` -> `stopping`
- `cancelled` -> `stopped`
- `failed` -> `failed`
- `succeeded` -> `completed`

Current Prefect-shaped state mapping:

- `Scheduled` / `Pending` -> `scheduled`
- `Running` -> `running`
- `Cancelling` -> `cancelling`
- `Cancelled` -> `cancelled`
- `Completed` -> `succeeded`
- `Failed` / `Crashed` -> `failed`

Each control event contains:

- `event_id`
- `run_id`
- `run_version`
- `task_type`
- `action`
- `requested_by`
- `step_name`
- `reason`
- `result`
- `created_at`

Key invariants:

- control events append to `control-events.jsonl` beside the run manifest
- stop requests move the run to `stopping` while preserving existing artifacts and checkpoints
- resume uses the nearest valid business checkpoint to choose the next step
- rerun creates a new run manifest version rather than overwriting previous artifacts
- section rerun marks only the target section artifact stale first, then propagates staleness to dependent artifacts
- `control-run --action rerun-section --execute` rewrites the target section, composite report, knowledge artifacts, and result payload, then clears stale state for rebuilt artifacts
- `sync-prefect-state` records Prefect-shaped runtime metadata under `manifest.runtime.prefect` without requiring Prefect as an installed dependency
- `services.workspace.prefect_flows.build_jira_deep_analysis_flow` provides a lazy real Prefect flow factory and does not import Prefect unless explicitly used
- this is an adapter contract only; Phase 1 does not require Prefect as a runtime dependency

## 12. Confluence Update Proposal Contract

Produced by:

- `packages/schema/confluence-update-proposal-schema.json`

Current shape:

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

Key invariants:

- `knowledge_action` is one of `add`, `revise`, `append`, `no_change`
- `candidate_pages` must contain at least one target page candidate
- `supporting_evidence` must stay evidence-bearing and citation-shaped

## 13. Concept Cards Contract

Produced by:

- `packages/schema/concept-cards-schema.json`

Current shape:

- `cards[]`
  - `card_id`
  - `label`
  - `category`
  - `summary`
  - `evidence`

Key invariants:

- `category` is one of `terminology`, `module`, `interface`, `risk`, `rule`
- every card must include at least one evidence reference
- concept cards remain derived artifacts and must not replace canonical source documents

## 14. Spec Asset Metadata Contract

Produced by:

- `services/workspace/spec_assets.py`

Current shape:

- `asset_id`
- `display_name`
- `version`
- `document_id`
- `source_pdf`
- `preferred_parser`
- `parser_used`
- `created_at`
- `paths`

`paths` contains:

- `document_json`
- `corpus_json`
- `markdown`
- `page_index`

Key invariants:

- each ingestion writes a new versioned asset directory
- one asset version must preserve canonical document, corpus, markdown projection, and page-index projection together
- registry entries must remain reusable by later task flows without rebuilding the PDF immediately

## 15. Retrieval Engine Comparison Baseline Contract

Produced by:

- `services/retrieval/engine.py`

Current shape:

- `engine`
- `query`
- `result_count`
- `top_result_document`
- `manual_review`

`manual_review` contains:

- `hit_quality`
- `readability`
- `citation_fidelity`

Key invariants:

- Phase 1 uses `pageindex` as the only live engine
- comparison payload must still exist even with one engine so later multi-engine evaluation does not require a contract rewrite
- retrieval engine adapters must preserve existing ACL filtering and citation behavior

## 16. Shared Retrieval Bundle Baseline Contract

Produced by:

- `services/retrieval/engine.py`
- `services/analysis/deep_analysis.py`

Current shape:

- `engine`
- `query`
- `results`
- `citation`
- `inspection`
- `comparison`
- `citations`
- `source_breakdown`

Key invariants:

- one bundle represents one shared retrieval pass over the secondary evidence corpus
- downstream consumers may split or append to the bundle, but should not reinterpret it as multiple unrelated retrieval runs
- `source_breakdown` must preserve document/source visibility for later section follow-up retrieval

## 17. Search Enhancer Baseline Contract

Produced by:

- `services/analysis/search_enhancer.py`
- `services/analysis/deep_analysis.py`

Current shape:

- `base_query`
- `section_name`
- `scope_hint`
- `additions`
- `bounds`
- `query`

Key invariants:

- enhancer output is deterministic and bounded
- enhancer caps Jira list-field values, total additions, and final query length
- enhancer may add issue family, route, component, labels, fix versions, section cues, and scope hints
- enhanced queries still execute through the active retrieval engine and ACL-filtered citation path
- no unconstrained web or agent research is introduced in Phase 1

## 18. Section Analysis Kernel Baseline Contract

Produced by:

- `services/analysis/section_analysis.py`
- `services/analysis/deep_analysis.py`

Current shape:

- `section_outputs`
  - `rca`
  - `spec_impact`
  - `decision_brief`
  - `general_summary`
- `composite_report`

Each section output contains:

- `section_name`
- `label`
- `runner_version`
- `followup_retrieval`
- `citations`
- `prompt`
- `answer`

`followup_retrieval` contains:

- `mode`
- `status`
- `base_bundle`
- `base_query`
- `enhanced_query`
- `enhancement`
- `allowed_policies`
- `top_k`
- `scope_hint`
- `followup_results`
- `followup_citations`

Key invariants:

- all four section outputs must be emitted from the shared retrieval baseline
- section runners are independently versioned
- follow-up retrieval remains append-only and bounded
- follow-up retrieval uses deterministic enhanced queries and preserves ACL filtering
- persisted section output artifacts are self-contained enough to run bounded follow-up retrieval later
- the composite markdown report must include citation/evidence baselines or explicit section artifact links
- manifest artifact input hashes must include snapshot document/page-index identity, not only CLI parameters

## 19. Image Evidence Enrichment Baseline Contract

Produced by:

- `services/analysis/image_evidence.py`
- `services/analysis/deep_analysis.py`

Current shape:

- `asset_count`
- `indexed_asset_count`
- `degraded_asset_count`
- `source_breakdown`
- `assets[]`

Each asset contains:

- `asset_id`
- `document_id`
- `source_type`
- `filename`
- `page`
- `section`
- `media_type`
- `image_uri`
- `local_path`
- `ocr_status`
- `caption_status`
- `enrichment_state`
- `indexed_text_fields`
- `gaps`
- `provenance`

Key invariants:

- image evidence remains derived from canonical document `visual_assets`
- Phase 1 records provided OCR/caption metadata and explicit missing-state gaps; it does not require production OCR or vision backends
- image evidence failures must degrade individual assets, not fail the full Jira analysis task
- indexed OCR/caption/alt text remains available through Markdown/content-block retrieval when provided

## 20. Knowledge Compiler Baseline Contract

Produced by:

- `services/analysis/knowledge_compiler.py`
- `services/analysis/deep_analysis.py`

Current artifacts:

- `knowledge/confluence_update_proposal.json`
- `knowledge/concept_cards.json`
- `knowledge/wiki_draft.md`

Key invariants:

- knowledge artifacts are derived from section/composite report artifacts and shared retrieval evidence
- `confluence_update_proposal` remains draft-only in Phase 1 and does not write back to Confluence
- `concept_cards` must be evidence-anchored when cards are emitted
- weak-evidence cases must not fabricate evidence; use `knowledge_action: no_change`, empty evidence, and explicit open questions

## 21. Static Task Workbench State Contract

Produced by:

- `apps/portal/portal_state.py`

Rendered by:

- `apps/portal/index.html`
- `apps/portal/app.js`

Current shape:

- `task_workbench`
  - `new_task_entry`
    - `fields[]`
    - `available_profiles[]`
    - `available_sources[]`
    - `command_preview`
  - `filters`
  - `selected_task_id`
  - `tasks[]`
  - `detail_tabs[]`
  - `report_tabs[]`
  - `knowledge_panels[]`
  - `retrieval_comparison`
  - `controls`

Each task contains:

- `task_id`
- `task_type`
- `issue_key`
- `project`
- `owner`
- `status`
- `updated_at`
- `selected`
- `summary`

Key invariants:

- the workbench state is static and fixture-backed in Phase 1
- when `workspace_dir` is provided, workbench tasks and artifact statuses are derived from real workspace run manifests
- `workspace_cli.py portal-state <workspace>` writes a portal state JSON file from real workspace run artifacts without starting a web server
- `new_task_entry` exposes the minimal analyze form state: `Issue Key`, `Analysis Profile`, and `Run`
- controls are UI placeholders for `stop`, `resume`, and `rerun`; they do not execute orchestration yet
- report tabs preserve the four-section analysis model: `RCA`, `Spec Impact`, `Decision Brief`, and `General Summary`
- knowledge panels reserve Confluence proposal, wiki draft, and concept-card review surfaces
- retrieval comparison remains present even while `pageindex` is the only active engine

## 22. Workspace Run Artifact Query Contract

Produced by:

- `services/workspace/workspace.py`
- `scripts/workspace_cli.py runs`
- `scripts/workspace_cli.py run-detail`
- `scripts/workspace_cli.py run-artifact`

Current commands:

- `runs <workspace>`
- `run-detail <workspace> <run>`
- `run-artifact <workspace> <run> <artifact_type>`

Key invariants:

- query commands are read-only and must not mutate run manifests or artifacts
- run summaries expose status, owner, issue key, checkpoints, artifact counts, and stale artifact counts
- run detail includes manifest, control events, artifact inventory, and a compact result summary
- artifact reads return JSON payloads for `.json` artifacts and text content for markdown/text artifacts
- artifact lookup uses the run manifest inventory rather than guessing file locations when possible

## 23. Workspace Source Registry Contract

Produced by:

- `services/workspace/source_registry.py`
- `scripts/workspace_cli.py source`
- `scripts/workspace_cli.py selector`
- `scripts/workspace_cli.py profile`
- `scripts/workspace_cli.py fetch-source`
- `scripts/workspace_cli.py refresh`
- `scripts/workspace_cli.py rebuild`
- `scripts/workspace_cli.py reindex`
- `scripts/workspace_cli.py analyze-jira`
- `scripts/workspace_cli.py run-analysis`

Current registry files:

- `workspace.yaml`
- `sources/<source-name>.yaml`
- `selectors/<selector-name>.yaml`
- `profiles/<profile-name>.yaml`
- `.local/credentials.yaml`

Current cache files:

- `raw/<kind>/payloads/<source-name>/latest.json`
- `raw/<kind>/payloads/<source-name>/fetch-manifest.json`
- `raw/<kind>/payloads/<source-name>/history/*.json`
- `build/normalize/<source-name>/manifest.json`
- `build/normalize/<source-name>/documents.json`
- `build/index/pageindex_v1/manifest.json`

Key invariants:

- registry files are local workspace configuration and are not runtime payload cache files
- `workspace.yaml` is the default workspace config; older `config.json` files are read-only compatible
- source names are stable identifiers used by payload cache and build manifests
- credentials support `bearer_env` and `bearer_inline`; env references are preferred for durable local workspaces
- `pdf.local_file` sources are represented as registry sources and write reusable spec assets under `raw/files/spec_assets/`
- `pdf.local_file` fetches also persist `raw/pdf/payloads/<source>/latest.json`, `fetch-manifest.json`, and normalize artifacts so PDF sources participate in the same cache DAG
- fetch cache invalidation is driven by source config hash, selector hash, and optional refresh frequency
- cached raw payloads live under `raw/<kind>/payloads/<source>/latest.json` and `history/*.json`
- `refresh <workspace>` only refetches stale sources with a previous selector profile in their fetch manifest
- `rebuild <workspace> --from raw` rebuilds normalize artifacts from cached payloads and assembles the snapshot without refetching
- `reindex <workspace>` rebuilds `build/index/pageindex_v1/page_index.json` from normalized documents without refetching
- run profiles may include `inputs.spec_assets` as a list of registered spec asset ids
- `analyze-jira <workspace> --profile ...` is the recommended Jira analysis entrypoint
- `analyze-jira` and `run-analysis` build a profile-scoped snapshot from the selected profile inputs unless `--use-existing-snapshot` is supplied
- `--use-existing-snapshot` reuses the matching profile-scoped snapshot rather than the shared `snapshots/current/` workspace snapshot
- analysis manifests record the selected sources, selected selector profiles, selected spec assets, and the scoped snapshot path used for the run
- `smoke-deep-analysis <workspace> --profile ...` routes through the profile analysis path
- `status <workspace>` exposes `cache.fetch`, `cache.normalize`, `cache.index`, and `cache.analysis` freshness
- `snapshots/current/` remains limited to `manifest.json`, `documents.json`, and `page_index.json`

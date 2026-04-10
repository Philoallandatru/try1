# Implementation Status

## Summary

The repository currently covers the full older Task 1 to Task 15 skeleton for Phase 1 with a minimal runnable implementation.

The active near-term roadmap has been narrowed to Markdown + PageIndex + local LLM consumption for Jira, Confluence, PPTX, and PDF. See `docs/replan-markdown-pageindex-local-llm.md`.

The current foundation is now largely in place against that narrower roadmap:

- Jira now builds canonical sections and content blocks directly from payload fields while preserving the existing readable Markdown projection.
- Confluence now builds canonical sections and content blocks directly from storage payloads while preserving the existing readable Markdown projection.
- PPTX and PDF are closer to the target because their adapters build canonical-like documents directly before Markdown/PageIndex export.
- PageIndex artifact shape has been standardized to `{"entries": [...]}` for the skill-ready normalizer, sync-export, snapshots, and retrieval toolkit artifact loading.
- `scripts/retrieval/toolkit_cli.py` and `scripts/platform_cli.py` search/citation can now consume exported PageIndex artifacts directly via `--page-index`; corpus-oriented document loading remains the default.
- `scripts/platform_cli.py` and `scripts/retrieval/toolkit_cli.py` can now also reuse snapshot-managed `page_index.json` via `--snapshot-dir`, and `retrieval-consume` can reuse snapshot-managed `documents.json`.
- Local LLM consumption now has a source-generic retrieval-consumption seam plus a generic CLI surface; the remaining work is mainly profile cleanup and fidelity expansion.

## Completed

- Task 1: ADR contract set
- Task 2: monorepo skeleton
- Task 3: schema and terminology contract
- Task 4: ACL contract
- Task 5: Markdown and Office preprocessing
- Task 6: PDF extraction and fidelity checks
- Task 7: Jira connector
- Task 8: Confluence connector
- Task 9: PageIndex-first hybrid retrieval
- Task 10: citation assembly and source inspection
- Task 11: evaluation harness and gold set runner
- Task 12: internal ops portal MVP
- Task 13: ops freshness and backup/restore checks
- Task 14: rollout gate automation
- Task 15: deferred module contracts
- Live step A: Jira Server live sync with canonical markdown normalization
- Live step B: Confluence page live sync with canonical markdown normalization
- Live step C: skill-ready normalization seam extraction
- Live step D: skill-ready retrieval seam extraction
- Live step E: independent skill-ready CLI entrypoints for normalization and retrieval
- Live step F: repository-local skill packaging for normalization and retrieval reuse
- Live step G: local snapshot persistence for documents and page index
- Live step H: incremental snapshot refresh from normalized sync payloads
- Live step I: snapshot-backed ops health through unified platform CLI
- Live step J: agent self-loop rules documented in `agent.md`
- Live step K: sequential `sync-health` ops path through unified platform CLI
- Live step L: sequential `multi-sync-health` dual-source ops path through unified platform CLI
- Live step M: mock-validated live dual-source orchestration for `multi-sync-health`
- Live step N: profile-backed `multi-sync-health` configuration for reusable ops manifests
- Live step O: profile-driven ops orchestration documented as a gated module contract
- Live step P: JSON schema contract and runtime validation for ops profiles
- Live step Q: Jira bug-template field mapping and `expand=names` custom field normalization
- Live step R: configurable Jira field-alias contract loaded from schema assets
- Live step S: schema-style test coverage for Jira field-alias contract
- Live step T: explicit Confluence page mapping contract with fixture and live normalization coverage
- Live step U: multi-source ops orchestration now regression-tests source contract content through snapshot persistence for CLI and profile paths
- Live step V: persisted page-index search now handles JSON-restored token lists as well as in-memory token sets
- Live step W: Jira issue analysis workflow covers markdown reporting, time-window reports, custom prompts, and Jira-plus-spec retrieval payloads
- Live step X: unified CLI exposes Jira time reports and Jira-plus-spec QA prompt payloads
- Live step Y: Jira analysis CLI supports both fixture-backed and live Jira Server sources
- Live step Z: Jira time reports can be written to Markdown files through `--output-md`
- Live step AA: Jira-plus-spec QA emits an extractive draft answer and can write it through `--output-answer-md`
- Live step AB: Jira analysis/reporting workflow is documented as a gated module contract
- Live step AC: Jira report filtering supports explicit windows, calendar dates, and exact ISO timestamps
- Live step AD: batch Jira-plus-spec reports run QA for each time-filtered issue and can write combined Markdown
- Live step AE: Jira-plus-spec QA supports opt-in local LLM backends while preserving extractive default behavior
- Live step AF: Jira-plus-spec QA exposes strict, balanced, and exploratory prompt modes for local LLM answers
- Live step AG: Jira time reports support opt-in local LLM summaries with separate raw report and answer exports
- Live step AH: Jira, Confluence, and MinerU PDF ingestion merge image references plus provided OCR/caption metadata into readable and indexable Markdown evidence blocks
- Live step AI: skill-ready normalization CLI can export readable Markdown and PageIndex JSON for Jira sync, Confluence sync, PPTX, PDF, and other normalized document sources

## Validation Status

Current validation entrypoints:

- `python scripts/gates/check_adr_contract.py`
- `python scripts/gates/check_repo_shape.py`
- `python scripts/gates/check_module_contracts.py`
- `python scripts/platform_cli.py ops-health --snapshot-dir .tmp/snapshot`
- `python scripts/platform_cli.py sync-health jira fixtures/connectors/jira/incremental_sync.json --snapshot-dir .tmp/snapshot --reference-time-iso 2026-04-06T09:10:00Z`
- `python scripts/platform_cli.py multi-sync-health --snapshot-dir .tmp/snapshot --jira-path fixtures/connectors/jira/incremental_sync.json --confluence-path fixtures/connectors/confluence/incremental_sync.json --reference-time-iso 2026-04-06T09:10:00Z`
- `python scripts/platform_cli.py multi-sync-health --profile fixtures/ops/multi_sync_health_profile.json --snapshot-dir .tmp/snapshot`
- `python -m unittest tests.schema.test_ops_profile_schema`
- `python -m unittest tests.schema.test_jira_field_aliases_schema`
- `python scripts/eval/run_recall_eval.py --dataset eval/gold_queries.yaml`
- `python scripts/gates/run_phase1_gate.py`
- `python -m unittest discover -s tests -t . -p "test_*.py" -v`

## Current Quality Snapshot

- `recall@10 = 1.0`
- `ndcg@10 = 1.0`
- `citation_fidelity = 1.0`
- rollout gate = pass

## Remaining Gaps to Production

- Expand fidelity for richer Jira and Confluence source shapes beyond the current fixture-backed paths.
- Continue simplifying Jira profile/orchestration boundaries now that the generic seam exists.
- Add snapshot-based index reuse to reduce unnecessary rebuilds.
- Replace minimal offline PDF parsing with the target production parser stack.
- Add production OCR and local vision caption backends for image assets; current visual asset support indexes image references and provided OCR/caption metadata.
- Defer hosted portal, persistent storage, real indexing backends, and request-scoped ACL identity handling until the current foundation chain is stable.

## Reusable Components

- schema contract validators
- ACL contract validators
- document normalization adapters
- live Jira and Confluence canonical markdown connectors
- Jira bug-template field mapping for structured issue metadata
- configurable Jira field-alias contract
- explicit Confluence page mapping contract for space, version, attachments, and storage-body normalization
- PDF fidelity checker
- PageIndex builder
- hybrid retrieval runner
- citation formatter
- snapshot persistence and incremental refresh
- snapshot-backed ops health reporting
- sequential connector -> snapshot -> ops health orchestration
- sequential multi-source connector -> snapshot -> aggregated ops health orchestration
- live dual-source orchestration validation through CLI-level mocks
- persisted source contract validation through `multi-sync-health` CLI and profile snapshot output
- persisted page-index search compatibility for JSON-restored snapshots
- Jira issue analysis helpers for markdown reports, window/date/timestamp time filters, prompt templates, and spec-backed question payloads
- unified CLI commands for fixture-backed and live Jira report, Markdown report export, optional local-LLM Jira report summary export, Jira-plus-spec QA payload generation, extractive/local-LLM answer export, and batch Jira-plus-spec reports
- visual asset normalization for merging Jira image attachments, Confluence inline/attachment images, and MinerU PDF image blocks into canonical Markdown content
- Markdown export utilities for turning canonical documents into readable Markdown and PageIndex JSON through `scripts/ingest/normalize_cli.py --output-md --output-page-index`
- source-generic retrieval-consumption helper for assembling citation-backed prompts and optional local LLM answers across Jira, Confluence, PPTX, and PDF fixture paths
- direct Jira payload-to-canonical normalization path with preserved readable Markdown projection
- direct Confluence payload-to-canonical normalization path with preserved readable Markdown projection
- gated Jira analysis/reporting module contract
- profile-backed source manifests for multi-source ops runs
- ops profile schema contract and runtime validation
- eval harness
- rollout gate runner

## Current Roadmap Status

### P0

- Done: persist foundation-first roadmap.
- Done: standardize skill-ready PageIndex artifact shape as `{"entries": [...]}`.
- Done: add direct PageIndex artifact input for `scripts/retrieval/toolkit_cli.py` and platform search/citation.
- Done: add four-source Markdown/PageIndex export tests.
- Done: document Jira/Confluence Markdown-first canonicalization as implementation debt in the connector docs.

### P1

- Done for current fixture-backed paths: add richer Jira and Confluence direct payload-to-canonical builders.
- Add source-generic local LLM retrieval-consumption service.
- Refactor Jira-specific analysis onto the generic consumption seam.

### P2

- Add index reuse and contextual chunking.
- Decide the PageIndex vs embedding/chunk index relationship.
- Add clustering and summarization as derived enrichment only.

## Operational Notes

- `scripts/platform_cli.py ops-health` now supports fixture mode and snapshot mode.
- `scripts/platform_cli.py sync-health` now supports a one-command operational refresh and health check path.
- `scripts/platform_cli.py multi-sync-health` now supports sequential Jira and Confluence refresh into a shared snapshot before reporting aggregated health.
- `scripts/platform_cli.py multi-sync-health --profile ...` now supports reusable source manifests with CLI override support.
- `packages/schema/ops-profile-schema.json` now defines the profile contract, and invalid profiles fail before orchestration starts.
- `packages/schema/jira-field-aliases.json` now defines the default Jira bug-field alias contract.
- Jira live sync requests `expand=names` and can map `customfield_*` display names such as `Root Cause` and `How to fix`.
- `docs/confluence-page-mapping.md` now defines the normalized Confluence page contract, including body, attachment, space, and version handling.
- `tests/ops/test_platform_cli.py` validates that `multi-sync-health` persists Jira issue fields and Confluence page mapping content into the shared snapshot for both direct CLI arguments and profile-driven runs.
- `services/retrieval/search/hybrid_search.py` accepts persisted page-index `tokens` lists in addition to in-memory token sets.
- `services/analysis/retrieval_consumption.py` now provides a source-generic retrieval -> prompt assembly -> local LLM consumption seam, and Jira spec QA now reuses it internally while preserving existing output contracts.
- `scripts/platform_cli.py retrieval-consume` now exposes the source-generic retrieval-consumption seam for Jira/Confluence fixture payloads and file-backed Markdown/Office/PDF sources.
- `connector` and `retrieval-consume` now support explicit UTF-8 `--output-json` file output for real-site testing without relying on shell redirection encoding.
- `normalize_cli` and `sync-export` now support `--output-md-dir` so multi-document Markdown export can be written as one file per document instead of one concatenated file.
- `scripts/platform_cli.py search`, `citation`, and `retrieval-consume` now support snapshot reuse directly, and `scripts/retrieval/toolkit_cli.py` search/citation now support snapshot-backed page index reuse.
- `services/analysis/jira_profiles.py` now holds Jira report and Jira-spec extractive profile logic so `jira_issue_analysis.py` stays closer to orchestration than prompt implementation.
- `services/connectors/jira/connector.py` now builds canonical sections and content blocks directly from Jira payload fields instead of deriving them from Markdown re-parsing.
- `services/connectors/confluence/connector.py` now builds canonical sections and content blocks directly from Confluence storage payloads instead of deriving them from Markdown re-parsing.
- `services/analysis/jira_issue_analysis.py` builds deterministic Jira reports and Jira-plus-spec question payloads; `services/analysis/llm_backends.py` adds explicit opt-in local LLM answer generation.
- `services/ingest/visual_assets.py` renders image evidence blocks for Markdown ingestion and indexing. It currently consumes image references plus provided `ocr_text`, `vision_caption`, and `alt_text` metadata; automatic download/OCR/vision extraction remains a production gap.
- `services/ingest/markdown_export.py` turns canonical documents into readable Markdown when a source does not already provide Markdown, and `scripts/ingest/normalize_cli.py --output-page-index` writes the PageIndex derived from the same normalized documents.
- `scripts/platform_cli.py jira-report` and `scripts/platform_cli.py jira-spec-qa` expose the Jira analysis workflow through the unified CLI for fixture-backed and live Jira Server sources.
- `scripts/platform_cli.py jira-report --output-md ...` writes the generated Jira report Markdown to disk while preserving JSON output.
- `scripts/platform_cli.py jira-spec-qa --output-answer-md ...` writes the generated extractive or local-LLM QA answer to disk while preserving JSON output.
- `docs/modules/jira-analysis-reporting.md` defines the Jira report and Jira-plus-spec QA module contract and is enforced by `scripts/gates/check_module_contracts.py`.
- `scripts/platform_cli.py jira-report` supports `--updated-from-iso/--updated-to-iso`, `--updated-on-date`, and `--updated-at-iso`.
- `scripts/platform_cli.py jira-batch-spec-report` runs Jira-plus-spec QA for each issue selected by the Jira time filter.
- `scripts/platform_cli.py jira-report`, `jira-spec-qa`, and `jira-batch-spec-report` support `--llm-backend none|mock|ollama|openai-compatible`, defaulting to `none`.
- `scripts/platform_cli.py jira-report`, `jira-spec-qa`, and `jira-batch-spec-report` support `--llm-prompt-mode strict|balanced|exploratory`, defaulting to `strict`.
- `jira-batch-spec-report` now forwards `--prompt-template` into each per-issue QA payload instead of treating it as a report-summary template.
- `tests/ops/test_platform_cli_live_orchestration.py` validates the live dual-source orchestration path without introducing network dependencies.
- `agent.md` now defines a bounded self-loop entry rule for `continue` and `继续`, with explicit stop conditions and per-iteration validation expectations.

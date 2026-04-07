# Implementation Status

## Summary

The repository currently covers the full planned Task 1 to Task 15 skeleton for Phase 1 with a minimal runnable implementation.

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

- Replace minimal offline PDF parsing with the target production parser stack.
- Upgrade the portal from static assets to a hosted internal service.
- Add persistent storage and real indexing backends.
- Add real authentication and request-scoped ACL identity handling.

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
- gated Jira analysis/reporting module contract
- profile-backed source manifests for multi-source ops runs
- ops profile schema contract and runtime validation
- eval harness
- rollout gate runner

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
- `services/analysis/jira_issue_analysis.py` builds deterministic Jira reports and Jira-plus-spec question payloads; `services/analysis/llm_backends.py` adds explicit opt-in local LLM answer generation.
- `scripts/platform_cli.py jira-report` and `scripts/platform_cli.py jira-spec-qa` expose the Jira analysis workflow through the unified CLI for fixture-backed and live Jira Server sources.
- `scripts/platform_cli.py jira-report --output-md ...` writes the generated Jira report Markdown to disk while preserving JSON output.
- `scripts/platform_cli.py jira-spec-qa --output-answer-md ...` writes the generated extractive or local-LLM QA answer to disk while preserving JSON output.
- `docs/modules/jira-analysis-reporting.md` defines the Jira report and Jira-plus-spec QA module contract and is enforced by `scripts/gates/check_module_contracts.py`.
- `scripts/platform_cli.py jira-report` supports `--updated-from-iso/--updated-to-iso`, `--updated-on-date`, and `--updated-at-iso`.
- `scripts/platform_cli.py jira-batch-spec-report` runs Jira-plus-spec QA for each issue selected by the Jira time filter.
- `scripts/platform_cli.py jira-report`, `jira-spec-qa`, and `jira-batch-spec-report` support `--llm-backend none|mock|ollama|openai-compatible`, defaulting to `none`.
- `scripts/platform_cli.py jira-report`, `jira-spec-qa`, and `jira-batch-spec-report` support `--llm-prompt-mode strict|balanced|exploratory`, defaulting to `strict`.
- `tests/ops/test_platform_cli_live_orchestration.py` validates the live dual-source orchestration path without introducing network dependencies.
- `agent.md` now defines a bounded self-loop entry rule for `continue` and `继续`, with explicit stop conditions and per-iteration validation expectations.

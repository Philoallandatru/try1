# Jira Issue Type Routing And Sync Export Plan

## Summary

Improve the Jira/Confluence pipeline by separating source synchronization from issue-specific analysis.

The next implementation should add a single sync/export command that pulls Jira and Confluence increments, normalizes them into canonical documents, exports loose Markdown and PageIndex artifacts, and persists source cursors in the snapshot manifest. Analysis commands should consume the normalized documents later and route Jira issues by deterministic Jira `issuetype`.

## Routing Model

Use a two-level Jira routing model:

- `metadata.issue_type_raw`: the original Jira issue type, for example `FW Bug` or `DAS/PRD`.
- `metadata.issue_family`: a stable coarse family used by downstream commands.
- `metadata.issue_route`: a more specific default analysis route.

Default mapping:

| Jira issue type | issue_family | issue_route |
| --- | --- | --- |
| `FW Bug` | `defect` | `fw_bug_rca` |
| `HW Bug` | `defect` | `hw_bug_rca` |
| `Test Bug` | `defect` | `test_bug_rca` |
| `Misc Bug` | `defect` | `misc_bug_rca` |
| `DAS/PRD` | `requirement` | `prd_review` |
| `MRD` | `requirement` | `mrd_review` |
| `Requirement Change` | `requirement_change` | `requirement_change_impact` |
| `Component Change` | `change_control` | `component_change_impact` |
| `Epic` | `delivery` | `delivery_summary` |
| `Story` | `delivery` | `story_summary` |
| `Task` | `delivery` | `task_summary` |
| `Release` | `release` | `release_summary` |
| unknown/unmapped | `unknown` | `generic_jira_summary` |

This mapping should live in a JSON config, for example `packages/schema/jira-issue-type-profiles.json`, so Jira workflow changes do not require code edits.

## Key Implementation Changes

- Update the Jira connector to read `fields.issuetype.name` first and then fixture top-level `type`.
- Store `issue_type_raw`, `issue_family`, and `issue_route` under each Jira document's `metadata`.
- Keep Jira Markdown rendering loose: title, basic metadata, issue fields, description, comments, and attachments should render when present; bug-only sections like `Root Cause`, `How to fix`, and `Action` should remain optional.
- Keep daily Jira reports broad: include every issue family, grouped or tagged by family, without forcing bug fields onto PRD/MRD issues.
- Add future analysis routing rules:
  - RCA commands consume `issue_family == "defect"`.
  - PRD/MRD review commands consume `issue_family == "requirement"`.
  - Change-impact commands consume `issue_family in {"requirement_change", "change_control"}`.
  - Delivery and release summaries remain separate from RCA and requirement review.
- Add a unified `sync-export` CLI command in `scripts/platform_cli.py`.
  - Inputs: existing Jira/Confluence live and fixture flags, `--profile`, `--snapshot-dir`, `--output-md`, `--output-page-index`, and `--export-scope incoming|snapshot`.
  - Behavior: load cursors from snapshot manifest by default, allow explicit cursor overrides, refresh the snapshot, then export readable Markdown and PageIndex.
  - Default scope: export only incoming documents from the current sync.
- Keep cursor state in the existing snapshot manifest.
  - Jira cursor should remain based on max updated ISO timestamp.
  - Confluence cursor should use max page last-modified or ingested ISO timestamp, not the numeric page version.
  - Snapshot refresh remains idempotent by merging documents by stable `document_id`.

## Evidence From Current Code

- `services/connectors/jira/connector.py` currently renders Jira Markdown in `_issue_to_markdown` and adds dedicated bug-oriented `Root Cause`, `How To Fix`, and `Action` sections when those alias fields exist.
- `services/connectors/jira/connector.py` currently writes Jira connector metadata in `_issue_to_document`, but does not yet persist `issue_type_raw`, `issue_family`, or `issue_route`.
- `services/connectors/confluence/connector.py` currently computes live Confluence `next_cursor` from `document["version"]`, which is the page version number, while live incremental CQL filters by `lastmodified`.
- `services/retrieval/persistence/snapshot_store.py` already stores per-source `cursor` values in `manifest["sources"][source_name]` and refreshes documents idempotently by `document_id`.
- `scripts/platform_cli.py` already exposes separate `connector`, `sync-health`, `multi-sync-health`, and Jira report commands, but has no combined sync/export command.

## Acceptance Criteria

- Jira documents produced from fixture and live-style payloads include `metadata.issue_type_raw`, `metadata.issue_family`, and `metadata.issue_route`.
- All listed Jira issue types map exactly as defined in the routing table; unmapped types resolve to `unknown` and `generic_jira_summary`.
- `Story` stays in `delivery` even when its description looks requirement-like; only `DAS/PRD` and `MRD` default to `requirement`.
- Jira Markdown export remains readable for PRD/MRD, Release, Story, Task, and unknown issue types even when root-cause/fix/action fields are absent.
- Daily Jira reports can include all issue families without forcing PRD/MRD or delivery issues into bug RCA output.
- Bug RCA logic can filter to `issue_family == "defect"` without string-matching raw Jira type names.
- PRD/MRD review logic can filter to `issue_family == "requirement"` without accidentally including `Story`.
- `sync-export` can run from fixture-backed inputs and produce Markdown plus PageIndex artifacts.
- `sync-export` can refresh a snapshot and use the persisted manifest cursor as the default for the next live sync unless a command-line cursor override is supplied.
- Live Confluence incremental sync stores an ISO last-modified cursor rather than a numeric page version cursor.

## Implementation Steps

1. Add issue type profile configuration.
   - Create `packages/schema/jira-issue-type-profiles.json` with the routing table above.
   - Add a small loader module near the Jira connector, analogous to the existing Jira field-alias loader.
   - Treat unknown or empty type values as `unknown`.

2. Update Jira normalization.
   - Resolve issue type from `fields.issuetype.name`, `fields.issuetype`, then top-level `type`.
   - Add routing metadata in `_issue_to_document`.
   - Keep the existing loose Markdown behavior, but ensure issue type/family/route are visible either in metadata or the general issue fields section.

3. Fix Confluence cursor semantics.
   - Preserve display `version` as the Confluence page version.
   - Add or reuse an ISO timestamp value from `version.when` / `provenance.ingested_at` for cursor calculation.
   - Change live `next_cursor` selection to use that ISO timestamp.

4. Add sync/export orchestration.
   - Add a small orchestration helper that reads existing source cursors from snapshot manifest, loads Jira/Confluence payloads, refreshes the snapshot, then selects `incoming` or merged `snapshot` documents for export.
   - Reuse existing Markdown export and PageIndex builders instead of inventing new rendering logic.
   - Expose the helper through `scripts/platform_cli.py sync-export`.

5. Keep analysis commands layered.
   - Do not make `sync-export` call an LLM.
   - Keep `jira-report` broad.
   - Add future specialty filters against `metadata.issue_family`, not raw `issuetype` strings.

## Test Plan

- Add connector tests for each issue family, especially PRD/MRD issues without root-cause fields.
- Add classification tests for all known Jira issue types listed in this plan.
- Add CLI tests for `sync-export` fixture mode and profile mode.
- Add cursor tests showing Jira and Confluence cursors persist correctly in `manifest.json`.
- Keep existing regressions green:
  - `python -m unittest tests.connectors.test_jira_sync tests.connectors.test_confluence_sync`
  - `python -m unittest tests.analysis.test_jira_issue_analysis`
  - `python -m unittest tests.ops.test_platform_cli`
  - `python -m unittest tests.retrieval.test_snapshot_store`

## Risks And Mitigations

- Risk: Jira admins rename issue types. Mitigation: keep routing in a JSON config and fallback to `unknown`.
- Risk: `Requirement Change` could be treated as normal PRD/MRD review. Mitigation: keep a separate `requirement_change` family with impact-analysis routing.
- Risk: `Story` descriptions may contain requirements. Mitigation: keep `Story` in `delivery` by default and require explicit Jira type changes or config overrides to include it in requirement review.
- Risk: Confluence numeric version cursors break live incremental sync. Mitigation: use ISO last-modified cursor for live sync while preserving page version as document version.
- Risk: `sync-export` becomes an all-purpose analysis command. Mitigation: restrict it to sync, snapshot refresh, Markdown export, and PageIndex export only.

## Assumptions

- "Download mutations" means incremental source download from Jira and Confluence.
- Jira issue routing should be deterministic and based on `issuetype`, not LLM classification.
- `sync-export` should not call an LLM or run specialty analysis by default.
- The canonical document and PageIndex contracts should remain stable.

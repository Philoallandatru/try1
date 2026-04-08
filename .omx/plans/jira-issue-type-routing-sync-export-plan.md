# Jira Issue Type Routing And Sync Export Work Plan

## Requirements Summary

Implement deterministic Jira issue routing by `issuetype` and add a single sync/export path for Jira and Confluence. The sync/export path should synchronize source increments, refresh the local snapshot, and export readable Markdown plus PageIndex artifacts without running specialty analysis or LLM calls.

## Acceptance Criteria

- Jira documents include `metadata.issue_type_raw`, `metadata.issue_family`, and `metadata.issue_route`.
- `FW Bug`, `HW Bug`, `Test Bug`, and `Misc Bug` map to `defect`.
- `DAS/PRD` and `MRD` map to `requirement`.
- `Requirement Change` maps to `requirement_change`.
- `Component Change` maps to `change_control`.
- `Epic`, `Story`, and `Task` map to `delivery`; `Story` does not enter PRD/MRD analysis by default.
- `Release` maps to `release`.
- Unknown issue types map to `unknown` and `generic_jira_summary`.
- Jira Markdown remains loose and renders non-bug issues without requiring root-cause/fix/action fields.
- Live Confluence incremental sync stores an ISO last-modified cursor, not a page-version number.
- `sync-export` can export incoming documents or the merged snapshot as Markdown and PageIndex JSON.

## Implementation Steps

1. Add `packages/schema/jira-issue-type-profiles.json` and a loader for issue type routing.
2. Update `services/connectors/jira/connector.py` to resolve raw Jira issue type and persist routing metadata.
3. Add Jira fixture coverage for PRD/MRD, Story, Release, Requirement Change, Component Change, and unknown issue types.
4. Update `services/connectors/confluence/connector.py` live cursor calculation to use ISO last-modified / ingested timestamp.
5. Add a sync/export orchestration helper that reuses `load_source_payload`, snapshot refresh, Markdown export, and PageIndex builders.
6. Expose `sync-export` in `scripts/platform_cli.py` with fixture/live/profile support, snapshot cursor defaults, explicit cursor overrides, and `--export-scope incoming|snapshot`.
7. Keep existing Jira report and Jira-plus-spec commands separate; add family filtering only to downstream specialty analysis when those commands are implemented.

## Risks And Mitigations

- Jira issue type names may change. Keep mappings configurable and fallback to `unknown`.
- `Story` may sometimes contain requirement detail. Keep it in `delivery` by default and require an explicit config override for requirement analysis.
- Confluence cursor changes can affect live sync. Preserve fixture behavior and test live-style cursor logic separately.
- `sync-export` can grow too broad. Keep it limited to sync, snapshot refresh, Markdown export, and PageIndex export.

## Verification Steps

- Run `python -m unittest tests.connectors.test_jira_sync tests.connectors.test_confluence_sync`.
- Run `python -m unittest tests.analysis.test_jira_issue_analysis`.
- Run `python -m unittest tests.ops.test_platform_cli`.
- Run `python -m unittest tests.retrieval.test_snapshot_store`.
- Run `python -m compileall docs scripts services tests`.

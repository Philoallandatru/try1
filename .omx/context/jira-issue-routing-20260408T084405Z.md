# Deep Interview Context: Jira Issue Routing

## Task Statement

Review the new requirement for improving the Jira/Confluence pipeline: Jira issues have multiple `issuetype` values and should not all be analyzed as bug/root-cause work.

## Desired Outcome

Confirm whether the documented plan is precise enough for implementation and identify high-impact ambiguity before coding starts.

## Stated Solution

- Add deterministic Jira issue routing by `issuetype`.
- Keep daily Jira reports broad across all issue types.
- Add a single sync/export command for Jira/Confluence incremental download, Markdown export, PageIndex export, and snapshot cursor persistence.
- Keep bug RCA, PRD/MRD review, change-impact review, delivery summary, and release summary as separate downstream analysis routes.

## Probable Intent Hypothesis

The pipeline should become flexible enough for heterogeneous Jira data while preserving auditable, reproducible behavior for later agent workflows such as Codex CLI / oh-my-codex execution.

## Known Facts And Evidence

- Current Jira connector already normalizes Jira issues and renders Markdown.
- Current Jira analysis prompt assumes bug-like fields such as root cause, fix, and evidence gap.
- Current snapshot store persists source cursors in `manifest.json`.
- Current plan is documented in `docs/jira-issue-type-routing-plan.md`.
- `agent.md` now documents deterministic Jira issue type routing.

## Constraints

- Do not change canonical document, citation, or PageIndex contracts casually.
- Do not use LLM classification for issue routing by default.
- Keep Jira/Confluence write-back out of scope.
- Keep sync/export separate from specialty analysis.

## Unknowns / Open Questions

- Whether `Story` should be treated as delivery work or as a requirement-like item when it contains PRD/MRD detail.
- Whether `Requirement Change` should have its own route or be merged into requirement review with an impact-analysis flag.
- Whether downstream output should group daily reports by `issue_family` or merely annotate each issue.

## Decision-Boundary Unknowns

- Which issue families the implementation may add without asking again.
- Whether adding a config schema for `jira-issue-type-profiles.json` is mandatory in the first implementation increment.
- Whether `sync-export` should support both incoming-only and snapshot-wide exports in the first implementation increment.

## Likely Codebase Touchpoints

- `services/connectors/jira/connector.py`
- `services/connectors/confluence/connector.py`
- `services/retrieval/persistence/snapshot_store.py`
- `scripts/platform_cli.py`
- `packages/schema/`
- `tests/connectors/`
- `tests/ops/test_platform_cli.py`
- `docs/jira-issue-type-routing-plan.md`
- `agent.md`

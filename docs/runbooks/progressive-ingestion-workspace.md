# Progressive Ingestion Workspace

## Purpose

This runbook describes the staged operator workflow for testing Jira and Confluence ingestion through a fixed workspace instead of ad hoc `.tmp/*` command chains.

For a from-zero setup guide and full source spec field reference, see [../workspace-cli-guide.md](../workspace-cli-guide.md).

The workspace is a workflow layer only:

- canonical document remains the source of truth
- snapshot files remain the stable runtime state
- PageIndex remains the retrieval projection
- workspace exports and wiki files remain derived outputs

## Initialize a Workspace

```powershell
python scripts/workspace_cli.py init .tmp\workspace
```

This creates:

- `raw/` for saved source specs and fetched payloads
- `snapshots/current/` for canonical documents and `page_index.json`
- `exports/latest/` for Markdown and PageIndex exports
- `runs/` for per-run request/result records

## Jira Staged Validation

### 1. Start from one issue

Edit `raw/jira/specs/one-issue.json` or create a new spec with:

- `kind: jira`
- `mode: fixture` or `live`
- `scope.type: issue`
- `scope.issue_key`

Fetch and build:

```powershell
python scripts/workspace_cli.py fetch .tmp\workspace .tmp\workspace\raw\jira\specs\one-issue.json
python scripts/workspace_cli.py build .tmp\workspace
```

### 2. Expand to a project slice

Use a spec with:

- `scope.type: project_slice`
- `scope.project_key`
- optional `issue_type`, `status`, `label`, `updated_from`, `updated_to`

Fetch again, then rebuild:

```powershell
python scripts/workspace_cli.py fetch .tmp\workspace .tmp\workspace\raw\jira\specs\project-slice.json
python scripts/workspace_cli.py build .tmp\workspace
```

### 3. Expand to full project

Use `scope.type: project_full` and rebuild from the broader payload.

## Confluence Staged Validation

### 1. Start from one page

Use a spec with:

- `kind: confluence`
- `scope.type: page`
- `scope.page_id`

### 2. Expand to a page tree

Use a spec with:

- `scope.type: page_tree`
- `scope.root_page_id`
- optional `scope.max_depth`

The workspace fetch path passes subtree intent into the Confluence Atlassian fetch service through:

- `root_page_id`
- `include_descendants`
- `max_depth`

The same subtree flow is also available through the lower-level live CLI when you want to bypass workspace orchestration:

```powershell
python scripts/platform_cli.py connector confluence `
  --live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --fetch-backend atlassian-api `
  --root-page-id 123456 `
  --include-descendants `
  --max-depth 2
```

### 3. Expand to a space slice

Use a spec with:

- `scope.type: space_slice`
- `scope.space_key`
- optional `label`, `modified_from`, `modified_to`

## Inspect, Query, Export

Inspect the current state:

```powershell
python scripts/workspace_cli.py status .tmp\workspace
python scripts/workspace_cli.py lint .tmp\workspace
```

Run a retrieval query against the current snapshot:

```powershell
python scripts/workspace_cli.py query .tmp\workspace "black screen"
python scripts/workspace_cli.py query .tmp\workspace "black screen" --llm-backend openai-compatible --llm-model qwen-9b --llm-base-url http://127.0.0.1:1234/v1
```

Export the derived Markdown/PageIndex bundle:

```powershell
python scripts/workspace_cli.py export .tmp\workspace
```

Bootstrap or continuously watch the workspace:

```powershell
python scripts/workspace_cli.py watch .tmp\workspace --run-once
python scripts/workspace_cli.py watch .tmp\workspace --interval-seconds 2
```

## Notes

- `fetch` writes normalized sync payloads into `raw/*/payloads/`.
- `build` rebuilds `snapshots/current/` from the current saved payload set.
- `export` does not mutate canonical documents; it only derives Markdown and PageIndex outputs.
- `runs/` keeps append-only request/result records for each workspace action.

# Workspace CLI Guide

## Purpose

This guide explains how to set up and use the workspace-first operator flow from zero.

Use this guide when you want:

- a fixed working directory for staged Jira and Confluence validation
- repeatable source registry entries instead of long ad hoc command lines
- a single source registry flow for `source -> selector -> profile -> analyze-jira`

The workspace is an orchestration layer only:

- canonical documents remain the source of truth
- snapshots remain the stable runtime state
- PageIndex remains the retrieval projection
- workspace exports and wiki outputs remain derived artifacts
- `wiki/topics.json`, `wiki/routes.json`, and `wiki/compilation-manifest.json` are operator-facing control-plane artifacts for curated wiki routing

## 1. Environment Setup From Zero

Create the local Python environment:

```powershell
python -m pip install --upgrade uv
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -e .
uv pip install -e ".[dev]"
```

If you do not use `uv`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Set live-source credentials only when needed:

```powershell
$env:JIRA_TOKEN = "<jira-token>"
$env:CONF_TOKEN = "<confluence-token>"
```

## 2. Initialize a Workspace

Create a new workspace:

```powershell
python scripts/workspace_cli.py init .tmp\workspace
```

This creates:

```text
.tmp/workspace/
  workspace.yaml
  sources/
  selectors/
  profiles/
  .local/
    credentials.example.yaml
  raw/
    jira/specs/
    jira/payloads/
    confluence/specs/
    confluence/payloads/
    files/
  snapshots/current/
  exports/latest/
  runs/
  wiki/
    topics.json
    routes.json
    compilation-manifest.json
    compiled/
    summaries/
    reports/
```

### `workspace.yaml`

The workspace config is lightweight. Current fields:

- `workspace_version`
- `created_at`
- `default_policies`
- `paths.snapshot_dir`
- `paths.export_dir`
- `paths.runs_dir`

In the current implementation this file is mostly metadata and defaults. Source-specific behavior is driven by the source registry. Existing workspaces with the older `config.json` file remain readable for compatibility, but new workspaces use `workspace.yaml`.

## 3. Source Registry Workflow

The source registry is the preferred persistent configuration surface for repeated workspace runs.

The official repeated operator path is:

1. `source add`
2. `selector add`
3. `profile add`
4. `analyze-jira`

Create a named Jira source:

```powershell
python scripts/workspace_cli.py source add .tmp\workspace jira_lab --connector-type jira.atlassian_api --base-url https://jira.example.com --credential-ref jira_lab_token --policy team:ssd --policy public
```

Create a fixture-backed Jira source for local validation:

```powershell
python scripts/workspace_cli.py source add .tmp\workspace jira_fixture --connector-type jira.atlassian_api --mode fixture --path fixtures/connectors/jira/incremental_sync.json --policy team:ssd
```

Create a local PDF source:

```powershell
python scripts/workspace_cli.py source add .tmp\workspace nvme_pdf --connector-type pdf.local_file --path fixtures/corpus/pdf/sample.pdf
python scripts/workspace_cli.py selector add .tmp\workspace nvme_pdf_file --source nvme_pdf --type file
python scripts/workspace_cli.py fetch-source .tmp\workspace --source nvme_pdf --selector-profile nvme_pdf_file
```

Create a selector profile:

```powershell
python scripts/workspace_cli.py selector add .tmp\workspace jira_one_issue --source jira_lab --type issue --issue-key SSD-777
```

Common bounded selector examples:

```powershell
python scripts/workspace_cli.py selector add .tmp\workspace jira_slice --source jira_lab --type project_slice --project-keys SSD,FIRMWARE --issue-type Bug --status "In Progress" --label nvme --updated-from 2026-04-01T00:00:00Z --updated-to 2026-04-10T00:00:00Z
python scripts/workspace_cli.py selector add .tmp\workspace conf_slice --source conf_fw --type space_slice --space-key SSDENG --label firmware --modified-from 2026-04-01T00:00:00Z --modified-to 2026-04-10T00:00:00Z --ancestor-id 123456 --title NVMe --page-ids 123,124
```

Create a reusable analysis profile:

```powershell
python scripts/workspace_cli.py profile add .tmp\workspace ssd_default --input jira=jira_lab:jira_one_issue --top-k 5 --policy team:ssd --policy public --llm-backend none --llm-prompt-mode strict
python scripts/workspace_cli.py profile list .tmp\workspace
python scripts/workspace_cli.py profile show .tmp\workspace ssd_default
python scripts/workspace_cli.py profile validate .tmp\workspace ssd_default
```

Fetch and cache source payload:

```powershell
python scripts/workspace_cli.py fetch-source .tmp\workspace --source jira_lab --selector-profile jira_one_issue
```

Refresh stale cached sources:

```powershell
python scripts/workspace_cli.py refresh .tmp\workspace
python scripts/workspace_cli.py source refresh .tmp\workspace jira_lab --selector-profile jira_one_issue
```

For `pdf.local_file` sources, `fetch-source` now writes the same cache-layer artifacts as Jira and Confluence:

- `raw/pdf/payloads/<source>/latest.json`
- `raw/pdf/payloads/<source>/fetch-manifest.json`
- `build/normalize/<source>/manifest.json`
- `build/normalize/<source>/documents.json`

This keeps PDF sources visible in the same fetch/normalize/index status DAG.

Build the snapshot from cached payload:

```powershell
python scripts/workspace_cli.py build .tmp\workspace
```

Rebuild from cached raw payload or rebuild only the index:

```powershell
python scripts/workspace_cli.py rebuild .tmp\workspace --from raw --source jira_lab
python scripts/workspace_cli.py reindex .tmp\workspace --index-name pageindex_v1
```

Run analysis through the official profile-driven entrypoint:

```powershell
python scripts/workspace_cli.py analyze-jira .tmp\workspace --profile ssd_default --issue-key SSD-777
python scripts/workspace_cli.py analyze-jira .tmp\workspace --profile ssd_default --issue-key SSD-777 --use-existing-snapshot
```

When `--use-existing-snapshot` is omitted, `analyze-jira` reads the profile inputs, fetches stale sources, builds a profile-scoped snapshot, and then runs the existing deep-analysis seam. When `--use-existing-snapshot` is supplied, the CLI reuses the matching profile-scoped snapshot instead of the shared workspace snapshot. `run-analysis` remains available as a compatibility alias.

Registry files are YAML:

```text
workspace/
  sources/jira_lab.yaml
  selectors/jira_one_issue.yaml
  profiles/ssd_deep_analysis_default.yaml
  .local/credentials.yaml
```

Credential values should stay in environment variables:

```yaml
version: 1
credentials:
  jira_lab_token:
    type: bearer_env
    env: JIRA_TOKEN
  jira_lab_pat:
    type: bearer_inline
    value: "<token>"
```

Source maintenance commands:

```powershell
python scripts/workspace_cli.py source configure .tmp\workspace jira_lab --base-url https://jira.example.com --auth-mode auto
python scripts/workspace_cli.py source set-credential .tmp\workspace jira_lab --credential-ref jira_lab_token
python scripts/workspace_cli.py source defaults .tmp\workspace jira_lab --include-comments --include-attachments --refresh-freq-minutes 30
python scripts/workspace_cli.py source test .tmp\workspace jira_lab --selector-profile jira_one_issue
python scripts/workspace_cli.py source disable .tmp\workspace jira_lab
python scripts/workspace_cli.py source enable .tmp\workspace jira_lab
```

The `status` command reports the cache DAG:

```text
cache.fetch      source config/selector/refresh freshness
cache.normalize  raw-payload-to-documents freshness
cache.index      normalized-documents-to-PageIndex freshness
cache.analysis   snapshot-to-analysis freshness for profile runs
```

### Compatibility Only

The legacy JSON spec flow remains available:

```powershell
python scripts/workspace_cli.py fetch <workspace> <spec>
```

It is still useful for compatibility and migration, but it is not the recommended repeated operator path.

## 4. Minimal Portal Entry

The static portal workbench now exposes a minimal analyze form in the `New Task` panel:

- `Issue Key`
- `Analysis Profile`
- `Run`

The panel renders the recommended `analyze-jira` command preview from the current workspace state and selected profile. The task detail and artifact panels still reuse the existing workbench/result contract.

## 4. Legacy Source Spec Files

Legacy `fetch <workspace> <spec>` operations are driven by JSON spec files. This mode is retained for compatibility and migration only. New operator workflows should use `source`, `selector`, `profile`, and `analyze-jira`.

### Common fields

Required or commonly used top-level fields:

- `kind`
  - `jira` or `confluence`
- `mode`
  - `fixture` or `live`
- `path`
  - required for `fixture`
- `base_url`
  - required for `live`
- `token`, `username`, `password`, `auth_mode`
  - optional live auth fields
- `scope`
  - the bounded selection to fetch
- `fetch`
  - fetch backend and optional fetch behavior flags

### Jira scope types

Supported `scope.type` values:

- `issue`
- `project_slice`
- `project_full`

#### Jira issue example

```json
{
  "kind": "jira",
  "mode": "live",
  "base_url": "https://jira.example.com",
  "token": "env-or-inline-token",
  "scope": {
    "type": "issue",
    "issue_key": "SSD-777"
  },
  "fetch": {
    "fetch_backend": "atlassian-api",
    "include_comments": true,
    "include_attachments": true,
    "include_image_metadata": true,
    "download_images": false
  }
}
```

#### Jira project slice example

```json
{
  "kind": "jira",
  "mode": "live",
  "base_url": "https://jira.example.com",
  "token": "env-or-inline-token",
  "scope": {
    "type": "project_slice",
    "project_key": "SSD",
    "issue_type": "Bug",
    "status": "In Progress",
    "label": "firmware",
    "updated_from": "2026-04-01T00:00:00Z",
    "updated_to": "2026-04-10T00:00:00Z"
  },
  "fetch": {
    "fetch_backend": "atlassian-api"
  }
}
```

### Confluence scope types

Supported `scope.type` values:

- `page`
- `page_tree`
- `space_slice`

#### Confluence single page example

```json
{
  "kind": "confluence",
  "mode": "live",
  "base_url": "https://confluence.example.com",
  "token": "env-or-inline-token",
  "scope": {
    "type": "page",
    "page_id": "123456"
  },
  "fetch": {
    "fetch_backend": "atlassian-api"
  }
}
```

#### Confluence page tree example

```json
{
  "kind": "confluence",
  "mode": "live",
  "base_url": "https://confluence.example.com",
  "token": "env-or-inline-token",
  "scope": {
    "type": "page_tree",
    "root_page_id": "123456",
    "max_depth": 2
  },
  "fetch": {
    "fetch_backend": "atlassian-api"
  }
}
```

#### Confluence space slice example

```json
{
  "kind": "confluence",
  "mode": "live",
  "base_url": "https://confluence.example.com",
  "token": "env-or-inline-token",
  "scope": {
    "type": "space_slice",
    "space_key": "SSDENG",
    "label": "firmware",
    "modified_from": "2026-04-01T00:00:00Z",
    "modified_to": "2026-04-10T00:00:00Z"
  },
  "fetch": {
    "fetch_backend": "atlassian-api"
  }
}
```

## 5. Workspace CLI Commands and Parameters

### `init`

```powershell
python scripts/workspace_cli.py init <workspace>
```

Parameters:

- `<workspace>`
  - required
  - target workspace root directory

### `fetch` (legacy)

```powershell
python scripts/workspace_cli.py fetch <workspace> <spec>
```

Parameters:

- `<workspace>`
  - required
  - existing initialized workspace
- `<spec>`
  - required
  - either:
    - an absolute or relative path to a spec file
    - a short spec name resolvable from `raw/jira/specs/` or `raw/confluence/specs/`

Behavior:

- reads the spec
- validates the spec
- calls the existing connector flow
- writes the resulting normalized sync payload into `raw/*/payloads/`
- writes a run log into `runs/<timestamp>-<source>-fetch/`

### `build`

```powershell
python scripts/workspace_cli.py build <workspace>
```

Parameters:

- `<workspace>`
  - required

Behavior:

- loads all current payload files from the workspace
- merges documents by `document_id`
- rebuilds `snapshots/current/manifest.json`
- rebuilds `snapshots/current/documents.json`
- rebuilds `snapshots/current/page_index.json`

### `export`

```powershell
python scripts/workspace_cli.py export <workspace>
```

Behavior:

- exports bundle Markdown to `exports/latest/documents.md`
- exports per-document Markdown tree to `exports/latest/documents/`
- copies snapshot `page_index.json` to `exports/latest/page_index.json`
- writes export metadata to `exports/latest/manifest.json`

### `ingest-spec-asset`

```powershell
python scripts/workspace_cli.py ingest-spec-asset <workspace> --spec-pdf <pdf-path> [--asset-id <id>] [--display-name <name>] [--preferred-parser auto|mineru|pypdf] [--mineru-python-exe <python>]
```

Behavior:

- ingests one PDF spec as a reusable workspace asset
- writes versioned outputs under `raw/files/spec_assets/<asset-id>/<version>/`
- writes:
  - `spec-doc.json`
  - `spec-corpus.json`
  - `page_index.json`
  - `document.md`
  - `metadata.json`
- updates `raw/files/spec_assets/registry.json`
- increments version on repeat ingestion for the same asset id

### `query`

```powershell
python scripts/workspace_cli.py query <workspace> "<question>" [--top-k N] [--policies ...] [--llm-backend ...]
```

Parameters:

- `<workspace>`
  - required
- `<question>`
  - required
- `--top-k`
  - optional
  - default: `5`
- `--policies`
  - optional
  - default: `team:ssd public`
- `--prompt-template`
  - optional
  - custom prompt template using the same evidence-driven flow
- `--output-answer-md`
  - optional
  - writes the selected answer text to a Markdown file
- `--llm-backend`
  - optional
  - `none`, `mock`, `openai-compatible`
- `--llm-model`
  - required when backend is `openai-compatible`
- `--llm-base-url`
  - required when backend is `openai-compatible`
- `--llm-api-key`
  - optional for `openai-compatible`
- `--llm-timeout-seconds`
  - optional
  - default: `120`
- `--llm-mock-response`
  - optional
  - mock return text when backend is `mock`
- `--llm-prompt-mode`
  - optional
  - `strict`, `balanced`, `exploratory`
  - default: `strict`

Behavior:

- reads `snapshots/current/page_index.json`
- performs PageIndex-first retrieval
- returns results, citation payload, generated AI prompt, and answer
- uses extractive fallback when `--llm-backend` is not set

Examples:

```powershell
python scripts/workspace_cli.py query .tmp\workspace "black screen"
python scripts/workspace_cli.py query .tmp\workspace "black screen" --llm-backend mock --llm-mock-response "Mock workspace answer"
python scripts/workspace_cli.py query .tmp\workspace "black screen" --llm-backend openai-compatible --llm-model qwen-9b --llm-base-url http://127.0.0.1:1234/v1
python scripts/workspace_cli.py query .tmp\workspace "black screen" --output-answer-md .tmp\workspace-answer.md
```

### `deep-analyze`

```powershell
python scripts/workspace_cli.py deep-analyze <workspace> <issue-key> [--top-k N] [--policies ...] [--llm-backend ...]
```

Parameters:

- `<workspace>`
  - required
- `<issue-key>`
  - required
- `--top-k`
  - optional
  - default: `5`
- `--policies`
  - optional
  - default: `team:ssd public`
- `--output-answer-md`
  - optional
  - writes the selected answer text to a Markdown file
- `--llm-backend`
  - optional
  - `none`, `mock`, `openai-compatible`
- `--llm-prompt-mode`
  - optional
  - `strict`, `balanced`, `exploratory`
  - default: `strict`

Behavior:

- reads `snapshots/current/documents.json`
- locates one Jira issue by `document_id`
- runs cross-source deep analysis against workspace Confluence and spec documents
- writes `result.json` and `run_manifest.json` under `runs/<timestamp>-workspace-deep-analyze/`
- returns the analysis payload and optional answer Markdown output path

Examples:

```powershell
python scripts/workspace_cli.py deep-analyze .tmp\workspace SSD-102
python scripts/workspace_cli.py deep-analyze .tmp\workspace SSD-102 --llm-backend mock --llm-mock-response "Mock deep analysis"
python scripts/workspace_cli.py deep-analyze .tmp\workspace SSD-102 --output-answer-md .tmp\deep-analysis-answer.md
```

### `smoke-deep-analysis`

```powershell
python scripts/workspace_cli.py smoke-deep-analysis <workspace> --jira-spec <spec> --confluence-spec <spec> --issue-key <issue-key> [--spec-pdf <pdf-path>] [--portal-state-output <path>]
```

Behavior:

- initializes the workspace if needed
- fetches one Jira spec and one Confluence spec
- optionally ingests one PDF as a reusable spec asset
- builds the workspace snapshot
- runs `deep-analyze`
- writes a portal state JSON from real workspace run artifacts

This command is intended for real Jira / Confluence / PDF smoke testing. Use live source specs for Jira and Confluence, and pass the local PDF path with `--spec-pdf`.

Example with fixture sources:

```powershell
python scripts/workspace_cli.py smoke-deep-analysis .tmp\workspace `
  --jira-spec project-slice `
  --confluence-spec page-tree `
  --issue-key SSD-102 `
  --spec-pdf fixtures/corpus/pdf/sample.pdf `
  --preferred-parser pypdf
```

Example shape for live testing:

```powershell
python scripts/workspace_cli.py init .tmp\real-workspace
# edit .tmp\real-workspace\raw\jira\specs\one-issue.json
# edit .tmp\real-workspace\raw\confluence\specs\page-tree.json
python scripts/workspace_cli.py smoke-deep-analysis .tmp\real-workspace `
  --jira-spec one-issue `
  --confluence-spec page-tree `
  --issue-key SSD-777 `
  --spec-pdf C:\path\to\spec.pdf `
  --preferred-parser pypdf `
  --portal-state-output .tmp\real-workspace\portal_state.json
```

### Optional Prefect runtime

Install the optional Prefect dependency only when you want real Prefect deployment/runtime support:

```powershell
uv pip install -e ".[prefect]"
```

The Prefect flow factory lives at:

```text
services.workspace.prefect_flows:build_jira_deep_analysis_flow
```

It creates a real Prefect flow named `jira_deep_analysis` when Prefect is installed. The flow calls the same workspace `deep_analyze_issue` path used by the CLI, so business artifacts remain file-backed and dict-first.

Submit an existing workspace run to a Prefect deployment:

```powershell
python scripts/workspace_cli.py submit-prefect-run .tmp\workspace <run-id> `
  --deployment-name jira_deep_analysis/analysis-prod `
  --timeout-seconds 0
```

Synchronize a Prefect state back into the workspace run manifest:

```powershell
python scripts/workspace_cli.py sync-prefect-state .tmp\workspace <run-id> `
  --prefect-state Completed `
  --flow-run-id <prefect-flow-run-id>
```

### `status`

```powershell
python scripts/workspace_cli.py status <workspace>
```

Behavior:

- reports:
  - spec counts
  - payload counts
  - current snapshot manifest
  - current export manifest
  - current wiki control-plane counts
  - latest run directory

### `inbox`

```powershell
python scripts/workspace_cli.py inbox <workspace>
```

Behavior:

- lists current Jira and Confluence candidate documents from the workspace snapshot
- shows whether each item is already routed into the curated wiki control plane
- shows topic assignment, route mode, and publish state when present

### `route`

```powershell
python scripts/workspace_cli.py route <workspace> --manifest <path>
```

Behavior:

- validates the operator route manifest against current snapshot documents
- writes:
  - `wiki/topics.json`
  - `wiki/routes.json`
  - `wiki/compilation-manifest.json`
- initializes routed items with publish state `unprocessed`

### `compile-wiki`

```powershell
python scripts/workspace_cli.py compile-wiki <workspace> [--llm-backend ...]
```

Behavior:

- reads the current topic registry, route manifest, and compilation manifest
- currently processes:
  - routed Confluence `summarize`
  - routed Jira `analyze`
- writes Confluence summary pages under `wiki/summaries/confluence/`
- writes Jira analysis pages under `wiki/compiled/analyses/jira/`
- writes compiled topic pages under `wiki/compiled/topics/`
- updates `wiki/compilation-manifest.json`
- includes Confluence summaries in topic pages
- includes Jira analysis in topic pages only when the route entry requests `promote: true`
- keeps non-promoted Jira items as analysis-only records

### `build-site`

```powershell
python scripts/workspace_cli.py build-site <workspace> --renderer vitepress
```

Behavior:

- reads the compiled topic-routed wiki artifacts
- emits a VitePress-ready site tree under `wiki/vitepress_site/`
- writes:
  - `wiki/vitepress_site/docs/index.md`
  - `wiki/vitepress_site/docs/topics/*.md`
  - `wiki/vitepress_site/docs/summaries/confluence/*.md`
  - `wiki/vitepress_site/docs/analyses/jira/*.md`
  - `wiki/vitepress_site/.vitepress/config.mts`
  - `wiki/vitepress_site/package.json`
  - `wiki/vitepress_site/README.md`
- does not run VitePress itself; it prepares renderer-ready content only
- after generation, the local preview path is:

```powershell
Set-Location .tmp\workspace\wiki\vitepress_site
npm install
npm run docs:dev
```

### `publish-wiki`

```powershell
python scripts/workspace_cli.py publish-wiki <workspace> --manifest <path> --renderer vitepress [--verify-site-build] [--llm-backend ...]
```

Behavior:

- runs the curated wiki flow as one operator command:
  - `route`
  - `compile-wiki`
  - `build-site`
- writes or refreshes the compilation report under `wiki/reports/compilation-report.json`
- when `--verify-site-build` is set, also runs the site build command and writes `wiki/reports/vitepress-build-report.json`
- records:
  - empty topics
  - unpromoted Jira document IDs
  - topic/summary/analysis counts

### `lint`

```powershell
python scripts/workspace_cli.py lint <workspace>
```

Behavior:

- validates all workspace spec files
- warns if payloads exist but no snapshot was built
- warns if snapshot is newer than export output
- checks presence of required snapshot files

### `watch`

```powershell
python scripts/workspace_cli.py watch <workspace> [--interval-seconds S] [--max-cycles N] [--run-once]
```

Parameters:

- `--interval-seconds`
  - optional
  - default: `2.0`
  - polling interval
- `--max-cycles`
  - optional
  - stop after N polling cycles
- `--run-once`
  - optional
  - fetch all current specs once, then run one build and exit

Current implementation note:

- `watch` is a polling implementation over workspace JSON spec/payload files
- it does not yet use filesystem events
- it does not watch `raw/files/`

## 6. End-to-End Flows

### Demo from zero

Use the workspace CLI when the goal is to stage source inputs and inspect snapshot/query behavior:

```powershell
python scripts/workspace_cli.py init .tmp\workspace
python scripts/workspace_cli.py source add .tmp\workspace jira_fixture --connector-type jira.atlassian_api --mode fixture --path fixtures/connectors/jira/incremental_sync.json --policy team:ssd
python scripts/workspace_cli.py selector add .tmp\workspace jira_one_issue --source jira_fixture --type issue --issue-key SSD-102
python scripts/workspace_cli.py source add .tmp\workspace conf_fixture --connector-type confluence.atlassian_api --mode fixture --path fixtures/connectors/confluence/page_sync.json --policy team:ssd
python scripts/workspace_cli.py selector add .tmp\workspace conf_one_page --source conf_fixture --type page --page-id CONF-201
python scripts/workspace_cli.py profile add .tmp\workspace ssd_default --input jira=jira_fixture:jira_one_issue --input confluence=conf_fixture:conf_one_page --top-k 5 --policy team:ssd --llm-backend none
python scripts/workspace_cli.py analyze-jira .tmp\workspace --profile ssd_default --issue-key SSD-102
python scripts/workspace_cli.py build .tmp\workspace
python scripts/workspace_cli.py query .tmp\workspace "black screen" --llm-backend mock --llm-mock-response "Mock workspace answer"
```

Use `platform_cli.py build-wiki-site` when the goal is a renderer-ready static site:

```powershell
python scripts/platform_cli.py build-wiki-site `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --confluence-path fixtures/connectors/confluence/page_sync.json `
  --snapshot-dir .tmp\wiki-demo\snapshot `
  --spec-pdf fixtures/corpus/pdf/sample.pdf `
  --preferred-parser pypdf `
  --reference-date 2026-04-05 `
  --output-dir .tmp\wiki-demo `
  --llm-backend mock `
  --llm-mock-response "Mock wiki answer"

Set-Location .tmp\wiki-demo\wiki_site
python -m mkdocs serve
```

Role split:

- `workspace_cli.py`
  - staged source preparation
  - payload capture
  - snapshot/query iteration
  - wiki routing control plane
  - Confluence summary compilation for curated wiki intake
  - Jira deep analysis before future topic promotion
  - topic page synthesis from curated Confluence and Jira inputs
  - VitePress-ready site assembly from compiled wiki artifacts
  - one-command wiki publish flow plus compilation reports
- `platform_cli.py build-wiki-site`
  - export package generation
  - MkDocs-compatible site assembly
  - renderer-ready demo output

### Jira from zero

1. Initialize workspace:

```powershell
python scripts/workspace_cli.py init .tmp\workspace
```

2. Add the Jira source and selector:

```powershell
python scripts/workspace_cli.py source add .tmp\workspace jira_lab --connector-type jira.atlassian_api --base-url https://jira.example.com --credential-ref jira_lab_token --policy team:ssd --policy public
python scripts/workspace_cli.py selector add .tmp\workspace jira_one_issue --source jira_lab --type issue --issue-key SSD-777
```

3. Add the analysis profile and run:

```powershell
python scripts/workspace_cli.py profile add .tmp\workspace ssd_default --input jira=jira_lab:jira_one_issue --top-k 5 --policy team:ssd --policy public --llm-backend none --llm-prompt-mode strict
python scripts/workspace_cli.py analyze-jira .tmp\workspace --profile ssd_default --issue-key SSD-777
```

4. Inspect:

```powershell
python scripts/workspace_cli.py status .tmp\workspace
```

5. Reuse the same profile for another Jira issue by creating or updating the selector, then running `analyze-jira` again.

### Confluence page tree from zero

1. Initialize workspace:

```powershell
python scripts/workspace_cli.py init .tmp\workspace
```

2. Add the Confluence source and selector:

```powershell
python scripts/workspace_cli.py source add .tmp\workspace conf_fw --connector-type confluence.atlassian_api --base-url https://confluence.example.com --credential-ref conf_fw_token --policy team:ssd --policy public
python scripts/workspace_cli.py selector add .tmp\workspace conf_tree --source conf_fw --type page_tree --root-page-id 123456 --max-depth 2
```

3. Add it to a Jira analysis profile:

```powershell
python scripts/workspace_cli.py profile add .tmp\workspace ssd_default --input jira=jira_lab:jira_one_issue --input confluence=conf_fw:conf_tree --top-k 5 --policy team:ssd --policy public --llm-backend none --llm-prompt-mode strict
```

4. Run Jira analysis with the selected Jira and Confluence sources:

```powershell
python scripts/workspace_cli.py analyze-jira .tmp\workspace --profile ssd_default --issue-key SSD-777
```

5. Export if needed:

```powershell
python scripts/workspace_cli.py export .tmp\workspace
```

## 7. Equivalent Lower-Level CLI Examples

### Confluence subtree via `platform_cli.py connector`

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

### Confluence subtree via `multi-sync-health`

```powershell
python scripts/platform_cli.py multi-sync-health `
  --snapshot-dir .tmp\snapshot `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --confluence-live `
  --confluence-base-url https://confluence.example.com `
  --confluence-token $env:CONF_TOKEN `
  --confluence-fetch-backend atlassian-api `
  --confluence-root-page-id 123456 `
  --confluence-include-descendants `
  --confluence-max-depth 2
```

### Confluence subtree via `sync-export`

```powershell
python scripts/platform_cli.py sync-export `
  --snapshot-dir .tmp\snapshot `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --confluence-live `
  --confluence-base-url https://confluence.example.com `
  --confluence-token $env:CONF_TOKEN `
  --confluence-fetch-backend atlassian-api `
  --confluence-root-page-id 123456 `
  --confluence-include-descendants `
  --confluence-max-depth 2 `
  --output-md-dir .tmp\export-docs
```

## 8. Current Boundaries

- Source registry files are YAML; legacy `fetch <workspace> <spec>` specs remain JSON for compatibility and are internally converted into source/selector registry entries before fetching.
- Confluence subtree fetch is currently bounded to the `atlassian-api` backend.
- `watch` is intentionally simple and optimized for operator workflows, not high-scale event processing.

## 9. Running the Wiki Site Locally

The generated wiki site is MkDocs-compatible. Install the site renderer in your local environment:

```powershell
python -m pip install mkdocs mkdocs-material
```

Build the site after `build-wiki-site` has generated `wiki_site/`:

```powershell
Set-Location .tmp\wiki-demo\wiki_site
python -m mkdocs build
```

Serve the site locally:

```powershell
Set-Location .tmp\wiki-demo\wiki_site
python -m mkdocs serve
```

Default local URL:

- `http://127.0.0.1:8000/`

The built static output will be under:

- `.tmp\wiki-demo\wiki_site\site\`

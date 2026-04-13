# SSD Knowledge Platform

Internal SSD knowledge platform for trusted retrieval and grounded Q&A over specifications, design documents, requirements, Jira issues, and Confluence pages.

This repository currently contains a Phase 1 foundation implementation for converting engineering sources into canonical documents, readable Markdown, PageIndex entries, and grounded retrieval/citation outputs.

- Contract and ADR layer
- Canonical schema and ACL contracts
- Markdown, Office, and PDF ingestion adapters
- Jira and Confluence fixture-backed and live connector paths
- Visual asset normalization for image references with provided OCR/caption metadata
- Markdown and PageIndex export from normalized documents
- PageIndex-first hybrid retrieval
- Citation assembly and source inspection
- Retrieval evaluation harness and rollout gate
- Internal ops portal MVP
- Skill-ready reusable component boundaries

## Core Terms

- `fixture`: a checked-in deterministic sample input or sample payload used for local development, contract validation, and repeatable tests. In this repo, fixture examples live mainly under `fixtures/` and stand in for live Jira, Confluence, Office, and PDF inputs.
- `canonical document`: the repository's source-of-truth normalized document shape. It is the durable internal representation that preserves provenance, ACL metadata, structure metadata, and content blocks before any Markdown export, PageIndex derivation, or local LLM consumption.
- `artifact`: a generated runtime or exchange output produced from canonical documents or from stable processing steps. In this repo, common artifacts include exported PageIndex JSON, snapshot files such as `manifest.json` / `documents.json` / `page_index.json`, evaluation outputs, and portal state outputs. Artifacts are derived outputs, not the source of truth unless a contract explicitly says they are the runtime input for a downstream step.

## Core Docs

- [agent.md](agent.md)
- [spec.md](spec.md)
- [todo.md](todo.md)
- [docs/architecture-overview.md](docs/architecture-overview.md)
- [docs/environment-setup.md](docs/environment-setup.md)
- [docs/platform-cli-guide.zh.md](docs/platform-cli-guide.zh.md)
- [docs/implementation-status.md](docs/implementation-status.md)
- [docs/cli-reference.md](docs/cli-reference.md)
- [docs/runbooks/progressive-ingestion-workspace.md](docs/runbooks/progressive-ingestion-workspace.md)
- [docs/runbooks/wiki-demo-validation.md](docs/runbooks/wiki-demo-validation.md)
- [docs/workspace-cli-guide.md](docs/workspace-cli-guide.md)

## Repository Shape

```text
apps/
services/
packages/
scripts/
fixtures/
tests/
docs/
ops/
eval/
```

## Packages And Dependencies

Runtime Python package discovery is explicit because this repository uses a flat layout with several non-package top-level directories. Editable installs package only:

- `apps*`
- `services*`

The top-level `packages/`, `scripts/`, `docs/`, `fixtures/`, `ops/`, `eval/`, `skills/`, and `tests/` directories are repository assets, not installable runtime packages.

Required runtime dependency:

- `pypdf>=4.0`: PDF fallback parsing.

Development dependency:

- `pytest>=8.0`: optional pytest runner. The canonical test command still uses `unittest`.

Optional local components:

- MinerU: richer PDF parsing when available; otherwise PDF parsing falls back to `pypdf`.
- Ollama: optional local LLM backend for Jira report/spec QA summaries.
- OpenAI-compatible local server: optional backend for LM Studio, vLLM, or llama.cpp server.

## Quick Start

Create a local Python environment with `uv`:

```powershell
python -m pip install --upgrade uv
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -e .
```

Or use the standard `venv` and `pip` workflow:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Convert supported sources to readable Markdown and PageIndex artifacts:

```powershell
python scripts/ingest/normalize_cli.py jira-sync fixtures/connectors/jira/full_sync.json --output-md .tmp/jira.md --output-page-index .tmp/jira-page-index.json
python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json --output-md .tmp/confluence.md --output-page-index .tmp/confluence-page-index.json
python scripts/ingest/normalize_cli.py pptx fixtures/corpus/office/sample.pptx --output-md .tmp/pptx.md --output-page-index .tmp/pptx-page-index.json
python scripts/ingest/normalize_cli.py pdf fixtures/corpus/pdf/sample.pdf --output-md .tmp/pdf.md --output-page-index .tmp/pdf-page-index.json
```

Run the full test suite:

```powershell
python -m unittest discover
```

Run retrieval evaluation and the Phase 1 rollout gate:

```powershell
python scripts/eval/run_recall_eval.py --dataset eval/gold_queries.yaml
python scripts/gates/run_phase1_gate.py
```

Use the unified CLI:

```powershell
python scripts/platform_cli.py gate
python scripts/platform_cli.py eval
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py citation "flush command"
```

Generate portal state for the static ops UI:

```powershell
python -c "from apps.portal.portal_state import write_portal_state; print(write_portal_state())"
```

## Workspace-First Operator Flow

For staged Jira and Confluence validation, use the workspace CLI instead of assembling long one-off commands by hand.

Initialize a workspace:

```powershell
python scripts/workspace_cli.py init .tmp\workspace
```

Fetch a saved source spec into the workspace:

```powershell
python scripts/workspace_cli.py fetch .tmp\workspace .tmp\workspace\raw\jira\specs\one-issue.json
python scripts/workspace_cli.py fetch .tmp\workspace .tmp\workspace\raw\confluence\specs\page-tree.json
```

Build the canonical snapshot from the fetched payloads:

```powershell
python scripts/workspace_cli.py build .tmp\workspace
```

Inspect status, query the snapshot, and export derived outputs:

```powershell
python scripts/workspace_cli.py status .tmp\workspace
python scripts/workspace_cli.py query .tmp\workspace "black screen"
python scripts/workspace_cli.py query .tmp\workspace "black screen" --llm-backend ollama --llm-model qwen2.5:7b
python scripts/workspace_cli.py export .tmp\workspace
python scripts/workspace_cli.py lint .tmp\workspace
python scripts/workspace_cli.py watch .tmp\workspace --run-once
```

The workspace keeps operator-oriented state under:

- `raw/` for reusable source specs and fetched payloads
- `snapshots/current/` for canonical documents plus `page_index.json`
- `exports/latest/` for Markdown and PageIndex exports
- `runs/` for per-run request/result records

This layer is workflow-oriented only. Canonical documents and snapshot/PageIndex contracts remain the source of truth.

## Decoupled Wiki Demo

The repository can now build a decoupled wiki demo in two layers:

- `export/`
  - stable document-level export package
- `wiki_site/`
  - MkDocs-compatible static site generated from the export package

Example:

```powershell
python scripts/platform_cli.py build-wiki-site `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --confluence-path fixtures/connectors/confluence/page_sync.json `
  --snapshot-dir .tmp\wiki-demo\snapshot `
  --spec-pdf fixtures/corpus/pdf/sample.pdf `
  --preferred-parser pypdf `
  --reference-date 2026-04-05 `
  --output-dir .tmp\wiki-demo
```

Quick render:

```powershell
Set-Location .tmp\wiki-demo\wiki_site
python -m mkdocs build
python -m mkdocs serve
```

For the full verification checklist, see [docs/runbooks/wiki-demo-validation.md](docs/runbooks/wiki-demo-validation.md).

## Pipelines

### 1. Source To Markdown And PageIndex

```text
Jira sync / Confluence sync / PPTX / PDF
        |
        v
source-specific parser or connector
        |
        v
canonical document
        |
        v
readable Markdown export
        |
        v
PageIndex JSON
```

Primary command:

```powershell
python scripts/ingest/normalize_cli.py <kind> <path> --output-md .tmp/source.md --output-page-index .tmp/source-page-index.json
```

Supported `kind` values:

- `jira-sync`
- `confluence-sync`
- `pptx`
- `pdf`
- `markdown`
- `docx`
- `xlsx`

### 2. Jira Connector Pipeline

```text
Jira fixture or live Jira API
        |
        v
field alias normalization
        |
        v
summary / description / bug fields / comments / attachments
        |
        v
canonical Jira Markdown
        |
        v
content_blocks + visual_assets
        |
        v
PageIndex
```

Live Jira uses `scripts/platform_cli.py connector jira --live ...`; fixture-backed conversion uses `scripts/ingest/normalize_cli.py jira-sync ...`.

Selective live Jira fetch is also available through the experimental Atlassian backend, for example:

```powershell
python scripts/platform_cli.py connector jira --live --base-url https://jira.example.com --token $env:JIRA_TOKEN --fetch-backend atlassian-api --issue-key SSD-777
```

### 3. Confluence Connector Pipeline

```text
Confluence fixture or live Confluence API
        |
        v
storage body + version + space + attachment metadata
        |
        v
HTML-to-Markdown normalization
        |
        v
inline/attachment image evidence blocks when metadata exists
        |
        v
canonical Confluence Markdown
        |
        v
PageIndex
```

Current Confluence image handling indexes provided `alt_text`, `ocr_text`, and `vision_caption` metadata. Automatic image download/OCR/vision captioning is still a future backend.

Selective live Confluence fetch is also available through the experimental Atlassian backend, for example:

```powershell
python scripts/platform_cli.py connector confluence --live --base-url https://confluence.example.com --token $env:CONF_TOKEN --fetch-backend atlassian-api --page-id 123456
```

### 4. PPTX Pipeline

```text
PPTX zip package
        |
        v
slide XML extraction
        |
        v
slide text blocks
        |
        v
slide number mapped to PageIndex page
        |
        v
Markdown sections: Slide 1, Slide 2, ...
        |
        v
PageIndex
```

PPTX slide images are not automatically OCRed yet. The current implementation indexes extracted slide text.

### 5. PDF Pipeline

```text
PDF
        |
        v
MinerU when available
        |
        v
pypdf fallback when MinerU is unavailable
        |
        v
page / section / table / figure / text blocks
        |
        v
MinerU image blocks become Markdown image evidence when metadata exists
        |
        v
PageIndex
```

The PDF fallback path is text-first. Production-grade OCR and local vision captioning are planned but not hidden behind the current parser.

### 6. Visual Asset Pipeline

```text
image reference or parser image block
        |
        v
visual asset metadata
        |
        v
Markdown image evidence block
        |
        v
content_blocks
        |
        v
PageIndex tokens
```

Supported visual metadata:

- `alt_text`
- `ocr_text`
- `vision_caption`

The system treats OCR and vision captions as derived evidence, not original source text.

### 7. Retrieval And Citation Pipeline

```text
canonical documents or exported PageIndex
        |
        v
PageIndex-first hybrid search
        |
        v
ACL filtering before ranking
        |
        v
top matching page entries
        |
        v
citation assembly
        |
        v
source inspection / evidence spans
```

Commands:

```powershell
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py citation "flush command"
```

### 8. Jira Analysis And Local LLM Pipeline

```text
Jira canonical documents
        |
        v
time filtering or issue selection
        |
        v
optional spec retrieval
        |
        v
citations + deterministic extractive answer
        |
        v
optional local LLM answer
```

LLM backends are opt-in:

- `none`: default deterministic behavior.
- `mock`: deterministic tests.
- `ollama`: local Ollama endpoint.
- `openai-compatible`: local LM Studio, vLLM, or llama.cpp server.

Prompt modes:

- `strict`: default, evidence-only reporting.
- `balanced`: allows cautious engineering inference.
- `exploratory`: labels hypotheses for investigation.

### 9. Snapshot And Ops Pipeline

```text
connector payload
        |
        v
snapshot refresh
        |
        v
documents.json + manifest.json + page_index.json
        |
        v
ops health report
```

Commands:

```powershell
python scripts/platform_cli.py sync-health jira fixtures/connectors/jira/incremental_sync.json --snapshot-dir .tmp/snapshot
python scripts/platform_cli.py multi-sync-health --snapshot-dir .tmp/snapshot --jira-path fixtures/connectors/jira/incremental_sync.json --confluence-path fixtures/connectors/confluence/incremental_sync.json
```

`sync-export` can now run against a single source when you only need to validate Markdown/PageIndex generation for Jira or Confluence:

```powershell
python scripts/platform_cli.py sync-export --snapshot-dir .tmp\jira-snapshot --jira-path fixtures\connectors\jira\incremental_sync.json --output-md .tmp\jira-only.md --output-page-index .tmp\jira-only-page-index.json
python scripts/platform_cli.py sync-export --snapshot-dir .tmp\confluence-snapshot --confluence-path fixtures\connectors\confluence\incremental_sync.json --output-md .tmp\confluence-only.md --output-page-index .tmp\confluence-only-page-index.json
```

## Environment

See [docs/environment-setup.md](docs/environment-setup.md) for:

- Python and dependency setup
- optional MinerU PDF parser configuration
- optional Ollama/OpenAI-compatible local LLM configuration
- live Jira and Confluence credential examples
- Markdown and PageIndex export commands

## Current Constraints

- Live Jira and Confluence connector paths exist, but production rollout still needs real-environment smoke coverage.
- The portal is a static internal UI backed by generated JSON state.
- Retrieval and evaluation currently run on the local fixture corpus.
- Image references can be merged into Markdown when `alt_text`, `ocr_text`, or `vision_caption` metadata is present; automatic image download/OCR/vision captioning is still a production gap.
- The implementation is structured to be extended into production integrations and reusable skills.

# Environment Setup

## Purpose

This guide describes the local environment needed to run the SSD knowledge platform ingestion and retrieval workflows.

The shortest supported workflow is:

```text
Jira / Confluence / PPTX / PDF
        -> canonical document
        -> readable Markdown
        -> PageIndex JSON
        -> retrieval / citation / Jira analysis
```

## Runtime

Use Python 3.12 or newer.

Preferred setup on Windows PowerShell uses `uv`:

```powershell
python --version
python -m pip install --upgrade uv
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -e .
```

For development-only dependencies:

```powershell
uv pip install -e ".[dev]"
```

If `uv` is not available, use the standard `venv` and `pip` workflow:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

The current repository keeps dependencies minimal. `pypdf` is declared as the required runtime dependency for the built-in PDF fallback parser and is installed by `uv pip install -e .` or `python -m pip install -e .`.

Editable install package discovery is explicit. Only `apps*` and `services*` are installable Python packages. Directories such as `packages`, `scripts`, `docs`, `fixtures`, `ops`, `eval`, `skills`, and `tests` are repository assets, not runtime packages.

## Optional Components

### MinerU PDF Parser

MinerU is optional. If installed, the PDF adapter will try MinerU first for richer PDF parsing and then fall back to `pypdf` when `preferred_parser=auto`.

Recommended local setup is to keep MinerU outside the base project environment because it pulls a heavier document parsing stack:

```powershell
uv venv .venv-mineru --python 3.12
.\.venv-mineru\Scripts\Activate.ps1
uv pip install -U "mineru[all]"
mineru --help
```

Then point the adapter at that interpreter:

```powershell
$env:MINERU_PYTHON_EXE = "$PWD\.venv-mineru\Scripts\python.exe"
```

You can also install MinerU in the active project environment when you are doing dedicated PDF parser work:

```powershell
uv pip install -U "mineru[all]"
```

### Local LLM

Local LLM support is optional and only used when `--llm-backend` is set.

For LM Studio (recommended for local testing):

1. Download and install LM Studio from https://lmstudio.ai/
2. Load a model (e.g., `qwen-9b` or similar)
3. Start the local server (default: `http://127.0.0.1:1234/v1`)

Example:

```powershell
python scripts/platform_cli.py jira-report `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --updated-on-date 2026-04-05 `
  --llm-backend openai-compatible `
  --llm-model qwen-9b `
  --llm-base-url http://127.0.0.1:1234/v1 `
  --llm-prompt-mode strict `
  --output-answer-md .tmp/jira-report-answer.md
```

For other local OpenAI-compatible servers such as vLLM or llama.cpp server:

```powershell
python scripts/platform_cli.py jira-spec-qa `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --jira-issue-id SSD-102 `
  --spec-corpus fixtures/retrieval/pageindex_corpus.json `
  --spec-document-id nvme-spec-v1 `
  --question "Does this issue relate to the selected spec?" `
  --llm-backend openai-compatible `
  --llm-model local-model `
  --llm-base-url http://localhost:1234/v1
```

### PageIndex

The repository's default PageIndex path does not require an external package. The normalizer builds a repository-local PageIndex JSON artifact from canonical documents:

```powershell
python scripts/ingest/normalize_cli.py pdf fixtures/corpus/pdf/sample.pdf `
  --output-md .tmp/pdf.md `
  --output-page-index .tmp/pdf-page-index.json
```

Only install the external PageIndex Python SDK if the task explicitly needs PageIndex.ai cloud processing or its API client:

```powershell
uv pip install -U pageindex
$env:PAGEINDEX_API_KEY = "<api-key>"
```

### Wiki Rendering

MkDocs Material is only required for local wiki-site preview/build. It is not part of the core retrieval runtime path.

Install locally when you need to render `wiki_site/`:

```powershell
python -m pip install mkdocs mkdocs-material
```

Expected local preview URL:

- `http://127.0.0.1:8000/`

Expected static output location after `mkdocs build`:

- `.tmp\wiki-demo\wiki_site\site\`

## Source Configuration

For the workspace-first staged operator flow, see:

- [workspace-cli-guide.md](workspace-cli-guide.md)
- [runbooks/progressive-ingestion-workspace.md](runbooks/progressive-ingestion-workspace.md)

### Fixture Sources

Fixture sources require no credentials:

```powershell
python scripts/ingest/normalize_cli.py jira-sync fixtures/connectors/jira/full_sync.json
python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json
python scripts/ingest/normalize_cli.py pptx fixtures/corpus/office/sample.pptx
python scripts/ingest/normalize_cli.py pdf fixtures/corpus/pdf/sample.pdf
```

### Live Jira

Live Jira requires a base URL and token or username/password:

```powershell
$env:JIRA_TOKEN = "<token>"

python scripts/platform_cli.py connector jira `
  --live `
  --base-url https://jira.example.com `
  --token $env:JIRA_TOKEN `
  --output-json .tmp\jira-live.json
```

### Live Confluence

Live Confluence requires a base URL and token or username/password:

```powershell
$env:CONF_TOKEN = "<token>"

python scripts/platform_cli.py connector confluence `
  --live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --output-json .tmp\confluence-live.json
```

To fetch one page and all descendants:

```powershell
python scripts/platform_cli.py connector confluence `
  --live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --fetch-backend atlassian-api `
  --root-page-id 123456 `
  --include-descendants `
  --max-depth 2 `
  --output-json .tmp\confluence-tree.json
```

### Live Retrieval Consumption

If you want to test the real website flow directly through the source-generic consumption seam, use `retrieval-consume` with a live source kind.

Live Jira:

```powershell
python scripts/platform_cli.py retrieval-consume `
  --source-kind jira-live `
  --base-url https://jira.example.com `
  --token $env:JIRA_TOKEN `
  --question "What changed in the latest SSD issue?" `
  --output-json .tmp\jira-live-consume.json
```

Live Confluence:

```powershell
python scripts/platform_cli.py retrieval-consume `
  --source-kind confluence-live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --space-key SSD `
  --question "What changed in the latency budget page?" `
  --output-json .tmp\confluence-live-consume.json
```

If you want the answer written to Markdown:

```powershell
python scripts/platform_cli.py retrieval-consume `
  --source-kind confluence-live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --space-key SSD `
  --question "What changed in the latency budget page?" `
  --llm-backend openai-compatible `
  --llm-model qwen-9b `
  --llm-base-url http://127.0.0.1:1234/v1 `
  --output-answer-md .tmp\live-confluence-answer.md
```

## Markdown And PageIndex Export

Use the skill-ready normalizer CLI when the goal is to generate readable Markdown and a PageIndex artifact from source documents:

```powershell
python scripts/ingest/normalize_cli.py jira-sync fixtures/connectors/jira/full_sync.json `
  --output-md .tmp/jira.md `
  --output-page-index .tmp/jira-page-index.json

python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json `
  --output-md .tmp/confluence.md `
  --output-page-index .tmp/confluence-page-index.json

python scripts/ingest/normalize_cli.py pptx fixtures/corpus/office/sample.pptx `
  --output-md .tmp/pptx.md `
  --output-page-index .tmp/pptx-page-index.json

python scripts/ingest/normalize_cli.py pdf fixtures/corpus/pdf/sample.pdf `
  --output-md .tmp/pdf.md `
  --output-page-index .tmp/pdf-page-index.json
```

If you want one Markdown file per canonical document instead of one concatenated Markdown output:

```powershell
python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json `
  --output-md-dir .tmp\docs `
  --output-page-index .tmp\confluence-page-index.json
```

The generated Markdown is human-readable. The generated PageIndex is derived from the same canonical document payload, so retrieval and citation use the same source representation.

## Image Handling

Jira, Confluence, and MinerU PDF ingestion can merge image references into Markdown evidence blocks when image metadata is available.

Currently supported image metadata:

- `alt_text`
- `ocr_text`
- `vision_caption`

Current limitation: automatic image download, OCR, and local vision captioning are not yet enabled. Those should be added as explicit backends rather than hidden behavior.

## Validation

Run the core validation set before opening or updating a PR:

```powershell
python scripts/gates/check_module_contracts.py
python -m unittest discover
python -m compileall docs scripts services tests
```

For the full Phase 1 gate:

```powershell
python scripts/gates/run_phase1_gate.py
```

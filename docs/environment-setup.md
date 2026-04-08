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

On Windows PowerShell:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

The current repository keeps dependencies minimal. `pypdf` is declared as the required runtime dependency for the built-in PDF fallback parser and is installed by `python -m pip install -e .`.

For development-only dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Editable install package discovery is explicit. Only `apps*` and `services*` are installable Python packages. Directories such as `packages`, `scripts`, `docs`, `fixtures`, `ops`, `eval`, `skills`, and `tests` are repository assets, not runtime packages.

## Optional Components

### MinerU PDF Parser

MinerU is optional. If installed, the PDF adapter will try MinerU first for richer PDF parsing and then fall back to `pypdf` when `preferred_parser=auto`.

If MinerU is installed in a separate Python environment, point the adapter at that interpreter:

```powershell
$env:MINERU_PYTHON_EXE = "C:\path\to\mineru-python.exe"
```

### Local LLM

Local LLM support is optional and only used when `--llm-backend` is set.

For Ollama:

```powershell
ollama list
ollama pull qwen2.5:1.5b
```

Example:

```powershell
python scripts/platform_cli.py jira-report `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --updated-on-date 2026-04-05 `
  --llm-backend ollama `
  --llm-model qwen2.5:1.5b `
  --llm-prompt-mode strict `
  --output-answer-md .tmp/jira-report-answer.md
```

For local OpenAI-compatible servers such as LM Studio, vLLM, or llama.cpp server:

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

## Source Configuration

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
  --token $env:JIRA_TOKEN
```

### Live Confluence

Live Confluence requires a base URL and token or username/password:

```powershell
$env:CONF_TOKEN = "<token>"

python scripts/platform_cli.py connector confluence `
  --live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN
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

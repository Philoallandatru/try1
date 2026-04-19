# Wiki Demo Validation

## Purpose

This runbook is the canonical checklist for validating the decoupled three-source wiki demo from zero to a rendered local site.

The wiki demo remains derived:

- canonical document remains the source of truth
- snapshot remains the stable runtime state
- export package is the stable handoff boundary
- `wiki_site/` is a renderer-facing derived output only

## 1. Environment Setup

Create and activate the local Python environment:

```powershell
python -m pip install --upgrade uv
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -e .
uv pip install -e ".[dev]"
```

Install local wiki rendering dependencies:

```powershell
python -m pip install mkdocs mkdocs-material
```

Optional local LLM setup:

For LM Studio:
1. Download and install LM Studio from https://lmstudio.ai/
2. Load a model (e.g., qwen-9b)
3. Start the local server (default: http://127.0.0.1:1234/v1)

## 2. Optional Live Credentials

Only needed for live-source validation:

```powershell
$env:JIRA_TOKEN = "<jira-token>"
$env:CONF_TOKEN = "<confluence-token>"
```

## 3. Fixture-Backed Demo Build

Build the full decoupled wiki demo from fixture Jira, fixture Confluence, and a PDF spec:

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
```

## 4. Spec-Corpus-Based Demo Build

If the spec corpus already exists, build from the corpus instead of re-parsing the PDF:

```powershell
python scripts/platform_cli.py build-wiki-site `
  --jira-path fixtures/connectors/jira/incremental_sync.json `
  --confluence-path fixtures/connectors/confluence/page_sync.json `
  --snapshot-dir .tmp\wiki-demo\snapshot `
  --spec-corpus fixtures/retrieval/pageindex_corpus.json `
  --spec-document-id nvme-spec-v1 `
  --clause 1.1 `
  --reference-date 2026-04-05 `
  --output-dir .tmp\wiki-demo `
  --llm-backend mock `
  --llm-mock-response "Mock wiki answer"
```

## 5. Optional Live Jira + Confluence + Real NVMe PDF Example

Use this when validating the real demo path:

```powershell
python scripts/platform_cli.py build-wiki-site `
  --jira-live `
  --jira-base-url https://jira.example.com `
  --jira-token $env:JIRA_TOKEN `
  --jira-project-key SSD `
  --confluence-live `
  --confluence-base-url https://confluence.example.com `
  --confluence-token $env:CONF_TOKEN `
  --confluence-fetch-backend atlassian-api `
  --confluence-root-page-id 123456 `
  --confluence-include-descendants `
  --confluence-max-depth 2 `
  --spec-pdf C:\docs\nvme.pdf `
  --preferred-parser pypdf `
  --reference-date 2026-04-05 `
  --output-dir .tmp\wiki-demo-live
```

## 6. Verify Generated Artifacts

Required artifact checks after `build-wiki-site`:

- `.tmp\wiki-demo\export\manifest.json`
- `.tmp\wiki-demo\export\changes.json`
- `.tmp\wiki-demo\export\page_index.json`
- `.tmp\wiki-demo\wiki_site\mkdocs.yml`
- `.tmp\wiki-demo\wiki_site\docs\index.md`

Quick inspection:

```powershell
Get-ChildItem -Recurse .tmp\wiki-demo\export
Get-ChildItem -Recurse .tmp\wiki-demo\wiki_site
```

## 7. Render the Site With MkDocs

Build the generated site:

```powershell
Set-Location .tmp\wiki-demo\wiki_site
python -m mkdocs build
```

Expected built output:

- `.tmp\wiki-demo\wiki_site\site\`

Serve the site locally:

```powershell
Set-Location .tmp\wiki-demo\wiki_site
python -m mkdocs serve
```

Expected preview URL:

- `http://127.0.0.1:8000/`

## 8. Verify Key Pages

Verify that these rendered pages load:

- home page:
  - `http://127.0.0.1:8000/`
- analysis page:
  - `http://127.0.0.1:8000/analysis/demo-overview/`
- source page:
  - `http://127.0.0.1:8000/sources/jira/SSD-102/`
- project page:
  - `http://127.0.0.1:8000/projects/ssd/`

Optional HTTP smoke checks:

```powershell
(Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing).StatusCode
(Invoke-WebRequest -Uri 'http://127.0.0.1:8000/analysis/demo-overview/' -UseBasicParsing).StatusCode
(Invoke-WebRequest -Uri 'http://127.0.0.1:8000/sources/jira/SSD-102/' -UseBasicParsing).StatusCode
(Invoke-WebRequest -Uri 'http://127.0.0.1:8000/projects/ssd/' -UseBasicParsing).StatusCode
```

## 9. Required Validation Commands

Run the implementation tests:

```powershell
python -m unittest tests.ops.test_wiki_site_builder -v
python -m unittest tests.ops.test_platform_cli.PlatformCliTest.test_cli_build_wiki_site_generates_export_and_mkdocs_tree tests.ops.test_platform_cli.PlatformCliTest.test_cli_build_wiki_site_can_build_spec_from_pdf -v
python scripts/gates/check_module_contracts.py
```

If any command examples were changed, re-run the demo build and local site build:

```powershell
python scripts/platform_cli.py build-wiki-site --jira-path fixtures/connectors/jira/incremental_sync.json --confluence-path fixtures/connectors/confluence/page_sync.json --snapshot-dir .tmp/wiki-demo/snapshot --spec-pdf fixtures/corpus/pdf/sample.pdf --preferred-parser pypdf --reference-date 2026-04-05 --output-dir .tmp/wiki-demo --llm-backend mock --llm-mock-response "Mock wiki answer"
Set-Location .tmp\wiki-demo\wiki_site
python -m mkdocs build
```

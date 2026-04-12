# CLI Reference

For a Chinese guide with command purpose, parameter tables, and end-to-end examples, see [platform-cli-guide.zh.md](platform-cli-guide.zh.md).

## Retrieval Model

The current retrieval implementation is PageIndex-first and page-scoped.

High-level flow:

1. source files or connector payloads are normalized into canonical documents
2. canonical documents are projected into PageIndex entries
3. search applies ACL filtering before scoring
4. ranking uses lexical overlap, token overlap, and source authority boost
5. citations and source inspection are assembled from the matched PageIndex entries

PageIndex artifacts use the canonical JSON shape:

```json
{
  "entries": [...]
}
```

Current retrieval source options:

- `--corpus`
  - loads canonical documents and rebuilds PageIndex at runtime
- `--page-index`
  - consumes an exported PageIndex artifact directly
- `--snapshot-dir`
  - reuses snapshot-managed `page_index.json`

Snapshot refresh currently merges documents by `document_id` and then rebuilds the full `page_index.json`. There is no entry-level patching or vector-index maintenance in the current implementation.

## Unified CLI

Primary entrypoint:

```bash
python scripts/platform_cli.py <command>
```

## Commands

### Governance

```bash
python scripts/platform_cli.py adr-check
python scripts/platform_cli.py repo-check
python scripts/platform_cli.py module-check
```

### Evaluation and Gates

```bash
python scripts/platform_cli.py eval
python scripts/platform_cli.py gate
python scripts/platform_cli.py ops-health
python scripts/platform_cli.py ops-health --snapshot-dir .tmp/snapshot
python scripts/platform_cli.py ops-health --snapshot-dir .tmp/snapshot --reference-time-iso 2026-04-06T09:10:00Z
python scripts/platform_cli.py sync-health jira fixtures/connectors/jira/incremental_sync.json --snapshot-dir .tmp/snapshot --reference-time-iso 2026-04-06T09:10:00Z
python scripts/platform_cli.py multi-sync-health --snapshot-dir .tmp/snapshot --jira-path fixtures/connectors/jira/incremental_sync.json --confluence-path fixtures/connectors/confluence/incremental_sync.json --reference-time-iso 2026-04-06T09:10:00Z
python scripts/platform_cli.py multi-sync-health --snapshot-dir .tmp/snapshot --jira-live --jira-base-url https://jira.example.com --jira-token $JIRA_TOKEN --confluence-live --confluence-base-url https://confluence.example.com --confluence-token $CONF_TOKEN
python scripts/platform_cli.py multi-sync-health --profile fixtures/ops/multi_sync_health_profile.json --snapshot-dir .tmp/snapshot
python scripts/platform_cli.py multi-sync-health --profile fixtures/ops/selective_live_multi_sync_profile.json --snapshot-dir .tmp/selective-live-snapshot
```

### Ingestion

```bash
python scripts/platform_cli.py ingest markdown fixtures/corpus/markdown/sample.md
python scripts/platform_cli.py ingest docx fixtures/corpus/office/sample.docx
python scripts/platform_cli.py ingest xlsx fixtures/corpus/office/sample.xlsx
python scripts/platform_cli.py ingest pptx fixtures/corpus/office/sample.pptx
python scripts/platform_cli.py ingest pdf fixtures/corpus/pdf/sample.pdf
```

### Connectors

```bash
python scripts/platform_cli.py connector jira fixtures/connectors/jira/full_sync.json
python scripts/platform_cli.py connector confluence fixtures/connectors/confluence/page_sync.json
python scripts/platform_cli.py connector jira fixtures/connectors/jira/full_sync.json --output-json .tmp/jira.json
python scripts/platform_cli.py connector jira --live --base-url https://jira.example.com --token $TOKEN
python scripts/platform_cli.py connector confluence --live --base-url https://confluence.example.com --token $TOKEN
```

Selective live fetch with the experimental Atlassian backend:

```bash
python scripts/platform_cli.py connector jira --live --base-url https://jira.example.com --token $JIRA_TOKEN --fetch-backend atlassian-api --issue-key SSD-777
python scripts/platform_cli.py connector jira --live --base-url https://jira.example.com --token $JIRA_TOKEN --fetch-backend atlassian-api --project-key SSD --issue-type Bug --updated-from 2026-04-01T00:00:00Z --updated-to 2026-04-10T00:00:00Z --no-include-comments
python scripts/platform_cli.py connector confluence --live --base-url https://confluence.example.com --token $CONF_TOKEN --fetch-backend atlassian-api --page-id 123456
python scripts/platform_cli.py connector confluence --live --base-url https://confluence.example.com --token $CONF_TOKEN --fetch-backend atlassian-api --space-key SSDENG --label firmware --modified-from 2026-04-01T00:00:00Z
```

Optional image download examples:

```bash
python scripts/platform_cli.py connector jira --live --base-url https://jira.example.com --token $JIRA_TOKEN --fetch-backend atlassian-api --issue-key SSD-777 --download-images --image-download-dir .tmp/jira-images
python scripts/platform_cli.py connector confluence --live --base-url https://confluence.example.com --token $CONF_TOKEN --fetch-backend atlassian-api --page-id 123456 --download-images --image-download-dir .tmp/confluence-images
```

### Retrieval and Citation

```bash
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py search "flush command" --page-index .tmp/page-index.json
python scripts/platform_cli.py search "flush command" --snapshot-dir .tmp/snapshot
python scripts/platform_cli.py citation "flush command"
python scripts/platform_cli.py citation "flush command" --page-index .tmp/page-index.json
python scripts/platform_cli.py citation "flush command" --snapshot-dir .tmp/snapshot
```

### Jira Analysis

```bash
python scripts/platform_cli.py jira-report --jira-path fixtures/connectors/jira/incremental_sync.json --updated-from-iso 2026-04-05T09:00:00Z --updated-to-iso 2026-04-05T10:00:00Z
python scripts/platform_cli.py jira-report --jira-path fixtures/connectors/jira/incremental_sync.json --updated-from-iso 2026-04-05T09:00:00Z --updated-to-iso 2026-04-05T10:00:00Z --output-md .tmp/jira-report.md
python scripts/platform_cli.py jira-report --jira-path fixtures/connectors/jira/full_sync.json --updated-on-date 2026-04-05
python scripts/platform_cli.py jira-report --jira-path fixtures/connectors/jira/incremental_sync.json --updated-at-iso 2026-04-05T09:30:00Z
python scripts/platform_cli.py jira-report --jira-live --jira-base-url https://jira.example.com --jira-token $JIRA_TOKEN --updated-from-iso 2026-04-05T09:00:00Z --updated-to-iso 2026-04-05T10:00:00Z
python scripts/platform_cli.py jira-report --jira-path fixtures/connectors/jira/incremental_sync.json --prompt-template "Summarize {issue_count} issue(s): {summaries}"
python scripts/platform_cli.py jira-report --jira-path fixtures/connectors/jira/incremental_sync.json --updated-on-date 2026-04-05 --llm-backend ollama --llm-model qwen2.5:7b --llm-prompt-mode strict --output-answer-md .tmp/jira-report-answer.md
python scripts/platform_cli.py jira-report --jira-path fixtures/connectors/jira/full_sync.json --report-profile pm-daily --reference-date 2026-04-05 --status-filter "In Progress" --llm-backend mock --llm-mock-response "Mock PM daily summary"
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?"
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?" --output-answer-md .tmp/jira-spec-answer.md
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?" --llm-backend ollama --llm-model qwen2.5:7b --llm-base-url http://localhost:11434
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?" --llm-backend ollama --llm-model qwen2.5:7b --llm-prompt-mode strict
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?" --llm-backend openai-compatible --llm-model local-model --llm-base-url http://localhost:1234/v1
python scripts/platform_cli.py jira-spec-qa --jira-live --jira-base-url https://jira.example.com --jira-token $JIRA_TOKEN --jira-issue-id SSD-102 --spec-document-id nvme-spec-v1 --question "Does this issue relate to the spec?"
python scripts/platform_cli.py jira-batch-spec-report --jira-path fixtures/connectors/jira/incremental_sync.json --updated-from-iso 2026-04-05T09:00:00Z --updated-to-iso 2026-04-05T10:00:00Z --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question-template "Analyze Jira {jira_issue_id} against the selected spec." --output-md .tmp/jira-batch-spec-report.md
python scripts/platform_cli.py jira-batch-spec-report --jira-path fixtures/connectors/jira/incremental_sync.json --updated-from-iso 2026-04-05T09:00:00Z --updated-to-iso 2026-04-05T10:00:00Z --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question-template "Analyze Jira {jira_issue_id} against the selected spec." --llm-backend ollama --llm-model qwen2.5:7b
python scripts/platform_cli.py spec-section-explain --jira-path fixtures/connectors/jira/incremental_sync.json --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --clause 1.1
python scripts/platform_cli.py confluence-wiki-demo --confluence-path fixtures/connectors/confluence/page_sync.json --output-dir .tmp/wiki-demo --llm-backend mock --llm-mock-response "Mock confluence wiki summary"
python scripts/platform_cli.py build-spec-corpus --spec-pdf fixtures/corpus/pdf/sample.pdf --output-dir .tmp/spec-build --preferred-parser pypdf
python scripts/platform_cli.py demo-orchestrate --jira-path fixtures/connectors/jira/incremental_sync.json --confluence-path fixtures/connectors/confluence/page_sync.json --snapshot-dir .tmp/demo/snapshot --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --clause 1.1 --reference-date 2026-04-05 --output-dir .tmp/demo
```

### Generic Retrieval Consumption

```bash
python scripts/platform_cli.py retrieval-consume --source-kind jira-sync --source-path fixtures/connectors/jira/incremental_sync.json --question "Which issue mentions medium priority?"
python scripts/platform_cli.py retrieval-consume --source-kind confluence-sync --source-path fixtures/connectors/confluence/page_sync.json --question "Which page mentions telemetry architecture?" --llm-backend mock --llm-mock-response "Mock confluence answer"
python scripts/platform_cli.py retrieval-consume --source-kind jira-live --base-url https://jira.example.com --token $JIRA_TOKEN --question "What changed in the latest SSD issue?"
python scripts/platform_cli.py retrieval-consume --source-kind confluence-live --base-url https://confluence.example.com --token $CONF_TOKEN --space-key SSD --question "What changed in the latency budget page?"
python scripts/platform_cli.py retrieval-consume --source-kind jira-live --base-url https://jira.example.com --token $JIRA_TOKEN --fetch-backend atlassian-api --issue-key SSD-777 --question "What changed in this exact issue?"
python scripts/platform_cli.py retrieval-consume --source-kind confluence-live --base-url https://confluence.example.com --token $CONF_TOKEN --fetch-backend atlassian-api --page-id 123456 --question "What changed on this exact page?"
python scripts/platform_cli.py retrieval-consume --source-kind pptx --source-path fixtures/corpus/office/sample.pptx --question "Which slide mentions latency targets?"
python scripts/platform_cli.py retrieval-consume --source-kind pdf --source-path fixtures/corpus/pdf/sample.pdf --question "What document covers flush semantics?"
python scripts/platform_cli.py retrieval-consume --snapshot-dir .tmp/snapshot --question "What document covers flush semantics?"
python scripts/platform_cli.py retrieval-consume --snapshot-dir .tmp/snapshot --question "What document covers flush semantics?" --output-json .tmp/consume.json
```

### Sync Export

```bash
python scripts/platform_cli.py sync-export --profile fixtures/ops/multi_sync_health_profile.json --snapshot-dir .tmp/snapshot --output-md .tmp/export.md --output-page-index .tmp/export-page-index.json
python scripts/platform_cli.py sync-export --profile fixtures/ops/multi_sync_health_profile.json --snapshot-dir .tmp/snapshot --output-md-dir .tmp/export-docs
```

`sync-export` performs a source sync, refreshes the local snapshot, and exports Markdown / Markdown tree / PageIndex from either:

- `--export-scope incoming`
  - only the documents returned by the current sync
- `--export-scope snapshot`
  - the full current snapshot document set

### Portal

```bash
python scripts/platform_cli.py portal-state --query "nvme flush"
```

## Notes

- All commands currently operate on local fixtures and local contracts.
- The CLI is intended to be stable enough to be wrapped as future reusable skills.
- The current retrieval model is page-scoped and not a dense-vector or learned sparse retrieval system.
- Ingestion now merges image references into canonical Markdown when Jira attachments, Confluence inline/attachment images, or MinerU PDF image blocks include image metadata. Provided `ocr_text`, `vision_caption`, and `alt_text` fields are indexed as image evidence; automatic OCR/vision extraction is not yet enabled.
- `ops-health` can now read either fixture-backed status or a real local snapshot manifest/page index via `--snapshot-dir`.
- `sync-health` provides a sequential ops path: connector payload -> snapshot refresh -> ops health.
- `multi-sync-health` provides a sequential dual-source path: Jira refresh -> Confluence refresh -> aggregated ops health.
- `multi-sync-health` supports both fixture-backed and live dual-source operation, with source-prefixed live configuration flags.
- `multi-sync-health` also supports a JSON profile file so source configuration can be versioned outside the command line.
- Live Jira/Confluence commands now support `--fetch-backend atlassian-api` plus bounded selectors such as `--issue-key`, `--project-key`, `--page-id`, `--title`, `--label`, and date windows. These selective flags are intentionally rejected on the `native` backend.
- `--download-images` is opt-in and requires `--image-download-dir`.
- `jira-report` builds a time-filtered Jira markdown report from fixture or live Jira input, supports explicit windows, calendar dates, and exact ISO timestamps, can write it to `--output-md`, can optionally call a local LLM backend through `--llm-backend`, can write that answer to `--output-answer-md`, and renders an optional prompt template.
- `jira-report --report-profile pm-daily` produces a project-manager-oriented daily report for `In Progress` issues with deterministic owner/priority/status/update/comment facts and four fixed sections: `Executive Summary`, `Active Today`, `In Progress But No Update`, and `Manager Attention`.
- `jira-spec-qa` builds a Jira-plus-spec retrieval payload from fixture or live Jira input, renders an optional prompt template, includes an extractive draft answer by default, can optionally call a local LLM backend through `--llm-backend`, and can write the selected answer to `--output-answer-md`.
- `jira-batch-spec-report` combines time-filtered Jira reporting with per-issue Jira-plus-spec QA, supports the same optional local LLM backend flags, and can write a combined Markdown report to `--output-md`.
- `spec-section-explain` is a section-centered demo flow that explains a selected spec clause or heading through retrieved Jira evidence. The payload now includes a lightweight `section_anchor_id` helper and a prompt section with structured Jira summaries.
- `retrieval-consume` is the source-generic retrieval-consumption CLI for Jira/Confluence fixture payloads, live Jira/Confluence sources, direct file-backed Markdown/Office/PDF inputs, and snapshot-backed document sets. It assembles citation-backed prompts and can optionally call a local LLM backend.
- `confluence-wiki-demo` builds a small static HTML wiki demo from Confluence-derived summaries, including an index page with grouped summary cards and detail pages that retain version/source/derived traceability markers.
- `build-spec-corpus` converts a spec PDF into `spec-doc.json` plus `spec-corpus.json` so downstream spec demo flows can consume a stable `{"documents": [...]}` corpus input.
- `demo-orchestrate` is the one-command demo path. It refreshes the snapshot-first Jira/Confluence demo inputs, writes `.tmp/demo/jira-daily.md` and `.tmp/demo/spec-section.md`, and builds `.tmp/demo/wiki/`.
- `sync-export` is the current document-level export path. It does not yet implement section-level derived wiki generation.
- PDF parsing defaults to `auto`: try MinerU first, then fall back to `pypdf`. If MinerU is installed in a separate Python environment, set `MINERU_PYTHON_EXE` or use `build-spec-corpus --mineru-python-exe ...`.
- `--llm-prompt-mode strict|balanced|exploratory` controls local-model behavior. Use `strict` for release notes and reviewable reports, `balanced` for engineering triage, and `exploratory` only for follow-up investigation ideas.

## Skill-Ready CLIs

### Offline Document Normalizer

```bash
python scripts/ingest/normalize_cli.py markdown fixtures/corpus/markdown/sample.md
python scripts/ingest/normalize_cli.py pdf fixtures/corpus/pdf/sample.pdf
python scripts/ingest/normalize_cli.py jira-sync fixtures/connectors/jira/full_sync.json
python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json
```

Write readable Markdown and a PageIndex from normalized sources:

```bash
python scripts/ingest/normalize_cli.py jira-sync fixtures/connectors/jira/full_sync.json --output-md .tmp/jira.md --output-page-index .tmp/jira-page-index.json
python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json --output-md .tmp/confluence.md --output-page-index .tmp/confluence-page-index.json
python scripts/ingest/normalize_cli.py pptx fixtures/corpus/office/sample.pptx --output-md .tmp/pptx.md --output-page-index .tmp/pptx-page-index.json
python scripts/ingest/normalize_cli.py pdf fixtures/corpus/pdf/sample.pdf --output-md .tmp/pdf.md --output-page-index .tmp/pdf-page-index.json
python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json --output-md-dir .tmp/docs
```

### Grounded Retrieval Toolkit

```bash
python scripts/retrieval/toolkit_cli.py index --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py index --corpus fixtures/retrieval/pageindex_corpus.json --output-page-index .tmp/page-index.json
python scripts/retrieval/toolkit_cli.py search "flush command" --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py search "flush command" --page-index .tmp/page-index.json
python scripts/retrieval/toolkit_cli.py search "flush command" --snapshot-dir .tmp/snapshot
python scripts/retrieval/toolkit_cli.py citation "flush command" --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py citation "flush command" --page-index .tmp/page-index.json
python scripts/retrieval/toolkit_cli.py citation "flush command" --snapshot-dir .tmp/snapshot
```

PageIndex artifacts use the canonical JSON shape `{"entries": [...]}`. `--corpus` rebuilds PageIndex from canonical documents; `--page-index` consumes an exported PageIndex artifact directly; `--snapshot-dir` reuses snapshot-managed `page_index.json`.

### Snapshot Persistence

```bash
python scripts/retrieval/snapshot_cli.py create --snapshot-dir .tmp/snapshot --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/snapshot_cli.py show --snapshot-dir .tmp/snapshot
python scripts/retrieval/snapshot_cli.py refresh --snapshot-dir .tmp/snapshot --sync-payload fixtures/connectors/jira/incremental_sync.json --source-name jira
```

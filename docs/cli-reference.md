# CLI Reference

For a Chinese guide with command purpose, parameter tables, and end-to-end examples, see [platform-cli-guide.zh.md](platform-cli-guide.zh.md).

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
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?"
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?" --output-answer-md .tmp/jira-spec-answer.md
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?" --llm-backend ollama --llm-model qwen2.5:7b --llm-base-url http://localhost:11434
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?" --llm-backend ollama --llm-model qwen2.5:7b --llm-prompt-mode strict
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures/connectors/jira/incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does the NAND TLC write issue relate to NVMe flush command evidence?" --llm-backend openai-compatible --llm-model local-model --llm-base-url http://localhost:1234/v1
python scripts/platform_cli.py jira-spec-qa --jira-live --jira-base-url https://jira.example.com --jira-token $JIRA_TOKEN --jira-issue-id SSD-102 --spec-document-id nvme-spec-v1 --question "Does this issue relate to the spec?"
python scripts/platform_cli.py jira-batch-spec-report --jira-path fixtures/connectors/jira/incremental_sync.json --updated-from-iso 2026-04-05T09:00:00Z --updated-to-iso 2026-04-05T10:00:00Z --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question-template "Analyze Jira {jira_issue_id} against the selected spec." --output-md .tmp/jira-batch-spec-report.md
python scripts/platform_cli.py jira-batch-spec-report --jira-path fixtures/connectors/jira/incremental_sync.json --updated-from-iso 2026-04-05T09:00:00Z --updated-to-iso 2026-04-05T10:00:00Z --spec-corpus fixtures/retrieval/pageindex_corpus.json --spec-document-id nvme-spec-v1 --question-template "Analyze Jira {jira_issue_id} against the selected spec." --llm-backend ollama --llm-model qwen2.5:7b
```

### Generic Retrieval Consumption

```bash
python scripts/platform_cli.py retrieval-consume --source-kind jira-sync --source-path fixtures/connectors/jira/incremental_sync.json --question "Which issue mentions medium priority?"
python scripts/platform_cli.py retrieval-consume --source-kind confluence-sync --source-path fixtures/connectors/confluence/page_sync.json --question "Which page mentions telemetry architecture?" --llm-backend mock --llm-mock-response "Mock confluence answer"
python scripts/platform_cli.py retrieval-consume --source-kind jira-live --base-url https://jira.example.com --token $JIRA_TOKEN --question "What changed in the latest SSD issue?"
python scripts/platform_cli.py retrieval-consume --source-kind confluence-live --base-url https://confluence.example.com --token $CONF_TOKEN --space-key SSD --question "What changed in the latency budget page?"
python scripts/platform_cli.py retrieval-consume --source-kind pptx --source-path fixtures/corpus/office/sample.pptx --question "Which slide mentions latency targets?"
python scripts/platform_cli.py retrieval-consume --source-kind pdf --source-path fixtures/corpus/pdf/sample.pdf --question "What document covers flush semantics?"
python scripts/platform_cli.py retrieval-consume --snapshot-dir .tmp/snapshot --question "What document covers flush semantics?"
python scripts/platform_cli.py retrieval-consume --snapshot-dir .tmp/snapshot --question "What document covers flush semantics?" --output-json .tmp/consume.json
```

### Portal

```bash
python scripts/platform_cli.py portal-state --query "nvme flush"
```

## Notes

- All commands currently operate on local fixtures and local contracts.
- The CLI is intended to be stable enough to be wrapped as future reusable skills.
- Ingestion now merges image references into canonical Markdown when Jira attachments, Confluence inline/attachment images, or MinerU PDF image blocks include image metadata. Provided `ocr_text`, `vision_caption`, and `alt_text` fields are indexed as image evidence; automatic OCR/vision extraction is not yet enabled.
- `ops-health` can now read either fixture-backed status or a real local snapshot manifest/page index via `--snapshot-dir`.
- `sync-health` provides a sequential ops path: connector payload -> snapshot refresh -> ops health.
- `multi-sync-health` provides a sequential dual-source path: Jira refresh -> Confluence refresh -> aggregated ops health.
- `multi-sync-health` supports both fixture-backed and live dual-source operation, with source-prefixed live configuration flags.
- `multi-sync-health` also supports a JSON profile file so source configuration can be versioned outside the command line.
- `jira-report` builds a time-filtered Jira markdown report from fixture or live Jira input, supports explicit windows, calendar dates, and exact ISO timestamps, can write it to `--output-md`, can optionally call a local LLM backend through `--llm-backend`, can write that answer to `--output-answer-md`, and renders an optional prompt template.
- `jira-spec-qa` builds a Jira-plus-spec retrieval payload from fixture or live Jira input, renders an optional prompt template, includes an extractive draft answer by default, can optionally call a local LLM backend through `--llm-backend`, and can write the selected answer to `--output-answer-md`.
- `jira-batch-spec-report` combines time-filtered Jira reporting with per-issue Jira-plus-spec QA, supports the same optional local LLM backend flags, and can write a combined Markdown report to `--output-md`.
- `retrieval-consume` is the source-generic retrieval-consumption CLI for Jira/Confluence fixture payloads, live Jira/Confluence sources, direct file-backed Markdown/Office/PDF inputs, and snapshot-backed document sets. It assembles citation-backed prompts and can optionally call a local LLM backend.
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

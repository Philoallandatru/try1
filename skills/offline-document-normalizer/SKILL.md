---
name: offline-document-normalizer
description: Normalize Markdown, Office, PDF, and fixture-backed Jira or Confluence sync payloads into canonical evidence documents. Use when converting local source files or connector snapshots into portable normalized JSON for indexing, inspection, or later skill workflows.
---

# Offline Document Normalizer

Use this skill when the task is to turn a source artifact into the canonical document schema without involving hosted services, persistence, or portal shaping.

## Use When

- Normalize a Markdown, DOCX, XLSX, PPTX, or PDF file into canonical JSON
- Convert a fixture-backed Jira sync payload into canonical `jira` documents
- Convert a fixture-backed Confluence sync payload into canonical `confluence` documents
- Produce portable normalized JSON before indexing or retrieval evaluation

## Do Not Use When

- The task is to fetch live Jira or Confluence data over the network
- The task is to implement persistence, hosted services, or ACL identity enforcement
- The task only needs search or citation over an existing corpus

## Entry Point

Primary command:

```bash
python scripts/ingest/normalize_cli.py <kind> <path>
```

Supported kinds:

- `markdown`
- `docx`
- `xlsx`
- `pptx`
- `pdf`
- `jira-sync`
- `confluence-sync`

## Workflow

1. Identify the source family and confirm it is local or fixture-backed.
2. Run `scripts/ingest/normalize_cli.py` with the matching kind.
3. Inspect the output for canonical fields:
   - `document_id`
   - `source_type`
   - `authority_level`
   - `version`
   - `language`
   - `title`
   - `provenance`
   - `acl`
   - `structure`
   - `terminology`
   - `content_blocks`
4. If the output will flow into retrieval, keep it unchanged and pass it to the retrieval toolkit.

## Implementation References

- `services/ingest/normalizer.py`
- `services/ingest/adapters/markdown/adapter.py`
- `services/ingest/adapters/office/adapter.py`
- `services/ingest/adapters/pdf/adapter.py`
- `services/connectors/jira/connector.py`
- `services/connectors/confluence/connector.py`
- `scripts/ingest/normalize_cli.py`

## Boundaries

- Keep output in canonical schema form.
- Do not add persistence-specific fields here.
- Do not add portal-specific response shaping here.
- Do not bypass source-specific normalization logic by hand-editing JSON unless the task explicitly requires fixture authoring.

## Validation

Recommended checks:

```bash
python scripts/ingest/normalize_cli.py markdown fixtures/corpus/markdown/sample.md
python scripts/ingest/normalize_cli.py pdf fixtures/corpus/pdf/sample.pdf
python scripts/ingest/normalize_cli.py jira-sync fixtures/connectors/jira/full_sync.json
python scripts/ingest/normalize_cli.py confluence-sync fixtures/connectors/confluence/page_sync.json
python -m unittest tests.ops.test_skill_ready_clis
```

## Output Expectation

Return the normalized JSON payload directly. If the task chains into retrieval, say that the output is ready for `scripts/retrieval/toolkit_cli.py`.

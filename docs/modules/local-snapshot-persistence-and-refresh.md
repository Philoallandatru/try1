# Local Snapshot Persistence And Refresh Module Contract

## Scope

Persist canonical documents and page-index entries into a local recoverable snapshot and support incremental refresh without changing retrieval contracts.

This module covers:

- local snapshot creation from canonical document corpora
- local persistence of:
  - manifest
  - documents
  - page index
- incremental refresh from normalized sync payloads
- stable CLI entrypoints for create, show, and refresh

This module does not cover:

- database backends
- hosted services
- portal query serving
- request-scoped identity ACL

## Inputs

- canonical document snapshots with top-level `documents`
- normalized connector sync payloads with:
  - `sync_type`
  - `cursor`
  - `documents`
- or fixture/raw Jira and Confluence sync payloads that are normalized before refresh
- target local snapshot directory

## Outputs

- `manifest.json`
- `documents.json`
- `page_index.json`
- refresh result payloads with updated document ids and source cursor state

## Dependencies

- canonical document schema
- page index builder
- retrieval toolkit loading contract
- backup and freshness runbook expectations

## KPIs

- snapshot completeness rate
- refresh merge correctness rate
- page-index rebuild consistency rate
- restore-readiness evidence completeness

## Implementation Steps

1. Keep persistence local and file-backed.
2. Persist canonical documents without schema reshaping.
3. Rebuild page index from persisted documents after every create or refresh.
4. Track per-source cursor state in the manifest.
5. Normalize raw connector payloads before refresh if needed.
6. Use incremental payloads to replace documents by `document_id`.
7. Keep snapshot inspection CLI-readable for ops and future restore checks.

## Boundary Rules

- Do not introduce database-specific abstractions in this step.
- Do not couple snapshot format to portal responses.
- Do not mutate retrieval ranking logic in this step.
- Do not merge documents using anything weaker than stable `document_id`.

## Validation

### Structural validation

- `python -m compileall docs scripts services tests`

### Behavioral validation

- create snapshot from fixture corpus
- refresh snapshot from fixture incremental sync payload
- confirm manifest, documents, and page index are all updated

### Entry-point validation

- `python scripts/retrieval/snapshot_cli.py create --snapshot-dir .tmp/snapshot --corpus fixtures/retrieval/pageindex_corpus.json`
- `python scripts/retrieval/snapshot_cli.py show --snapshot-dir .tmp/snapshot`
- `python scripts/retrieval/snapshot_cli.py refresh --snapshot-dir .tmp/snapshot --sync-payload fixtures/connectors/jira/incremental_sync.json --source-name jira`

## Exit Criteria

- snapshot store persists canonical documents and page index locally
- incremental refresh replaces matching document ids and updates manifest cursor state
- retrieval contracts remain unchanged for downstream search and citation consumers

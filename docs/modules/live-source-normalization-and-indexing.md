# Live Source Normalization And Indexing Module Contract

## Scope

Implement live Jira Server issue sync and live Confluence page sync without changing the canonical retrieval and citation contracts.

This module covers:

- authenticated live fetch from Jira Server and Confluence
- pagination and incremental cursor handling
- normalization of source payloads into canonical markdown-backed documents
- direct compatibility with page-level indexing, search, and citation inspection
- extraction of reusable normalization and retrieval seams for later skill packaging

This module does not cover:

- persistent storage
- hosted portal migration
- request-scoped identity ACL
- production parser replacement beyond the existing PDF adapter path

## Inputs

- Jira Server REST payloads from `/rest/api/2/search`
- Confluence REST payloads from `/rest/api/content`
- fixture sync snapshots for deterministic contract tests
- markdown, PDF, and connector-origin content that must be normalized into the canonical document schema
- allowed ACL policies used by retrieval

## Outputs

- canonical `jira` documents with:
  - normalized markdown body
  - provenance, ACL, metadata, comments, and attachments
- canonical `confluence` documents with:
  - normalized markdown body
  - provenance, ACL, metadata, and attachments
- reusable normalization seam in `services/ingest/normalizer.py`
- reusable retrieval seam in `services/retrieval/toolkit.py`
- page-index-compatible connector outputs that can flow into:
  - search
  - citation assembly
  - source inspection

## Dependencies

- canonical schema contract in `packages/schema/document-schema.json`
- Jira bug field mapping contract in `docs/jira-bug-field-mapping.md`
- Jira field alias contract in `packages/schema/jira-field-aliases.json`
- Confluence page mapping contract in `docs/confluence-page-mapping.md`
- retrieval and citation contracts in `services/retrieval/*`
- fixture compatibility tests for local deterministic validation
- CLI contract in `scripts/platform_cli.py`

## KPIs

- connector output schema completeness
- zero contract regressions in fixture-backed tests
- live connector output indexability rate
- citation compatibility rate for connector-origin documents
- normalization reuse coverage across markdown, PDF, Jira, and Confluence paths

## Implementation Steps

1. Lock the boundary.
   Keep retrieval, citation, and portal contracts unchanged. Only evolve source fetching and normalization seams.

2. Extract the reusable normalizer.
   Move document assembly concerns out of source-specific adapters into `services/ingest/normalizer.py`.
   Reuse this seam from markdown, PDF, Jira, and Confluence paths.

3. Extract the reusable retrieval seam.
   Add `services/retrieval/toolkit.py` as the stable entrypoint for:
   - snapshot loading
   - page-index building
   - document search
   - top-result citation assembly

4. Upgrade Jira from fixture loader to dual-path connector.
   Preserve fixture loading.
   Add authenticated live fetch, pagination, incremental cursor support, and markdown normalization.
   Preserve the bug-template field mapping in `docs/jira-bug-field-mapping.md`.
   Load the default field aliases from `packages/schema/jira-field-aliases.json`.

5. Upgrade Confluence from fixture loader to dual-path connector.
   Preserve fixture loading.
   Add authenticated live fetch, pagination, incremental cursor support, attachment handling, and storage-HTML-to-markdown normalization.
   Preserve the page mapping rules in `docs/confluence-page-mapping.md`.

6. Wire connectors into page index.
   Ensure connector-origin documents can flow directly into `build_page_index` and then into `search` and `citation` paths.

7. Expose boundaries at the CLI.
   Add `--live` connector mode and validate required arguments before any network attempt.

8. Freeze the seam for later skill extraction.
   Treat `services/ingest/normalizer.py` and `services/retrieval/toolkit.py` as the preferred skill-ready entrypoints.

## Boundary Rules

- Do not change the canonical document schema in this step.
- Do not add persistence in this step.
- Do not mix portal-specific shaping into connector normalization.
- Do not allow connector-specific payloads to bypass canonical normalization before indexing.
- Do not relax ACL filtering behavior to accommodate live sources.

## Validation

Validation for this module is split into three layers.

### 1. Structural validation

- `python -m compileall services scripts tests`
- fixture-backed connector tests remain the contract baseline

### 2. Behavioral validation

- fixture connector output must still satisfy old tests
- live connector mock tests must prove:
  - canonical document output
  - page-index compatibility
  - metadata and attachment propagation

### 3. Retrieval compatibility validation

- connector-origin documents must be indexable through `build_page_index`
- connector-origin documents must be retrievable through search
- citation and inspection contracts must remain unchanged for downstream consumers

## Current Validation Entry Points

- `python -m unittest tests.connectors.test_jira_sync tests.connectors.test_confluence_sync`
- `python -m unittest tests.connectors.test_live_connectors`
- `python -m unittest tests.connectors.test_jira_field_aliases tests.schema.test_jira_field_aliases_schema`
- `python -m unittest tests.retrieval.test_connector_page_index`
- `python -m unittest tests.ops.test_platform_cli`

## Exit Criteria

- live Jira and Confluence paths produce canonical documents
- fixture paths remain backward compatible
- connector-origin documents flow through page index and search without special cases
- skill-ready seams are documented and used by implementation code

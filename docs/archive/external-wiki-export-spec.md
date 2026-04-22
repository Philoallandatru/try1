# External Wiki Export Spec

## Purpose

This document defines a derived export layer that lets the current repository produce stable, machine-readable packages for an external wiki system.

The export layer exists to support downstream wiki construction without changing the repository truth model:

- canonical document remains the source of truth
- Markdown remains a readable projection
- PageIndex remains a retrieval projection
- external wiki artifacts remain derived outputs only

This export layer must not introduce a new truth-bearing schema and must not write back into canonical documents.

## Status

This capability is an integration-facing derived export surface. It is compatible with the current foundation roadmap, but it is not itself a replacement for the canonical document, Markdown, or PageIndex contracts.

## Non-Goals

This export layer does not perform:

- final project or topic classification
- wiki page synthesis such as index pages, conflict pages, or analysis pages
- operator-facing summarization as truth
- any write-back into Jira, Confluence, or canonical document storage
- any change to ACL, citation, provenance, or authority contracts
- section-level spec rewrite generation or section-anchor export as a stable contract

## Export Model

The export root represents one export batch and must contain:

- `manifest.json`
- `changes.json`
- `page_index.json`
- `documents/`

Recommended layout:

```text
<export-root>/
  manifest.json
  changes.json
  page_index.json
  documents/
    <source-type>/
      <document-id>/
        <version>/
          document.md
          metadata.json
```

Key rules:

- one canonical document produces one Markdown file
- one canonical document produces one metadata JSON file
- versions are preserved as separate directories
- re-export must not overwrite prior version directories
- `page_index.json` keeps the current artifact shape: `{"entries": [...]}`

Current boundary:

- export is document-level
- `sync-export` and related paths do not yet emit section-level manifests, per-section markdown, or section-link artifacts
- future section-level wiki generation should be introduced as an additive derived export layer, not by mutating the document-level contract

## Per-Document Markdown Output

`document.md` is the readable Markdown projection for one canonical document.

Requirements:

- content must remain a readable projection of the canonical document
- output must not inject LLM-authored summary or wiki explanation text
- title, source URI, and structure-derived sections remain allowed because they are already part of the projection path
- output path must be stable under `source_type/document_id/version`

## Per-Document Metadata Output

Each exported document must also produce `metadata.json`.

Minimum fields:

- `document_id`
- `source_type`
- `version`
- `title`
- `authority_level`
- `language`
- `provenance`
- `acl`
- `structure`
- `terminology`
- `exported_at`
- `markdown_path`
- `page_index_entry_count`

Recommended additional fields:

- `latest_for_document`
- `previous_versions`
- `source_snapshot`
- `content_hash`

Rules:

- metadata must preserve provenance, ACL, and structure fields from the canonical document contract
- metadata may include export-specific fields, but those fields must not redefine source truth
- metadata must be sufficient for an external wiki to decide naming, grouping, and incremental updates without reparsing the original source

## Batch Manifest Contract

`manifest.json` describes the export batch and the current latest pointers.

Minimum fields:

- `exported_at`
- `export_mode`
- `document_count`
- `source_type_counts`
- `latest_versions`
- `page_index_path`
- `documents`

Definitions:

- `source_type_counts` is a map of source type to count
- `latest_versions` is a map keyed by `document_id`, pointing to the latest exported version path
- `documents` is the batch file index for all exported document entries

Rules:

- manifest is the machine entrypoint for external wiki synchronization
- manifest must be readable without inspecting the document directory tree directly
- manifest must not replace `snapshot_store` manifests; it belongs only to the wiki export layer

## Change Log Contract

`changes.json` is the machine-readable delta feed for external wiki ingestion.

Minimum fields per entry:

- `exported_at`
- `change_type`
- `document_id`
- `version`
- `source_type`
- `paths`
- `previous_version`

Allowed `change_type` values:

- `new`
- `updated`
- `unchanged`

Rules:

- change tracking is export-batch scoped
- a new version of an existing `document_id` must be reported as `updated`
- first-time export of a `document_id` must be reported as `new`
- repeated export of the same version may be reported as `unchanged`

## CLI Surface

The preferred implementation path is to extend existing CLIs instead of introducing a parallel command set.

Expected behavior additions:

- `scripts/ingest/normalize_cli.py`
  - keep `--output-md` and `--output-page-index` compatibility
  - add export-directory support for per-document wiki-ready output
- `scripts/platform_cli.py sync-export`
  - add batch export-directory support for Jira/Confluence sync-driven wiki-ready output

Current implementation note:

- `normalize_cli.py` already supports `--output-md`, `--output-md-dir`, and `--output-page-index`
- `platform_cli.py sync-export` already supports document-level Markdown tree and PageIndex export
- section-level export remains future work

Service-layer factoring is allowed and recommended if export-path assembly, manifest generation, and change-log generation would otherwise be duplicated.

## Storage Boundary

This export layer is separate from snapshot persistence.

Snapshot persistence continues to own:

- `manifest.json`
- `documents.json`
- `page_index.json`

under the snapshot directory only.

The wiki export layer owns:

- export-batch `manifest.json`
- export-batch `changes.json`
- per-document `document.md`
- per-document `metadata.json`

These responsibilities must remain separate.

## Validation Requirements

Validation must cover:

- single-source export for `markdown`, `docx`, `xlsx`, `pptx`, and `pdf`
- sync-export batch output for Jira and Confluence
- version-history preservation for repeated export of one `document_id`
- correctness of `manifest.json` latest-version pointers
- correctness of `changes.json` new/updated/unchanged classification
- preservation of current `--output-md` and `--output-page-index` behavior
- continued traceability from exported Markdown back to citation and source inspection contracts

Current non-goal for validation:

- section-level spec rewrite exports are not part of the current compatibility surface

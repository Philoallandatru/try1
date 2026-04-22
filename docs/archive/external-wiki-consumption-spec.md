# External Wiki Consumption Spec

## Purpose

This document defines how an external wiki system consumes export packages from the current repository.

The external wiki is a derived knowledge layer. It organizes, links, and accumulates knowledge, but it does not replace canonical source truth.

## Source of Truth Boundary

The external wiki must preserve the following model:

- canonical document is the source of truth
- Markdown is a readable source projection
- PageIndex is the retrieval projection
- citations and source inspection are the evidence trace
- external wiki pages are derived organizational artifacts

The external wiki must never treat a synthesized page as a replacement for canonical source truth.

## Inputs

The external wiki may consume only stable outputs from this repository:

- per-document `document.md`
- per-document `metadata.json`
- export-batch `manifest.json`
- export-batch `changes.json`
- `page_index.json`
- retrieval search, citation, and source inspection results

It should not consume raw Jira payloads, raw Confluence payloads, or original binary source files directly when the export package is available.

Current boundary:

- the implemented export/consumption path is document-level
- per-section derived wiki pages are not yet a stable repository export contract
- if a downstream wiki wants section-level explanation pages today, it must build them as its own derived layer on top of document-level exports and repository retrieval surfaces

## Consumption Responsibilities

The external wiki is responsible for:

- project and topic classification
- page naming and placement
- wiki index generation
- log generation
- topic-page generation
- analysis-page generation
- conflict-page generation
- LLM maintenance rules for accumulated knowledge pages

The repository export layer is not responsible for any of the above.

## Expected Wiki Structure

Recommended external layout:

```text
raw_exports/
sources/
projects/
topics/
analysis/
conflicts/
index.md
log.md
AGENTS.md
```

Recommended role of each area:

- `raw_exports/`
  - imported export packages or synchronized export roots
- `sources/`
  - one source-summary page per exported canonical document
- `projects/`
  - project landing pages and current-view aggregation
- `topics/`
  - cross-project thematic pages
- `analysis/`
  - long-lived question outputs, comparisons, and derived reports
- `conflicts/`
  - explicit new-vs-old claim divergence records
- `index.md`
  - human-readable top-level navigation
- `log.md`
  - append-only operational timeline

## Consumption Workflow

### Ingest

For each export batch:

1. Read `manifest.json`
2. Read `changes.json`
3. Process changed documents first
4. Load the referenced `metadata.json` and `document.md`
5. Create or update source-summary pages
6. Link source-summary pages into project and topic structures
7. Create conflict records if newly exported material contradicts existing derived pages
8. Append a machine-consumable and human-readable entry to `log.md`

### Query

When answering a question:

1. search the wiki's existing project/topic/analysis pages
2. fall back to source-summary pages when necessary
3. fall back to repository retrieval and citation surfaces when evidence needs to be refreshed
4. preserve citations or evidence pointers in the answer
5. optionally persist durable answers as new derived analysis pages

Current recommendation:

- use document-level export packages as the primary synchronization unit
- use repository retrieval/citation surfaces when section-level evidence must be refreshed on demand
- do not assume the repository currently emits section-anchor manifests or section-level rewrite pages

### Lint

Periodic health checks should detect:

- orphan source-summary pages
- missing project or topic links
- stale derived pages superseded by newer exports
- conflict candidates not yet recorded
- derived pages lacking evidence pointers

## Source Summary Page Contract

Each source-summary page should be built from one exported document.

It should retain at least:

- title
- source type
- document ID
- version
- authority level
- source URI
- key structure anchors
- related projects or topics
- links back to the export package or source evidence

This page may contain distilled summary text, but it must clearly remain a derived page.

## Derived Page Metadata

Recommended frontmatter for derived external wiki pages:

- `title`
- `kind`
- `project`
- `source_type`
- `document_id`
- `version`
- `source_uri`
- `authority_level`
- `derived_from`
- `status`
- `tags`

Rules:

- all derived pages must include `derived_from`
- analysis and topic pages may reference multiple source documents
- conflict pages must record both old and new evidence sources
- if evidence is unresolved, page `status` should reflect that explicitly

For future section-level derived pages, keep the same derived-page discipline and add explicit section traceability such as:

- `section`
- `clause`
- `page`
- `section_anchor_id`

These fields are not part of the stable export contract yet.

## Version Handling

The external wiki must preserve version history semantics from the export layer.

Rules:

- a new version does not erase historical source-summary pages automatically
- current-view pages may point to the latest version, but historical pages remain accessible
- conflict detection should compare new derived claims against prior derived pages and source summaries, not mutate old source records silently

## Citation and Traceability

Any durable analysis or topic page must be traceable back to repository evidence.

Minimum traceability path:

- external wiki page
- `derived_from`
- `document_id` and `version`
- citation or source inspection reference

The external wiki may add human-friendly synthesis, but must not sever the path back to evidence-bearing repository outputs.

## Compatibility Expectations

The external wiki should assume:

- JSON is the machine contract
- Markdown is the readable document body
- the repository may extend metadata fields over time, but must preserve the core fields required by this spec
- final classification logic remains outside the repository export layer

## Validation Requirements

Validation should cover:

- ingestion of single-document export packages
- ingestion of batch export packages driven by `changes.json`
- correct creation of source-summary pages from `metadata.json` and `document.md`
- correct handling of new document versions without destructive overwrite
- traceability from derived pages back to repository evidence
- conflict-page generation when derived conclusions diverge across versions or sources

Current non-goal for validation:

- section-level derived wiki generation is not yet required for export/consumption compatibility

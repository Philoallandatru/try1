# Confluence Page Mapping

This repository normalizes Confluence page payloads into canonical markdown documents with stable retrieval metadata.

## Source Fields

- `id` -> `document_id`
- `title` -> top-level markdown heading and canonical title
- `space.key` or `space` -> `metadata.space`
- `version.number` or `version` -> canonical document version string
- `version.when` -> `ingested_at`
- `body.storage.value` -> markdown body content
- `attachments` or `children.attachment.results` -> attachment list and attachment markdown block

## Markdown Rules

- Page title is emitted as `# <title>`.
- `body.storage.value` is converted with a narrow HTML-to-markdown pass:
  - `<h1>` to `<h6>` become markdown headings
  - `<p>` becomes paragraph text
  - `<li>` becomes `-` list items
  - `<br>` becomes a line break
- Remaining tags are stripped after the supported transforms run.
- If body content is empty, the connector emits `No body.`
- If attachments exist, the connector appends `## Attachments` followed by one markdown list item per attachment.

## Attachment Rules

- Preferred attachment source is `attachments`.
- If `attachments` is absent, the connector falls back to `children.attachment.results`.
- Attachment markdown format is:
  - `- [name](download) (media_type)` when `_links.download` exists
  - `- name (media_type)` otherwise
- Attachment count is stored in `metadata.attachment_count`.

## Metadata Rules

- `metadata.space` stores the Confluence space key.
- `metadata.incremental` is `true` only when the sync was cursor-driven.
- `attachments` remain available on the canonical document for downstream indexing or inspection.

## Validation Coverage

- Fixture sync tests assert `space`, `version`, `ingested_at`, attachment normalization, and body-to-markdown behavior.
- Live connector tests assert the same normalization contract against mocked Confluence API payloads.

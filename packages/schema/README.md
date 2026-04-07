# Schema Package

This package defines the canonical normalized knowledge document model used across ingestion, retrieval, evaluation, and portal workflows.

## Contract Goals

- Preserve provenance, ACL metadata, structure metadata, and terminology metadata.
- Treat pages, sections, clauses, tables, figures, worksheets, and slides as first-class objects.
- Support multilingual evidence and cross-language retrieval.

## Core Model

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

## Additional Contracts

- `document-schema.json`: canonical normalized knowledge document
- `ops-profile-schema.json`: profile contract for `scripts/platform_cli.py multi-sync-health`
- `jira-field-aliases.json`: default alias contract for Jira bug-template field normalization

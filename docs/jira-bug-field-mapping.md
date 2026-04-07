# Jira Bug Field Mapping

## Purpose

Define how Jira Server bug-template fields are normalized into canonical markdown and metadata during live and fixture sync.

## Canonical Field Labels

The Jira connector currently promotes these fields into `document["metadata"]["issue_fields"]` and the `## Issue Fields` markdown section:

- `Type`
- `Labels`
- `Priority`
- `Component`
- `Affects Version/s`
- `Resolution`
- `Status`
- `Fix Version/s`
- `Severity`
- `Report department`
- `Root Cause`
- `How to fix`
- `Action`
- `Frequency`
- `FailRunTime`

## Matching Rules

The connector resolves each canonical label using this precedence:

1. direct field key match in `issue["fields"]`
2. direct top-level key match in the fixture issue object
3. Jira `expand=names` display-name match for `customfield_*` keys

The default alias contract is stored in:

- `packages/schema/jira-field-aliases.json`

This lets live Jira Server payloads map custom fields such as:

- `customfield_10001 -> Root Cause`
- `customfield_10002 -> How to fix`
- `customfield_10003 -> Report department`

## Output Rules

- all matched fields are written into `metadata.issue_fields`
- all matched fields are rendered into the markdown `## Issue Fields` section
- `Root Cause`, `How to fix`, and `Action` also get dedicated markdown sections when present
- comments remain preserved under `## Comments`

## Boundary

- this mapping does not change the canonical document schema
- this mapping does not introduce Jira write-back
- this mapping does not resolve unknown custom fields automatically without either:
  - a direct key alias
  - or a Jira `names` mapping from live search

## Validation

- `python -m unittest tests.connectors.test_jira_sync`
- `python -m unittest tests.connectors.test_live_connectors`

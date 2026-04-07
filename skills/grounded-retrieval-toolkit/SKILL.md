---
name: grounded-retrieval-toolkit
description: Build page indexes, run ACL-safe search, and assemble citations from a normalized corpus snapshot. Use when a task needs grounded retrieval or citation output from canonical document JSON without adding storage or portal logic.
---

# Grounded Retrieval Toolkit

Use this skill when the task is to operate on an existing normalized corpus and produce page-index entries, search results, or top-result citation payloads.

## Use When

- Build page-index entries from a canonical document snapshot
- Search a normalized corpus with ACL filtering
- Produce citation and source inspection payloads from the top grounded match
- Verify that connector- or ingest-origin documents are retrieval compatible

## Do Not Use When

- The task is to normalize raw documents before they become canonical JSON
- The task is to fetch live source data
- The task is to add persistence, reranking infrastructure, or portal endpoints

## Entry Point

Primary command:

```bash
python scripts/retrieval/toolkit_cli.py <command> ...
```

Supported commands:

- `index --corpus <path>`
- `search "<query>" --corpus <path> [--policies ...]`
- `citation "<query>" --corpus <path> [--policies ...]`

## Workflow

1. Confirm the input is a canonical snapshot with a top-level `documents` array.
2. Use `index` when the task is to inspect or validate page-level entries.
3. Use `search` when the task is to rank grounded evidence sets.
4. Use `citation` when the task needs the top-result citation and inspection payload.
5. Preserve ACL policy inputs and do not weaken filtering before ranking.

## Implementation References

- `services/retrieval/toolkit.py`
- `services/retrieval/indexing/page_index.py`
- `services/retrieval/search/hybrid_search.py`
- `services/retrieval/citations/assembler.py`
- `scripts/retrieval/toolkit_cli.py`

## Boundaries

- Keep ACL filtering before ordering.
- Keep authority weighting inside retrieval logic, not in the caller.
- Do not reshape the citation contract for portal convenience in this layer.
- Do not use this skill as a substitute for normalization of raw source files.

## Validation

Recommended checks:

```bash
python scripts/retrieval/toolkit_cli.py index --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py search "flush command" --corpus fixtures/retrieval/pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py citation "flush command" --corpus fixtures/retrieval/pageindex_corpus.json
python -m unittest tests.ops.test_skill_ready_clis tests.retrieval.test_connector_page_index
```

## Output Expectation

- `index` returns JSON with `entries`
- `search` returns ranked page entries
- `citation` returns:
  - `citation`
  - `inspection`

# SSD Knowledge Platform Agent Manual

## 1. Project Goal

This repository implements the Phase 1 foundation of an internal SSD knowledge platform.

Phase 1 is not a general AI assistant. It is a retrieval and grounded Q&A substrate for:

- specifications
- firmware and ASIC design documents
- product requirements
- Jira issues
- Confluence pages

The system must preserve:

- evidence fidelity
- auditable citations
- correct ACL filtering
- reproducible evaluation

## 2. Scope Boundary

### In Scope for Phase 1

- ingestion for `md`, `pdf`, `docx`, `xlsx`, `pptx`, Jira, and Confluence
- canonical document normalization with provenance, ACL, structure, and terminology metadata
- page-index-first retrieval
- citation assembly and source inspection
- evaluation and rollout gates
- local skill-ready entrypoints for normalization and retrieval
- local snapshot persistence and incremental refresh

### Explicitly Out of Scope for This Phase

- PR review automation
- testcase optimization
- product design optimization
- Jira or Confluence write-back
- hosted portal migration
- database-backed storage
- request-scoped identity ACL

## 3. Implementation Priorities

Work should still follow this order:

1. contracts and gates
2. schema and ACL
3. ingestion and normalization
4. retrieval and citation
5. evaluation
6. portal
7. ops
8. deferred modules

Do not bypass:

- ACL filtering
- citation fidelity
- retrieval evaluation gates

## 4. Current Stable Reusable Seams

### Normalization

- `services/ingest/normalizer.py`
- `scripts/ingest/normalize_cli.py`

This is the preferred reusable seam for:

- markdown
- PDF
- fixture-backed Jira sync payloads
- fixture-backed Confluence sync payloads

### Retrieval

- `services/retrieval/toolkit.py`
- `scripts/retrieval/toolkit_cli.py`

This is the preferred reusable seam for:

- page index building
- ACL-safe search
- citation assembly
- source inspection

### Local Snapshot Persistence

- `services/retrieval/persistence/snapshot_store.py`
- `scripts/retrieval/snapshot_cli.py`

This is the preferred seam for:

- local recoverable snapshots
- manifest tracking
- incremental refresh by `document_id`

## 5. Local Skills

Repository-local skills now exist under `skills/`:

- `skills/offline-document-normalizer/SKILL.md`
- `skills/grounded-retrieval-toolkit/SKILL.md`

These skills wrap stable CLI entrypoints and should be preferred over ad hoc scripting when the task matches their scope.

## 6. Execution Rules

### Validation First

Every meaningful change must keep a validation path.

Preferred validation layers:

- unit tests
- contract checks
- CLI smoke checks
- compile checks

### Contract Stability

Do not change canonical document shape, citation shape, or retrieval contract shape casually.

If a new capability is needed, adapt at the edges first:

- connector normalization
- local persistence
- skill-ready wrappers

### Evidence

Store meaningful execution evidence under `.sisyphus/evidence/` when the task is large enough to require recorded artifacts.

### Self-Loop Entry Rule

When the user says `continue`, `继续`, or otherwise delegates the next step without narrowing scope, enter a bounded self-loop.

Each loop iteration must follow this sequence:

1. restate the current target module or gap
2. check the phase boundary before changing code
3. implement one coherent increment
4. run the smallest validation set that proves the increment
5. record what changed, what passed, and what remains
6. choose the next highest-leverage in-scope increment

Do not enter an open-ended loop across multiple deferred modules at once.

### Self-Loop Stop Conditions

Exit the loop and ask for direction when any of these becomes true:

- the next step crosses the current phase boundary
- the next step requires a product or architecture decision not already documented
- the next step weakens citation, ACL, page index, or contract guarantees
- validation cannot be completed with available local tooling
- the remaining work is clearly in an explicit out-of-scope area

### Self-Loop Reporting Contract

At the end of each loop iteration, report only:

- the increment completed
- the validation actually run
- the next recommended in-scope step

Never claim the loop is complete without fresh validation in the same iteration.

## 7. Architecture Hard Constraints

- retrieval must remain PageIndex-first
- ACL filtering must happen before ranking and answer assembly
- citation must resolve to `document + version + page + section/clause` where available
- ranking default remains `canonical > supporting > contextual`
- structure metadata such as page, clause, worksheet, slide, table, and figure must remain first-class

## 8. Snapshot Rules

Local snapshot persistence is file-backed in this phase.

Persist only:

- `manifest.json`
- `documents.json`
- `page_index.json`

Refresh rules:

- normalize raw connector payloads before refresh when needed
- merge by stable `document_id`
- rebuild page index after every create or refresh

Do not add database abstractions here yet.

## 9. Jira Issue Type Routing

When adding Jira analysis or sync/export behavior, preserve deterministic routing based on Jira `issuetype`.

Store these fields under Jira document metadata:

- `issue_type_raw`: original Jira issue type such as `FW Bug`, `DAS/PRD`, or `Release`
- `issue_family`: stable coarse family for downstream routing
- `issue_route`: specific default analysis route

Default issue families:

- `defect`: `FW Bug`, `HW Bug`, `Test Bug`, `Misc Bug`
- `requirement`: `DAS/PRD`, `MRD`
- `requirement_change`: `Requirement Change`
- `change_control`: `Component Change`
- `delivery`: `Epic`, `Story`, `Task`
- `release`: `Release`
- `unknown`: any unmapped issue type

Routing rules:

- daily Jira reports may include all issue families
- root-cause analysis must only consume `issue_family == "defect"`
- PRD/MRD analysis must only consume `issue_family == "requirement"`
- change-impact analysis should consume `requirement_change` and `change_control`
- delivery and release summaries must not be forced through bug RCA prompts

Keep Jira Markdown generation loose. Render available title, metadata, issue fields, description, comments, and attachments. Bug-only fields such as `Root Cause`, `How to fix`, and `Action` are optional and must not be required for PRD/MRD, release, or delivery issues.

The planned implementation details live in `docs/jira-issue-type-routing-plan.md`.

## 10. Recommended Validation Entry Points

### Contracts and Gates

- `python scripts/gates/check_adr_contract.py`
- `python scripts/gates/check_repo_shape.py`
- `python scripts/gates/check_module_contracts.py`

### Unified Platform CLI

- `python scripts/platform_cli.py eval`
- `python scripts/platform_cli.py gate`
- `python scripts/platform_cli.py ops-health`

### Skill-Ready CLIs

- `python scripts/ingest/normalize_cli.py markdown fixtures/corpus/markdown/sample.md`
- `python scripts/ingest/normalize_cli.py jira-sync fixtures/connectors/jira/full_sync.json`
- `python scripts/retrieval/toolkit_cli.py search "flush command" --corpus fixtures/retrieval/pageindex_corpus.json`
- `python scripts/retrieval/toolkit_cli.py citation "flush command" --corpus fixtures/retrieval/pageindex_corpus.json`

### Snapshot CLI

- `python scripts/retrieval/snapshot_cli.py create --snapshot-dir .tmp/snapshot --corpus fixtures/retrieval/pageindex_corpus.json`
- `python scripts/retrieval/snapshot_cli.py refresh --snapshot-dir .tmp/snapshot --sync-payload fixtures/connectors/jira/incremental_sync.json --source-name jira`
- `python scripts/retrieval/snapshot_cli.py show --snapshot-dir .tmp/snapshot`

### Test Suites

- `python -m unittest discover -s tests -t . -p "test_*.py" -v`
- `python -m compileall skills docs scripts services tests`

## 11. Handoff Template

For substantial work, summarize in this order:

- goal
- changed artifacts
- validation run
- open gaps
- next recommended step

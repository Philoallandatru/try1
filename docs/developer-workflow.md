# Developer Workflow

## Purpose

This document defines the expected day-to-day workflow for extending the SSD knowledge platform foundation without breaking the repository contracts.

## 1. Start with the Contract

Before implementing a new slice:

1. identify which task or phase it belongs to
2. locate the governing contract in:
   - `agent.md`
   - `spec.md`
   - `todo.md`
   - `docs/adr/*`
3. confirm whether the change affects:
   - schema
   - ACL
   - retrieval
   - citation
   - evaluation
   - ops
   - portal

If the change alters one of those contracts, update the relevant contract doc first or in the same slice.

## 2. Write or Update a Failing Test First

Use the repository’s current testing style:

- `tests/ingest/*` for adapters and source parsing
- `tests/connectors/*` for sync behavior
- `tests/retrieval/*` for search and citation
- `tests/eval/*` for metrics and harnesses
- `tests/ops/*` for freshness, backup/restore, and CLI utilities
- `tests/gates/*` for repo and release guards
- `tests/portal/*` for operator-facing state and UI contracts

Rules:

- add a happy-path check
- add a failure-path check where the task requires gating behavior
- keep fixture-backed tests deterministic

## 3. Implement the Smallest Vertical Slice

Preferred order:

1. contract or fixture
2. minimal implementation
3. validation command
4. evidence update

Do not:

- change unrelated layers in the same slice
- add deferred features into Phase 1 runtime code
- bypass ACL or citation rules for convenience

## 4. Run Validation

Core commands:

```bash
python scripts/gates/check_adr_contract.py
python scripts/gates/check_repo_shape.py
python scripts/gates/check_module_contracts.py
python scripts/eval/run_recall_eval.py --dataset eval/gold_queries.yaml
python scripts/gates/run_phase1_gate.py
python -m unittest discover -s tests -t . -p "test_*.py" -v
```

Unified CLI alternatives:

```bash
python scripts/platform_cli.py eval
python scripts/platform_cli.py gate
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py citation "flush command"
```

## 5. Record Evidence

All major work should update:

- `.sisyphus/evidence/`

Minimum evidence expectations:

- command run
- happy-path result
- failure-path result if applicable
- summary of outputs
- reusable components identified

## 6. Update User-Facing or Maintainer Docs

When behavior changes, check whether to update:

- `README.md`
- `docs/architecture-overview.md`
- `docs/implementation-status.md`
- `docs/cli-reference.md`
- `docs/api-contracts.md`
- `docs/live-integration-plan.md`
- `docs/skill-extraction-plan.md`

## 7. Preserve Skill-Ready Boundaries

When adding new logic:

- keep reusable behavior in `services/*`, `packages/*`, or `scripts/*`
- keep project-specific policy outside generic helpers where possible
- prefer CLI-friendly JSON outputs for reusable components

If a component becomes broadly reusable, add or update:

- `docs/modules/skill-ready-components.md`
- `docs/skill-extraction-plan.md`

## 8. Definition of Done

A slice is done only when:

- tests pass
- gates still pass
- evidence is updated
- relevant docs are updated
- no Phase 1 scope boundary was violated


# Implementation Status

## Summary

The repository currently covers the full planned Task 1 to Task 15 skeleton for Phase 1 with a minimal runnable implementation.

## Completed

- Task 1: ADR contract set
- Task 2: monorepo skeleton
- Task 3: schema and terminology contract
- Task 4: ACL contract
- Task 5: Markdown and Office preprocessing
- Task 6: PDF extraction and fidelity checks
- Task 7: Jira connector
- Task 8: Confluence connector
- Task 9: PageIndex-first hybrid retrieval
- Task 10: citation assembly and source inspection
- Task 11: evaluation harness and gold set runner
- Task 12: internal ops portal MVP
- Task 13: ops freshness and backup/restore checks
- Task 14: rollout gate automation
- Task 15: deferred module contracts

## Validation Status

Current validation entrypoints:

- `python scripts/gates/check_adr_contract.py`
- `python scripts/gates/check_repo_shape.py`
- `python scripts/gates/check_module_contracts.py`
- `python scripts/eval/run_recall_eval.py --dataset eval/gold_queries.yaml`
- `python scripts/gates/run_phase1_gate.py`
- `python -m unittest discover -s tests -t . -p "test_*.py" -v`

## Current Quality Snapshot

- `recall@10 = 1.0`
- `ndcg@10 = 1.0`
- `citation_fidelity = 1.0`
- rollout gate = pass

## Remaining Gaps to Production

- Replace fixture-driven connectors with live Jira / Confluence integrations.
- Replace minimal offline PDF parsing with the target production parser stack.
- Upgrade the portal from static assets to a hosted internal service.
- Add persistent storage and real indexing backends.
- Add real authentication and request-scoped ACL identity handling.

## Reusable Components

- schema contract validators
- ACL contract validators
- document normalization adapters
- PDF fidelity checker
- PageIndex builder
- hybrid retrieval runner
- citation formatter
- eval harness
- rollout gate runner


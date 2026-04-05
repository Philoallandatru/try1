# Foundation and Ingest Phase Evidence

## Scope

- Task 1 ADR contract
- Task 2 repository skeleton
- Task 3 schema contract
- Task 4 ACL contract
- Task 5 markdown and office preprocessing
- Task 6 PDF structural extraction
- Task 7 Jira connector
- Task 8 Confluence connector
- Task 9 PageIndex-first hybrid retrieval
- Task 10 Citation assembly and source inspection
- Task 11 Retrieval evaluation harness
- Task 12 Internal operations portal MVP
- Task 13 Observability, freshness, and runbooks
- Task 14 Rollout gate automation
- Task 15 Deferred module contracts

## Happy Path Validations

- `python scripts/gates/check_adr_contract.py`
  - Result: passed
- `python scripts/gates/check_repo_shape.py`
  - Result: passed
- `python -m unittest tests.ingest.test_markdown_adapter tests.ingest.test_office_adapters -v`
  - Result: passed
- `python -m unittest tests.ingest.test_pdf_extraction tests.ingest.test_pdf_fidelity tests.connectors.test_jira_sync tests.connectors.test_confluence_sync -v`
  - Result: passed
- `python -m unittest tests.retrieval.test_hybrid_search tests.retrieval.test_acl_filtered_search -v`
  - Result: passed
- `python -m unittest tests.retrieval.test_citation_contract -v`
  - Result: passed
- `python -m unittest tests.eval.test_eval_metrics -v`
  - Result: passed
- `python scripts/eval/run_recall_eval.py --dataset eval/gold_queries.yaml`
  - Result: passed
- `python -m unittest tests.portal.test_portal_state tests.portal.test_portal_ui_contract -v`
  - Result: passed
- `python -m unittest tests.ops.test_ops_health -v`
  - Result: passed
- `python -m unittest tests.gates.test_phase1_gate -v`
  - Result: passed
- `python scripts/gates/run_phase1_gate.py`
  - Result: passed
- `python -m unittest tests.gates.test_module_contracts -v`
  - Result: passed
- `python scripts/gates/check_module_contracts.py`
  - Result: passed
- `python -m unittest discover -s tests -t . -p "test_*.py" -v`
  - Result: passed

## Failure Path Notes

- Initial `unittest discover` run returned `NO TESTS RAN` before package discovery markers were added under `tests/`.
- Resolution: added minimal `__init__.py` files under `tests/` package boundaries.

## Outputs

- ADR set created under `docs/adr/`
- Repo skeleton and placeholder boundaries created
- Canonical schema contract added
- ACL propagation contract added
- Markdown adapter implemented
- Minimal OOXML office adapters implemented for `docx`, `xlsx`, and `pptx`
- Minimal PDF extraction adapter implemented with page, section, clause, table, and figure preservation
- Jira connector implemented for full and incremental sync fixtures
- Confluence connector implemented for page sync, attachment metadata, and incremental sync fixtures
- PageIndex-first retrieval implemented with page-level indexing, terminology-assisted hybrid search, authority-aware ranking, and ACL pre-filtering
- Citation assembly implemented with `document`, `version`, `page`, `section`, `clause`, `table_id`, and `figure_id` fields
- Source inspection payload implemented for operator drilldown
- Eval metrics implemented for recall, nDCG, and citation fidelity
- Gold-set dataset implemented with clause, field, table, version, terminology, cross-language, and abbreviation coverage
- Eval runner implemented with healthy-pass and degraded-fail behavior
- Portal MVP implemented with ingestion status, corpus inventory, search workspace, evaluation health, and citation inspection views
- Static portal state generation implemented for direct UI consumption
- Ops health reporting implemented for freshness and backup/restore validation
- Runbooks added for freshness monitoring, backup/restore, and Phase 1 rollout
- Rollout gate implemented with healthy-pass and degraded-fail behavior
- Deferred module contracts added for product design optimization, testcase optimization, wiki summarization intelligence, and PR review intelligence

## Reusable Skill Candidates

- Schema contract validator
- ACL contract validator
- OOXML normalization helpers
- Repo shape gate
- PDF fidelity checker
- Connector sync fixture loaders
- PageIndex builder
- Hybrid retrieval runner
- Citation contract formatter
- Source inspection payload builder
- Eval metric library
- Gold-set runner
- Portal state builder
- Static ops portal shell
- Ops health snapshot builder
- Rollout gate runner
- Deferred module contract validator

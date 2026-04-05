# SSD Knowledge Platform Execution TODO

## 使用方式

本文件按 4 个阶段组织执行工作，并把原始 15 个任务映射到各阶段中。阅读顺序应为：

1. 先看阶段目标与完成标准
2. 再看每个阶段的输入、输出、验证与阻塞项
3. 最后下钻到映射任务执行具体 packet

每个阶段都使用统一模板：

- Goal
- Mapped Tasks
- Inputs
- Outputs
- Validation
- Parallelism
- Blockers
- Commit Boundaries

建议每个阶段执行完成后，再额外补充：

- Acceptance Checklist
- Deliverable Template
- Handoff Notes

---

## 阶段 1：Contract and Foundation

### Goal

固化产品、仓库、schema、ACL 四个基础合同，建立后续实现必须遵守的边界、验证与 gate。

### Mapped Tasks

- Task 1 Freeze Phase 1 Product Contract
- Task 2 Bootstrap Repository Skeleton
- Task 3 Define Canonical Schema and Terminology Contract
- Task 4 Define ACL Propagation Contract

### Inputs

- Phase 1 scope and non-goals
- Source authority model
- Quality thresholds
- Planned monorepo shape

### Outputs

- ADR contract set
- Repository skeleton
- Canonical schema contract
- Terminology contract
- ACL propagation contract
- 对应 tests 和 validation scripts

### Validation

- ADR tests and contract checker pass
- Repo shape tests and smoke gate pass
- Schema fixture tests pass
- ACL contract tests pass

### Parallelism

- Task 2 can start after Task 1 begins stabilizing.
- Task 3 and Task 4 can run in parallel after Task 1.

### Blockers

- 产品范围未冻结
- 权威性模型未定
- schema 与 ACL 边界不清晰

### Commit Boundaries

- `docs(adr): freeze phase-1 kb retrieval contract`
- `chore(repo): bootstrap monorepo skeleton`
- `feat(schema): define canonical knowledge document model`
- `feat(security): add acl model and enforcement contracts`

### Completion Criteria

- ADR、repo shape、schema、ACL 四组测试和脚本校验均通过。

### Acceptance Checklist

- Scope、authority、schema、ACL 四类合同均已冻结。
- 所有合同都有对应 test 或 gate。
- 目录骨架与 contract boundary 对齐。
- 后续阶段需要的输入名称、位置、边界已清晰。

### Deliverable Template

- Contracts created or updated
- Validation scripts added
- Test suites added
- Evidence locations recorded
- Next-stage prerequisites listed

---

## 阶段 2：Ingestion Backbone

### Goal

打通所有 Phase 1 必需数据源的 ingestion path，并统一进入 normalized document schema，同时保留结构与语言保真。

### Mapped Tasks

- Task 5 Markdown and Office Preprocessing
- Task 6 PDF Structural Extraction and Fidelity Checks
- Task 7 Jira Connector
- Task 8 Confluence Connector

### Inputs

- Canonical schema contract
- ACL propagation contract
- Terminology contract
- Fixture strategy for corpus and connectors

### Outputs

- Markdown adapter
- Office adapters for `docx`、`xlsx`、`pptx`
- PDF structural extraction path
- PDF fidelity checks
- Jira connector
- Confluence connector
- Source-family fixtures and tests

### Validation

- Markdown adapter tests pass
- Office adapter tests pass
- PDF extraction tests pass
- PDF fidelity tests pass
- Jira full sync and incremental sync tests pass
- Confluence page sync, attachment metadata, and incremental sync tests pass

### Parallelism

- Task 5 and Task 6 can run in parallel after schema and ACL contracts stabilize.
- Task 7 and Task 8 can run in parallel after connector contracts stabilize.

### Blockers

- Schema fields for provenance, structure, ACL, language not frozen
- PDF parser route not chosen
- Connector metadata and version marker contracts not defined

### Commit Boundaries

- `feat(ingest): add markdown and office preprocessing pipeline`
- `feat(ingest): add pdf structural extraction pipeline`
- `feat(connectors): add jira ingestion connector`
- `feat(connectors): add confluence ingestion connector`

### Completion Criteria

- 所有 source family 至少有 happy-path 和 failure-path fixture。
- PDF fidelity、connector incremental sync 均被验证。

### Acceptance Checklist

- `md`、`pdf`、`docx`、`xlsx`、`pptx`、Jira、Confluence 全部有 ingestion path。
- 摄取结果可进入统一 normalized schema。
- PDF 与 Office 的结构对象没有被扁平化丢失。
- Connector 支持版本或增量同步语义。

### Deliverable Template

- Adapters or connectors implemented
- Fixture corpus added
- Happy-path evidence recorded
- Failure-path evidence recorded
- Reusable normalization interfaces noted

---

## 阶段 3：Retrieval and Evaluation Core

### Goal

构建 ACL-safe、authority-aware、citation-complete 的检索基础，并通过 gold-set 和指标门槛把质量固化为 release gate。

### Mapped Tasks

- Task 9 PageIndex-first Hybrid Retrieval
- Task 10 Citation Assembly and Source Inspection
- Task 11 Evaluation Harness and Gold-Set Runner

### Inputs

- Normalized corpus from ingestion layer
- Authority model
- ACL contract
- Citation requirements
- Evaluation threshold definitions

### Outputs

- PageIndex-first indexing
- Hybrid retrieval
- ACL pre-rerank filtering
- Authority-aware ranking
- Citation assembly layer
- Source inspection contract
- Gold-set dataset
- Eval service helpers
- Recall and regression runner

### Validation

- Hybrid search tests pass
- ACL-filtered retrieval tests pass
- Citation contract tests pass
- Eval metric and degraded-config tests pass
- Eval runner succeeds on `eval/gold_queries.yaml`

### Parallelism

- Citation assembly can start once retrieval result shape stabilizes.
- Eval harness should evolve close to retrieval work to catch regressions early.

### Blockers

- Ingestion outputs not yet stable
- Citation payload shape unresolved
- Cross-language retrieval assumptions untested

### Commit Boundaries

- `feat(retrieval): add pageindex hybrid indexing and search`
- `feat(retrieval): add citation assembly and source inspection`
- `feat(eval): add retrieval gold-set and regression harness`

### Completion Criteria

- hybrid retrieval、ACL filter、citation contract、eval runner 全部通过。
- 关键指标达到既定门槛。

### Acceptance Checklist

- ACL pre-rerank filtering 已落实。
- 权威排序默认遵循 `canonical > supporting > contextual`。
- Citation payload 字段完整。
- Gold set 与门槛脚本都可执行。
- 至少一个 degraded-config failure case 已被验证。

### Deliverable Template

- Index and search artifacts
- Citation contract artifacts
- Eval datasets and runners
- Metric snapshots
- Skillization candidates promoted to backlog

---

## 阶段 4：Operator Surface and Operationalization

### Goal

提供内部操作入口、运维可观测性、上线门禁和 deferred module 合同，为 pilot 与后续 skill 化、智能模块演进建立交付边界。

### Mapped Tasks

- Task 12 Internal Operations Portal MVP
- Task 13 Observability, Freshness Checks, and Runbooks
- Task 14 Rollout Gate Automation
- Task 15 Deferred Module Contracts

### Inputs

- Stable retrieval and citation contracts
- Eval outputs and thresholds
- Ingestion freshness requirements
- Operational recovery expectations

### Outputs

- Internal operations portal MVP
- Ingestion status and corpus inventory views
- Search and citation inspection flow
- Observability signals
- Freshness checks
- Backup and restore runbooks
- Rollout gate automation
- Deferred module contract docs

### Validation

- Portal smoke tests pass
- Search and citation drilldown E2E passes
- Ops tests for freshness and backup-restore pass
- Phase 1 rollout gate tests pass
- Module contract completeness tests pass

### Parallelism

- Portal work should start only when retrieval and citation contracts are stable enough.
- Task 15 can proceed after Task 2 and Task 14 and does not block pilot by default.

### Blockers

- Retrieval output churn
- Missing ops evidence sources
- Gate automation missing eval or security evidence

### Commit Boundaries

- `feat(portal): add internal operations portal mvp`
- `feat(ops): add observability, freshness, and pilot runbooks`
- `docs(release): add phase-1 rollout gate`
- `docs(modules): define deferred intelligence module contracts`

### Completion Criteria

- portal smoke/E2E 通过。
- backup/restore、freshness、rollout gate 通过。
- deferred modules 文档完整。

### Acceptance Checklist

- Operator 可以完成 ingestion status、inventory、search、citation inspection 关键流程。
- Observability、freshness、backup/restore 均有 runbook 与验证路径。
- Rollout gate 能阻止 degraded build。
- Deferred module docs 仅定义接口，不偷跑实现。

### Deliverable Template

- Portal features shipped
- Ops and runbook artifacts
- Gate automation artifacts
- Deferred contracts added
- Pilot readiness summary recorded

---

## Task Map: 原始 15 个任务

### 阶段 1

1. Freeze Phase 1 Product Contract
2. Bootstrap Repository Skeleton
3. Define Canonical Schema and Terminology Contract
4. Define ACL Propagation Contract

### 阶段 2

5. Implement Markdown and Office Preprocessing
6. Implement PDF Structural Extraction and Fidelity Checks
7. Implement Jira Connector
8. Implement Confluence Connector

### 阶段 3

9. Implement PageIndex-First Hybrid Retrieval
10. Implement Citation Assembly and Source Inspection
11. Implement Evaluation Harness and Gold-Set Runner

### 阶段 4

12. Implement Internal Operations Portal MVP
13. Add Observability, Freshness Checks, and Operational Runbooks
14. Add Rollout Gate Automation
15. Define Deferred Module Contracts

---

## Appendix A: Skillization Backlog

第一批优先抽象为可复用能力的项目：

- schema contract validator
- ACL contract validator
- document normalization toolkit
- PDF fidelity checker
- retrieval eval skill
- rollout gate skill

Skill 化要求：

- 优先输出稳定接口、清晰输入输出、与具体 Phase 1 业务解耦
- 能独立运行或被 CI/agent 调用
- 不直接绑定 SSD 团队专属发布策略

---

## Appendix B: Critical Path Snapshot

主路径：

Task 1 -> Task 3 -> Task 5/6 -> Task 7/8 -> Task 9 -> Task 10 -> Task 11 -> Task 12 -> Task 13 -> Task 14

补充说明：

- Task 2 可在 Task 1 后尽早并行。
- Task 15 后置，不阻塞 pilot。
- 任何并行都不能破坏合同先行、验证先行的原则。

---

## Appendix C: Stage Handoff Template

每个阶段结束时，建议按以下模板写 handoff，供下一个 agent 直接接手：

### Handoff Summary

- Stage completed
- Completion status
- Commits or change sets
- Evidence references

### Ready Inputs for Next Stage

- Stable contracts
- Stable fixtures or datasets
- Stable script entrypoints

### Remaining Risks

- Known gaps
- Pending validations
- External dependencies

### Recommended Immediate Next Step

- Next task to start
- First validation to write
- First reusable boundary to preserve

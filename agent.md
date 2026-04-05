# SSD Knowledge Platform Agent Manual

## 1. 项目目标

本仓库服务于 SSD 内部知识平台的 Phase 1 交付。Phase 1 的目标是构建一个可信的检索与 grounded Q&A 基础设施，用于协议规范、固件与 ASIC 设计文档、产品需求、Jira 和 Confluence 内容的统一摄取、检索、引用与评估。

该系统是检索基础设施，不是通用 AI 助手。任何实现都必须优先保证证据保真、引用可审计、权限过滤正确，以及评测结果可复现。

## 2. 范围边界

### In Scope for Phase 1

- Internal ingestion for `md`, `pdf`, `docx`, `xlsx`, `pptx`, Jira, and Confluence.
- Layout-preserving preprocessing with a PDF path built around MinerU or an equivalent offline parser.
- Canonical normalized document schema with provenance, ACL metadata, structure metadata, and terminology metadata.
- PageIndex-first retrieval with hybrid search, reranking, and exact citations.
- Internal operations portal for ingestion status, corpus inventory, search, citation inspection, and evaluation health.
- Retrieval evaluation harness with explicit recall and citation fidelity gates.
- Internal deployment only, with self-hosted inference only.

### Explicitly Out of Scope for Phase 1

- PR review automation.
- Testcase optimization.
- Product design optimization.
- Any Jira or Confluence write-back workflow.
- Broad multi-team workflow orchestration.
- Human annotation product surfaces.

## 3. 工作优先级

实现顺序必须遵循以下优先级：

1. 合同与 gate
2. schema 与 ACL
3. ingestion
4. retrieval 与 citation
5. eval
6. portal
7. ops
8. deferred modules

任何实现都不得绕过以下约束：

- ACL filtering
- citation fidelity
- retrieval evaluation gate

## 4. 执行规则

### TDD

- Ingestion 能力采用 fixture-first TDD。
- API 与跨模块契约采用 contract-first TDD。
- Portal 与 operator workflow 采用 E2E-first validation。
- Bug fix 必须遵循 red, green, refactor。
- 架构任务必须先定义 contract 和 validation，再进入实现。

### Commit

- 每个 commit 必须是垂直切片、可独立验证、单独保留也安全。
- 不允许把 deferred module 脚手架和 Phase 1 运行时功能混在同一提交。
- 任何提交前必须完成该切片对应的测试、fixture 或 gate 校验。

### Evidence

- 所有执行证据统一存放到 `.sisyphus/evidence/`。
- 每个 major task 至少包含一个 happy-path 和一个 failure-path 验证产物。

### Gate

- Retrieval 质量是 release gate，不是非正式检查。
- 安全与 ACL 负向测试必须作为强制门禁存在。

## 5. 架构硬约束

- Retrieval 必须采用 PageIndex-first 设计。
- ACL filtering 必须发生在 rerank 和 answer assembly 之前。
- Citation 至少精确到 `document + version + page + section/clause`，在可用时包含 `table_id` 或 `figure_id`。
- Ranking 默认遵循 `canonical > supporting > contextual`。
- 原始语言证据必须保留，且系统必须支持跨语言检索。
- Heading、clause numbering、worksheet、slide、table、figure、page 等结构信息必须作为一等对象保留下来。

## 6. Skill 化原则

优先把可复用能力沉淀为独立模块、契约或脚本入口，再考虑提升为独立 skill。不要把 Phase 1 的业务策略、团队约束或临时实现细节写死在 skill 中。

第一批适合 skill 化的能力：

- 文档结构归一化
- PDF fidelity 校验
- ACL 合同校验
- Retrieval eval runner
- Rollout gate runner

Skill 只封装通用且可迁移的能力，不承载 SSD Phase 1 的特定发布边界、团队流程或项目期次判断。

## 7. 建议的可复用边界

建议优先把以下边界设计为可复用单元：

- `packages/schema`
  - 知识文档标准模型
  - provenance、ACL、structure、terminology 的统一 contract
- `packages/acl`
  - ACL 传播、继承、过滤契约
- `packages/terminology`
  - 术语、缩写、别名、字段、命令与错误术语映射契约
- `scripts/gates/*`
  - 合同校验、发布门禁与质量门禁脚本
- `scripts/eval/*`
  - 检索评测、gold-set runner、回归检查入口

这些边界在设计时应保持项目无关、接口稳定、便于日后迁移为 skill 或接入 CI。

## 8. 执行顺序

### Critical Path

Task 1 -> Task 3 -> Task 5 and Task 6 -> Task 7 and Task 8 -> Task 9 -> Task 10 -> Task 11 -> Task 12 -> Task 13 -> Task 14

### Parallelism Guidance

- Task 2 can start immediately after Task 1.
- Task 3 and Task 4 can proceed in parallel after Task 1.
- Task 5 and Task 6 can proceed in parallel after schema and ACL contracts stabilize.
- Task 7 and Task 8 can proceed in parallel after connector contracts stabilize.
- Portal work should begin only after retrieval and citation contracts are stable enough to avoid UI churn.
- Task 15 does not block the pilot if release gates are already satisfied.

所有执行都必须以合同为先、验证为先、证据为先。

## 9. 全局验收清单

任何阶段、任务或提交在宣称完成前，都必须至少核对以下条目：

- 范围没有越界，没有引入 Phase 1 明确排除的能力。
- 当前切片有对应的测试、fixture 或 gate，且验证已通过。
- ACL、安全、引用、权威排序约束没有被绕过。
- 新增接口、schema、脚本入口已在对应 contract 文档中反映。
- 执行证据已落到 `.sisyphus/evidence/` 或已有明确证据留存方案。
- 改动边界支持后续 skill 化，没有把项目专属逻辑硬编码进通用模块。
- 当前产物可以被后续 agent 直接消费，而不需要额外口头解释。

## 10. 阶段输出模板

后续 agent 在推进每个阶段时，输出物建议按以下模板组织，确保 handoff 清晰且可审计：

### Stage Output Summary

- Stage
- Goal
- Status
- Owner or Agent
- Date

### Deliverables

- Implemented artifacts
- Updated contracts
- Added scripts or gates
- Added fixtures or datasets

### Validation Evidence

- Happy-path checks
- Failure-path checks
- Gate results
- Evidence locations

### Open Risks

- Known limitations
- Deferred decisions
- Blocking dependencies

### Next Handoff

- Recommended next task
- Required inputs for the next task
- Reusable outputs that should be promoted into packages or skills

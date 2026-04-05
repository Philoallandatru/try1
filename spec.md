# SSD Knowledge Platform Phase 1 Spec

## 1. Product Goal

构建一个面向 SSD 团队的内部可信知识检索平台。Phase 1 的目标是提供统一摄取、结构保真、ACL 安全、权威性优先、带精确引用的检索与 grounded Q&A 能力，为后续智能模块建立可靠基础。

## 2. Phase 1 Scope

### In Scope

- Internal ingestion for `md`, `pdf`, `docx`, `xlsx`, `pptx`, Jira, and Confluence.
- Layout-preserving preprocessing with a PDF path built around MinerU or an equivalent offline parser.
- Canonical normalized document schema with provenance, ACL metadata, structure metadata, and terminology metadata.
- PageIndex-first retrieval with hybrid search, reranking, and exact citations.
- Internal operations portal for ingestion status, corpus inventory, search, citation inspection, and evaluation health.
- Retrieval evaluation harness with explicit recall and citation fidelity gates.
- Internal deployment only, with self-hosted inference only.

### Out of Scope

- PR review automation.
- Testcase optimization.
- Product design optimization.
- Any Jira or Confluence write-back workflow.
- Broad multi-team workflow orchestration.
- Human annotation product surfaces.

## 3. Product Contract

Phase 1 必须满足以下产品合同：

- 支持所有规定 source family 的内部摄取。
- 所有内容进入统一 normalized document schema。
- 检索架构采用 PageIndex-first。
- 返回结果必须包含 exact citations。
- 提供面向 operator 的内部 portal。
- 提供 retrieval evaluation harness。
- 推理与部署仅限内部、自托管。

Phase 1 是 retrieval foundation，不是 generic assistant。系统必须优先生成可审计证据，而不是看起来合理的概括性回答。

## 4. Source Authority Model

### Authority Levels

- `canonical`
  - normative specifications
  - ratified standards
  - approved design baselines
  - approved product requirements
- `supporting`
  - internal design notes
  - Jira discussions
  - Confluence explanations
  - design reviews
  - derived analyses
- `contextual`
  - press releases
  - announcements
  - background articles
  - non-normative summaries

### Ranking Rule

- 默认排序优先 `canonical`，其次 `supporting`，最后 `contextual`。
- 除非用户明确请求背景或非规范性上下文，否则 contextual 内容不能压过 canonical 内容。
- 例如，press release 不能作为 NVMe 或 PCIe ratified specification 的首要证据。

## 5. Evidence and Fidelity Requirements

系统必须保留并暴露以下一等结构：

- headings
- clause numbering
- page numbers
- tables
- figures
- worksheet names
- slide boundaries
- document versions
- original language

系统必须满足以下保真要求：

- Citation 至少精确到 `document + version + page + section/clause`。
- 当可用时，citation 必须带 `table_id` 或 `figure_id`。
- 原始语言证据必须保留。
- 系统必须支持 cross-language retrieval。
- 协议与设计文档不能被降格成 plain text blob。

## 6. Security and Access Model

ACL metadata 必须进入 normalized document model，并在检索主路径中持续传播。ACL 过滤必须在 rerank 之前执行，也必须在 answer assembly 之前执行。

安全模型的最低约束：

- deny-by-default
- 支持 ACL inheritance
- ACL negative tests pass rate 必须是 100%
- 不允许未授权文档进入候选结果集合后再被后置裁剪

## 7. Retrieval and Answering Contract

Retrieval contract 包含以下能力：

- metadata-aware hybrid retrieval
- vector + lexical search
- authority-aware ordering
- ACL-safe candidate filtering
- reranking
- citation assembly
- source inspection

Citation payload 至少包含：

- `document`
- `version`
- `page`
- `section` 或 `clause`
- `table_id` 或 `figure_id`，当可用时

Source inspection 至少能够让 operator 查看：

- 证据来源文档
- 文档版本
- 页码与结构位置
- 与回答绑定的引用片段

## 8. Evaluation Contract

### Quality Thresholds

- `recall@10 >= 0.90`
- `nDCG@10 >= 0.80`
- `citation fidelity >= 0.95`
- `ACL negative test pass rate = 100%`
- freshness SLA：Jira 与 Confluence 增量变更在约定预算内可见
- portal search success rate：seeded smoke queries 均返回 cited results

### Gold-Set Coverage

gold set 必须覆盖：

- clause lookup questions
- field or parameter lookup questions
- table hit questions
- version-difference questions
- terminology mapping questions
- Chinese query to English spec retrieval
- English query to Chinese design or requirement retrieval
- abbreviation to full-term retrieval
- full-term to abbreviation retrieval

## 9. Monorepo Shape

仓库采用 monorepo，并明确 runtime boundary 与 contract boundary。

```text
apps/
  portal/
services/
  ingest/
  connectors/
  retrieval/
  eval/
packages/
  schema/
  acl/
  terminology/
  shared-config/
ops/
docs/
  adr/
  runbooks/
  modules/
fixtures/
  corpus/
  schema/
  connectors/
eval/
scripts/
  ingest/
  eval/
  gates/
tests/
  ingest/
  connectors/
  retrieval/
  security/
  portal/
  ops/
```

## 10. Release Contract

只有在以下条件全部成立时，Phase 1 才算完成：

- Ingestion works across all required source families.
- Retrieval returns ACL-safe cited evidence.
- Evaluation metrics meet thresholds.
- Portal supports operator workflows end to end.
- Operational runbooks and recovery paths are validated.

最终完成判断必须通过 release gates，而不是凭主观观察。

## 11. Acceptance Checklist

以下清单用于判断当前规格是否被正确实现，任何实现方案都必须可映射到这些验收项：

- 所有规定 source family 都存在可执行摄取路径。
- 所有摄取结果都能落入统一 normalized document schema。
- 文档结构对象被保留，至少覆盖 heading、clause、page、table、figure、worksheet、slide、language。
- 检索链路在 rerank 前完成 ACL 过滤。
- 默认排序遵循 `canonical > supporting > contextual`。
- 返回结果附带精确 citation，并支持 source inspection。
- cross-language retrieval 覆盖 seeded scenarios。
- eval gold set 覆盖 clause、field、table、version-diff、terminology、跨语言、缩写映射问题。
- 质量指标满足 `recall@10`、`nDCG@10`、citation fidelity、ACL negative tests 等门槛。
- portal、ops、rollout gate 都具备端到端可验证路径。

## 12. Phase Output Expectations

为了让实现过程可审计、可交接，每个阶段至少应产出以下类型的结果：

- Contract artifacts
  - ADR、schema、ACL、evaluation 或 release contract 文档
- Runtime artifacts
  - service、adapter、connector、portal 或 script 代码
- Validation artifacts
  - tests、fixtures、gold set、gate scripts、smoke checks
- Evidence artifacts
  - 证明 happy-path 和 failure-path 的执行证据
- Reusable artifacts
  - 可抽象进入 `packages/*`、`scripts/*` 或后续 skill 的稳定能力

# Platform CLI 中文指南

## 目标

本文档面向仓库当前已经实现的命令行能力，重点说明：

- 统一平台入口 `scripts/platform_cli.py`
- skill-ready 离线文档标准化入口 `scripts/ingest/normalize_cli.py`
- grounded retrieval 工具入口 `scripts/retrieval/toolkit_cli.py`
- snapshot 持久化入口 `scripts/retrieval/snapshot_cli.py`
- PageIndex 当前的工作原理
- 从零构建索引、导出 Markdown / PageIndex、到增量刷新 snapshot 的推荐路径

本文只描述**当前代码已经实现**的行为，不覆盖未来设计中的 section-level wiki 重写流水线。

## 入口总览

| 入口 | 用途 |
| --- | --- |
| `python scripts/platform_cli.py ...` | 统一平台 CLI，覆盖治理检查、评估、ingest、connector、ops、search、citation、Jira 分析、generic retrieval consumption、sync export |
| `python scripts/ingest/normalize_cli.py ...` | skill-ready 离线文档 normalizer，将源文档或 sync payload 转成 canonical document、Markdown、PageIndex |
| `python scripts/retrieval/toolkit_cli.py ...` | skill-ready grounded retrieval toolkit，支持构建 PageIndex、搜索、引用 |
| `python scripts/retrieval/snapshot_cli.py ...` | snapshot 持久化与增量刷新 |

## 环境准备

推荐使用 `uv`：

```powershell
python -m pip install --upgrade uv
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -e .
uv pip install -e ".[dev]"
```

或使用标准 `venv`：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

所有命令都在仓库根目录执行：

```powershell
cd C:\Users\10259\Documents\code\codex\codex-try
```

如果要连接 live Jira / Confluence，优先使用环境变量而不是把 token 写进命令历史：

```powershell
$env:JIRA_TOKEN = "<jira-token>"
$env:CONF_TOKEN = "<conf-token>"
```

## PageIndex 当前如何工作

PageIndex 是当前检索系统的核心投影，不是向量库。

数据流如下：

1. 各种源先被标准化为 canonical document。
2. canonical document 保留：
   - `provenance`
   - `acl`
   - `structure`
   - `content_blocks`
3. `services/retrieval/indexing/page_index.py` 按 `page` 构建检索 entry。
4. 每个 entry 会保留该页的：
   - 文档元数据
   - `acl`
   - `structure`
   - `content_blocks`
   - 拼接后的 `text`
   - `token_counts`
   - `tokens`
5. 搜索使用 `services/retrieval/search/hybrid_search.py`：
   - 先做 ACL 过滤
   - 再做 lexical + token overlap + authority boost 打分
6. citation 使用 `services/retrieval/citations/assembler.py` 从命中 entry 中提取：
   - `document`
   - `version`
   - `page`
   - `section`
   - `clause`
   - `table_id`
   - `figure_id`
   - `evidence_span`

当前实现的关键点：

- 检索是 **PageIndex-first**
- ACL 过滤发生在打分前
- `canonical > supporting > contextual`
- PageIndex artifact 的标准形状是：

```json
{
  "entries": [...]
}
```

## 检索输入源的三种模式

`search` / `citation` / `toolkit_cli` 当前支持三种输入源：

1. `--corpus`
   - 读取 canonical documents
   - 运行时重新构建 PageIndex
2. `--page-index`
   - 直接消费已导出的 `{"entries": [...]}` artifact
3. `--snapshot-dir`
   - 直接复用 snapshot 中的 `page_index.json`

推荐理解方式：

- 做开发验证时，用 `--corpus`
- 做 artifact 复用时，用 `--page-index`
- 做增量维护或 ops 路径时，用 `--snapshot-dir`

## 统一 CLI

统一入口：

```powershell
python scripts/platform_cli.py <command> [args]
```

### 治理检查

```powershell
python scripts/platform_cli.py adr-check
python scripts/platform_cli.py repo-check
python scripts/platform_cli.py module-check
```

用途：

- `adr-check`：检查 ADR 合同
- `repo-check`：检查仓库结构
- `module-check`：检查模块合同文档是否完整

### 评估与 Gate

```powershell
python scripts/platform_cli.py eval
python scripts/platform_cli.py gate
python scripts/platform_cli.py real-validate --spec-pdf fixtures\corpus\pdf\sample.pdf --context-pdf fixtures\corpus\pdf\sample.pdf
```

常用参数：

| 命令 | 关键参数 | 说明 |
| --- | --- | --- |
| `eval` | `--dataset` `--corpus` | 运行 retrieval 评估 |
| `gate` | `--dataset` `--corpus` | 运行 Phase 1 gate |
| `real-validate` | `--spec-pdf` `--context-pdf` `--model` | 使用真实 PDF + Ollama 做验证 |

### portal-state

```powershell
python scripts/platform_cli.py portal-state --query "nvme flush"
```

用途：

- 生成 portal 所需状态 JSON

### ops-health

```powershell
python scripts/platform_cli.py ops-health
python scripts/platform_cli.py ops-health --snapshot-dir .tmp\snapshot
python scripts/platform_cli.py ops-health --snapshot-dir .tmp\snapshot --reference-time-iso 2026-04-06T09:10:00Z
```

常用参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--snapshot-dir` | 无 | 从本地 snapshot 读取状态 |
| `--freshness-budget-minutes` | `30` | 新鲜度预算 |
| `--reference-time-iso` | 无 | 固定参考时间，便于测试 |

### ingest

```powershell
python scripts/platform_cli.py ingest markdown fixtures\corpus\markdown\sample.md
python scripts/platform_cli.py ingest docx fixtures\corpus\office\sample.docx
python scripts/platform_cli.py ingest xlsx fixtures\corpus\office\sample.xlsx
python scripts/platform_cli.py ingest pptx fixtures\corpus\office\sample.pptx
python scripts/platform_cli.py ingest pdf fixtures\corpus\pdf\sample.pdf
```

用途：

- 将单个文件解析为 canonical document JSON

支持类型：

- `markdown`
- `docx`
- `xlsx`
- `pptx`
- `pdf`

### connector

```powershell
python scripts/platform_cli.py connector jira fixtures\connectors\jira\full_sync.json
python scripts/platform_cli.py connector confluence fixtures\connectors\confluence\page_sync.json
python scripts/platform_cli.py connector jira fixtures\connectors\jira\full_sync.json --output-json .tmp\jira.json
```

live 模式示例：

```powershell
python scripts/platform_cli.py connector jira --live --base-url https://jira.example.com --token $env:JIRA_TOKEN
python scripts/platform_cli.py connector confluence --live --base-url https://confluence.example.com --token $env:CONF_TOKEN
```

选择性 live 拉取示例：

```powershell
python scripts/platform_cli.py connector jira --live --base-url https://jira.example.com --token $env:JIRA_TOKEN --fetch-backend atlassian-api --issue-key SSD-777
python scripts/platform_cli.py connector confluence --live --base-url https://confluence.example.com --token $env:CONF_TOKEN --fetch-backend atlassian-api --page-id 123456
```

说明：

- `kind` 只能是 `jira` 或 `confluence`
- fixture 模式需要位置参数 `path`
- live 模式必须提供 `--base-url`
- selective fetch 只在 `--fetch-backend atlassian-api` 下可用
- `--output-json` 会显式用 UTF-8 写文件，避免 shell 重定向编码问题

### sync-health

```powershell
python scripts/platform_cli.py sync-health jira fixtures\connectors\jira\incremental_sync.json --snapshot-dir .tmp\snapshot
python scripts/platform_cli.py sync-health confluence fixtures\connectors\confluence\incremental_sync.json --snapshot-dir .tmp\snapshot
```

用途：

- 执行单个 source 的同步
- 刷新 snapshot
- 立即输出 ops health

它是下面这条链的封装：

```text
connector payload -> refresh_snapshot -> build_ops_health
```

### multi-sync-health

```powershell
python scripts/platform_cli.py multi-sync-health --snapshot-dir .tmp\snapshot --jira-path fixtures\connectors\jira\incremental_sync.json --confluence-path fixtures\connectors\confluence\incremental_sync.json
python scripts/platform_cli.py multi-sync-health --profile fixtures\ops\multi_sync_health_profile.json --snapshot-dir .tmp\snapshot
```

用途：

- 顺序执行 Jira 与 Confluence 同步
- 刷新到同一个 snapshot
- 输出聚合后的 health

### search

```powershell
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py search "flush command" --page-index .tmp\page-index.json
python scripts/platform_cli.py search "flush command" --snapshot-dir .tmp\snapshot
python scripts/platform_cli.py search "flush command" --policies team:ssd public
```

### citation

```powershell
python scripts/platform_cli.py citation "flush command"
python scripts/platform_cli.py citation "flush command" --page-index .tmp\page-index.json
python scripts/platform_cli.py citation "flush command" --snapshot-dir .tmp\snapshot
```

说明：

- `search` 返回检索结果及分数
- `citation` 返回 citation 友好的结果
- 这两个命令都支持 `--corpus / --page-index / --snapshot-dir`

### jira-report

```powershell
python scripts/platform_cli.py jira-report --jira-path fixtures\connectors\jira\incremental_sync.json --updated-on-date 2026-04-05 --output-md .tmp\jira-report.md
python scripts/platform_cli.py jira-report --jira-path fixtures\connectors\jira\full_sync.json --report-profile pm-daily --reference-date 2026-04-05 --status-filter "In Progress" --llm-backend mock --llm-mock-response "Mock PM daily summary"
```

用途：

- 从 Jira fixture 或 live Jira 生成按时间过滤的 Markdown 报告
- 可选接本地 LLM 生成总结
- `--report-profile pm-daily` 可生成面向项目管理者的日报，区分“当天有更新的 In Progress”与“仍 In Progress 但当天无更新”的问题

### jira-spec-qa

```powershell
python scripts/platform_cli.py jira-spec-qa --jira-path fixtures\connectors\jira\incremental_sync.json --jira-issue-id SSD-102 --spec-corpus fixtures\retrieval\pageindex_corpus.json --spec-document-id nvme-spec-v1 --question "Does this issue relate to the selected spec?"
```

用途：

- 单个 Jira issue + spec 联合检索与问答

### spec-section-explain

```powershell
python scripts/platform_cli.py spec-section-explain --jira-path fixtures\connectors\jira\incremental_sync.json --spec-corpus fixtures\retrieval\pageindex_corpus.json --spec-document-id nvme-spec-v1 --clause 1.1
```

用途：

- 选定一个 spec 小节或 clause
- 检索相关 Jira 证据
- 生成一个 section-centered 的解释 payload

### confluence-wiki-demo

```powershell
python scripts/platform_cli.py confluence-wiki-demo --confluence-path fixtures\connectors\confluence\page_sync.json --output-dir .tmp\wiki-demo --llm-backend mock --llm-mock-response "Mock confluence wiki summary"
```

用途：

- 读取 Confluence 页面
- 生成每页 summary
- 导出一个最小静态 wiki demo：
  - `index.html`
  - `pages/<document-id>.html`

### jira-batch-spec-report

```powershell
python scripts/platform_cli.py jira-batch-spec-report --jira-path fixtures\connectors\jira\incremental_sync.json --updated-from-iso 2026-04-05T09:00:00Z --updated-to-iso 2026-04-05T10:00:00Z --spec-corpus fixtures\retrieval\pageindex_corpus.json --spec-document-id nvme-spec-v1 --question-template "Analyze Jira {jira_issue_id} against the selected spec." --output-md .tmp\jira-batch-spec-report.md
```

用途：

- 对时间窗口内的多个 Jira issue 逐条跑 spec QA

### retrieval-consume

```powershell
python scripts/platform_cli.py retrieval-consume --source-kind jira-sync --source-path fixtures\connectors\jira\incremental_sync.json --question "Which issue mentions medium priority?"
python scripts/platform_cli.py retrieval-consume --source-kind pdf --source-path fixtures\corpus\pdf\sample.pdf --question "What document covers flush semantics?"
python scripts/platform_cli.py retrieval-consume --snapshot-dir .tmp\snapshot --question "What document covers flush semantics?"
```

用途：

- 当前已经实现的 source-generic retrieval consumption 入口
- 负责：
  - 读取源文档或 snapshot
  - 组装 citations
  - 生成 prompt
  - 可选调用本地 LLM

支持的 `--source-kind`：

- `jira-sync`
- `confluence-sync`
- `jira-live`
- `confluence-live`
- `markdown`
- `docx`
- `xlsx`
- `pptx`
- `pdf`

关键参数：

| 参数 | 说明 |
| --- | --- |
| `--snapshot-dir` | 直接从 snapshot 的 `documents.json` 读取 |
| `--source-kind` | 数据源类型 |
| `--source-path` | 文件或 fixture 路径 |
| `--question` | 必填问题 |
| `--prompt-template` | 自定义 prompt 模板 |
| `--output-answer-md` | 写出 answer Markdown |
| `--output-json` | 写出完整 JSON 结果 |
| `--top-k` | 检索 top-k，默认 `5` |
| `--policies` | ACL policy 列表 |

### sync-export

```powershell
python scripts/platform_cli.py sync-export --profile fixtures\ops\multi_sync_health_profile.json --snapshot-dir .tmp\snapshot --output-md .tmp\export.md --output-page-index .tmp\export-page-index.json
python scripts/platform_cli.py sync-export --profile fixtures\ops\multi_sync_health_profile.json --snapshot-dir .tmp\snapshot --output-md-dir .tmp\export-docs
```

用途：

- 运行多源同步
- 刷新 snapshot
- 基于同步结果导出 Markdown / Markdown tree / PageIndex

关键参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--profile` | 无 | profile 驱动的源配置 |
| `--snapshot-dir` | 无 | snapshot 根目录 |
| `--export-scope` | `incoming` | `incoming` 或 `snapshot` |
| `--output-md` | 无 | 导出单个拼接 Markdown |
| `--output-md-dir` | 无 | 每文档一个 Markdown 文件 |
| `--output-page-index` | 无 | 导出 `{"entries": [...]}` |

`--export-scope` 说明：

- `incoming`：只导出本次同步进来的文档
- `snapshot`：导出当前 snapshot 中的全部文档

## skill-ready CLI

### normalize_cli

```powershell
python scripts/ingest/normalize_cli.py markdown fixtures\corpus\markdown\sample.md
python scripts/ingest/normalize_cli.py jira-sync fixtures\connectors\jira\full_sync.json --output-md .tmp\jira.md --output-page-index .tmp\jira-page-index.json
python scripts/ingest/normalize_cli.py confluence-sync fixtures\connectors\confluence\page_sync.json --output-md-dir .tmp\docs
python scripts/ingest/normalize_cli.py pdf fixtures\corpus\pdf\sample.pdf --output-md .tmp\pdf.md --output-page-index .tmp\pdf-page-index.json
```

用途：

- 将源文档或 sync payload 标准化
- 可同时导出：
  - readable Markdown
  - Markdown tree
  - PageIndex JSON

支持类型：

- `markdown`
- `docx`
- `xlsx`
- `pptx`
- `pdf`
- `jira-sync`
- `confluence-sync`

### toolkit_cli

```powershell
python scripts/retrieval/toolkit_cli.py index --corpus fixtures\retrieval\pageindex_corpus.json --output-page-index .tmp\page-index.json
python scripts/retrieval/toolkit_cli.py search "flush command" --page-index .tmp\page-index.json
python scripts/retrieval/toolkit_cli.py citation "flush command" --snapshot-dir .tmp\snapshot
```

用途：

- `index`：从 canonical document corpus 构建 `{"entries": [...]}` artifact
- `search`：搜索
- `citation`：引用结果

### snapshot_cli

```powershell
python scripts/retrieval/snapshot_cli.py create --snapshot-dir .tmp\snapshot --corpus fixtures\retrieval\pageindex_corpus.json
python scripts/retrieval/snapshot_cli.py show --snapshot-dir .tmp\snapshot
python scripts/retrieval/snapshot_cli.py refresh --snapshot-dir .tmp\snapshot --sync-payload fixtures\connectors\jira\incremental_sync.json --source-name jira
```

用途：

- `create`：初始化 snapshot
- `show`：查看 snapshot 内容
- `refresh`：按 sync payload 增量刷新

## Snapshot 与增量维护

当前 snapshot 固定维护三个文件：

- `manifest.json`
- `documents.json`
- `page_index.json`

刷新机制如下：

1. 读取已有 `documents.json`
2. 读取新的 `sync_payload`
3. 按 `document_id` 合并新旧 documents
4. 对合并后的 documents **全量重建** `page_index.json`
5. 更新 `manifest.json`

这意味着当前实现的索引维护策略是：

- 文档级 merge
- PageIndex 全量重建
- 没有 entry 级 patch
- 没有 embedding index 增量维护

优点：

- 简单
- 可验证
- 与当前 Phase 1 的 file-backed snapshot 边界一致

## 推荐工作流

### 1. 单文件 / 单 payload 标准化

```powershell
python scripts/ingest/normalize_cli.py pdf fixtures\corpus\pdf\sample.pdf --output-md .tmp\pdf.md --output-page-index .tmp\pdf-page-index.json
```

### 2. 构建独立 PageIndex artifact

```powershell
python scripts/retrieval/toolkit_cli.py index --corpus fixtures\retrieval\pageindex_corpus.json --output-page-index .tmp\page-index.json
```

### 3. 初始化 snapshot

```powershell
python scripts/retrieval/snapshot_cli.py create --snapshot-dir .tmp\snapshot --corpus fixtures\retrieval\pageindex_corpus.json
```

### 4. 增量刷新 snapshot

```powershell
python scripts/retrieval/snapshot_cli.py refresh --snapshot-dir .tmp\snapshot --sync-payload fixtures\connectors\jira\incremental_sync.json --source-name jira
python scripts/retrieval/snapshot_cli.py refresh --snapshot-dir .tmp\snapshot --sync-payload fixtures\connectors\confluence\incremental_sync.json --source-name confluence
```

### 5. 基于 snapshot 检索 / 引用

```powershell
python scripts/platform_cli.py search "flush command" --snapshot-dir .tmp\snapshot
python scripts/platform_cli.py citation "flush command" --snapshot-dir .tmp\snapshot
python scripts/platform_cli.py retrieval-consume --snapshot-dir .tmp\snapshot --question "What document covers flush semantics?"
```

### 6. 基于 profile 做批量 sync-export

```powershell
python scripts/platform_cli.py sync-export --profile fixtures\ops\multi_sync_health_profile.json --snapshot-dir .tmp\snapshot --output-md-dir .tmp\export-docs --output-page-index .tmp\export-page-index.json
```

## 当前限制

- 当前检索仍是 PageIndex-first 的 token / lexical 检索，不是向量检索。
- snapshot refresh 会全量重建 `page_index.json`。
- `sync-export` 目前是按文档级导出，不是按 spec section 级导出。
- `retrieval-consume` 是 generic retrieval consumption，不是 section-aware wiki 重写流水线。
- PDF 支持 MinerU 优先、`pypdf` 回退；Office / Jira / Confluence 的 fidelity 仍在逐步增强。

## 常见建议

- 做本地开发验证时，优先用 `normalize_cli + toolkit_cli`
- 做可复用 artifact 时，优先导出 `--output-page-index`
- 做持续更新时，优先维护 `snapshot-dir`
- 做面向问答或总结的消费层时，优先用 `retrieval-consume`

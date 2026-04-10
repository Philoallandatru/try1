# 平台 CLI 中文手册

## 目标

本文档覆盖仓库里的主要命令入口、每个命令的用途、参数和案例。

命令入口分为 4 类：

| 入口 | 用途 |
| --- | --- |
| `python scripts/platform_cli.py ...` | 统一平台 CLI，覆盖治理检查、评估、ingest、connector、snapshot health、检索、Jira 分析。 |
| `python scripts/ingest/normalize_cli.py ...` | skill-ready 离线文档 normalizer，把源文件转换为 canonical document、Markdown 和 PageIndex。 |
| `python scripts/retrieval/toolkit_cli.py ...` | skill-ready grounded retrieval toolkit，生成索引、搜索、引用。 |
| `python scripts/retrieval/snapshot_cli.py ...` | snapshot 持久化 CLI，创建、查看、刷新本地 snapshot。 |

## 通用准备

推荐用 `uv` 创建本地 Python 环境：

```powershell
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"
```

所有命令都在仓库根目录执行：

```powershell
cd C:\Users\10259\Documents\code\codex\codex-try
```

如果命令连接 live Jira 或 Confluence，不要把 token 写进命令历史或文档。优先用环境变量：

```powershell
$env:JIRA_TOKEN = "<jira-token>"
$env:CONF_TOKEN = "<confluence-token>"
```

## 统一平台 CLI

统一入口：

```powershell
python scripts/platform_cli.py <command> [args]
```

### `adr-check`

用途：检查 ADR 合同是否满足仓库约束。

参数：无。

案例：

```powershell
python scripts/platform_cli.py adr-check
```

### `repo-check`

用途：检查仓库结构是否符合 Phase 1 约定。

参数：无。

案例：

```powershell
python scripts/platform_cli.py repo-check
```

### `module-check`

用途：检查模块合同文档是否覆盖必要 CLI、runbook 和能力边界。

参数：无。

案例：

```powershell
python scripts/platform_cli.py module-check
```

### `eval`

用途：运行 retrieval 评估数据集，输出 recall、NDCG、citation fidelity 等指标。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--dataset` | 否 | `eval/gold_queries.yaml` | gold query 数据集。 |
| `--corpus` | 否 | `fixtures/retrieval/pageindex_corpus.json` | PageIndex corpus。 |

案例：

```powershell
python scripts/platform_cli.py eval
python scripts/platform_cli.py eval --dataset eval/gold_queries.yaml --corpus fixtures/retrieval/pageindex_corpus.json
```

### `real-validate`

用途：用真实 PDF 和本地 Ollama 模型运行 PDF 验证流程。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--spec-pdf` | 是 | 无 | 规格 PDF 路径。 |
| `--context-pdf` | 是 | 无 | 上下文 PDF 路径。 |
| `--model` | 否 | `qwen2.5:0.5b` | Ollama 模型名。 |
| `--ollama-exe` | 否 | 用户目录下的 Ollama 安装路径 | Ollama 可执行文件路径。 |

案例：

```powershell
python scripts/platform_cli.py real-validate `
  --spec-pdf fixtures\corpus\pdf\sample.pdf `
  --context-pdf fixtures\corpus\pdf\sample.pdf `
  --model qwen3:1.7b
```

### `gate`

用途：运行 Phase 1 rollout gate。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--dataset` | 否 | `eval/gold_queries.yaml` | 评估数据集。 |
| `--corpus` | 否 | `fixtures/retrieval/pageindex_corpus.json` | PageIndex corpus。 |

案例：

```powershell
python scripts/platform_cli.py gate
```

### `portal-state`

用途：生成静态 ops portal 所需的状态 JSON。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--query` | 否 | `nvme flush` | portal 默认检索 query。 |

案例：

```powershell
python scripts/platform_cli.py portal-state --query "flush command"
```

### `ops-health`

用途：检查本地 fixture 或 snapshot 的 freshness、backup/restore 和 PageIndex 健康状态。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--snapshot-dir` | 否 | 无 | 本地 snapshot 目录。 |
| `--freshness-budget-minutes` | 否 | `30` | 新鲜度预算。 |
| `--reference-time-iso` | 否 | 无 | 固定参考时间，常用于测试。 |

案例：

```powershell
python scripts/platform_cli.py ops-health
python scripts/platform_cli.py ops-health --snapshot-dir .tmp\snapshot
```

### `ingest`

用途：把单个文件解析为 canonical document JSON。

参数：

| 参数 | 必填 | 可选值 | 说明 |
| --- | --- | --- | --- |
| `kind` | 是 | `markdown`、`docx`、`xlsx`、`pptx`、`pdf` | 输入文件类型。 |
| `path` | 是 | 文件路径 | 输入文件路径。 |

案例：

```powershell
python scripts/platform_cli.py ingest markdown fixtures\corpus\markdown\sample.md
python scripts/platform_cli.py ingest pdf fixtures\corpus\pdf\sample.pdf
```

### `connector`

用途：读取 Jira 或 Confluence fixture，或连接 live Jira/Confluence 并输出标准化 sync payload。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `kind` | 是 | 无 | `jira` 或 `confluence`。 |
| `path` | fixture 模式必填 | 无 | fixture payload 路径。 |
| `--live` | live 模式必填 | `False` | 使用 live API。 |
| `--base-url` | live 模式必填 | 无 | Jira 或 Confluence 根地址。 |
| `--username` | Basic auth 常用 | 无 | 用户名或邮箱。 |
| `--password` | Basic auth 可选 | 无 | 密码。 |
| `--token` | token auth 常用 | 无 | API token 或 PAT。 |
| `--auth-mode` | 否 | `auto` | `auto`、`basic`、`bearer`。 |
| `--cursor` | 否 | 无 | 增量同步游标。 |
| `--page-size` | 否 | `50` | 每页拉取数量。 |
| `--jql` | Jira 使用 | `order by updated asc` | Jira 查询语句。 |
| `--cql` | Confluence 使用 | 无 | Confluence CQL 查询语句。 |
| `--space-key` | Confluence 使用 | 无 | Confluence space key。 |
| `--insecure` | 否 | `False` | 跳过 SSL 校验。 |

Jira fixture 案例：

```powershell
python scripts/platform_cli.py connector jira fixtures\connectors\jira\full_sync.json
```

Jira live 全量拉取指定项目案例：

```powershell
python scripts/platform_cli.py connector jira `
  --live `
  --base-url https://jira.example.com `
  --token $env:JIRA_TOKEN `
  --auth-mode bearer `
  --jql "project = SSD ORDER BY updated ASC" `
  --page-size 100 > .tmp\jira-SSD-full-sync.json
```

Jira Cloud Basic auth 案例：

```powershell
python scripts/platform_cli.py connector jira `
  --live `
  --base-url https://your-domain.atlassian.net `
  --username "you@example.com" `
  --token $env:JIRA_TOKEN `
  --auth-mode basic `
  --jql "project = SSD ORDER BY updated ASC" `
  --page-size 100 > .tmp\jira-SSD-full-sync.json
```

Confluence live 案例：

```powershell
python scripts/platform_cli.py connector confluence `
  --live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --space-key SSD
```

### `sync-health`

用途：执行单个 source 的同步、snapshot refresh 和 ops health。

参数：包含 `connector` 的通用 source 参数，并额外支持：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--snapshot-dir` | 是 | 无 | snapshot 目录。 |
| `--corpus` | 否 | `fixtures/retrieval/pageindex_corpus.json` | 初始 corpus。 |
| `--freshness-budget-minutes` | 否 | `30` | 新鲜度预算。 |
| `--reference-time-iso` | 否 | 无 | 固定参考时间。 |

案例：

```powershell
python scripts/platform_cli.py sync-health jira fixtures\connectors\jira\incremental_sync.json `
  --snapshot-dir .tmp\snapshot
```

live Jira 案例：

```powershell
python scripts/platform_cli.py sync-health jira `
  --live `
  --base-url https://jira.example.com `
  --token $env:JIRA_TOKEN `
  --auth-mode bearer `
  --jql "project = SSD ORDER BY updated ASC" `
  --snapshot-dir .tmp\snapshot
```

### `multi-sync-health`

用途：顺序同步 Jira 和 Confluence 两个 source，刷新同一个 snapshot，并输出聚合健康状态。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--snapshot-dir` | 视 profile 而定 | 无 | snapshot 目录。 |
| `--profile` | 否 | 无 | JSON profile 路径。 |
| `--corpus` | 否 | `fixtures/retrieval/pageindex_corpus.json` | 初始 corpus。 |
| `--freshness-budget-minutes` | 否 | `30` | 新鲜度预算。 |
| `--reference-time-iso` | 否 | 无 | 固定参考时间。 |
| `--jira-path` | Jira fixture 模式 | 无 | Jira fixture 路径。 |
| `--jira-live` | Jira live 模式 | `False` | 使用 live Jira。 |
| `--jira-base-url` | Jira live 模式 | 无 | Jira 根地址。 |
| `--jira-username` | Basic auth 常用 | 无 | Jira 用户名。 |
| `--jira-password` | Basic auth 可选 | 无 | Jira 密码。 |
| `--jira-token` | token auth 常用 | 无 | Jira token。 |
| `--jira-auth-mode` | 否 | `auto` | `auto`、`basic`、`bearer`。 |
| `--jira-cursor` | 否 | 无 | Jira 增量游标。 |
| `--jira-page-size` | 否 | `50` | Jira 每页数量。 |
| `--jira-jql` | 否 | `order by updated asc` | Jira JQL。 |
| `--jira-insecure` | 否 | `False` | 跳过 Jira SSL 校验。 |
| `--confluence-path` | Confluence fixture 模式 | 无 | Confluence fixture 路径。 |
| `--confluence-live` | Confluence live 模式 | `False` | 使用 live Confluence。 |
| `--confluence-base-url` | Confluence live 模式 | 无 | Confluence 根地址。 |
| `--confluence-username` | Basic auth 常用 | 无 | Confluence 用户名。 |
| `--confluence-password` | Basic auth 可选 | 无 | Confluence 密码。 |
| `--confluence-token` | token auth 常用 | 无 | Confluence token。 |
| `--confluence-auth-mode` | 否 | `auto` | `auto`、`basic`、`bearer`。 |
| `--confluence-cursor` | 否 | 无 | Confluence 增量游标。 |
| `--confluence-page-size` | 否 | `25` | Confluence 每页数量。 |
| `--confluence-cql` | 否 | 无 | Confluence CQL。 |
| `--confluence-space-key` | 否 | 无 | Confluence space key。 |
| `--confluence-insecure` | 否 | `False` | 跳过 Confluence SSL 校验。 |

fixture 案例：

```powershell
python scripts/platform_cli.py multi-sync-health `
  --snapshot-dir .tmp\snapshot `
  --jira-path fixtures\connectors\jira\incremental_sync.json `
  --confluence-path fixtures\connectors\confluence\incremental_sync.json
```

profile 案例：

```powershell
python scripts/platform_cli.py multi-sync-health `
  --profile fixtures\ops\multi_sync_health_profile.json `
  --snapshot-dir .tmp\snapshot
```

### `search`

用途：在 PageIndex corpus 或 snapshot 文档中检索。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `query` | 是 | 无 | 检索文本。 |
| `--corpus` | 否 | `fixtures/retrieval/pageindex_corpus.json` | corpus 路径，会从 canonical documents 重建 PageIndex。 |
| `--page-index` | 否 | 无 | PageIndex artifact 路径，直接消费 `{"entries": [...]}`。 |
| `--snapshot-dir` | 否 | 无 | snapshot 目录，直接复用其中的 `page_index.json`。 |
| `--policies` | 否 | `team:ssd public` | 允许的 ACL policies。 |

案例：

```powershell
python scripts/platform_cli.py search "flush command"
python scripts/platform_cli.py search "flush command" --page-index .tmp\page-index.json
python scripts/platform_cli.py search "flush command" --snapshot-dir .tmp\snapshot
python scripts/platform_cli.py search "flush command" --policies team:ssd public
```

### `citation`

用途：对 query 返回带引用的检索结果。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `query` | 是 | 无 | 检索文本。 |
| `--corpus` | 否 | `fixtures/retrieval/pageindex_corpus.json` | corpus 路径，会从 canonical documents 重建 PageIndex。 |
| `--page-index` | 否 | 无 | PageIndex artifact 路径，直接消费 `{"entries": [...]}`。 |
| `--snapshot-dir` | 否 | 无 | snapshot 目录，直接复用其中的 `page_index.json`。 |
| `--policies` | 否 | `team:ssd public` | 允许的 ACL policies。 |

案例：

```powershell
python scripts/platform_cli.py citation "flush command"
python scripts/platform_cli.py citation "flush command" --page-index .tmp\page-index.json
python scripts/platform_cli.py citation "flush command" --snapshot-dir .tmp\snapshot
```

### `jira-report`

用途：从 Jira fixture 或 live Jira 拉取 issues，按时间过滤并生成 Markdown 报告。可选调用本地 LLM 总结。

Jira source 参数：

| 参数 | 说明 |
| --- | --- |
| `--jira-path` | Jira fixture 文件路径。 |
| `--jira-live` | 使用 live Jira。 |
| `--jira-base-url` | Jira 根地址。 |
| `--jira-username` | Jira 用户名或邮箱。 |
| `--jira-password` | Jira 密码。 |
| `--jira-token` | Jira token。 |
| `--jira-auth-mode` | `auto`、`basic`、`bearer`。 |
| `--jira-cursor` | 增量游标。 |
| `--jira-page-size` | 每页拉取数量，默认 50。 |
| `--jira-jql` | Jira JQL，默认 `order by updated asc`。 |
| `--jira-insecure` | 跳过 SSL 校验。 |

报告参数：

| 参数 | 说明 |
| --- | --- |
| `--updated-from-iso` | 起始更新时间。 |
| `--updated-to-iso` | 结束更新时间。 |
| `--updated-on-date` | 指定日期。 |
| `--updated-at-iso` | 指定单个更新时间点。 |
| `--prompt-template` | 自定义 prompt 模板。 |
| `--output-md` | 写出 Markdown 报告。 |
| `--output-answer-md` | 写出本地 LLM answer，需要设置 `--llm-backend`。 |

LLM 参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--llm-backend` | `none` | `none`、`mock`、`ollama`、`openai-compatible`。 |
| `--llm-model` | 无 | 模型名。 |
| `--llm-base-url` | 无 | OpenAI-compatible 或 Ollama base URL。 |
| `--llm-api-key` | 无 | OpenAI-compatible API key。 |
| `--llm-timeout-seconds` | `120` | 超时时间。 |
| `--llm-mock-response` | 无 | mock backend 返回文本。 |
| `--llm-prompt-mode` | `strict` | `strict`、`balanced`、`exploratory`。 |

案例：

```powershell
python scripts/platform_cli.py jira-report `
  --jira-path fixtures\connectors\jira\incremental_sync.json `
  --updated-on-date 2026-04-05 `
  --output-md .tmp\jira-report.md
```

live + Ollama 案例：

```powershell
python scripts/platform_cli.py jira-report `
  --jira-live `
  --jira-base-url https://jira.example.com `
  --jira-token $env:JIRA_TOKEN `
  --jira-auth-mode bearer `
  --jira-jql "project = SSD ORDER BY updated ASC" `
  --updated-on-date 2026-04-08 `
  --llm-backend ollama `
  --llm-model qwen3:1.7b `
  --output-md .tmp\jira-report.md `
  --output-answer-md .tmp\jira-report-answer.md
```

### `jira-spec-qa`

用途：把一个 Jira issue 与指定 spec 文档结合，生成 spec-grounded QA payload 和答案。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| Jira source 参数 | 是 | 见 `jira-report` | `--jira-path` 或 `--jira-live` 必须提供一种。 |
| `--jira-issue-id` | 否 | 无 | 指定 issue key。 |
| `--spec-corpus` | 否 | `fixtures/retrieval/pageindex_corpus.json` | spec corpus。 |
| `--spec-document-id` | 是 | 无 | spec 文档 ID。 |
| `--question` | 是 | 无 | 问题。 |
| `--prompt-template` | 否 | 无 | 自定义 prompt 模板。 |
| `--output-answer-md` | 否 | 无 | 写出答案 Markdown。 |
| `--policies` | 否 | `team:ssd public` | ACL policies。 |
| LLM 参数 | 否 | 见 `jira-report` | 可选本地 LLM backend。 |

案例：

```powershell
python scripts/platform_cli.py jira-spec-qa `
  --jira-path fixtures\connectors\jira\incremental_sync.json `
  --jira-issue-id SSD-102 `
  --spec-corpus fixtures\retrieval\pageindex_corpus.json `
  --spec-document-id nvme-spec-v1 `
  --question "Does this issue relate to the selected spec?" `
  --output-answer-md .tmp\jira-spec-answer.md
```

### `jira-batch-spec-report`

用途：对一批时间过滤后的 Jira issues 执行 spec QA，并生成组合报告。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| Jira source 参数 | 是 | 见 `jira-report` | `--jira-path` 或 `--jira-live` 必须提供一种。 |
| 时间过滤参数 | 否 | 无 | 同 `jira-report`。 |
| `--spec-corpus` | 否 | `fixtures/retrieval/pageindex_corpus.json` | spec corpus。 |
| `--spec-document-id` | 是 | 无 | spec 文档 ID。 |
| `--question-template` | 否 | `Analyze Jira {jira_issue_id} against the selected spec.` | 每个 issue 的问题模板。 |
| `--output-md` | 否 | 无 | 写出组合 Markdown 报告。 |
| `--policies` | 否 | `team:ssd public` | ACL policies。 |
| LLM 参数 | 否 | 见 `jira-report` | 可选本地 LLM backend。 |

案例：

```powershell
python scripts/platform_cli.py jira-batch-spec-report `
  --jira-path fixtures\connectors\jira\incremental_sync.json `
  --updated-on-date 2026-04-05 `
  --spec-corpus fixtures\retrieval\pageindex_corpus.json `
  --spec-document-id nvme-spec-v1 `
  --question-template "Analyze Jira {jira_issue_id} against the selected spec." `
  --output-md .tmp\jira-batch-spec-report.md
```

### `retrieval-consume`

用途：统一的 source-generic retrieval-consumption 入口。可直接读取 Jira/Confluence fixture、live Jira/live Confluence、Markdown/Office/PDF 文件，或 snapshot 目录中的 `documents.json`，执行检索、组装 citation-backed prompt，并可选调用本地 LLM。

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--snapshot-dir` | 与 `--source-kind/--source-path` 二选一 | snapshot 目录，直接复用其中的 `documents.json`。 |
| `--source-kind` | 与 `--snapshot-dir` 二选一 | `jira-sync`、`confluence-sync`、`jira-live`、`confluence-live`、`markdown`、`docx`、`xlsx`、`pptx`、`pdf`。 |
| `--source-path` | fixture/file 模式需要 | 输入文件或 fixture 路径。 |
| `--base-url` | live 模式需要 | Jira 或 Confluence 根地址。 |
| `--username` | live Basic auth 可选 | 用户名。 |
| `--password` | live Basic auth 可选 | 密码。 |
| `--token` | live token auth 常用 | API token 或 PAT。 |
| `--auth-mode` | 否 | `auto`、`basic`、`bearer`。 |
| `--cursor` | 否 | 增量游标。 |
| `--page-size` | 否 | 每页拉取数量。 |
| `--jql` | Jira live 使用 | Jira JQL。 |
| `--cql` | Confluence live 使用 | Confluence CQL。 |
| `--space-key` | Confluence live 使用 | Confluence 空间 key。 |
| `--insecure` | 否 | 跳过 SSL 校验。 |
| `--question` | 是 | 问题文本。 |
| `--prompt-template` | 否 | 自定义 prompt 模板。 |
| `--output-answer-md` | 否 | 写出答案 Markdown。 |
| `--policies` | 否 | ACL policies。 |
| `--top-k` | 否 | 检索返回条数，默认 `5`。 |
| LLM 参数 | 否 | 与 `jira-report` 相同。 |

案例：

```powershell
python scripts/platform_cli.py retrieval-consume `
  --source-kind confluence-sync `
  --source-path fixtures\connectors\confluence\page_sync.json `
  --question "Which page mentions telemetry architecture?" `
  --llm-backend mock `
  --llm-mock-response "Mock confluence answer"
```

```powershell
python scripts/platform_cli.py retrieval-consume `
  --source-kind pdf `
  --source-path fixtures\corpus\pdf\sample.pdf `
  --question "What document covers flush semantics?"
```

```powershell
python scripts/platform_cli.py retrieval-consume `
  --snapshot-dir .tmp\snapshot `
  --question "What document covers flush semantics?"
```

```powershell
python scripts/platform_cli.py retrieval-consume `
  --source-kind jira-live `
  --base-url https://jira.example.com `
  --token $env:JIRA_TOKEN `
  --question "What changed in the latest SSD issue?"
```

```powershell
python scripts/platform_cli.py retrieval-consume `
  --source-kind confluence-live `
  --base-url https://confluence.example.com `
  --token $env:CONF_TOKEN `
  --space-key SSD `
  --question "What changed in the latency budget page?"
```

## Skill-ready normalizer CLI

入口：

```powershell
python scripts/ingest/normalize_cli.py <kind> <path> [--output-md <path>] [--output-page-index <path>]
```

用途：把输入源转换为标准化文档；可选写出可读 Markdown 和 PageIndex JSON。PageIndex JSON 使用统一 artifact 形状：`{"entries": [...]}`。

参数：

| 参数 | 必填 | 可选值 | 说明 |
| --- | --- | --- | --- |
| `kind` | 是 | `markdown`、`docx`、`xlsx`、`pptx`、`pdf`、`jira-sync`、`confluence-sync` | 输入源类型。 |
| `path` | 是 | 文件路径 | 输入源路径。 |
| `--output-md` | 否 | 输出路径 | 写出 Markdown。 |
| `--output-page-index` | 否 | 输出路径 | 写出 PageIndex JSON。 |

案例：

```powershell
python scripts/ingest/normalize_cli.py pdf fixtures\corpus\pdf\sample.pdf `
  --output-md .tmp\pdf.md `
  --output-page-index .tmp\pdf-page-index.json
```

```powershell
python scripts/ingest/normalize_cli.py jira-sync fixtures\connectors\jira\full_sync.json `
  --output-md .tmp\jira.md `
  --output-page-index .tmp\jira-page-index.json
```

## Skill-ready retrieval toolkit CLI

入口：

```powershell
python scripts/retrieval/toolkit_cli.py <command> [args]
```

### `toolkit_cli.py index`

用途：从 corpus 构建 retrieval index，并可选写出 PageIndex artifact。

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--corpus` | 是 | corpus 或 snapshot 文档 JSON 路径。 |
| `--output-page-index` | 否 | 写出 PageIndex artifact，形状为 `{"entries": [...]}`。 |

案例：

```powershell
python scripts/retrieval/toolkit_cli.py index --corpus fixtures\retrieval\pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py index --corpus fixtures\retrieval\pageindex_corpus.json --output-page-index .tmp\page-index.json
```

### `toolkit_cli.py search`

用途：在 corpus 中检索 query，或直接读取已导出的 PageIndex artifact。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `query` | 是 | 无 | 检索文本。 |
| `--corpus` | 与 `--page-index` 二选一 | 无 | corpus 路径，会从 canonical documents 重建 PageIndex。 |
| `--page-index` | 与 `--corpus` 二选一 | 无 | PageIndex artifact 路径，直接消费 `{"entries": [...]}`。 |
| `--snapshot-dir` | 与 `--corpus`、`--page-index` 三选一 | 无 | snapshot 目录，直接复用其中的 `page_index.json`。 |
| `--policies` | 否 | `team:ssd public` | ACL policies。 |

案例：

```powershell
python scripts/retrieval/toolkit_cli.py search "flush command" --corpus fixtures\retrieval\pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py search "flush command" --page-index .tmp\page-index.json
python scripts/retrieval/toolkit_cli.py search "flush command" --snapshot-dir .tmp\snapshot
```

### `toolkit_cli.py citation`

用途：在 corpus 中检索 query 并生成引用输出，或直接读取已导出的 PageIndex artifact。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `query` | 是 | 无 | 检索文本。 |
| `--corpus` | 与 `--page-index` 二选一 | 无 | corpus 路径，会从 canonical documents 重建 PageIndex。 |
| `--page-index` | 与 `--corpus` 二选一 | 无 | PageIndex artifact 路径，直接消费 `{"entries": [...]}`。 |
| `--snapshot-dir` | 与 `--corpus`、`--page-index` 三选一 | 无 | snapshot 目录，直接复用其中的 `page_index.json`。 |
| `--policies` | 否 | `team:ssd public` | ACL policies。 |

案例：

```powershell
python scripts/retrieval/toolkit_cli.py citation "flush command" --corpus fixtures\retrieval\pageindex_corpus.json
python scripts/retrieval/toolkit_cli.py citation "flush command" --page-index .tmp\page-index.json
python scripts/retrieval/toolkit_cli.py citation "flush command" --snapshot-dir .tmp\snapshot
```

## Snapshot CLI

入口：

```powershell
python scripts/retrieval/snapshot_cli.py <command> [args]
```

### `snapshot_cli.py create`

用途：从 corpus 创建本地 snapshot。

参数：

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--snapshot-dir` | 是 | 无 | snapshot 目录。 |
| `--corpus` | 是 | 无 | corpus 路径。 |
| `--source-name` | 否 | `manual` | source 名称。 |
| `--cursor` | 否 | 无 | source cursor。 |
| `--sync-type` | 否 | `full` | 同步类型。 |

案例：

```powershell
python scripts/retrieval/snapshot_cli.py create `
  --snapshot-dir .tmp\snapshot `
  --corpus fixtures\retrieval\pageindex_corpus.json `
  --source-name manual
```

### `snapshot_cli.py show`

用途：查看 snapshot manifest 和状态。

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--snapshot-dir` | 是 | snapshot 目录。 |

案例：

```powershell
python scripts/retrieval/snapshot_cli.py show --snapshot-dir .tmp\snapshot
```

### `snapshot_cli.py refresh`

用途：用 Jira 或 Confluence sync payload 刷新 snapshot。

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--snapshot-dir` | 是 | snapshot 目录。 |
| `--sync-payload` | 是 | sync payload 路径。 |
| `--source-name` | 是 | source 名称，例如 `jira` 或 `confluence`。 |

案例：

```powershell
python scripts/retrieval/snapshot_cli.py refresh `
  --snapshot-dir .tmp\snapshot `
  --sync-payload fixtures\connectors\jira\incremental_sync.json `
  --source-name jira
```

## 常见问题

### Jira 401

`urllib.error.HTTPError: HTTP Error 401` 表示 Jira 不接受认证头。

排查：

1. Jira Cloud 通常用 `--username "you@example.com" --token $env:JIRA_TOKEN --auth-mode basic`。
2. Jira Server/Data Center PAT 通常用 `--token $env:JIRA_TOKEN --auth-mode bearer`。
3. 确认 `--base-url` 包含实际根路径，例如 `/jira`。
4. 确认账号有目标项目权限。

### Live connector 拉不到数据

先把 query 简化到最小：

```powershell
--jql "project = SSD ORDER BY updated ASC"
```

如果 Jira UI 中同一条 JQL 查不到数据，CLI 也不会查到数据。

### 什么时候用 `platform_cli.py ingest`，什么时候用 `normalize_cli.py`

- 只想看 canonical JSON：用 `platform_cli.py ingest`。
- 想同时写 Markdown 和 PageIndex：用 `scripts/ingest/normalize_cli.py --output-md --output-page-index`。

### 什么时候用 `platform_cli.py search`，什么时候用 `toolkit_cli.py search`

- 平台日常命令：用 `platform_cli.py search`，有默认 corpus。
- 把检索功能封装给外部 skill 或工具：用 `scripts/retrieval/toolkit_cli.py search`，显式传 `--corpus`。

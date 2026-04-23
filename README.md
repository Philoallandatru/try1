# SSD Knowledge Portal

**本地化知识平台，用于 SSD 工程团队的智能检索和问答**

通过统一的 Web 界面管理 Jira、Confluence、PDF 规范和设计文档，提供基于本地 LLM 的深度分析和每日报告。

---

## 快速开始

### 1. 安装依赖

```powershell
# 使用 uv（推荐）
python -m pip install --upgrade uv
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -e .

# 或使用标准 pip
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

### 2. 启动 Portal Runner

```powershell
# 启动后端服务器（端口 8787）
python -m apps.portal_runner.server

# 或指定主机和端口
python -m apps.portal_runner.server --host 0.0.0.0 --port 8787
```

浏览器访问 `http://localhost:8787`

### 3. 配置数据源

**通过 Web UI：**

1. 点击 "Sources" → "Add Source"
2. 选择类型（Jira / Confluence / File Upload）
3. 填写连接信息
4. 测试连接
5. 开始同步

**支持的数据源：**
- **Jira** - 单个 Issue、整个 Project 或 JQL 查询
- **Confluence** - 单个 Page 或整个 Space
- **文件上传** - PDF、DOCX、XLSX、PPTX（自动使用 MinerU 解析）

### 4. 运行分析

**单 Issue 深度分析：**
1. 在 Issues 列表中选择一个 Jira Issue
2. 点击 "Deep Analysis"
3. 系统自动检索相关规范、设计文档、关联 Issue
4. 本地 LLM 生成综合分析报告
5. 结果保存到知识库 `workspace/knowledge/issues/{issue_id}/`

**每日报告（渐进式生成）：**
1. 点击 "Generate Daily Report"
2. 5 秒内获得快速报告（基于 Issue 字段）
3. 后台自动对每个 Issue 进行深度分析
4. 报告实时更新（通过 WebSocket）
5. 完整报告保存到 `workspace/knowledge/reports/daily/{date}/`

---

## 核心功能

### 📊 统一数据源管理

- **智能配置向导** - 3 步完成 Jira/Confluence 连接
- **增量同步** - 初始全量 + 后续增量更新
- **连接测试** - 实时验证凭证和权限
- **同步状态** - 可视化进度和错误处理

### 🔍 多策略检索

- **BM25** - 快速关键词匹配
- **语义检索** - 向量相似度搜索
- **混合检索** - 加权组合（当前默认）
- **结构感知** - 基于文档结构（章节、表格、条款）提升相关性
- **LLM 重排序** - 使用本地 LLM 重新排序 Top-K 结果

**质量评估：**
- Golden Dataset 自动评估
- Recall@5、Precision@5、MRR 指标
- 策略对比和参数调优

### 🤖 本地 LLM 分析

- **深度分析** - 单 Issue 综合分析（< 30 秒）
- **每日报告** - 渐进式生成（快速版 < 5 秒，完整版 < 5 分钟）
- **引用追踪** - 所有结论都有源文档引用
- **可配置后端** - LM Studio / Ollama / Mock

### 📚 内部知识库

- **结构化存储** - `workspace/knowledge/{issues|reports}`
- **跨类型检索** - 统一搜索 Issues 和 Reports
- **版本历史** - 保留分析演进过程
- **Markdown 格式** - 易读易编辑

---

## 技术架构

### 数据流

```
数据源 → 连接器 → 规范化文档 → 投影层 → 检索 → 分析 → 知识库
                              ↓
                    Markdown（可读）
                    PageIndex（检索）
```

### 信任模型

- **Canonical Document** = 真实来源（Source of Truth）
- **Markdown** = 人类可读投影
- **PageIndex** = 检索投影
- **分析结果** = 派生知识（存储在知识库）

### 核心组件

**后端：**
- Python 3.11+, FastAPI
- MinerU（PDF/Office 解析）
- BM25 + Sentence Transformers（检索）
- LM Studio（本地 LLM）

**前端：**
- React 18, TypeScript
- TanStack Query（数据获取）
- Tailwind CSS（样式）
- WebSocket（实时更新）

**存储：**
- 本地优先（无云依赖）
- 基于 Git 的工作空间
- 文件系统知识库

---

## 使用场景

### 场景 1：新人快速上手

**问题：** 新工程师需要理解 NVMe Flush Command 的实现

**解决方案：**
1. 在 Portal 中搜索 "NVMe flush command"
2. 系统检索相关 Jira Issues、Confluence 设计文档、NVMe Spec
3. 查看引用和源文档
4. 点击 "Deep Analysis" 获取综合分析

**结果：** 30 分钟内理解完整上下文，而非花费数小时翻阅文档

### 场景 2：每日站会准备

**问题：** PM 需要准备每日站会，了解昨天的进展

**解决方案：**
1. 点击 "Generate Daily Report"
2. 5 秒内获得快速摘要（Issue 状态、优先级、更新）
3. 后台自动深度分析每个 Issue
4. 15 分钟后获得完整报告（根因分析、关联上下文、建议）

**结果：** 节省 30+ 分钟手动整理时间，获得更深入的洞察

### 场景 3：规范查询

**问题：** 工程师需要查找 PCIe 规范中的特定章节

**解决方案：**
1. 上传 PCIe Spec PDF（自动 MinerU 解析）
2. 搜索 "PCIe TLP format"
3. 系统返回相关章节、表格、图表
4. 点击引用直接跳转到 PDF 页面

**结果：** 秒级查找，而非手动翻阅数百页 PDF

---

## 高级功能

### 检索评估

创建 Golden Dataset 评估检索质量：

```yaml
# eval/golden_queries.yaml
golden_queries:
  - id: "jira-root-cause-1"
    query: "Why did the NVMe flush command fail?"
    expected_documents:
      - document_id: "SSD-777"
        relevance: 1.0
```

运行评估：

```powershell
python scripts/platform_cli.py eval --dataset eval/golden_queries.yaml
```

### 工作空间管理

详细的启动和配置说明请参考 [STARTUP_GUIDE.md](STARTUP_GUIDE.md)。

前端开发相关文档：
- [前端 README](apps/portal_web/README.md)
- [API 文档](apps/portal_web/API.md)
- [性能监控](apps/portal_web/PERFORMANCE.md)
- [工作空间管理](apps/portal_web/WORKSPACE_MANAGER.md)

---

## 配置

### 环境变量

```powershell
# Jira
$env:JIRA_BASE_URL = "https://jira.example.com"
$env:JIRA_TOKEN = "your-token"

# Confluence
$env:CONFLUENCE_BASE_URL = "https://confluence.example.com"
$env:CONFLUENCE_TOKEN = "your-token"

# LM Studio
$env:LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
$env:LM_STUDIO_MODEL = "qwen2.5-coder-7b-instruct"
```

### LM Studio 设置

1. 下载并安装 [LM Studio](https://lmstudio.ai/)
2. 下载模型（推荐：qwen2.5-coder-7b-instruct）
3. 启动本地服务器（端口 1234）
4. Portal 自动连接

**支持的后端：**
- `lm-studio` - LM Studio OpenAI-compatible API（推荐）
- `ollama` - Ollama 本地服务
- `mock` - 测试用 Mock 后端
- `none` - 仅提取式回答（无 LLM）

---

## 项目结构

```
codex-try/
├── apps/                    # 应用层
│   ├── portal_runner/      # Portal Runner 后端 API
│   └── portal_web/         # Portal Web 前端
├── services/               # 服务层
│   ├── connectors/         # Jira/Confluence 连接器
│   ├── ingest/            # 文件解析（MinerU/pypdf）
│   ├── retrieval/         # 检索引擎
│   └── analysis/          # LLM 分析服务
├── packages/              # 共享包
│   ├── schema/           # 数据模型
│   ├── acl/              # 访问控制
│   └── terminology/      # 术语管理
├── fixtures/             # 测试数据
├── docs/                # 文档
│   ├── redesign-2026-spec.md    # 2026 重新设计规范
│   ├── architecture-overview.md  # 架构概览
│   └── environment-setup.md      # 环境设置
└── tests/               # 单元测试
```

---

## 文档

### 用户文档
- [环境设置](docs/environment-setup.md) - Python、MinerU、LM Studio 配置
- [平台 CLI 指南](docs/platform-cli-guide.zh.md) - 命令行工具使用
- [工作空间 CLI 指南](docs/workspace-cli-guide.md) - 工作空间管理

### 技术文档
- [2026 重新设计规范](docs/redesign-2026-spec.md) - 最新架构设计
- [架构概览](docs/architecture-overview.md) - 系统架构
- [实现状态](docs/implementation-status.md) - 开发进度
- [P0 完成状态](docs/P0-completion-status.md) - 里程碑状态

### 开发文档
- [开发者工作流](docs/developer-workflow.md) - 开发指南
- [API 契约](docs/api-contracts.md) - API 规范
- [CLI 参考](docs/cli-reference.md) - 命令行参考

---

## 开发

### 运行测试

```powershell
# 所有测试
python -m unittest discover

# 特定模块
python -m unittest tests.test_jira_connector

# 检索评估
python scripts/eval/run_recall_eval.py --dataset eval/gold_queries.yaml

# Phase 1 门禁
python scripts/gates/run_phase1_gate.py
```

### 代码风格

```powershell
# 格式化
black .

# 类型检查
mypy services/ apps/

# Lint
ruff check .
```

---

## 路线图

### ✅ Phase A-D: 基础设施（已完成 ~90%）

- [x] 四种数据源转换（Jira/Confluence/PDF/Office）
- [x] 统一 PageIndex 格式
- [x] 多策略检索
- [x] 本地 LLM 集成
- [x] Portal Runner Web UI
- [ ] 文档更新和验证

### 🚧 Phase 1: 重新设计实现（进行中）

- [ ] 统一 Source 模型和 API
- [ ] 增量同步策略
- [ ] 智能配置向导
- [ ] Golden Dataset 评估
- [ ] 深度分析功能
- [ ] 渐进式每日报告

### 🔜 Phase 2: 检索优化（计划中）

- [ ] 结构感知检索
- [ ] LLM 重排序
- [ ] 策略对比仪表板
- [ ] 自动参数调优

### 🔜 Phase 3: 高级功能（未来）

- [ ] 多工作空间支持
- [ ] 协作功能
- [ ] 高级聚类和摘要
- [ ] 生产级 OCR 管道

---

## 常见问题

### Q: 需要云服务吗？

**A:** 不需要。所有功能都在本地运行，包括 LLM（通过 LM Studio）。数据不会离开你的机器。

### Q: 支持哪些 LLM 模型？

**A:** 任何 OpenAI-compatible API 的模型。推荐：
- qwen2.5-coder-7b-instruct（代码理解）
- llama-3.1-8b-instruct（通用）
- deepseek-coder-6.7b（代码生成）

### Q: 可以连接多个 Jira 实例吗？

**A:** 可以。每个 Source 独立配置，支持多个 Jira/Confluence 实例。

### Q: 检索质量如何评估？

**A:** 通过 Golden Dataset 自动评估。创建包含预期结果的查询集，系统计算 Recall@5、Precision@5、MRR 指标。

### Q: 支持中文吗？

**A:** 支持。检索和 LLM 分析都支持中文内容。推荐使用 qwen 系列模型以获得更好的中文效果。

---

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)（待创建）。

---

## 许可证

内部项目，仅供 SSD 团队使用。

---

## 支持

- **文档：** [docs/](docs/)
- **问题反馈：** 创建 GitHub Issue
- **帮助命令：** `python scripts/platform_cli.py --help`

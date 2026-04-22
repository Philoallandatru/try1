# Qwen3.5-4b 模型集成指南

本文档说明如何在 Codex 系统中集成和使用 Qwen3.5-4b 模型进行 Jira 问题分析。

## 前置条件

### 1. 安装 Ollama

Ollama 是一个本地运行大语言模型的工具。

**Windows:**
```bash
# 下载并安装 Ollama
# 访问: https://ollama.ai/download
```

**Linux/Mac:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. 拉取 Qwen 模型

```bash
# 拉取 Qwen2.5 4B 模型（约 2.5GB）
ollama pull qwen2.5:4b

# 验证模型已安装
ollama list
```

### 3. 启动 Ollama 服务

```bash
# Ollama 通常会自动启动服务
# 如果需要手动启动:
ollama serve
```

服务默认运行在 `http://localhost:11434`

## 快速测试

### 1. 基本功能测试

```bash
# 运行集成测试脚本
python test_qwen_integration.py
```

### 2. 命令行测试

```bash
# 使用 Ollama CLI 直接测试
ollama run qwen2.5:4b "请用一句话介绍 BM25 算法"
```

## 在 Codex 中使用

### 1. 使用 CLI 进行 Jira 分析

```bash
# 分析 Jira 问题
python scripts/platform_cli.py jira-analysis \
  --source fixtures/connectors/jira/issue_with_sprint_epic.json \
  --llm-backend ollama \
  --llm-model qwen2.5:4b \
  --output-format markdown

# 生成 Sprint 报告
python scripts/platform_cli.py jira-analysis \
  --source fixtures/connectors/jira/issue_with_sprint_epic.json \
  --llm-backend ollama \
  --llm-model qwen2.5:4b \
  --report-type sprint-summary \
  --output analysis_report.md
```

### 2. 在 Python 代码中使用

```python
from services.analysis.llm_backends import build_llm_backend
from services.connectors.jira.connector import load_jira_sync

# 创建 LLM 后端
backend = build_llm_backend(
    backend="ollama",
    model="qwen2.5:4b",
    base_url="http://localhost:11434",
    timeout_seconds=120,
)

# 加载 Jira 数据
result = load_jira_sync("path/to/jira_sync.json")
doc = result["documents"][0]

# 构建提示词
prompt = f"""
分析以下 Jira 问题:
- 问题: {doc['document_id']}
- 标题: {doc['title']}
- Sprint: {doc['sprints'][0]['name'] if doc['sprints'] else '无'}
- Epic: {doc['epic']['key'] if doc.get('epic') else '无'}

请提供问题概述和风险评估。
"""

# 生成分析
response = backend.generate(prompt)
print(response)
```

## 模型配置

### 支持的后端

1. **Ollama** (推荐用于本地开发)
   - 模型: `qwen2.5:4b`, `qwen2.5:7b`, `qwen2.5:14b`
   - 优点: 本地运行，隐私保护，无需 API key
   - 缺点: 需要本地资源

2. **OpenAI Compatible** (用于生产环境)
   - 支持任何 OpenAI 兼容的 API
   - 可以使用云端 Qwen 服务

### 性能优化

**Qwen2.5:4b 模型规格:**
- 参数量: 4B
- 内存需求: ~4GB RAM
- 推理速度: ~20-30 tokens/s (CPU), ~100+ tokens/s (GPU)
- 上下文长度: 32K tokens

**优化建议:**
1. 使用 GPU 加速（如果可用）
2. 调整 `timeout_seconds` 参数适应网络和硬件
3. 批量处理多个问题以提高效率

## 功能示例

### 1. Sprint 进度分析

```python
# 分析 Sprint 中所有问题的进度
sprint_issues = [doc for doc in documents if doc.get('sprints')]

prompt = f"""
分析 Sprint {sprint_name} 的进度:
- 总问题数: {len(sprint_issues)}
- 已完成: {completed_count}
- 进行中: {in_progress_count}
- 待处理: {todo_count}

请评估 Sprint 是否能按时完成，并提出建议。
"""
```

### 2. Epic 关联分析

```python
# 分析 Epic 下的所有问题
epic_issues = [doc for doc in documents if doc.get('epic', {}).get('key') == epic_key]

prompt = f"""
分析 Epic {epic_key} 的整体情况:
- 子问题数: {len(epic_issues)}
- 涉及的 Sprint: {sprint_list}
- 关键依赖: {dependencies}

请评估 Epic 的完成风险和时间线。
"""
```

### 3. 评论情感分析

```python
# 分析问题评论的情感和关注点
comments = doc.get('comment_metadata', [])

prompt = f"""
分析以下评论的情感和关键信息:
{comments_text}

请识别:
1. 团队关注的主要问题
2. 情感倾向（积极/消极/中性）
3. 需要升级的风险
"""
```

## 故障排查

### 问题 1: Ollama 服务未启动

```bash
# 检查服务状态
curl http://localhost:11434/api/tags

# 如果失败，手动启动
ollama serve
```

### 问题 2: 模型未找到

```bash
# 列出已安装的模型
ollama list

# 重新拉取模型
ollama pull qwen2.5:4b
```

### 问题 3: 超时错误

```python
# 增加超时时间
backend = build_llm_backend(
    backend="ollama",
    model="qwen2.5:4b",
    timeout_seconds=300,  # 增加到 5 分钟
)
```

### 问题 4: 内存不足

```bash
# 使用更小的模型
ollama pull qwen2.5:1.5b

# 或者限制并发请求数
```

## 下一步

1. **Phase 3 完成**: 实现完整的 Jira 分析功能
2. **Confluence 分析**: 扩展到 Confluence 文档分析
3. **自定义提示词**: 根据团队需求定制分析模板
4. **批量处理**: 实现高效的批量分析流程
5. **结果缓存**: 缓存分析结果以提高性能

## 参考资源

- [Ollama 官方文档](https://ollama.ai/docs)
- [Qwen 模型介绍](https://github.com/QwenLM/Qwen)
- [OpenAI API 兼容性](https://platform.openai.com/docs/api-reference)

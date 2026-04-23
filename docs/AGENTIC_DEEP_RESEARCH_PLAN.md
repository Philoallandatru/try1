# Agentic Deep Research 实施方案

## 概述

本文档描述如何在现有 BM25 检索系统基础上实现 Agentic Deep Research 功能。

## 核心价值

### 当前检索 vs Deep Research

```
【当前 BM25 检索】
用户查询 → 检索 Top-K → 返回结果
- 单次检索
- 浅层匹配
- 无推理链

【Agentic Deep Research】
用户查询 → Agent 规划 → 多轮检索 → 推理综合 → 深度报告
- 多轮迭代
- 深度分析
- 推理链追踪
```

### 适用场景

**需要 Deep Research 的场景**：
- ❌ "NVMe 规范中 Admin Command Set 的定义是什么？" → 单次检索即可
- ✅ "为什么我的 SSD 在高负载下性能下降 30%？" → 需要多轮推理
  1. 检索性能下降的常见原因
  2. 检索温度管理机制
  3. 检索固件日志分析方法
  4. 综合诊断报告

## 1. 是否需要引入 Agent 框架？

### 初级阶段（无框架）

可以先用简单的循环 + 状态机实现：

```python
# 简单的多轮检索
def simple_deep_research(query):
    context = []
    for round in range(3):
        # 基于上下文改写查询
        refined_query = llm.refine_query(query, context)
        # 检索
        results = retriever.search(refined_query)
        # 分析结果，决定是否继续
        analysis = llm.analyze(results)
        context.append(analysis)
        if analysis.is_sufficient:
            break
    return llm.synthesize(context)
```

### 进阶阶段（推荐框架）

当需要以下能力时，建议引入框架：
- **多 Agent 协作**：一个 Agent 负责查询规划，一个负责检索，一个负责综合
- **复杂决策树**：根据检索结果动态调整策略
- **工具调用**：除了检索，还需要调用计算器、代码执行器等

**推荐框架**：
1. **LangGraph**（推荐）：适合复杂的状态流转，可视化好
2. **AutoGen**：适合多 Agent 对话式协作
3. **CrewAI**：适合角色分工明确的场景

## 2. 是否需要 Memory 框架？

**强烈推荐**，这是 Deep Research 的核心。

### Memory 的作用

```
第1轮：查询 "NVMe 黑屏问题"
  ↓ 检索到：可能是驱动问题
  ↓ 存入 Memory

第2轮：基于 Memory 追问 "NVMe 驱动版本兼容性"
  ↓ 检索到：某些版本有 bug
  ↓ 更新 Memory

第3轮：基于 Memory 查询 "如何回退驱动"
  ↓ 检索到：具体步骤
  ↓ 综合 Memory 生成完整报告
```

### Memory 类型

1. **短期记忆**（当前会话）：
   - 已检索的文档 ID（避免重复）
   - 已回答的子问题
   - 当前推理链

2. **长期记忆**（跨会话）：
   - 用户历史问题模式
   - 常见问题的最佳检索路径
   - 领域知识图谱

### 实现方案

- **简单方案**：用 Python dict + JSON 持久化
- **框架方案**：
  - **LangChain Memory**：ConversationBufferMemory, VectorStoreMemory
  - **Mem0**：专门的 AI Memory 框架
  - **Redis + 向量数据库**：高性能方案

## 3. 现有检索实现作为地基

### 当前系统的优势

✅ **BM25 检索**：成熟稳定，适合精确匹配  
✅ **评估系统**：可以量化 Deep Research 的检索质量  
✅ **多文档类型**：PDF、Jira、Confluence 都支持  
✅ **API 化**：易于被 Agent 调用  

### 需要扩展的部分

```python
# 当前：单次检索
results = retrieval_api.search(query, top_k=10)

# Deep Research：多轮迭代检索
class DeepResearchEngine:
    def __init__(self, retrieval_api, llm):
        self.retrieval_api = retrieval_api  # 复用现有检索
        self.llm = llm
        self.memory = Memory()
    
    def research(self, query):
        # 第1步：查询分解
        sub_queries = self.llm.decompose_query(query)
        
        # 第2步：多轮检索
        for sub_q in sub_queries:
            # 复用现有检索 API
            results = self.retrieval_api.search(sub_q, top_k=5)
            
            # 分析结果
            analysis = self.llm.analyze(results)
            self.memory.add(sub_q, analysis)
            
            # 动态生成后续查询
            if analysis.needs_more_info:
                follow_up = self.llm.generate_follow_up(analysis)
                sub_queries.append(follow_up)
        
        # 第3步：综合报告
        return self.llm.synthesize(self.memory.get_all())
```

### 建议的架构

```
┌─────────────────────────────────────┐
│   Deep Research Agent (新增)         │
│  - 查询规划                          │
│  - 多轮迭代                          │
│  - 结果综合                          │
└──────────┬──────────────────────────┘
           │ 调用
           ↓
┌─────────────────────────────────────┐
│   Retrieval API (现有，复用)         │
│  - BM25 检索                         │
│  - 评估系统                          │
│  - 索引管理                          │
└─────────────────────────────────────┘
```

## 4. 模型规模需求

### Qwen3.5-35B 适用性分析

**完全适用，甚至可能过大**：

| 任务 | 推荐模型规模 | Qwen3.5-35B 是否适用 |
|------|-------------|---------------------|
| 查询改写 | 7B-14B | ✅ 过剩但可用 |
| 结果分析 | 14B-35B | ✅ 合适 |
| 推理规划 | 35B+ | ✅ 合适 |
| 综合报告 | 35B-70B | ✅ 合适 |

### 混合模型策略（成本优化）

```python
class DeepResearchEngine:
    def __init__(self):
        self.small_model = Qwen3.5_7B   # 查询改写、简单分析
        self.large_model = Qwen3.5_35B  # 复杂推理、综合报告
    
    def research(self, query):
        # 用小模型做查询改写（省钱）
        sub_queries = self.small_model.decompose(query)
        
        # 用大模型做深度分析（质量）
        analysis = self.large_model.analyze(results)
        
        # 用大模型生成最终报告
        return self.large_model.synthesize(context)
```

### 模型选择建议

1. **Qwen3.5-7B**：
   - 查询改写、关键词提取
   - 简单的相关性判断
   - 成本低，速度快

2. **Qwen3.5-14B**：
   - 中等复杂度的推理
   - 结果排序和过滤
   - 性价比最高

3. **Qwen3.5-35B**：
   - 复杂的多步推理
   - 综合分析和报告生成
   - 质量最高，但成本较高

## 实施路线

### Phase 1：最小可行方案（2周）

- ❌ 不引入框架
- ✅ 简单的 3 轮迭代检索
- ✅ 基于 dict 的简单 Memory
- ✅ 复用现有 Retrieval API
- ✅ 使用 Qwen3.5-14B

**交付物**：
- `packages/deep_research/simple_engine.py`
- `packages/deep_research/memory.py`
- 基础 API 端点

### Phase 2：引入框架（4周）

- ✅ 引入 LangGraph
- ✅ 实现 Memory 持久化
- ✅ 多 Agent 协作（规划 + 检索 + 综合）
- ✅ 混合模型策略（7B + 35B）

**交付物**：
- LangGraph 状态图定义
- 多 Agent 协作流程
- Memory 持久化层
- 前端界面

### Phase 3：优化增强（持续）

- 向量检索 + BM25 混合
- 知识图谱增强
- 用户反馈学习
- 性能优化

## 技术栈建议

### 核心依赖

```toml
[dependencies]
# Agent 框架
langgraph = "^0.2.0"
langchain = "^0.3.0"

# Memory
redis = "^5.0.0"
chromadb = "^0.5.0"  # 向量存储

# LLM
openai = "^1.0.0"  # 兼容 Qwen API
anthropic = "^0.40.0"  # 可选

# 现有依赖（保留）
rank-bm25 = "^0.2.2"
jieba = "^0.42.1"
```

### 目录结构

```
packages/deep_research/
├── __init__.py
├── engine.py              # 主引擎
├── memory.py              # Memory 管理
├── agents/
│   ├── planner.py         # 查询规划 Agent
│   ├── retriever.py       # 检索 Agent
│   └── synthesizer.py     # 综合 Agent
├── graph.py               # LangGraph 状态图
└── models.py              # 数据模型

apps/portal_runner/
├── deep_research_api.py   # API 层
└── deep_research_routes.py # REST 端点

apps/portal_web/src/
└── DeepResearchPage.tsx   # 前端界面
```

## 关键设计决策

### 1. 为什么复用现有检索？

- ✅ BM25 检索已经过评估验证
- ✅ 避免重复开发
- ✅ 保持系统一致性

### 2. 为什么推荐 LangGraph？

- ✅ 状态流转可视化
- ✅ 易于调试和监控
- ✅ 支持复杂的条件分支
- ✅ 与 LangChain 生态集成

### 3. 为什么需要 Memory？

- ✅ 避免重复检索相同内容
- ✅ 保持推理链的连贯性
- ✅ 支持多轮对话
- ✅ 学习用户偏好

## 评估指标

### Deep Research 质量指标

1. **检索效率**：
   - 平均检索轮数
   - 重复检索率
   - 检索覆盖率

2. **答案质量**：
   - 完整性（是否回答所有子问题）
   - 准确性（事实正确性）
   - 连贯性（推理链是否合理）

3. **用户体验**：
   - 响应时间
   - 用户满意度
   - 后续追问率

### 评估方法

- 复用现有的 Golden Dataset
- 添加 Deep Research 专用测试集
- A/B 测试：单次检索 vs Deep Research

## 风险与挑战

### 技术风险

1. **成本控制**：多轮 LLM 调用成本高
   - 缓解：混合模型策略，缓存中间结果

2. **响应延迟**：多轮检索耗时长
   - 缓解：流式输出，异步处理

3. **质量保证**：Agent 可能陷入循环
   - 缓解：设置最大轮数，添加终止条件

### 业务风险

1. **用户期望管理**：Deep Research 不是万能的
   - 缓解：明确适用场景，提供降级方案

2. **维护成本**：Agent 系统复杂度高
   - 缓解：充分的日志和监控，模块化设计

## 参考资料

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [Mem0 框架](https://github.com/mem0ai/mem0)
- [Deep Research 论文](https://arxiv.org/abs/2401.12345)
- [Qwen 模型文档](https://github.com/QwenLM/Qwen)

## 更新日志

- 2025-01-XX: 初始版本

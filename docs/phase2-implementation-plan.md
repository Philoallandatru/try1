# Phase 2 实施计划 - 检索系统

**目标**: 实现多策略检索系统和评估框架  
**时间**: Weeks 3-4  
**状态**: 🚀 准备开始

---

## 概述

Phase 2 专注于构建高质量的检索系统，支持多种检索策略并通过 Golden Dataset 进行评估。

### 核心目标
1. ✅ **多策略检索**: BM25、语义搜索、混合检索、结构感知、LLM 重排序
2. ✅ **Golden Dataset**: 20-50 个查询的评估数据集
3. ✅ **自动化评估**: Recall@5、Precision@5、MRR 指标
4. ✅ **策略对比**: 可视化不同策略的性能
5. ✅ **检索 API**: 统一的检索服务接口

---

## 任务分解

### Task #14: 向量化和索引系统 (优先级: P0)
**描述**: 实现文档向量化和向量索引存储

**子任务**:
1. 选择嵌入模型（本地模型 vs API）
   - 推荐: `sentence-transformers/all-MiniLM-L6-v2` (本地，快速)
   - 备选: OpenAI `text-embedding-3-small` (API，高质量)

2. 实现向量化服务
   - 文档分块策略（chunk size, overlap）
   - 批量向量化接口
   - 向量缓存机制

3. 向量存储选择
   - 推荐: ChromaDB (轻量级，易集成)
   - 备选: FAISS (高性能，需要额外管理)
   - 备选: Qdrant (功能丰富，需要独立服务)

4. 索引管理
   - 创建/更新/删除索引
   - 增量索引更新（新文档自动向量化）
   - 索引持久化

**文件**:
- `packages/retrieval/embedding_service.py` - 向量化服务
- `packages/retrieval/vector_store.py` - 向量存储抽象
- `packages/retrieval/chromadb_store.py` - ChromaDB 实现
- `packages/retrieval/test_embedding.py` - 测试

**验收标准**:
- ✅ 文档可以被向量化并存储
- ✅ 支持批量向量化（>100 docs/sec）
- ✅ 向量索引持久化到磁盘
- ✅ 增量更新正常工作

---

### Task #15: BM25 检索实现 (优先级: P0)
**描述**: 实现基于关键词的 BM25 检索

**子任务**:
1. 选择 BM25 库
   - 推荐: `rank-bm25` (纯 Python，简单)
   - 备选: Elasticsearch (功能强大，但重量级)

2. 实现 BM25 索引
   - 文档预处理（分词、停用词）
   - BM25 参数调优（k1, b）
   - 索引持久化

3. 实现 BM25 搜索
   - 查询预处理
   - Top-K 检索
   - 结果评分

**文件**:
- `packages/retrieval/bm25_retriever.py` - BM25 检索器
- `packages/retrieval/test_bm25.py` - 测试

**验收标准**:
- ✅ BM25 检索返回相关文档
- ✅ 检索速度 < 100ms (1000 文档)
- ✅ 支持中英文查询

---

### Task #16: 语义检索实现 (优先级: P0)
**描述**: 实现基于向量相似度的语义检索

**子任务**:
1. 实现语义搜索
   - 查询向量化
   - 向量相似度搜索（cosine similarity）
   - Top-K 检索

2. 优化检索性能
   - 向量索引优化（HNSW）
   - 批量查询支持
   - 结果缓存

**文件**:
- `packages/retrieval/semantic_retriever.py` - 语义检索器
- `packages/retrieval/test_semantic.py` - 测试

**验收标准**:
- ✅ 语义检索返回相关文档
- ✅ 检索速度 < 200ms (1000 文档)
- ✅ 支持同义词和语义相似查询

---

### Task #17: 混合检索实现 (优先级: P0)
**描述**: 实现 BM25 + 语义检索的混合策略

**子任务**:
1. 实现混合检索
   - BM25 和语义检索并行执行
   - 结果融合（Reciprocal Rank Fusion）
   - 权重调优（alpha 参数）

2. 实现结构感知检索
   - 根据文档结构加权（标题、章节、表格）
   - 元数据过滤（source_type, date_range）

**文件**:
- `packages/retrieval/hybrid_retriever.py` - 混合检索器
- `packages/retrieval/structure_aware_retriever.py` - 结构感知检索器
- `packages/retrieval/test_hybrid.py` - 测试

**验收标准**:
- ✅ 混合检索结合关键词和语义优势
- ✅ 结构感知检索提升相关性
- ✅ 可配置权重参数

---

### Task #18: LLM 重排序 (优先级: P1)
**描述**: 使用本地 LLM 对检索结果重排序

**子任务**:
1. 实现 LLM 重排序
   - 调用 LM Studio API
   - 生成相关性评分
   - 重排序 Top-K 结果

2. 优化重排序性能
   - 批量评分
   - 超时处理
   - 降级策略（LLM 不可用时）

**文件**:
- `packages/retrieval/llm_reranker.py` - LLM 重排序器
- `packages/retrieval/test_reranker.py` - 测试

**验收标准**:
- ✅ LLM 重排序提升相关性
- ✅ 重排序时间 < 2 秒（10 个文档）
- ✅ LLM 不可用时降级到混合检索

---

### Task #19: Golden Dataset 创建 (优先级: P0)
**描述**: 创建评估数据集

**子任务**:
1. 设计 Golden Dataset 格式
   - YAML 格式定义
   - 查询 + 期望文档 + 相关性评分

2. 创建初始数据集
   - 20-50 个真实查询
   - 覆盖不同查询类型（关键词、语义、混合）
   - 覆盖不同数据源（Jira、Confluence、PDF）

3. 数据集管理
   - 版本控制
   - 持续扩展机制

**文件**:
- `data/golden_dataset.yaml` - Golden Dataset
- `packages/retrieval/golden_dataset.py` - 数据集加载器
- `packages/retrieval/test_golden_dataset.py` - 测试

**验收标准**:
- ✅ 至少 20 个高质量查询
- ✅ 每个查询有明确的期望文档
- ✅ 覆盖多种查询类型和数据源

---

### Task #20: 评估框架 (优先级: P0)
**描述**: 实现自动化评估系统

**子任务**:
1. 实现评估指标
   - Recall@5: 相关文档召回率
   - Precision@5: 前 5 个结果的精确率
   - MRR: 平均倒数排名

2. 实现评估服务
   - 运行 Golden Dataset 查询
   - 计算评估指标
   - 生成评估报告

3. 策略对比
   - 并行评估多个策略
   - 生成对比报告
   - 可视化结果

**文件**:
- `packages/retrieval/evaluation.py` - 评估服务
- `packages/retrieval/metrics.py` - 评估指标
- `packages/retrieval/test_evaluation.py` - 测试

**验收标准**:
- ✅ 评估运行时间 < 1 分钟
- ✅ Recall@5 > 0.8
- ✅ 生成详细的评估报告

---

### Task #21: 检索 API 端点 (优先级: P0)
**描述**: 实现检索相关的 API 端点

**子任务**:
1. 实现检索 API
   - `POST /api/search` - 执行搜索
   - `GET /api/search/strategies` - 列出可用策略
   - `POST /api/search/evaluate` - 运行评估

2. 实现检索服务
   - 统一的检索接口
   - 策略选择和切换
   - 结果格式化

**文件**:
- `apps/portal_runner/retrieval_api.py` - 检索业务逻辑
- `apps/portal_runner/retrieval_routes.py` - FastAPI 路由
- `apps/portal_runner/test_retrieval_api.py` - 测试

**验收标准**:
- ✅ 所有 API 端点正常工作
- ✅ 支持所有检索策略
- ✅ 返回格式统一

---

### Task #22: 检索 UI (优先级: P1)
**描述**: 实现检索和评估的前端界面

**子任务**:
1. 实现搜索界面
   - 搜索框和策略选择
   - 结果展示（文档列表 + 评分）
   - 高亮显示匹配内容

2. 实现评估仪表板
   - 策略对比图表
   - 评估指标展示
   - Golden Dataset 管理

**文件**:
- `apps/portal_web/src/main.tsx` - 搜索和评估 UI
- `apps/portal_web/src/styles.css` - 样式

**验收标准**:
- ✅ 用户可以执行搜索并查看结果
- ✅ 用户可以对比不同策略
- ✅ 评估结果可视化清晰

---

### Task #23: Phase 2 集成测试 (优先级: P0)
**描述**: 端到端集成测试

**子任务**:
1. 测试完整检索流程
   - 文档向量化 → 索引 → 搜索 → 结果
   - 所有检索策略
   - 评估流程

2. 性能测试
   - 检索延迟
   - 索引构建时间
   - 评估运行时间

**文件**:
- `tests/phase2_integration_test.py` - 集成测试

**验收标准**:
- ✅ 所有测试通过
- ✅ 性能指标达标
- ✅ 评估指标 > 目标值

---

## 技术栈

### 核心库
- **向量化**: `sentence-transformers` (本地模型)
- **向量存储**: `chromadb` (轻量级向量数据库)
- **BM25**: `rank-bm25` (关键词检索)
- **LLM**: LM Studio API (本地 LLM)

### 可选库
- **FAISS**: 高性能向量检索（如果 ChromaDB 性能不足）
- **Qdrant**: 功能丰富的向量数据库（如果需要高级功能）
- **Elasticsearch**: 全文搜索引擎（如果需要企业级功能）

---

## 实施顺序

### Week 3: 核心检索功能
1. **Day 1-2**: Task #14 - 向量化和索引系统
2. **Day 3**: Task #15 - BM25 检索
3. **Day 4**: Task #16 - 语义检索
4. **Day 5**: Task #17 - 混合检索

### Week 4: 评估和优化
1. **Day 1**: Task #19 - Golden Dataset 创建
2. **Day 2**: Task #20 - 评估框架
3. **Day 3**: Task #21 - 检索 API
4. **Day 4**: Task #22 - 检索 UI
5. **Day 5**: Task #23 - 集成测试

### 可选任务（时间允许）
- Task #18 - LLM 重排序（提升检索质量）

---

## 成功标准

### 技术指标
- ✅ **Recall@5 > 0.8**: 80% 的相关文档在前 5 个结果中
- ✅ **Precision@5 > 0.6**: 前 5 个结果中 60% 是相关的
- ✅ **MRR > 0.7**: 第一个相关文档平均在前 2 个结果中
- ✅ **检索延迟 < 500ms**: 快速响应
- ✅ **评估时间 < 1 分钟**: 快速迭代

### 用户体验
- ✅ 用户可以通过 UI 执行搜索
- ✅ 用户可以选择不同的检索策略
- ✅ 用户可以查看评估结果和策略对比
- ✅ 搜索结果相关性高

---

## 风险和缓解

### 风险 1: 向量化性能不足
**缓解**: 使用批量向量化、缓存、异步处理

### 风险 2: 检索质量不达标
**缓解**: 通过 Golden Dataset 持续优化、调整参数、尝试不同策略

### 风险 3: LLM 重排序太慢
**缓解**: 限制重排序文档数量、使用更快的模型、实现降级策略

### 风险 4: 向量存储选择不当
**缓解**: 先用 ChromaDB 快速验证，如果性能不足再切换到 FAISS 或 Qdrant

---

## 下一步

准备开始 **Task #14: 向量化和索引系统**

需要确认：
1. 使用哪个嵌入模型？（推荐本地 `all-MiniLM-L6-v2`）
2. 使用哪个向量存储？（推荐 ChromaDB）
3. 是否需要支持中文？（如果需要，选择多语言模型）

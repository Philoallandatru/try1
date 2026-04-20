# Phase 2 简化实施计划 - BM25 检索系统

**目标**: 实现基于 BM25 的轻量级检索系统  
**时间**: Week 3  
**状态**: 🚀 准备开始

---

## 设计决策

### 为什么选择 BM25 而非向量检索？

1. **简单高效**: 无需训练模型、无需 GPU、无需向量数据库
2. **技术文档友好**: 对于技术文档（代码、规范、问题描述），关键词匹配效果很好
3. **可解释性强**: 用户可以理解为什么某个文档被检索到
4. **低延迟**: 毫秒级响应，无需等待向量计算
5. **易于调试**: 可以直接看到匹配的关键词

### 检索架构

```
文档 → 分词 → BM25 索引 → 检索 → 结果排序
                ↓
         (可选) 稀疏向量增强
```

**核心组件**:
- **BM25 索引**: 使用 `rank-bm25` 库
- **分词器**: 支持中英文分词
- **文档存储**: SQLite (已有)
- **可选增强**: SPLADE 稀疏向量（如果 BM25 效果不够好）

---

## 任务分解

### Task #14: BM25 检索核心 (优先级: P0)
**描述**: 实现 BM25 索引和检索功能

**子任务**:
1. 实现文档预处理
   - 中英文分词（jieba + nltk）
   - 停用词过滤
   - 文本规范化

2. 实现 BM25 索引
   - 使用 `rank-bm25` 库
   - 索引持久化（pickle）
   - 增量更新支持

3. 实现 BM25 检索
   - Top-K 检索
   - 结果评分
   - 高亮匹配词

**文件**:
- `packages/retrieval/__init__.py` - 包初始化
- `packages/retrieval/tokenizer.py` - 分词器
- `packages/retrieval/bm25_index.py` - BM25 索引
- `packages/retrieval/bm25_retriever.py` - BM25 检索器
- `packages/retrieval/test_bm25.py` - 测试

**验收标准**:
- ✅ 支持中英文文档检索
- ✅ 检索速度 < 100ms (1000 文档)
- ✅ 索引可以持久化和加载
- ✅ 支持增量更新

---

### Task #15: 文档索引管理 (优先级: P0)
**描述**: 实现文档索引的生命周期管理

**子任务**:
1. 索引构建
   - 从数据库读取所有文档
   - 批量构建索引
   - 进度显示

2. 索引更新
   - 监听数据源同步事件
   - 增量更新索引
   - 删除过期文档

3. 索引存储
   - 索引文件管理
   - 版本控制
   - 自动备份

**文件**:
- `packages/retrieval/index_manager.py` - 索引管理器
- `packages/retrieval/index_builder.py` - 索引构建器
- `packages/retrieval/test_index_manager.py` - 测试

**验收标准**:
- ✅ 可以构建完整索引
- ✅ 支持增量更新
- ✅ 索引文件自动管理

---

### Task #16: Golden Dataset 创建 (优先级: P0)
**描述**: 创建评估数据集

**子任务**:
1. 设计 Golden Dataset 格式
   ```yaml
   queries:
     - id: "q1"
       query: "NVMe flush command 失败原因"
       expected_docs:
         - doc_id: "SSD-777"
           relevance: 1.0
         - doc_id: "SSD-778"
           relevance: 0.8
   ```

2. 创建初始数据集
   - 20-30 个真实查询
   - 覆盖不同查询类型
   - 覆盖不同数据源

**文件**:
- `data/golden_dataset.yaml` - Golden Dataset
- `packages/retrieval/golden_dataset.py` - 数据集加载器

**验收标准**:
- ✅ 至少 20 个高质量查询
- ✅ 每个查询有明确的期望文档

---

### Task #17: 评估框架 (优先级: P0)
**描述**: 实现自动化评估系统

**子任务**:
1. 实现评估指标
   - Recall@K: 相关文档召回率
   - Precision@K: 前 K 个结果的精确率
   - MRR: 平均倒数排名
   - NDCG: 归一化折损累积增益

2. 实现评估服务
   - 运行 Golden Dataset 查询
   - 计算评估指标
   - 生成评估报告

**文件**:
- `packages/retrieval/evaluation.py` - 评估服务
- `packages/retrieval/metrics.py` - 评估指标
- `packages/retrieval/test_evaluation.py` - 测试

**验收标准**:
- ✅ 评估运行时间 < 30 秒
- ✅ Recall@5 > 0.7
- ✅ 生成详细的评估报告

---

### Task #18: 检索 API 端点 (优先级: P0)
**描述**: 实现检索相关的 API 端点

**子任务**:
1. 实现检索 API
   - `POST /api/search` - 执行搜索
   - `GET /api/search/stats` - 索引统计
   - `POST /api/search/rebuild` - 重建索引
   - `POST /api/search/evaluate` - 运行评估

2. 实现检索服务
   - 统一的检索接口
   - 结果格式化
   - 错误处理

**文件**:
- `apps/portal_runner/retrieval_api.py` - 检索业务逻辑
- `apps/portal_runner/retrieval_routes.py` - FastAPI 路由
- `apps/portal_runner/test_retrieval_api.py` - 测试

**验收标准**:
- ✅ 所有 API 端点正常工作
- ✅ 返回格式统一
- ✅ 错误处理完善

---

### Task #19: 检索 UI (优先级: P1)
**描述**: 实现检索的前端界面

**子任务**:
1. 实现搜索界面
   - 搜索框
   - 结果列表（文档标题、摘要、评分）
   - 高亮匹配词
   - 分页

2. 实现索引管理界面
   - 索引统计（文档数、索引大小）
   - 重建索引按钮
   - 索引状态显示

**文件**:
- `apps/portal_web/src/main.tsx` - 搜索 UI
- `apps/portal_web/src/styles.css` - 样式

**验收标准**:
- ✅ 用户可以执行搜索并查看结果
- ✅ 匹配词高亮显示
- ✅ 索引管理功能可用

---

### Task #20: Phase 2 集成测试 (优先级: P0)
**描述**: 端到端集成测试

**子任务**:
1. 测试完整检索流程
   - 文档索引 → 搜索 → 结果
   - 增量更新
   - 评估流程

2. 性能测试
   - 索引构建时间
   - 检索延迟
   - 评估运行时间

**文件**:
- `tests/phase2_integration_test.py` - 集成测试

**验收标准**:
- ✅ 所有测试通过
- ✅ 性能指标达标
- ✅ 评估指标 > 目标值

---

## 可选增强：稀疏向量

如果 BM25 效果不够好，可以考虑添加稀疏向量增强：

### Task #21: SPLADE 稀疏向量 (优先级: P2, 可选)
**描述**: 使用 SPLADE 模型生成稀疏向量

**为什么选择 SPLADE？**
- 稀疏向量（类似 BM25，但学习得到）
- 比密集向量更高效
- 可以与 BM25 结合使用

**实现**:
```python
from transformers import AutoModelForMaskedLM, AutoTokenizer

# 使用预训练的 SPLADE 模型
model = AutoModelForMaskedLM.from_pretrained("naver/splade-cocondenser-ensembledistil")
tokenizer = AutoTokenizer.from_pretrained("naver/splade-cocondenser-ensembledistil")

# 生成稀疏向量
def encode_sparse(text):
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)
    # 提取稀疏向量
    sparse_vec = torch.max(torch.log(1 + torch.relu(outputs.logits)), dim=1).values
    return sparse_vec
```

**混合检索**:
```python
# BM25 分数
bm25_scores = bm25.get_scores(query)

# SPLADE 分数
splade_scores = compute_splade_scores(query, documents)

# 加权融合
final_scores = alpha * bm25_scores + (1 - alpha) * splade_scores
```

---

## 技术栈

### 核心库
- **BM25**: `rank-bm25` (纯 Python，简单)
- **中文分词**: `jieba` (成熟稳定)
- **英文分词**: `nltk` (标准库)
- **存储**: SQLite (已有)

### 可选库
- **SPLADE**: `transformers` + `naver/splade-cocondenser-ensembledistil`
- **评估**: `scikit-learn` (计算指标)

---

## 实施顺序

### Week 3: 核心检索功能
1. **Day 1**: Task #14 - BM25 检索核心
2. **Day 2**: Task #15 - 文档索引管理
3. **Day 3**: Task #16 - Golden Dataset 创建
4. **Day 4**: Task #17 - 评估框架
5. **Day 5**: Task #18 - 检索 API + Task #19 - 检索 UI

### Week 4: 测试和优化（如果需要）
1. **Day 1**: Task #20 - 集成测试
2. **Day 2-3**: 性能优化和 Bug 修复
3. **Day 4-5**: (可选) Task #21 - SPLADE 稀疏向量增强

---

## 成功标准

### 技术指标
- ✅ **Recall@5 > 0.7**: 70% 的相关文档在前 5 个结果中
- ✅ **Precision@5 > 0.5**: 前 5 个结果中 50% 是相关的
- ✅ **MRR > 0.6**: 第一个相关文档平均在前 2-3 个结果中
- ✅ **检索延迟 < 100ms**: 快速响应
- ✅ **索引构建 < 10 秒**: 1000 个文档

### 用户体验
- ✅ 用户可以通过 UI 执行搜索
- ✅ 搜索结果相关性高
- ✅ 匹配词高亮显示
- ✅ 索引自动更新

---

## 与 Phase 1 的集成

### 数据流
```
Phase 1: 数据源 → 连接器 → 同步 → 数据库
                                    ↓
Phase 2:                    索引构建 → BM25 索引 → 检索
```

### 集成点
1. **数据源同步完成** → 触发索引更新
2. **文档内容** → 从数据库读取并索引
3. **检索结果** → 返回文档 ID，前端查询详情

---

## 风险和缓解

### 风险 1: BM25 对中文支持不好
**缓解**: 使用 jieba 分词，效果通常很好

### 风险 2: 检索质量不达标
**缓解**: 
- 调整 BM25 参数（k1, b）
- 添加同义词扩展
- 考虑 SPLADE 稀疏向量增强

### 风险 3: 索引更新太慢
**缓解**: 
- 使用增量更新而非全量重建
- 异步索引构建
- 批量处理

---

## 下一步

准备开始 **Task #14: BM25 检索核心**

需要确认：
1. **是否需要支持中文**？（如果需要，安装 jieba）
2. **文档存储在哪里**？（应该是 SQLite 数据库）
3. **索引文件存储位置**？（建议 `workspace/.index/`）
4. **是否需要 SPLADE 增强**？（可以先用 BM25，不够再加）

请确认后我就开始实施！

---

## 当前进度

- [x] Task #14: BM25 检索核心 ✅ (Commit: 4b92cfb)
- [x] Task #15: 文档索引管理 ✅ (Commit: 37a0851)
- [ ] Task #16: Golden Dataset 创建
- [ ] Task #17: 评估框架
- [ ] Task #18: 检索 API 端点
- [ ] Task #19: 检索 UI
- [ ] Task #20: Phase 2 集成测试

**完成度**: 2/7 (29%)

### Task #15 完成详情

**实现内容**:
- DocumentDatabase: 文档存储和管理
  * 支持文档 CRUD 操作
  * 支持按数据源过滤
  * 支持索引状态跟踪（indexed_at 字段）
  * 支持查询未索引和过期文档

- IndexManager: 索引生命周期管理
  * 全量索引构建（build_full_index）
  * 增量索引更新（update_index_incremental）
  * 索引持久化和加载
  * 索引统计和健康检查

**测试结果**:
- ✅ 文档数据库操作测试通过
- ✅ 全量索引构建测试通过
- ✅ 检索功能测试通过
- ✅ 增量更新测试通过
- ✅ 健康检查测试通过

**下一步**: Task #16 - Golden Dataset 创建

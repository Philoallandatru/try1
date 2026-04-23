# 检索调试工具文档

## 概述

检索调试工具提供了一套用于分析、调试和优化检索质量的功能。这些工具帮助开发者深入理解 BM25 算法的工作原理，诊断检索问题，并通过人工标注改进检索效果。

## 功能模块

### 1. 查询分析器 (Query Analyzer)

分析查询的分词和统计信息。

**API 端点**: `POST /api/retrieval/debug/analyze-query`

**请求示例**:
```json
{
  "query": "NVMe SSD 固件升级失败"
}
```

**响应示例**:
```json
{
  "status": "success",
  "analysis": {
    "original_query": "NVMe SSD 固件升级失败",
    "tokens": ["nvme", "ssd", "固件", "升级", "失败"],
    "token_count": 5,
    "unique_tokens": 5,
    "token_frequencies": {
      "nvme": 1,
      "ssd": 1,
      "固件": 1,
      "升级": 1,
      "失败": 1
    },
    "query_length": 15
  }
}
```

**用途**:
- 检查分词是否正确
- 识别停用词过滤效果
- 发现查询中的重复词
- 优化查询改写策略

### 2. 评分解释器 (Score Explainer)

详细解释 BM25 评分的计算过程。

**API 端点**: `POST /api/retrieval/debug/explain-score`

**请求示例**:
```json
{
  "query": "NVMe 固件升级",
  "doc_id": "doc_123"
}
```

**响应示例**:
```json
{
  "status": "success",
  "explanation": {
    "doc_id": "doc_123",
    "query": "NVMe 固件升级",
    "query_tokens": ["nvme", "固件", "升级"],
    "total_score": 12.3456,
    "doc_length": 150,
    "avg_doc_length": 200.5,
    "total_documents": 1000,
    "term_scores": [
      {
        "term": "nvme",
        "tf": 3,
        "df": 50,
        "idf": 2.9957,
        "score": 4.1234
      },
      {
        "term": "固件",
        "tf": 2,
        "df": 100,
        "idf": 2.3026,
        "score": 3.5678
      },
      {
        "term": "升级",
        "tf": 1,
        "df": 200,
        "idf": 1.6094,
        "score": 1.6544
      }
    ],
    "parameters": {
      "k1": 1.5,
      "b": 0.75
    }
  }
}
```

**BM25 评分公式**:
```
score(D, Q) = Σ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))

其中:
- D: 文档
- Q: 查询
- qi: 查询中的第 i 个词
- f(qi, D): 词 qi 在文档 D 中的词频 (TF)
- |D|: 文档 D 的长度
- avgdl: 所有文档的平均长度
- k1: 词频饱和参数 (默认 1.5)
- b: 长度归一化参数 (默认 0.75)
- IDF(qi) = log((N - df(qi) + 0.5) / (df(qi) + 0.5) + 1)
  - N: 文档总数
  - df(qi): 包含词 qi 的文档数
```

**用途**:
- 理解为什么某个文档排名高/低
- 诊断词频 (TF) 和逆文档频率 (IDF) 的影响
- 调优 BM25 参数 (k1, b)
- 发现文档长度对评分的影响

### 3. 文档评分对比 (Document Score Comparison)

对比多个文档的 BM25 评分。

**API 端点**: `POST /api/retrieval/debug/compare-scores`

**请求示例**:
```json
{
  "query": "PCIe 链路训练",
  "doc_ids": ["doc_123", "doc_456", "doc_789"]
}
```

**响应示例**:
```json
{
  "status": "success",
  "comparison": {
    "query": "PCIe 链路训练",
    "document_count": 3,
    "explanations": [
      {
        "doc_id": "doc_123",
        "total_score": 15.6789,
        "term_scores": [...]
      },
      {
        "doc_id": "doc_456",
        "total_score": 12.3456,
        "term_scores": [...]
      },
      {
        "doc_id": "doc_789",
        "total_score": 8.9012,
        "term_scores": [...]
      }
    ]
  }
}
```

**用途**:
- 对比相似文档的评分差异
- 发现为什么某个文档排名更高
- A/B 测试不同的检索配置

### 4. 相关性标注 (Relevance Annotation)

人工标注文档与查询的相关性。

**API 端点**: `POST /api/retrieval/debug/annotate`

**请求示例**:
```json
{
  "query": "BSOD 蓝屏",
  "doc_id": "doc_123",
  "relevance": 3,
  "notes": "Highly relevant - directly addresses BSOD issue"
}
```

**相关性等级**:
- **0**: 不相关 (Not relevant)
- **1**: 边缘相关 (Marginally relevant)
- **2**: 相关 (Relevant)
- **3**: 高度相关 (Highly relevant)

**响应示例**:
```json
{
  "status": "success",
  "annotation": {
    "query": "BSOD 蓝屏",
    "doc_id": "doc_123",
    "relevance": 3,
    "notes": "Highly relevant - directly addresses BSOD issue"
  }
}
```

**用途**:
- 构建人工标注的测试集
- 评估检索质量
- 训练学习排序 (Learning to Rank) 模型
- 发现检索系统的弱点

### 5. 获取标注记录

**API 端点**: `GET /api/retrieval/debug/annotations`

**查询参数**:
- `query` (可选): 按查询过滤
- `doc_id` (可选): 按文档 ID 过滤

**请求示例**:
```
GET /api/retrieval/debug/annotations?query=BSOD%20蓝屏
```

**响应示例**:
```json
{
  "status": "success",
  "annotations": [
    {
      "query": "BSOD 蓝屏",
      "doc_id": "doc_123",
      "relevance": 3,
      "notes": "Highly relevant"
    },
    {
      "query": "BSOD 蓝屏",
      "doc_id": "doc_456",
      "relevance": 1,
      "notes": "Only mentions BSOD briefly"
    }
  ]
}
```

### 6. 相关性统计

**API 端点**: `GET /api/retrieval/debug/relevance-stats/{query}`

**请求示例**:
```
GET /api/retrieval/debug/relevance-stats/BSOD%20蓝屏
```

**响应示例**:
```json
{
  "status": "success",
  "stats": {
    "query": "BSOD 蓝屏",
    "total_annotations": 10,
    "relevance_distribution": {
      "0": 2,
      "1": 3,
      "2": 3,
      "3": 2
    },
    "avg_relevance": 1.5
  }
}
```

## 使用场景

### 场景 1: 诊断检索质量问题

**问题**: 用户反馈某个查询的检索结果不准确。

**调试步骤**:

1. **分析查询分词**:
   ```bash
   POST /api/retrieval/debug/analyze-query
   {"query": "用户的查询"}
   ```
   检查分词是否正确，是否有停用词被过滤。

2. **查看 Top-K 结果**:
   ```bash
   POST /api/retrieval/search
   {"query": "用户的查询", "top_k": 10}
   ```

3. **解释评分**:
   对 Top-K 结果中的每个文档，解释其评分：
   ```bash
   POST /api/retrieval/debug/explain-score
   {"query": "用户的查询", "doc_id": "doc_id"}
   ```

4. **人工标注**:
   标注 Top-K 结果的相关性：
   ```bash
   POST /api/retrieval/debug/annotate
   {"query": "用户的查询", "doc_id": "doc_id", "relevance": 2}
   ```

5. **分析问题**:
   - 如果相关文档评分低：检查 TF/IDF 是否合理
   - 如果不相关文档评分高：可能需要添加停用词或调整 BM25 参数
   - 如果分词错误：需要优化分词器或添加领域词典

### 场景 2: 优化 BM25 参数

**目标**: 调优 k1 和 b 参数以提升检索效果。

**步骤**:

1. 准备测试查询集（10-20 个典型查询）
2. 对每个查询，标注 Top-10 结果的相关性
3. 使用不同的 k1 和 b 参数运行评估
4. 对比评估指标（MAP, MRR, NDCG）
5. 选择最优参数

**参数说明**:
- **k1** (默认 1.5): 控制词频饱和度
  - 较小的 k1 (0.5-1.0): 词频影响较小，适合短文档
  - 较大的 k1 (2.0-3.0): 词频影响较大，适合长文档
  
- **b** (默认 0.75): 控制文档长度归一化
  - b = 0: 不考虑文档长度
  - b = 1: 完全归一化到平均长度
  - 较小的 b (0.3-0.5): 长文档更有优势
  - 较大的 b (0.8-1.0): 短文档更有优势

### 场景 3: 构建 Golden Dataset

**目标**: 创建高质量的评估数据集。

**步骤**:

1. **选择代表性查询**:
   - 覆盖不同类型（故障排查、规范查询、知识查询）
   - 覆盖不同难度（简单、中等、困难）

2. **执行检索**:
   ```bash
   POST /api/retrieval/search
   {"query": "查询", "top_k": 20}
   ```

3. **人工标注**:
   对 Top-20 结果逐一标注相关性：
   ```bash
   POST /api/retrieval/debug/annotate
   {"query": "查询", "doc_id": "doc_id", "relevance": 0-3}
   ```

4. **导出标注**:
   ```bash
   GET /api/retrieval/debug/annotations?query=查询
   ```

5. **转换为 Golden Dataset 格式**:
   将标注转换为 YAML 格式，添加到 `data/golden_dataset.yaml`

## 最佳实践

### 1. 查询分析

- **定期检查分词质量**: 对新领域的查询，检查分词是否合理
- **维护领域词典**: 将专业术语添加到分词器词典
- **监控查询模式**: 识别常见查询模式，优化查询改写

### 2. 评分调试

- **关注 IDF 异常**: 如果某个词的 IDF 过高或过低，检查文档集是否有问题
- **检查文档长度**: 过长或过短的文档可能需要特殊处理
- **对比相似查询**: 相似查询的评分模式应该一致

### 3. 相关性标注

- **多人标注**: 对重要查询，由多人标注并取平均
- **标注指南**: 制定清晰的相关性判断标准
- **定期审查**: 定期审查标注质量，更新过时的标注

### 4. 性能优化

- **批量操作**: 使用批量 API 减少网络开销
- **缓存结果**: 缓存常见查询的分析结果
- **异步处理**: 对大规模标注任务使用异步处理

## 工具集成

### Python 客户端示例

```python
import requests

class RetrievalDebugClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = f"{base_url}/api/retrieval/debug"
    
    def analyze_query(self, query):
        response = requests.post(
            f"{self.base_url}/analyze-query",
            json={"query": query}
        )
        return response.json()
    
    def explain_score(self, query, doc_id):
        response = requests.post(
            f"{self.base_url}/explain-score",
            json={"query": query, "doc_id": doc_id}
        )
        return response.json()
    
    def annotate(self, query, doc_id, relevance, notes=""):
        response = requests.post(
            f"{self.base_url}/annotate",
            json={
                "query": query,
                "doc_id": doc_id,
                "relevance": relevance,
                "notes": notes
            }
        )
        return response.json()

# 使用示例
client = RetrievalDebugClient()

# 分析查询
analysis = client.analyze_query("NVMe 固件升级")
print(analysis)

# 解释评分
explanation = client.explain_score("NVMe 固件升级", "doc_123")
print(explanation)

# 标注相关性
annotation = client.annotate("NVMe 固件升级", "doc_123", 3, "非常相关")
print(annotation)
```

## 故障排查

### 问题 1: 分词结果不符合预期

**原因**: 分词器缺少领域词典

**解决方案**:
1. 检查 `packages/retrieval/tokenizer.py` 的词典配置
2. 添加领域专业术语到词典
3. 重建索引

### 问题 2: 评分解释返回错误

**原因**: 文档不在索引中

**解决方案**:
1. 检查文档是否已被索引
2. 使用 `GET /api/retrieval/stats` 查看索引状态
3. 如果需要，重建索引

### 问题 3: 标注数据丢失

**原因**: 标注数据未持久化

**解决方案**:
1. 检查 `.local/retrieval/annotations.json` 文件
2. 确保应用有写入权限
3. 定期备份标注数据

## 参考资料

- [BM25 算法详解](https://en.wikipedia.org/wiki/Okapi_BM25)
- [信息检索评估指标](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))
- [检索评估 API 文档](./RETRIEVAL_EVALUATION_API.md)

## 更新日志

- 2025-01-XX: 初始版本
  - 查询分析器
  - 评分解释器
  - 相关性标注工具
  - 文档评分对比

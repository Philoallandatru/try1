# 检索评估 API 文档

## 概述

检索评估 API 提供了完整的评估管理功能，包括：
- Golden Dataset 管理
- 评估执行和结果保存
- 评估历史查询和对比

## API 端点

### Dataset 管理

#### 上传 Dataset

```http
POST /api/retrieval/datasets
Content-Type: application/json

{
  "content": "YAML content of the dataset",
  "dataset_id": "optional_dataset_id"
}
```

**响应**:
```json
{
  "status": "success",
  "dataset": {
    "dataset_id": "golden_dataset_v2",
    "name": "ssd_firmware_retrieval_v2",
    "description": "SSD 固件、NVMe 协议、PCIe 规范检索评估数据集",
    "version": 2,
    "created_at": "2026-04-23T...",
    "updated_at": "2026-04-23T...",
    "total_queries": 40,
    "total_documents": 41,
    "categories": {
      "troubleshooting": 10,
      "specification": 14,
      "knowledge": 16
    }
  }
}
```

#### 列出所有 Datasets

```http
GET /api/retrieval/datasets
```

**响应**:
```json
{
  "status": "success",
  "datasets": [
    {
      "dataset_id": "golden_dataset_v2",
      "name": "ssd_firmware_retrieval_v2",
      "total_queries": 40,
      "total_documents": 41,
      ...
    }
  ]
}
```

#### 获取 Dataset 详情

```http
GET /api/retrieval/datasets/{dataset_id}
```

**响应**:
```json
{
  "status": "success",
  "dataset": {
    "dataset_id": "golden_dataset_v2",
    "name": "ssd_firmware_retrieval_v2",
    ...
  },
  "content": "YAML content..."
}
```

#### 删除 Dataset

```http
DELETE /api/retrieval/datasets/{dataset_id}
```

**响应**:
```json
{
  "status": "success",
  "message": "Dataset golden_dataset_v2 deleted"
}
```

---

### 评估执行

#### 运行评估

```http
POST /api/retrieval/evaluate
Content-Type: application/json

{
  "golden_dataset_path": "data/golden_dataset.yaml",
  "top_k": 10,
  "save_result": true
}
```

**响应**:
```json
{
  "status": "success",
  "run_id": "eval_20260423_123456",
  "aggregate_metrics": {
    "total_queries": 40,
    "mean_average_precision": 0.75,
    "mean_reciprocal_rank": 0.82,
    "mean_ndcg_at_5": 0.78,
    "mean_ndcg_at_10": 0.80,
    "mean_precision_at_1": 0.85,
    "mean_precision_at_3": 0.80,
    "mean_precision_at_5": 0.75,
    "mean_precision_at_10": 0.70,
    "mean_recall_at_1": 0.30,
    "mean_recall_at_3": 0.50,
    "mean_recall_at_5": 0.65,
    "mean_recall_at_10": 0.80
  },
  "per_query_results": [
    {
      "query_id": "q001",
      "query_text": "黑屏问题如何排查",
      "average_precision": 0.83,
      "reciprocal_rank": 1.0,
      "ndcg_at_5": 0.85,
      "precision_at_5": 0.80,
      "recall_at_5": 0.67
    },
    ...
  ]
}
```

---

### 评估结果管理

#### 列出评估结果

```http
GET /api/retrieval/results?dataset_id=golden_dataset_v2&limit=10
```

**查询参数**:
- `dataset_id` (可选): 按 dataset ID 过滤
- `limit` (可选): 限制返回数量

**响应**:
```json
{
  "status": "success",
  "results": [
    {
      "run_id": "eval_20260423_123456",
      "dataset_id": "golden_dataset_v2",
      "dataset_name": "ssd_firmware_retrieval_v2",
      "timestamp": "2026-04-23T12:34:56",
      "top_k": 10,
      "total_queries": 40,
      "aggregate_metrics": {
        "mean_average_precision": 0.75,
        ...
      }
    }
  ]
}
```

#### 获取评估详情

```http
GET /api/retrieval/results/{run_id}
```

**响应**:
```json
{
  "status": "success",
  "result": {
    "run_id": "eval_20260423_123456",
    "dataset_id": "golden_dataset_v2",
    "dataset_name": "ssd_firmware_retrieval_v2",
    "timestamp": "2026-04-23T12:34:56",
    "top_k": 10,
    "total_queries": 40,
    "aggregate_metrics": { ... },
    "per_query_results": [
      {
        "query_id": "q001",
        "query_text": "黑屏问题如何排查",
        "average_precision": 0.83,
        "reciprocal_rank": 1.0,
        "ndcg_at_5": 0.85,
        "ndcg_at_10": 0.87,
        "precision_at_1": 1.0,
        "precision_at_3": 0.67,
        "precision_at_5": 0.80,
        "precision_at_10": 0.70,
        "recall_at_1": 0.33,
        "recall_at_3": 0.67,
        "recall_at_5": 0.67,
        "recall_at_10": 1.0,
        "retrieved_docs": ["doc1", "doc2", ...],
        "relevant_docs": ["doc1", "doc3"]
      },
      ...
    ],
    "config": null
  }
}
```

#### 删除评估结果

```http
DELETE /api/retrieval/results/{run_id}
```

**响应**:
```json
{
  "status": "success",
  "message": "Evaluation result eval_20260423_123456 deleted"
}
```

#### 对比评估结果

```http
POST /api/retrieval/results/compare
Content-Type: application/json

{
  "run_ids": ["eval_20260423_123456", "eval_20260423_234567"]
}
```

**响应**:
```json
{
  "status": "success",
  "comparison": {
    "runs": [
      {
        "run_id": "eval_20260423_123456",
        "dataset_name": "ssd_firmware_retrieval_v2",
        "timestamp": "2026-04-23T12:34:56",
        "top_k": 10,
        "metrics": {
          "mean_average_precision": 0.75,
          "mean_reciprocal_rank": 0.82,
          ...
        }
      },
      {
        "run_id": "eval_20260423_234567",
        "dataset_name": "ssd_firmware_retrieval_v2",
        "timestamp": "2026-04-23T23:45:67",
        "top_k": 10,
        "metrics": {
          "mean_average_precision": 0.78,
          "mean_reciprocal_rank": 0.85,
          ...
        }
      }
    ],
    "metric_names": [
      "mean_average_precision",
      "mean_reciprocal_rank",
      ...
    ]
  }
}
```

---

## 评估指标说明

### MAP (Mean Average Precision)
平均精度均值，衡量检索结果的整体质量。值越高越好（0-1）。

### MRR (Mean Reciprocal Rank)
平均倒数排名，衡量第一个相关文档的排名。值越高越好（0-1）。

### NDCG@K (Normalized Discounted Cumulative Gain)
归一化折损累积增益，考虑文档相关性分级和排名位置。值越高越好（0-1）。

### Precision@K
前 K 个结果中相关文档的比例。值越高越好（0-1）。

### Recall@K
前 K 个结果中召回的相关文档占所有相关文档的比例。值越高越好（0-1）。

---

## 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 上传 dataset
with open("data/golden_dataset.yaml", "r") as f:
    content = f.read()

response = requests.post(
    f"{BASE_URL}/api/retrieval/datasets",
    json={"content": content, "dataset_id": "my_dataset"}
)
print(response.json())

# 2. 运行评估
response = requests.post(
    f"{BASE_URL}/api/retrieval/evaluate",
    json={
        "golden_dataset_path": "data/golden_dataset.yaml",
        "top_k": 10,
        "save_result": True
    }
)
result = response.json()
print(f"MAP: {result['aggregate_metrics']['mean_average_precision']}")

# 3. 列出评估结果
response = requests.get(f"{BASE_URL}/api/retrieval/results")
results = response.json()
for r in results['results']:
    print(f"{r['run_id']}: MAP={r['aggregate_metrics']['mean_average_precision']:.3f}")

# 4. 对比两次评估
response = requests.post(
    f"{BASE_URL}/api/retrieval/results/compare",
    json={"run_ids": ["eval_1", "eval_2"]}
)
comparison = response.json()
```

### cURL 示例

```bash
# 列出 datasets
curl http://localhost:8000/api/retrieval/datasets

# 运行评估
curl -X POST http://localhost:8000/api/retrieval/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "golden_dataset_path": "data/golden_dataset.yaml",
    "top_k": 10,
    "save_result": true
  }'

# 获取评估结果
curl http://localhost:8000/api/retrieval/results/eval_20260423_123456
```

---

## 数据存储

评估数据存储在 `.local/retrieval/` 目录：

```
.local/retrieval/
├── datasets/
│   ├── golden_dataset_v2.yaml
│   └── test_dataset.yaml
└── results/
    ├── eval_20260423_123456.json
    └── eval_20260423_234567.json
```

---

## 错误处理

所有 API 在出错时返回：

```json
{
  "status": "error",
  "error": "Error message"
}
```

常见错误：
- `404`: Dataset 或 Result 不存在
- `400`: 请求参数无效
- `500`: 服务器内部错误

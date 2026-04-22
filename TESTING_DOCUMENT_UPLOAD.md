# 文档上传功能测试指南

## 当前状态

✅ 后端代码已实现并提交
✅ 前端界面已实现并提交
✅ 服务器正在运行 (http://localhost:8000)
⚠️  服务器需要重启以加载新的文档管理路由

## 测试步骤

### 1. 重启后端服务器

**选项 A: 如果使用 --reload 模式**
服务器应该自动重新加载。等待几秒钟后继续。

**选项 B: 手动重启**
```bash
# 停止当前服务器 (Ctrl+C)
# 然后重新启动
cd apps/portal_runner
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### 2. 验证 API 端点

运行测试脚本：
```bash
python test_document_upload.py
```

或手动测试：
```bash
# 测试文档类型端点
curl -H "Authorization: Bearer change-me" http://localhost:8000/api/documents/types

# 测试列表端点
curl -H "Authorization: Bearer change-me" "http://localhost:8000/api/documents/list?workspace=demo"
```

### 3. 测试文档上传

**方法 A: 使用测试脚本**
```bash
python test_document_upload.py
```

**方法 B: 使用 curl**
```bash
curl -X POST \
  -H "Authorization: Bearer change-me" \
  -F "workspace=demo" \
  -F "document_type=spec" \
  -F "display_name=NVMe Specification" \
  -F "file=@documents/fms-08-09-2023-ssds-201-1-ozturk-final.pdf" \
  http://localhost:8000/api/documents/upload
```

**方法 C: 使用前端界面**
1. 打开浏览器访问 http://localhost:5173
2. 输入 token: `change-me`
3. 选择 workspace: `demo`
4. 点击左侧导航的 "Documents"
5. 拖拽或选择 PDF 文件
6. 选择文档类型 (Spec/Policy/Other)
7. 点击 "Upload Document"

### 4. 验证文档已索引

```bash
# 检查索引统计
curl -H "Authorization: Bearer change-me" \
  "http://localhost:8000/api/retrieval/stats?workspace_dir=workspaces/demo"

# 重建索引（如果需要）
curl -X POST \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"workspace_dir":"workspaces/demo"}' \
  http://localhost:8000/api/retrieval/index/build

# 搜索测试
curl -X POST \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"workspace_dir":"workspaces/demo","query":"SSD","top_k":5}' \
  http://localhost:8000/api/retrieval/search
```

### 5. 测试前端搜索

1. 访问 http://localhost:5173/search
2. 点击 "Rebuild Index" 按钮
3. 输入搜索关键词（如 "SSD", "NVMe", "firmware"）
4. 查看搜索结果是否包含上传的文档

## 可用的测试文档

documents 文件夹中有以下 PDF 文件可供测试：

1. **fms-08-09-2023-ssds-201-1-ozturk-final.pdf** (396 KB)
   - 建议类型: Other
   - 描述: FMS 2023 SSD Paper

2. **20190719_NVME-301-1_Das Sharma_FINAL.pdf** (1.5 MB)
   - 建议类型: Spec
   - 描述: NVMe Technical Presentation

3. **PCI-Express-5-Update-Keys-to-Addressing-an-Evolving-Specification.pdf** (3.2 MB)
   - 建议类型: Spec
   - 描述: PCIe 5.0 Specification Update

4. **PCI_Firmware_v3.3_20210120_NCB.pdf** (1.8 MB)
   - 建议类型: Policy
   - 描述: PCI Firmware Specification

5. **NVM-Express-Base-Specification-Revision-2.1-2024.08.05-Ratified.pdf** (12 MB)
   - 建议类型: Spec
   - 描述: NVMe Base Specification 2.1

## 预期结果

### 成功的上传应该返回：
```json
{
  "success": true,
  "message": "Document uploaded successfully",
  "metadata": {
    "doc_id": "...",
    "display_name": "...",
    "document_type": "spec",
    "version": "v1",
    "document_id": "...",
    "priority": 100,
    ...
  }
}
```

### 文档列表应该显示：
- 文档名称
- 文档类型（Spec/Policy/Other）
- 文件大小
- 上传时间
- 版本号

### 搜索结果应该：
- 包含上传的文档
- 按相关性排序
- Spec 类型文档优先级更高

## 故障排除

### 问题 1: API 返回 404
- 确认服务器已重启
- 检查 server.py 是否包含 document_router
- 查看服务器日志

### 问题 2: 上传失败
- 检查文件路径是否正确
- 确认 workspace 存在
- 查看服务器错误日志

### 问题 3: 文档未出现在搜索中
- 运行 "Rebuild Index"
- 检查 workspace/document-assets/ 目录
- 验证文档是否成功解析

### 问题 4: 前端无法访问
- 确认前端服务器运行在 http://localhost:5173
- 检查 token 是否正确
- 清除浏览器缓存

## 下一步

测试完成后，可以：
1. 上传更多文档测试批量功能
2. 测试不同文档类型的检索优先级
3. 验证文档删除功能
4. 测试文档版本管理
5. 添加更多文档类型（如果需要）

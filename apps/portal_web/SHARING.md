# 分析结果分享功能

## 概述

分享功能允许用户创建分析结果的分享链接，控制访问权限和过期时间。

## 功能特性

### 1. 分享链接创建

- **权限级别**：
  - `view`：只读访问
  - `comment`：可以查看和评论（预留）
  - `edit`：可以编辑（预留）

- **过期时间**：
  - 1小时
  - 24小时
  - 7天
  - 30天
  - 永不过期

- **访问控制**：
  - 需要认证：要求用户登录才能访问
  - 公开访问：任何人都可以通过链接访问
  - 指定用户：只允许特定用户访问

### 2. 分享管理

- 查看所有分享链接
- 查看访问统计（访问次数、最后访问时间）
- 删除分享链接
- 自动清理过期链接

## API 端点

### 创建分享

```http
POST /api/shares
Content-Type: application/json
X-User-Id: user123

{
  "workspace_dir": "/path/to/workspace",
  "analysis_id": "issue-123",
  "permissions": "view",
  "expires_in": "7d",
  "require_auth": true,
  "allowed_users": ["user1", "user2"]
}
```

**响应**：
```json
{
  "share_id": "abc123xyz",
  "share_url": "/shared/abc123xyz",
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-01-08T00:00:00Z",
  "permissions": "view",
  "require_auth": true
}
```

### 访问分享

```http
GET /api/shares/{share_id}
X-User-Id: user123
```

**响应**：
```json
{
  "share_id": "abc123xyz",
  "analysis_id": "issue-123",
  "workspace_dir": "/path/to/workspace",
  "permissions": "view",
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-01-08T00:00:00Z",
  "access_count": 5
}
```

**错误响应**：
- `404 Not Found`：分享不存在
- `410 Gone`：分享已过期
- `403 Forbidden`：无权限访问

### 列出分享

```http
GET /api/shares?workspace_dir=/path/to/workspace
X-User-Id: user123
```

**响应**：
```json
{
  "shares": [
    {
      "share_id": "abc123xyz",
      "analysis_id": "issue-123",
      "workspace_dir": "/path/to/workspace",
      "created_at": "2024-01-01T00:00:00Z",
      "expires_at": "2024-01-08T00:00:00Z",
      "permissions": "view",
      "require_auth": true,
      "access_count": 5,
      "last_accessed": "2024-01-05T12:00:00Z"
    }
  ]
}
```

### 删除分享

```http
DELETE /api/shares/{share_id}
X-User-Id: user123
```

**响应**：
```json
{
  "status": "deleted",
  "share_id": "abc123xyz"
}
```

## 前端组件

### ShareDialog

分享对话框组件，提供创建分享链接的界面。

**Props**：
```typescript
interface ShareDialogProps {
  isOpen: boolean;
  onClose: () => void;
  analysisId: string;
  workspaceDir: string;
  onShare: (settings: ShareSettings) => Promise<void>;
}
```

**使用示例**：
```tsx
import { ShareDialog } from './ShareDialog';

function AnalysisPage() {
  const [showShareDialog, setShowShareDialog] = useState(false);

  const handleShare = async (settings) => {
    const response = await fetch('/api/shares', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workspace_dir: workspaceDir,
        analysis_id: analysisId,
        ...settings,
      }),
    });
    const data = await response.json();
    console.log('Share created:', data);
  };

  return (
    <>
      <button onClick={() => setShowShareDialog(true)}>
        Share
      </button>
      <ShareDialog
        isOpen={showShareDialog}
        onClose={() => setShowShareDialog(false)}
        analysisId={analysisId}
        workspaceDir={workspaceDir}
        onShare={handleShare}
      />
    </>
  );
}
```

## 权限控制

分享功能需要 `analysis.share` 权限：

- **Owner**：✅ 可以分享
- **Admin**：✅ 可以分享
- **Write**：❌ 不能分享
- **Read**：❌ 不能分享

在 UI 中使用权限保护：

```tsx
import { ProtectedButton } from './PermissionContext';
import { Permission } from './PermissionContext';

<ProtectedButton
  permission={Permission.ANALYSIS_SHARE}
  onClick={() => setShowShareDialog(true)}
>
  <Share2 size={16} />
  Share
</ProtectedButton>
```

## 数据存储

分享数据存储在 `.local/shares/shares.json`：

```json
{
  "abc123xyz": {
    "share_id": "abc123xyz",
    "analysis_id": "issue-123",
    "workspace_dir": "/path/to/workspace",
    "created_by": "user123",
    "created_at": "2024-01-01T00:00:00Z",
    "expires_at": "2024-01-08T00:00:00Z",
    "permissions": "view",
    "require_auth": true,
    "allowed_users": ["user1", "user2"],
    "access_count": 5,
    "last_accessed": "2024-01-05T12:00:00Z"
  }
}
```

## 安全考虑

1. **分享 ID 生成**：使用 `secrets.token_urlsafe(16)` 生成随机 ID，防止猜测
2. **过期检查**：每次访问时检查是否过期
3. **权限验证**：验证用户是否有权限访问
4. **访问日志**：记录访问次数和时间
5. **自动清理**：定期清理过期的分享链接

## 未来改进

1. **评论功能**：允许用户在分享的分析结果上添加评论
2. **编辑权限**：允许协作编辑分析结果
3. **访问日志**：详细的访问日志（谁、何时、从哪里访问）
4. **通知**：分享被访问时通知创建者
5. **批量分享**：一次分享多个分析结果
6. **嵌入模式**：生成可嵌入的 iframe 代码

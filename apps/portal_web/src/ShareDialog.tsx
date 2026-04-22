import React, { useState } from 'react';
import { usePermissions, Permission } from './PermissionContext';

export interface ShareSettings {
  shareId: string;
  expiresAt?: string;
  permissions: 'view' | 'comment' | 'edit';
  requireAuth: boolean;
  allowedUsers?: string[];
}

interface ShareDialogProps {
  isOpen: boolean;
  onClose: () => void;
  analysisId: string;
  workspaceDir: string;
  onShare: (settings: ShareSettings) => Promise<void>;
}

export function ShareDialog({
  isOpen,
  onClose,
  analysisId,
  workspaceDir,
  onShare,
}: ShareDialogProps) {
  const { hasPermission } = usePermissions();
  const [permissions, setPermissions] = useState<'view' | 'comment' | 'edit'>('view');
  const [requireAuth, setRequireAuth] = useState(true);
  const [expiresIn, setExpiresIn] = useState<string>('7d');
  const [allowedUsers, setAllowedUsers] = useState<string>('');
  const [isSharing, setIsSharing] = useState(false);
  const [shareUrl, setShareUrl] = useState<string>('');
  const [error, setError] = useState<string>('');

  const canShare = hasPermission(Permission.ANALYSIS_SHARE);

  if (!isOpen) return null;

  const handleShare = async () => {
    if (!canShare) {
      setError('您没有分享权限');
      return;
    }

    setIsSharing(true);
    setError('');

    try {
      const expiresAt = expiresIn
        ? new Date(Date.now() + parseExpiry(expiresIn)).toISOString()
        : undefined;

      const settings: ShareSettings = {
        shareId: generateShareId(),
        expiresAt,
        permissions,
        requireAuth,
        allowedUsers: allowedUsers
          ? allowedUsers.split(',').map((u) => u.trim()).filter(Boolean)
          : undefined,
      };

      await onShare(settings);

      const url = `${window.location.origin}/shared/${settings.shareId}`;
      setShareUrl(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : '分享失败');
    } finally {
      setIsSharing(false);
    }
  };

  const handleCopyUrl = () => {
    if (shareUrl) {
      navigator.clipboard.writeText(shareUrl);
    }
  };

  const handleClose = () => {
    setShareUrl('');
    setError('');
    onClose();
  };

  return (
    <div className="share-dialog-overlay" onClick={handleClose}>
      <div className="share-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="share-dialog-header">
          <h2>分享分析结果</h2>
          <button className="close-button" onClick={handleClose}>
            ×
          </button>
        </div>

        <div className="share-dialog-content">
          {!shareUrl ? (
            <>
              <div className="form-group">
                <label>访问权限</label>
                <select
                  value={permissions}
                  onChange={(e) => setPermissions(e.target.value as any)}
                  disabled={!canShare}
                >
                  <option value="view">仅查看</option>
                  <option value="comment">查看和评论</option>
                  <option value="edit">完全编辑</option>
                </select>
              </div>

              <div className="form-group">
                <label>有效期</label>
                <select
                  value={expiresIn}
                  onChange={(e) => setExpiresIn(e.target.value)}
                  disabled={!canShare}
                >
                  <option value="1h">1 小时</option>
                  <option value="24h">24 小时</option>
                  <option value="7d">7 天</option>
                  <option value="30d">30 天</option>
                  <option value="">永久</option>
                </select>
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={requireAuth}
                    onChange={(e) => setRequireAuth(e.target.checked)}
                    disabled={!canShare}
                  />
                  需要登录访问
                </label>
              </div>

              {requireAuth && (
                <div className="form-group">
                  <label>允许的用户（逗号分隔，留空表示所有已登录用户）</label>
                  <input
                    type="text"
                    value={allowedUsers}
                    onChange={(e) => setAllowedUsers(e.target.value)}
                    placeholder="user1@example.com, user2@example.com"
                    disabled={!canShare}
                  />
                </div>
              )}

              {error && <div className="error-message">{error}</div>}

              <div className="dialog-actions">
                <button onClick={handleClose} disabled={isSharing}>
                  取消
                </button>
                <button
                  onClick={handleShare}
                  disabled={isSharing || !canShare}
                  className="primary"
                >
                  {isSharing ? '生成中...' : '生成分享链接'}
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="share-success">
                <p>分享链接已生成：</p>
                <div className="share-url-container">
                  <input
                    type="text"
                    value={shareUrl}
                    readOnly
                    className="share-url"
                  />
                  <button onClick={handleCopyUrl} className="copy-button">
                    复制
                  </button>
                </div>
                <p className="share-info">
                  权限: {permissions === 'view' ? '仅查看' : permissions === 'comment' ? '查看和评论' : '完全编辑'}
                  {expiresIn && ` · 有效期: ${expiresIn}`}
                  {requireAuth && ' · 需要登录'}
                </p>
              </div>

              <div className="dialog-actions">
                <button onClick={handleClose} className="primary">
                  完成
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function generateShareId(): string {
  return Math.random().toString(36).substring(2, 15) +
    Math.random().toString(36).substring(2, 15);
}

function parseExpiry(expiry: string): number {
  const match = expiry.match(/^(\d+)([hd])$/);
  if (!match) return 0;

  const value = parseInt(match[1], 10);
  const unit = match[2];

  if (unit === 'h') {
    return value * 60 * 60 * 1000;
  } else if (unit === 'd') {
    return value * 24 * 60 * 60 * 1000;
  }

  return 0;
}

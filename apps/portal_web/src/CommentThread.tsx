import React, { useState, useEffect } from 'react';
import { MessageSquare, Reply, Edit2, Trash2, Check, X } from 'lucide-react';

export interface Comment {
  comment_id: string;
  analysis_id: string;
  workspace_dir: string;
  user_id: string;
  user_name: string;
  content: string;
  created_at: string;
  updated_at?: string;
  parent_id?: string;
  annotation?: {
    type: string;
    start: number;
    end: number;
    text: string;
    color?: string;
  };
  resolved: boolean;
}

interface CommentThreadProps {
  analysisId: string;
  workspaceDir: string;
  userId: string;
  userName: string;
}

export function CommentThread({
  analysisId,
  workspaceDir,
  userId,
  userName,
}: CommentThreadProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [showResolved, setShowResolved] = useState(false);

  useEffect(() => {
    loadComments();
  }, [analysisId, workspaceDir, showResolved]);

  const loadComments = async () => {
    try {
      const response = await fetch(
        `/api/comments?workspace_dir=${encodeURIComponent(workspaceDir)}&analysis_id=${encodeURIComponent(analysisId)}&include_resolved=${showResolved}`,
        {
          headers: {
            'X-User-Id': userId,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to load comments');
      }

      const data = await response.json();
      setComments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load comments');
    }
  };

  const handleSubmit = async (parentId?: string) => {
    const content = parentId ? editContent : newComment;
    if (!content.trim()) return;

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/comments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': userId,
          'X-User-Name': userName,
        },
        body: JSON.stringify({
          analysis_id: analysisId,
          workspace_dir: workspaceDir,
          content: content.trim(),
          parent_id: parentId || null,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create comment');
      }

      setNewComment('');
      setReplyTo(null);
      setEditContent('');
      await loadComments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create comment');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (commentId: string, content: string) => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch(
        `/api/comments/${commentId}?workspace_dir=${encodeURIComponent(workspaceDir)}&analysis_id=${encodeURIComponent(analysisId)}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'X-User-Id': userId,
          },
          body: JSON.stringify({ content }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to update comment');
      }

      setEditingId(null);
      setEditContent('');
      await loadComments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update comment');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!confirm('确定要删除这条评论吗？')) return;

    setLoading(true);
    setError('');

    try {
      const response = await fetch(
        `/api/comments/${commentId}?workspace_dir=${encodeURIComponent(workspaceDir)}&analysis_id=${encodeURIComponent(analysisId)}`,
        {
          method: 'DELETE',
          headers: {
            'X-User-Id': userId,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to delete comment');
      }

      await loadComments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete comment');
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async (commentId: string, resolved: boolean) => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch(
        `/api/comments/${commentId}?workspace_dir=${encodeURIComponent(workspaceDir)}&analysis_id=${encodeURIComponent(analysisId)}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'X-User-Id': userId,
          },
          body: JSON.stringify({ resolved }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to resolve comment');
      }

      await loadComments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resolve comment');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  const rootComments = comments.filter(c => !c.parent_id);
  const getReplies = (commentId: string) => comments.filter(c => c.parent_id === commentId);

  const renderComment = (comment: Comment, isReply = false) => {
    const isEditing = editingId === comment.comment_id;
    const isOwner = comment.user_id === userId;
    const replies = getReplies(comment.comment_id);

    return (
      <div key={comment.comment_id} className={`comment ${isReply ? 'comment-reply' : ''} ${comment.resolved ? 'comment-resolved' : ''}`}>
        <div className="comment-header">
          <div className="comment-author">
            <strong>{comment.user_name}</strong>
            <span className="comment-time">{formatDate(comment.created_at)}</span>
            {comment.updated_at && <span className="comment-edited">(已编辑)</span>}
          </div>
          {isOwner && (
            <div className="comment-actions">
              {!isEditing && (
                <>
                  <button
                    onClick={() => {
                      setEditingId(comment.comment_id);
                      setEditContent(comment.content);
                    }}
                    className="comment-action-btn"
                    title="编辑"
                  >
                    <Edit2 size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(comment.comment_id)}
                    className="comment-action-btn"
                    title="删除"
                  >
                    <Trash2 size={14} />
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {comment.annotation && (
          <div className="comment-annotation">
            <span className={`annotation-badge annotation-${comment.annotation.type}`}>
              {comment.annotation.type}
            </span>
            <span className="annotation-text">"{comment.annotation.text}"</span>
          </div>
        )}

        {isEditing ? (
          <div className="comment-edit">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="comment-textarea"
              rows={3}
            />
            <div className="comment-edit-actions">
              <button
                onClick={() => handleUpdate(comment.comment_id, editContent)}
                className="btn-primary"
                disabled={loading || !editContent.trim()}
              >
                <Check size={14} /> 保存
              </button>
              <button
                onClick={() => {
                  setEditingId(null);
                  setEditContent('');
                }}
                className="btn-secondary"
              >
                <X size={14} /> 取消
              </button>
            </div>
          </div>
        ) : (
          <div className="comment-content">{comment.content}</div>
        )}

        <div className="comment-footer">
          {!isReply && (
            <button
              onClick={() => setReplyTo(replyTo === comment.comment_id ? null : comment.comment_id)}
              className="comment-reply-btn"
            >
              <Reply size={14} /> 回复
            </button>
          )}
          <button
            onClick={() => handleResolve(comment.comment_id, !comment.resolved)}
            className="comment-resolve-btn"
          >
            {comment.resolved ? '重新打开' : '标记为已解决'}
          </button>
        </div>

        {replyTo === comment.comment_id && (
          <div className="comment-reply-form">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              placeholder="写下你的回复..."
              className="comment-textarea"
              rows={3}
            />
            <div className="comment-reply-actions">
              <button
                onClick={() => handleSubmit(comment.comment_id)}
                className="btn-primary"
                disabled={loading || !editContent.trim()}
              >
                发送回复
              </button>
              <button
                onClick={() => {
                  setReplyTo(null);
                  setEditContent('');
                }}
                className="btn-secondary"
              >
                取消
              </button>
            </div>
          </div>
        )}

        {replies.length > 0 && (
          <div className="comment-replies">
            {replies.map(reply => renderComment(reply, true))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="comment-thread">
      <div className="comment-thread-header">
        <h3>
          <MessageSquare size={20} />
          评论 ({comments.length})
        </h3>
        <label className="comment-filter">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
          />
          显示已解决
        </label>
      </div>

      {error && <div className="comment-error">{error}</div>}

      <div className="comment-new">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="添加评论..."
          className="comment-textarea"
          rows={3}
        />
        <button
          onClick={() => handleSubmit()}
          className="btn-primary"
          disabled={loading || !newComment.trim()}
        >
          发表评论
        </button>
      </div>

      <div className="comment-list">
        {rootComments.length === 0 ? (
          <div className="comment-empty">暂无评论</div>
        ) : (
          rootComments.map(comment => renderComment(comment))
        )}
      </div>
    </div>
  );
}

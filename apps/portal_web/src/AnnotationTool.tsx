import React, { useState, useRef, useEffect } from 'react';
import { Highlighter, MessageSquare, HelpCircle, AlertCircle } from 'lucide-react';

export interface Annotation {
  type: 'highlight' | 'note' | 'question' | 'issue';
  start: number;
  end: number;
  text: string;
  color?: string;
}

interface AnnotationToolProps {
  content: string;
  analysisId: string;
  workspaceDir: string;
  userId: string;
  userName: string;
  onAnnotate?: (annotation: Annotation, comment: string) => void;
}

export function AnnotationTool({
  content,
  analysisId,
  workspaceDir,
  userId,
  userName,
  onAnnotate,
}: AnnotationToolProps) {
  const [selectedText, setSelectedText] = useState('');
  const [selectionRange, setSelectionRange] = useState<{ start: number; end: number } | null>(null);
  const [showMenu, setShowMenu] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [annotationType, setAnnotationType] = useState<Annotation['type'] | null>(null);
  const [comment, setComment] = useState('');
  const [annotations, setAnnotations] = useState<Array<Annotation & { comment_id: string }>>([]);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadAnnotations();
  }, [analysisId, workspaceDir]);

  const loadAnnotations = async () => {
    try {
      const response = await fetch(
        `/api/comments/annotations/list?workspace_dir=${encodeURIComponent(workspaceDir)}&analysis_id=${encodeURIComponent(analysisId)}`
      );

      if (response.ok) {
        const data = await response.json();
        setAnnotations(data.annotations.map((a: any) => ({
          ...a.annotation,
          comment_id: a.comment_id,
        })));
      }
    } catch (err) {
      console.error('Failed to load annotations:', err);
    }
  };

  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) {
      setShowMenu(false);
      return;
    }

    const text = selection.toString().trim();
    if (!text) {
      setShowMenu(false);
      return;
    }

    // 获取选中文本在内容中的位置
    const range = selection.getRangeAt(0);
    const preSelectionRange = range.cloneRange();
    preSelectionRange.selectNodeContents(contentRef.current!);
    preSelectionRange.setEnd(range.startContainer, range.startOffset);
    const start = preSelectionRange.toString().length;
    const end = start + text.length;

    setSelectedText(text);
    setSelectionRange({ start, end });

    // 计算菜单位置
    const rect = range.getBoundingClientRect();
    setMenuPosition({
      x: rect.left + rect.width / 2,
      y: rect.top - 10,
    });

    setShowMenu(true);
  };

  const handleAnnotate = async (type: Annotation['type']) => {
    if (!selectionRange || !selectedText) return;

    setAnnotationType(type);
  };

  const handleSubmitAnnotation = async () => {
    if (!selectionRange || !selectedText || !annotationType) return;

    const annotation: Annotation = {
      type: annotationType,
      start: selectionRange.start,
      end: selectionRange.end,
      text: selectedText,
    };

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
          content: comment || `标注: ${selectedText}`,
          annotation,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create annotation');
      }

      // 重置状态
      setShowMenu(false);
      setAnnotationType(null);
      setComment('');
      setSelectedText('');
      setSelectionRange(null);

      // 清除选择
      window.getSelection()?.removeAllRanges();

      // 重新加载标注
      await loadAnnotations();

      // 通知父组件
      if (onAnnotate) {
        onAnnotate(annotation, comment);
      }
    } catch (err) {
      console.error('Failed to create annotation:', err);
      alert('创建标注失败');
    }
  };

  const handleCancelAnnotation = () => {
    setShowMenu(false);
    setAnnotationType(null);
    setComment('');
    setSelectedText('');
    setSelectionRange(null);
    window.getSelection()?.removeAllRanges();
  };

  const renderAnnotatedContent = () => {
    if (annotations.length === 0) {
      return <div className="annotation-content">{content}</div>;
    }

    // 按位置排序标注
    const sortedAnnotations = [...annotations].sort((a, b) => a.start - b.start);

    // 构建带标注的内容
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;

    sortedAnnotations.forEach((annotation, index) => {
      // 添加标注前的文本
      if (annotation.start > lastIndex) {
        parts.push(
          <span key={`text-${index}`}>
            {content.substring(lastIndex, annotation.start)}
          </span>
        );
      }

      // 添加标注文本
      parts.push(
        <span
          key={`annotation-${index}`}
          className={`annotation annotation-${annotation.type}`}
          title={`${annotation.type} 标注`}
        >
          {content.substring(annotation.start, annotation.end)}
        </span>
      );

      lastIndex = annotation.end;
    });

    // 添加最后的文本
    if (lastIndex < content.length) {
      parts.push(
        <span key="text-end">
          {content.substring(lastIndex)}
        </span>
      );
    }

    return <div className="annotation-content">{parts}</div>;
  };

  const getAnnotationIcon = (type: Annotation['type']) => {
    switch (type) {
      case 'highlight':
        return <Highlighter size={16} />;
      case 'note':
        return <MessageSquare size={16} />;
      case 'question':
        return <HelpCircle size={16} />;
      case 'issue':
        return <AlertCircle size={16} />;
    }
  };

  return (
    <div className="annotation-tool">
      <div
        ref={contentRef}
        className="annotation-container"
        onMouseUp={handleTextSelection}
      >
        {renderAnnotatedContent()}
      </div>

      {showMenu && !annotationType && (
        <div
          className="annotation-menu"
          style={{
            left: `${menuPosition.x}px`,
            top: `${menuPosition.y}px`,
          }}
        >
          <button
            className="annotation-menu-item annotation-menu-highlight"
            onClick={() => handleAnnotate('highlight')}
            title="高亮"
          >
            <Highlighter size={16} />
            高亮
          </button>
          <button
            className="annotation-menu-item annotation-menu-note"
            onClick={() => handleAnnotate('note')}
            title="笔记"
          >
            <MessageSquare size={16} />
            笔记
          </button>
          <button
            className="annotation-menu-item annotation-menu-question"
            onClick={() => handleAnnotate('question')}
            title="问题"
          >
            <HelpCircle size={16} />
            问题
          </button>
          <button
            className="annotation-menu-item annotation-menu-issue"
            onClick={() => handleAnnotate('issue')}
            title="问题"
          >
            <AlertCircle size={16} />
            问题
          </button>
        </div>
      )}

      {annotationType && (
        <div className="annotation-dialog">
          <div className="annotation-dialog-header">
            {getAnnotationIcon(annotationType)}
            <span>添加{annotationType === 'highlight' ? '高亮' : annotationType === 'note' ? '笔记' : annotationType === 'question' ? '问题' : '问题'}</span>
          </div>
          <div className="annotation-dialog-body">
            <div className="annotation-selected-text">
              "{selectedText}"
            </div>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="添加评论（可选）..."
              className="annotation-comment-input"
              rows={3}
              autoFocus
            />
          </div>
          <div className="annotation-dialog-footer">
            <button
              onClick={handleSubmitAnnotation}
              className="btn-primary"
            >
              保存
            </button>
            <button
              onClick={handleCancelAnnotation}
              className="btn-secondary"
            >
              取消
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

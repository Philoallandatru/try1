"""
评论和标注 API

提供分析结果的评论和标注功能。
"""

import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel


class Comment(BaseModel):
    """评论模型"""
    comment_id: str
    analysis_id: str
    workspace_dir: str
    user_id: str
    user_name: str
    content: str
    created_at: str
    updated_at: Optional[str] = None
    parent_id: Optional[str] = None  # 用于回复评论
    annotation: Optional[Dict[str, Any]] = None  # 标注信息
    resolved: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "comment_id": "cmt_abc123",
                "analysis_id": "issue_001",
                "workspace_dir": "/path/to/workspace",
                "user_id": "user_001",
                "user_name": "张三",
                "content": "这个分析结果很有价值",
                "created_at": "2024-01-01T12:00:00Z",
                "parent_id": None,
                "annotation": {
                    "type": "highlight",
                    "start": 100,
                    "end": 150,
                    "text": "highlighted text"
                },
                "resolved": False
            }
        }


class Annotation(BaseModel):
    """标注模型"""
    type: str  # highlight, note, question, issue
    start: int  # 起始位置
    end: int  # 结束位置
    text: str  # 标注的文本
    color: Optional[str] = None  # 标注颜色


class CommentManager:
    """评论管理器"""

    def __init__(self, storage_dir: str = ".comments"):
        """
        初始化评论管理器

        Args:
            storage_dir: 评论存储目录
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _get_comment_file(self, workspace_dir: str, analysis_id: str) -> str:
        """获取评论文件路径"""
        # 使用 workspace_dir 和 analysis_id 创建唯一的文件名
        safe_workspace = workspace_dir.replace("/", "_").replace("\\", "_").replace(":", "")
        safe_analysis = analysis_id.replace("/", "_").replace("\\", "_")
        filename = f"{safe_workspace}_{safe_analysis}.json"
        return os.path.join(self.storage_dir, filename)

    def _load_comments(self, workspace_dir: str, analysis_id: str) -> List[Dict[str, Any]]:
        """加载评论列表"""
        comment_file = self._get_comment_file(workspace_dir, analysis_id)
        if not os.path.exists(comment_file):
            return []

        try:
            with open(comment_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def _save_comments(self, workspace_dir: str, analysis_id: str, comments: List[Dict[str, Any]]):
        """保存评论列表"""
        comment_file = self._get_comment_file(workspace_dir, analysis_id)
        with open(comment_file, 'w', encoding='utf-8') as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)

    def create_comment(
        self,
        analysis_id: str,
        workspace_dir: str,
        user_id: str,
        user_name: str,
        content: str,
        parent_id: Optional[str] = None,
        annotation: Optional[Dict[str, Any]] = None
    ) -> Comment:
        """
        创建评论

        Args:
            analysis_id: 分析 ID
            workspace_dir: 工作空间目录
            user_id: 用户 ID
            user_name: 用户名
            content: 评论内容
            parent_id: 父评论 ID（用于回复）
            annotation: 标注信息

        Returns:
            创建的评论对象
        """
        import secrets

        comment_id = f"cmt_{secrets.token_hex(8)}"
        now = datetime.utcnow().isoformat() + "Z"

        comment = Comment(
            comment_id=comment_id,
            analysis_id=analysis_id,
            workspace_dir=workspace_dir,
            user_id=user_id,
            user_name=user_name,
            content=content,
            created_at=now,
            parent_id=parent_id,
            annotation=annotation,
            resolved=False
        )

        # 加载现有评论
        comments = self._load_comments(workspace_dir, analysis_id)

        # 添加新评论
        comments.append(comment.model_dump())

        # 保存
        self._save_comments(workspace_dir, analysis_id, comments)

        return comment

    def get_comments(
        self,
        workspace_dir: str,
        analysis_id: str,
        include_resolved: bool = True
    ) -> List[Comment]:
        """
        获取评论列表

        Args:
            workspace_dir: 工作空间目录
            analysis_id: 分析 ID
            include_resolved: 是否包含已解决的评论

        Returns:
            评论列表
        """
        comments = self._load_comments(workspace_dir, analysis_id)

        if not include_resolved:
            comments = [c for c in comments if not c.get('resolved', False)]

        return [Comment(**c) for c in comments]

    def get_comment(
        self,
        workspace_dir: str,
        analysis_id: str,
        comment_id: str
    ) -> Optional[Comment]:
        """
        获取单个评论

        Args:
            workspace_dir: 工作空间目录
            analysis_id: 分析 ID
            comment_id: 评论 ID

        Returns:
            评论对象，如果不存在返回 None
        """
        comments = self._load_comments(workspace_dir, analysis_id)

        for c in comments:
            if c.get('comment_id') == comment_id:
                return Comment(**c)

        return None

    def update_comment(
        self,
        workspace_dir: str,
        analysis_id: str,
        comment_id: str,
        content: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> Optional[Comment]:
        """
        更新评论

        Args:
            workspace_dir: 工作空间目录
            analysis_id: 分析 ID
            comment_id: 评论 ID
            content: 新的评论内容
            resolved: 是否已解决

        Returns:
            更新后的评论对象，如果不存在返回 None
        """
        comments = self._load_comments(workspace_dir, analysis_id)

        for i, c in enumerate(comments):
            if c.get('comment_id') == comment_id:
                if content is not None:
                    c['content'] = content
                    c['updated_at'] = datetime.utcnow().isoformat() + "Z"

                if resolved is not None:
                    c['resolved'] = resolved

                comments[i] = c
                self._save_comments(workspace_dir, analysis_id, comments)
                return Comment(**c)

        return None

    def delete_comment(
        self,
        workspace_dir: str,
        analysis_id: str,
        comment_id: str
    ) -> bool:
        """
        删除评论

        Args:
            workspace_dir: 工作空间目录
            analysis_id: 分析 ID
            comment_id: 评论 ID

        Returns:
            是否删除成功
        """
        comments = self._load_comments(workspace_dir, analysis_id)

        # 找到要删除的评论
        original_len = len(comments)
        comments = [c for c in comments if c.get('comment_id') != comment_id]

        if len(comments) < original_len:
            # 同时删除所有回复
            comments = [c for c in comments if c.get('parent_id') != comment_id]
            self._save_comments(workspace_dir, analysis_id, comments)
            return True

        return False

    def get_comment_thread(
        self,
        workspace_dir: str,
        analysis_id: str,
        comment_id: str
    ) -> List[Comment]:
        """
        获取评论线程（包括所有回复）

        Args:
            workspace_dir: 工作空间目录
            analysis_id: 分析 ID
            comment_id: 根评论 ID

        Returns:
            评论线程列表
        """
        comments = self._load_comments(workspace_dir, analysis_id)

        # 找到根评论
        root_comment = None
        for c in comments:
            if c.get('comment_id') == comment_id:
                root_comment = c
                break

        if not root_comment:
            return []

        # 找到所有回复
        thread = [Comment(**root_comment)]
        replies = [c for c in comments if c.get('parent_id') == comment_id]
        thread.extend([Comment(**r) for r in replies])

        return thread

    def get_annotations(
        self,
        workspace_dir: str,
        analysis_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取所有标注

        Args:
            workspace_dir: 工作空间目录
            analysis_id: 分析 ID

        Returns:
            标注列表
        """
        comments = self._load_comments(workspace_dir, analysis_id)

        annotations = []
        for c in comments:
            if c.get('annotation') and not c.get('resolved', False):
                annotations.append({
                    'comment_id': c.get('comment_id'),
                    'annotation': c.get('annotation'),
                    'content': c.get('content'),
                    'user_name': c.get('user_name'),
                    'created_at': c.get('created_at')
                })

        return annotations

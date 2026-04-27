"""
模拟 Jira 和 Confluence REST API 服务器

用于性能测试，可以生成大量模拟数据而不依赖真实的 Atlassian 实例。

使用方法:
    # 启动服务器（默认端口 8888）
    python scripts/mock_atlassian_server.py

    # 指定端口
    python scripts/mock_atlassian_server.py --port 9000

    # 指定数据规模
    python scripts/mock_atlassian_server.py --jira-issues 10000 --confluence-pages 5000

然后在配置数据源时使用:
    Base URL: http://localhost:8888
    Token: mock-token (任意值都可以)
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn


# ============================================================================
# 数据生成器
# ============================================================================

class MockDataGenerator:
    """生成模拟的 Jira 和 Confluence 数据"""

    def __init__(self, jira_issues: int = 10000, confluence_pages: int = 5000):
        self.jira_issues_count = jira_issues
        self.confluence_pages_count = confluence_pages
        self.base_date = datetime.now() - timedelta(days=365)

        # 预定义的数据
        self.projects = ["SSD", "FW", "HW", "TEST", "DOC"]
        self.issue_types = ["Bug", "Task", "Story", "Epic", "Sub-task"]
        self.statuses = ["Open", "In Progress", "In Review", "Resolved", "Closed"]
        self.priorities = ["Highest", "High", "Medium", "Low", "Lowest"]
        self.components = ["NVMe", "SATA", "PCIe", "Firmware", "Driver", "Testing"]
        self.labels = ["performance", "security", "bug-fix", "feature", "refactor", "documentation"]

        self.spaces = ["TECH", "DESIGN", "SPEC", "WIKI", "TEAM"]
        self.page_types = ["page", "blogpost"]

    def generate_jira_issue(self, issue_number: int) -> dict[str, Any]:
        """生成单个 Jira Issue"""
        project = random.choice(self.projects)
        issue_key = f"{project}-{issue_number}"

        # 生成时间戳（越新的 issue 时间越近）
        days_ago = int((self.jira_issues_count - issue_number) / 10)
        created = self.base_date + timedelta(days=days_ago)
        updated = created + timedelta(days=random.randint(0, 30))

        return {
            "id": str(10000 + issue_number),
            "key": issue_key,
            "self": f"http://localhost:8888/rest/api/2/issue/{issue_key}",
            "fields": {
                "summary": f"[Mock] Issue {issue_key}: {random.choice(['Fix', 'Implement', 'Update', 'Refactor'])} {random.choice(self.components)}",
                "description": self._generate_description(issue_key),
                "issuetype": {
                    "id": str(random.randint(1, 5)),
                    "name": random.choice(self.issue_types),
                    "subtask": False,
                },
                "project": {
                    "id": str(self.projects.index(project) + 1),
                    "key": project,
                    "name": f"{project} Project",
                },
                "status": {
                    "id": str(random.randint(1, 5)),
                    "name": random.choice(self.statuses),
                },
                "priority": {
                    "id": str(random.randint(1, 5)),
                    "name": random.choice(self.priorities),
                },
                "assignee": {
                    "name": f"user{random.randint(1, 20)}",
                    "displayName": f"Test User {random.randint(1, 20)}",
                    "emailAddress": f"user{random.randint(1, 20)}@example.com",
                },
                "reporter": {
                    "name": f"user{random.randint(1, 20)}",
                    "displayName": f"Test User {random.randint(1, 20)}",
                    "emailAddress": f"user{random.randint(1, 20)}@example.com",
                },
                "created": created.isoformat() + "+0000",
                "updated": updated.isoformat() + "+0000",
                "components": [
                    {"id": str(i), "name": comp}
                    for i, comp in enumerate(random.sample(self.components, k=random.randint(1, 3)))
                ],
                "labels": random.sample(self.labels, k=random.randint(0, 3)),
                "comment": {
                    "comments": self._generate_comments(random.randint(0, 5)),
                    "maxResults": 50,
                    "total": random.randint(0, 5),
                    "startAt": 0,
                },
                "attachment": self._generate_attachments(random.randint(0, 3)),
            },
        }

    def _generate_description(self, issue_key: str) -> str:
        """生成 Issue 描述"""
        templates = [
            f"This is a mock issue {issue_key} for performance testing.\n\n"
            f"h2. Problem\n"
            f"The system is experiencing performance issues when processing large datasets.\n\n"
            f"h2. Expected Behavior\n"
            f"The system should handle {random.randint(1000, 10000)} items per second.\n\n"
            f"h2. Actual Behavior\n"
            f"Currently processing only {random.randint(10, 100)} items per second.\n\n"
            f"h2. Steps to Reproduce\n"
            f"1. Configure data source with large dataset\n"
            f"2. Run sync operation\n"
            f"3. Observe performance metrics\n",

            f"Mock issue {issue_key} - Testing data synchronization.\n\n"
            f"*Background:*\n"
            f"We need to improve the data sync performance for handling large-scale operations.\n\n"
            f"*Acceptance Criteria:*\n"
            f"- [ ] Sync completes in under {random.randint(5, 30)} minutes\n"
            f"- [ ] Memory usage stays below {random.randint(200, 500)} MB\n"
            f"- [ ] No data loss during sync\n",
        ]
        return random.choice(templates)

    def _generate_comments(self, count: int) -> list[dict]:
        """生成评论"""
        comments = []
        for i in range(count):
            comments.append({
                "id": str(100000 + i),
                "author": {
                    "name": f"user{random.randint(1, 20)}",
                    "displayName": f"Test User {random.randint(1, 20)}",
                },
                "body": f"This is comment {i+1}. {random.choice(['LGTM', 'Needs review', 'Fixed in latest commit', 'Testing now'])}",
                "created": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat() + "+0000",
            })
        return comments

    def _generate_attachments(self, count: int) -> list[dict]:
        """生成附件"""
        attachments = []
        for i in range(count):
            attachments.append({
                "id": str(200000 + i),
                "filename": f"attachment_{i+1}.{random.choice(['png', 'jpg', 'pdf', 'txt'])}",
                "size": random.randint(1024, 1024*1024),
                "mimeType": random.choice(["image/png", "image/jpeg", "application/pdf", "text/plain"]),
                "content": f"http://localhost:8888/attachment/{200000 + i}",
            })
        return attachments

    def generate_confluence_page(self, page_number: int) -> dict[str, Any]:
        """生成单个 Confluence Page"""
        space = random.choice(self.spaces)
        page_id = str(300000 + page_number)

        days_ago = int((self.confluence_pages_count - page_number) / 10)
        created = self.base_date + timedelta(days=days_ago)
        updated = created + timedelta(days=random.randint(0, 30))

        return {
            "id": page_id,
            "type": random.choice(self.page_types),
            "status": "current",
            "title": f"[Mock] {random.choice(['Design', 'Specification', 'Guide', 'Documentation'])} - Page {page_number}",
            "space": {
                "id": str(self.spaces.index(space) + 1),
                "key": space,
                "name": f"{space} Space",
            },
            "version": {
                "number": random.randint(1, 20),
                "when": updated.isoformat() + "+0000",
                "by": {
                    "username": f"user{random.randint(1, 20)}",
                    "displayName": f"Test User {random.randint(1, 20)}",
                },
            },
            "body": {
                "storage": {
                    "value": self._generate_page_content(page_number),
                    "representation": "storage",
                }
            },
            "metadata": {
                "labels": {
                    "results": [
                        {"name": label} for label in random.sample(self.labels, k=random.randint(0, 3))
                    ]
                }
            },
            "_links": {
                "self": f"http://localhost:8888/rest/api/content/{page_id}",
                "webui": f"/pages/viewpage.action?pageId={page_id}",
            },
        }

    def _generate_page_content(self, page_number: int) -> str:
        """生成 Confluence 页面内容"""
        return f"""
<h1>Mock Page {page_number}</h1>
<p>This is a mock Confluence page for performance testing.</p>

<h2>Overview</h2>
<p>This page contains information about {random.choice(self.components)} implementation.</p>

<h2>Technical Details</h2>
<ul>
    <li>Component: {random.choice(self.components)}</li>
    <li>Version: {random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 99)}</li>
    <li>Status: {random.choice(['Active', 'Deprecated', 'In Development'])}</li>
</ul>

<h2>Related Issues</h2>
<p>See {random.choice(self.projects)}-{random.randint(1, 1000)} for more details.</p>

<ac:structured-macro ac:name="info">
    <ac:rich-text-body>
        <p>This is mock content generated for testing purposes.</p>
    </ac:rich-text-body>
</ac:structured-macro>
"""


# ============================================================================
# FastAPI 应用
# ============================================================================

app = FastAPI(title="Mock Atlassian Server", version="1.0.0")

# 全局数据生成器
generator: MockDataGenerator | None = None


def verify_auth(authorization: str | None) -> bool:
    """验证认证（接受任何 token）"""
    if not authorization:
        return False
    # 接受任何 Bearer token 或 Basic auth
    return authorization.startswith("Bearer ") or authorization.startswith("Basic ")


# ============================================================================
# Jira REST API 端点
# ============================================================================

@app.get("/rest/api/2/search")
async def jira_search(
    jql: str = Query(default="order by updated asc"),
    startAt: int = Query(default=0),
    maxResults: int = Query(default=50),
    authorization: str | None = Header(default=None),
):
    """Jira Issue 搜索 API"""
    if not verify_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if generator is None:
        raise HTTPException(status_code=500, detail="Generator not initialized")

    # 计算返回的 issues
    total = generator.jira_issues_count
    end_at = min(startAt + maxResults, total)

    issues = []
    for i in range(startAt + 1, end_at + 1):
        issues.append(generator.generate_jira_issue(i))

    return {
        "expand": "schema,names",
        "startAt": startAt,
        "maxResults": maxResults,
        "total": total,
        "issues": issues,
    }


@app.get("/rest/api/2/issue/{issue_key}")
async def jira_get_issue(
    issue_key: str,
    authorization: str | None = Header(default=None),
):
    """获取单个 Jira Issue"""
    if not verify_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if generator is None:
        raise HTTPException(status_code=500, detail="Generator not initialized")

    # 从 issue_key 中提取编号
    try:
        issue_number = int(issue_key.split("-")[1])
        if issue_number < 1 or issue_number > generator.jira_issues_count:
            raise HTTPException(status_code=404, detail="Issue not found")
        return generator.generate_jira_issue(issue_number)
    except (IndexError, ValueError):
        raise HTTPException(status_code=404, detail="Issue not found")


@app.get("/rest/api/2/serverInfo")
async def jira_server_info(authorization: str | None = Header(default=None)):
    """Jira 服务器信息（用于连接测试）"""
    if not verify_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {
        "baseUrl": "http://localhost:8888",
        "version": "9.12.0",
        "versionNumbers": [9, 12, 0],
        "deploymentType": "Mock Server",
        "buildNumber": 912000,
        "buildDate": datetime.now().isoformat(),
        "serverTitle": "Mock Jira Server",
    }


# ============================================================================
# Confluence REST API 端点
# ============================================================================

@app.get("/wiki/rest/api/content")
async def confluence_search(
    type: str = Query(default="page"),
    spaceKey: str | None = Query(default=None),
    start: int = Query(default=0),
    limit: int = Query(default=25),
    expand: str = Query(default="body.storage,version,space,metadata.labels"),
    authorization: str | None = Header(default=None),
):
    """Confluence 内容搜索 API"""
    if not verify_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if generator is None:
        raise HTTPException(status_code=500, detail="Generator not initialized")

    # 计算返回的 pages
    total = generator.confluence_pages_count
    end_at = min(start + limit, total)

    results = []
    for i in range(start + 1, end_at + 1):
        page = generator.generate_confluence_page(i)
        # 如果指定了 spaceKey，过滤
        if spaceKey and page["space"]["key"] != spaceKey:
            continue
        results.append(page)

    return {
        "results": results,
        "start": start,
        "limit": limit,
        "size": len(results),
        "_links": {
            "self": f"http://localhost:8888/wiki/rest/api/content?start={start}&limit={limit}",
            "next": f"http://localhost:8888/wiki/rest/api/content?start={end_at}&limit={limit}" if end_at < total else None,
        },
    }


@app.get("/wiki/rest/api/content/{page_id}")
async def confluence_get_page(
    page_id: str,
    expand: str = Query(default="body.storage,version,space,metadata.labels"),
    authorization: str | None = Header(default=None),
):
    """获取单个 Confluence Page"""
    if not verify_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if generator is None:
        raise HTTPException(status_code=500, detail="Generator not initialized")

    try:
        page_number = int(page_id) - 300000
        if page_number < 1 or page_number > generator.confluence_pages_count:
            raise HTTPException(status_code=404, detail="Page not found")
        return generator.generate_confluence_page(page_number)
    except ValueError:
        raise HTTPException(status_code=404, detail="Page not found")


# ============================================================================
# 通用端点
# ============================================================================

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Mock Atlassian Server",
        "jira_api": "http://localhost:8888/rest/api/2/",
        "confluence_api": "http://localhost:8888/wiki/rest/api/",
        "jira_issues": generator.jira_issues_count if generator else 0,
        "confluence_pages": generator.confluence_pages_count if generator else 0,
        "usage": {
            "jira_search": "GET /rest/api/2/search?jql=...&startAt=0&maxResults=50",
            "confluence_search": "GET /wiki/rest/api/content?type=page&start=0&limit=25",
            "auth": "Use any Bearer token or Basic auth (e.g., 'Bearer mock-token')",
        },
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "jira_issues": generator.jira_issues_count if generator else 0,
        "confluence_pages": generator.confluence_pages_count if generator else 0,
    }


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Mock Atlassian Server for performance testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8888, help="Port to bind to")
    parser.add_argument("--jira-issues", type=int, default=10000, help="Number of mock Jira issues")
    parser.add_argument("--confluence-pages", type=int, default=5000, help="Number of mock Confluence pages")

    args = parser.parse_args()

    # 初始化数据生成器
    global generator
    generator = MockDataGenerator(
        jira_issues=args.jira_issues,
        confluence_pages=args.confluence_pages,
    )

    print("=" * 80)
    print("Mock Atlassian Server")
    print("=" * 80)
    print(f"Jira API:       http://{args.host}:{args.port}/rest/api/2/")
    print(f"Confluence API: http://{args.host}:{args.port}/wiki/rest/api/")
    print(f"Mock Data:")
    print(f"   - Jira Issues:      {args.jira_issues:,}")
    print(f"   - Confluence Pages: {args.confluence_pages:,}")
    print(f"\nAuthentication: Use any token (e.g., 'Bearer mock-token')")
    print(f"\nUsage:")
    print(f"   1. Start this server")
    print(f"   2. Configure data source:")
    print(f"      Base URL: http://localhost:{args.port}")
    print(f"      Token: mock-token (any value works)")
    print(f"   3. Run performance diagnosis")
    print("=" * 80)
    print()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

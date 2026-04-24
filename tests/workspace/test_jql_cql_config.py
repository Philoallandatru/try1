"""
测试 JQL/CQL 简化配置功能
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from services.workspace.workspace import (
    init_workspace,
    add_workspace_source,
    configure_workspace_source,
    fetch_workspace_source,
    load_source,
)


@pytest.fixture
def temp_workspace():
    """创建临时工作空间"""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "test_workspace"
    init_workspace(workspace_path)
    yield workspace_path
    shutil.rmtree(temp_dir)


def test_add_jira_source_with_jql(temp_workspace):
    """测试添加带 JQL 的 Jira 数据源"""
    result = add_workspace_source(
        temp_workspace,
        "test_jira",
        connector_type="jira.atlassian_api",
        base_url="https://test.atlassian.net",
        jql="project = TEST AND status = Open",
    )

    source = result["source"]
    assert source["name"] == "test_jira"
    assert source["kind"] == "jira"
    assert source["config"]["jql"] == "project = TEST AND status = Open"


def test_add_confluence_source_with_cql(temp_workspace):
    """测试添加带 CQL 的 Confluence 数据源"""
    result = add_workspace_source(
        temp_workspace,
        "test_confluence",
        connector_type="confluence.atlassian_api",
        base_url="https://test.atlassian.net",
        cql="space = DOCS AND type = page",
    )

    source = result["source"]
    assert source["name"] == "test_confluence"
    assert source["kind"] == "confluence"
    assert source["config"]["cql"] == "space = DOCS AND type = page"


def test_configure_source_update_jql(temp_workspace):
    """测试更新数据源的 JQL"""
    # 先添加数据源
    add_workspace_source(
        temp_workspace,
        "test_jira",
        connector_type="jira.atlassian_api",
        base_url="https://test.atlassian.net",
        jql="project = TEST",
    )

    # 更新 JQL
    result = configure_workspace_source(
        temp_workspace,
        "test_jira",
        jql="project = TEST AND assignee = currentUser()",
    )

    source = result["source"]
    assert source["config"]["jql"] == "project = TEST AND assignee = currentUser()"


def test_configure_source_update_cql(temp_workspace):
    """测试更新数据源的 CQL"""
    # 先添加数据源
    add_workspace_source(
        temp_workspace,
        "test_confluence",
        connector_type="confluence.atlassian_api",
        base_url="https://test.atlassian.net",
        cql="space = DOCS",
    )

    # 更新 CQL
    result = configure_workspace_source(
        temp_workspace,
        "test_confluence",
        cql="space = DOCS AND label = important",
    )

    source = result["source"]
    assert source["config"]["cql"] == "space = DOCS AND label = important"


def test_load_source_with_jql_cql(temp_workspace):
    """测试加载带 JQL/CQL 的数据源"""
    add_workspace_source(
        temp_workspace,
        "test_jira",
        connector_type="jira.atlassian_api",
        base_url="https://test.atlassian.net",
        jql="project = TEST",
    )

    source = load_source(temp_workspace, "test_jira")

    assert source["name"] == "test_jira"
    assert source["config"]["jql"] == "project = TEST"


def test_add_source_without_jql_cql(temp_workspace):
    """测试添加不带 JQL/CQL 的数据源（传统方式）"""
    result = add_workspace_source(
        temp_workspace,
        "test_jira",
        connector_type="jira.atlassian_api",
        base_url="https://test.atlassian.net",
    )

    source = result["source"]
    assert source["name"] == "test_jira"
    assert "jql" not in source.get("config", {})


def test_both_jql_and_cql(temp_workspace):
    """测试 JQL 和 CQL 同时提供时的行为"""
    result = add_workspace_source(
        temp_workspace,
        "test_source",
        connector_type="jira.atlassian_api",
        base_url="https://test.atlassian.net",
        jql="project = TEST",
        cql="space = DOCS",
    )

    source = result["source"]
    # 两者都应该被保存到 config 中
    assert source["config"]["jql"] == "project = TEST"
    assert source["config"]["cql"] == "space = DOCS"

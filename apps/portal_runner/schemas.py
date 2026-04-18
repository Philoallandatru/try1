from __future__ import annotations

from dataclasses import dataclass


TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


@dataclass(frozen=True)
class PipelineInput:
    pipeline_id: str
    jira_issue_key: str | None = None
    confluence_page_id: str | None = None
    confluence_page_ids: str | None = None
    confluence_scope: str | None = None
    confluence_root_page_id: str | None = None
    confluence_space_key: str | None = None
    confluence_label: str | None = None
    confluence_modified_from: str | None = None
    confluence_modified_to: str | None = None
    confluence_max_depth: int | None = None
    spec_asset_id: str | None = None
    preferred_parser: str | None = None
    publish_wiki: bool | None = None
    topic_slug: str | None = None
    topic_title: str | None = None
    mock_response: str | None = None
    profile: str | None = None
    prompt: str | None = None

    def public_summary(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "jira_issue_key": self.jira_issue_key,
            "confluence_page_id": self.confluence_page_id,
            "confluence_page_ids": self.confluence_page_ids,
            "confluence_scope": self.confluence_scope,
            "confluence_root_page_id": self.confluence_root_page_id,
            "confluence_space_key": self.confluence_space_key,
            "confluence_label": self.confluence_label,
            "confluence_modified_from": self.confluence_modified_from,
            "confluence_modified_to": self.confluence_modified_to,
            "confluence_max_depth": self.confluence_max_depth,
            "spec_asset_id": self.spec_asset_id,
            "preferred_parser": self.preferred_parser,
            "publish_wiki": self.publish_wiki,
            "topic_slug": self.topic_slug,
            "topic_title": self.topic_title,
            "profile": self.profile,
            "prompt": self.prompt,
        }


@dataclass(frozen=True)
class PipelineDefinition:
    pipeline_id: str
    label: str
    description: str
    required_inputs: list[str]
    accepts_pdf: bool
    steps: list[str]

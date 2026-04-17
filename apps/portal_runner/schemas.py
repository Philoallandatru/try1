from __future__ import annotations

from dataclasses import dataclass


TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


@dataclass(frozen=True)
class PipelineInput:
    pipeline_id: str
    jira_issue_key: str | None = None
    confluence_page_id: str | None = None
    preferred_parser: str | None = None
    publish_wiki: bool | None = None
    topic_slug: str | None = None
    topic_title: str | None = None
    mock_response: str | None = None

    def public_summary(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "jira_issue_key": self.jira_issue_key,
            "confluence_page_id": self.confluence_page_id,
            "preferred_parser": self.preferred_parser,
            "publish_wiki": self.publish_wiki,
            "topic_slug": self.topic_slug,
            "topic_title": self.topic_title,
        }


@dataclass(frozen=True)
class PipelineDefinition:
    pipeline_id: str
    label: str
    description: str
    required_inputs: list[str]
    accepts_pdf: bool
    steps: list[str]

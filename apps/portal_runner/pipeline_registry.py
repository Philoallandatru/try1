from __future__ import annotations

from apps.portal_runner.schemas import PipelineDefinition


PIPELINES: dict[str, PipelineDefinition] = {
    "jira_live_smoke": PipelineDefinition(
        pipeline_id="jira_live_smoke",
        label="Jira live smoke",
        description="Fetch one live Jira issue and persist the normalized payload.",
        required_inputs=["jira_issue_key"],
        accepts_pdf=False,
        steps=["validate_config", "jira_live_fetch"],
    ),
    "confluence_live_smoke": PipelineDefinition(
        pipeline_id="confluence_live_smoke",
        label="Confluence live smoke",
        description="Fetch one live Confluence page and persist the normalized payload.",
        required_inputs=["confluence_page_id"],
        accepts_pdf=False,
        steps=["validate_config", "confluence_live_fetch"],
    ),
    "pdf_ingest_smoke": PipelineDefinition(
        pipeline_id="pdf_ingest_smoke",
        label="PDF ingest smoke",
        description="Upload a PDF and ingest it as a reusable shared workspace spec asset.",
        required_inputs=["pdf"],
        accepts_pdf=True,
        steps=["validate_config", "store_uploaded_pdf", "workspace_init", "pdf_spec_asset_ingest"],
    ),
    "jira_pdf_qa_smoke": PipelineDefinition(
        pipeline_id="jira_pdf_qa_smoke",
        label="Jira PDF/Confluence QA",
        description="Run Jira QA over one Jira issue, a small Confluence slice, and an uploaded or reusable spec asset.",
        required_inputs=["jira_issue_key", "confluence_selector"],
        accepts_pdf=True,
        steps=[
            "validate_config",
            "store_uploaded_pdf",
            "jira_live_fetch",
            "confluence_live_fetch",
            "workspace_init",
            "spec_asset_select_or_ingest",
            "workspace_build",
            "deep_analysis",
            "portal_state",
        ],
    ),
    "full_real_data_smoke": PipelineDefinition(
        pipeline_id="full_real_data_smoke",
        label="Full real-data smoke",
        description="Run Jira, Confluence, PDF, workspace analysis, portal-state, and optional wiki publish.",
        required_inputs=["jira_issue_key", "confluence_page_id", "pdf"],
        accepts_pdf=True,
        steps=[
            "validate_config",
            "store_uploaded_pdf",
            "jira_live_fetch",
            "confluence_live_fetch",
            "workspace_init",
            "pdf_spec_asset_ingest",
            "workspace_build",
            "deep_analysis",
            "portal_state",
            "optional_publish_wiki",
        ],
    ),
    "profile_prompt_debug": PipelineDefinition(
        pipeline_id="profile_prompt_debug",
        label="Profile prompt debug",
        description="Build a registry-backed workspace profile and ask an LLM to debug Jira plus selected knowledge sources.",
        required_inputs=["prompt"],
        accepts_pdf=True,
        steps=[
            "validate_config",
            "store_uploaded_pdf",
            "workspace_init",
            "profile_prepare",
            "profile_prompt_query",
            "portal_state",
        ],
    ),
}


def list_pipeline_definitions(enabled_config: dict[str, bool] | None = None) -> list[dict]:
    enabled_config = enabled_config or {}
    rows = []
    for definition in PIPELINES.values():
        rows.append(
            {
                "pipeline_id": definition.pipeline_id,
                "label": definition.label,
                "description": definition.description,
                "required_inputs": definition.required_inputs,
                "accepts_pdf": definition.accepts_pdf,
                "steps": definition.steps,
                "enabled": enabled_config.get(definition.pipeline_id, True),
            }
        )
    return rows


def get_pipeline_definition(pipeline_id: str) -> PipelineDefinition:
    try:
        return PIPELINES[pipeline_id]
    except KeyError as exc:
        raise ValueError(f"Unknown pipeline: {pipeline_id}") from exc

from __future__ import annotations

from typing import Callable

from services.analysis.llm_backends import build_llm_backend
from services.workspace.prefect_adapter import PrefectRuntimeUnavailable


def _load_prefect_flow() -> Callable[..., Callable]:
    try:
        from prefect import flow
    except ImportError as error:
        raise PrefectRuntimeUnavailable(
            "Prefect is not installed. Install the optional Prefect dependencies before building Prefect flows."
        ) from error
    return flow


def build_jira_deep_analysis_flow(flow_decorator: Callable[..., Callable] | None = None):
    decorator = flow_decorator or _load_prefect_flow()

    @decorator(name="jira_deep_analysis")
    def jira_deep_analysis_flow(
        workspace_dir: str,
        issue_key: str,
        policies: list[str] | None = None,
        top_k: int = 5,
        prompt_mode: str = "strict",
        llm_backend: str = "none",
        llm_model: str | None = None,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        llm_mock_response: str | None = None,
        llm_timeout_seconds: int = 120,
    ) -> dict:
        from services.workspace.workspace import deep_analyze_issue

        backend = build_llm_backend(
            backend=llm_backend,
            model=llm_model,
            base_url=llm_base_url,
            api_key=llm_api_key,
            mock_response=llm_mock_response,
            timeout_seconds=llm_timeout_seconds,
        )
        payload = deep_analyze_issue(
            workspace_dir,
            issue_key,
            policies=policies,
            top_k=top_k,
            prompt_mode=prompt_mode,
            llm_backend=backend,
        )
        return {
            "issue_id": payload["issue_id"],
            "analysis_profile": payload["analysis_profile"],
            "run_dir": payload["run_dir"],
            "run_manifest_path": payload["run_manifest_path"],
            "answer": payload["answer"],
        }

    return jira_deep_analysis_flow


def _prefect_unavailable_flow(*_args, **_kwargs):
    raise PrefectRuntimeUnavailable(
        "Prefect is not installed. Install the optional Prefect dependencies before running the jira_deep_analysis flow."
    )


try:
    jira_deep_analysis = build_jira_deep_analysis_flow()
except PrefectRuntimeUnavailable:
    jira_deep_analysis = _prefect_unavailable_flow


def run_jira_deep_analysis_flow(
    *,
    workspace_dir: str,
    issue_key: str,
    policies: list[str] | None = None,
    top_k: int = 5,
    prompt_mode: str = "strict",
    llm_backend: str = "none",
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_mock_response: str | None = None,
    llm_timeout_seconds: int = 120,
) -> dict:
    flow_fn = build_jira_deep_analysis_flow()
    return flow_fn(
        workspace_dir=workspace_dir,
        issue_key=issue_key,
        policies=policies,
        top_k=top_k,
        prompt_mode=prompt_mode,
        llm_backend=llm_backend,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_mock_response=llm_mock_response,
        llm_timeout_seconds=llm_timeout_seconds,
    )

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from services.workspace.task_control import apply_adapter_state, build_control_event


PREFECT_STATE_TO_ADAPTER_STATE = {
    "scheduled": "scheduled",
    "pending": "scheduled",
    "running": "running",
    "cancelling": "cancelling",
    "cancelled": "cancelled",
    "completed": "succeeded",
    "failed": "failed",
    "crashed": "failed",
}


class PrefectRuntimeUnavailable(RuntimeError):
    pass


def prefect_state_to_adapter_state(state_name: str) -> str:
    normalized = state_name.strip().lower()
    try:
        return PREFECT_STATE_TO_ADAPTER_STATE[normalized]
    except KeyError as error:
        expected = ", ".join(sorted(PREFECT_STATE_TO_ADAPTER_STATE))
        raise ValueError(f"Unsupported Prefect state: {state_name}. Expected one of: {expected}") from error


def build_prefect_run_reference(
    manifest: dict,
    *,
    flow_run_id: str | None = None,
    flow_name: str = "jira_deep_analysis",
    deployment_name: str | None = None,
) -> dict:
    return {
        "adapter": "prefect",
        "flow_name": flow_name,
        "deployment_name": deployment_name,
        "flow_run_id": flow_run_id or f"prefect-{manifest['run_id']}",
        "run_id": manifest["run_id"],
        "run_version": manifest["run_version"],
        "task_type": manifest["task_type"],
    }


def _deployment_identifier(*, flow_name: str, deployment_name: str | None) -> str:
    if not deployment_name:
        raise ValueError("deployment_name is required for real Prefect submission")
    if "/" in deployment_name:
        return deployment_name
    return f"{flow_name}/{deployment_name}"


def _load_run_deployment() -> Callable[..., Any]:
    try:
        from prefect.deployments import run_deployment
    except ImportError:
        try:
            from prefect.deployments.flow_runs import run_deployment
        except ImportError as error:
            raise PrefectRuntimeUnavailable(
                "Prefect is not installed. Install the optional Prefect dependencies before using real Prefect submission."
            ) from error
    return run_deployment


def _flow_run_attr(flow_run: object, name: str) -> object:
    if isinstance(flow_run, dict):
        return flow_run.get(name)
    return getattr(flow_run, name, None)


def _flow_run_id(flow_run: object) -> str | None:
    value = _flow_run_attr(flow_run, "id")
    return str(value) if value is not None else None


def _flow_run_state_name(flow_run: object) -> str:
    state_name = _flow_run_attr(flow_run, "state_name")
    if state_name:
        return str(state_name)
    state = _flow_run_attr(flow_run, "state")
    if isinstance(state, dict):
        return str(state.get("name") or state.get("type") or "Scheduled")
    if state is not None:
        nested_name = getattr(state, "name", None) or getattr(state, "type", None)
        if nested_name:
            return str(nested_name)
    state_type = _flow_run_attr(flow_run, "state_type")
    return str(state_type or "Scheduled")


def apply_prefect_state(
    manifest: dict,
    *,
    prefect_state: str,
    requested_by: str,
    flow_run_id: str | None = None,
    flow_name: str = "jira_deep_analysis",
    deployment_name: str | None = None,
    error: dict | None = None,
) -> tuple[dict, dict]:
    adapter_state = prefect_state_to_adapter_state(prefect_state)
    reference = build_prefect_run_reference(
        manifest,
        flow_run_id=flow_run_id,
        flow_name=flow_name,
        deployment_name=deployment_name,
    )
    updated = apply_adapter_state(manifest, adapter_state, error=error)
    updated.setdefault("runtime", {})
    updated["runtime"]["adapter"] = "prefect"
    updated["runtime"]["prefect"] = {
        **reference,
        "prefect_state": prefect_state,
        "adapter_state": adapter_state,
    }
    event = build_control_event(
        manifest=updated,
        action="sync_adapter_state",
        requested_by=requested_by,
        step_name="prefect_state_sync",
        reason=f"Prefect state `{prefect_state}` mapped to adapter state `{adapter_state}`.",
        result=deepcopy(updated["runtime"]["prefect"]),
    )
    return updated, event


class MockPrefectTaskAdapter:
    def __init__(
        self,
        *,
        flow_name: str = "jira_deep_analysis",
        deployment_name: str | None = None,
    ) -> None:
        self.flow_name = flow_name
        self.deployment_name = deployment_name

    def submit(self, manifest: dict, *, requested_by: str) -> tuple[dict, dict]:
        return apply_prefect_state(
            manifest,
            prefect_state="Scheduled",
            requested_by=requested_by,
            flow_name=self.flow_name,
            deployment_name=self.deployment_name,
        )

    def sync_state(
        self,
        manifest: dict,
        *,
        prefect_state: str,
        requested_by: str,
        flow_run_id: str | None = None,
        error: dict | None = None,
    ) -> tuple[dict, dict]:
        return apply_prefect_state(
            manifest,
            prefect_state=prefect_state,
            requested_by=requested_by,
            flow_run_id=flow_run_id,
            flow_name=self.flow_name,
            deployment_name=self.deployment_name,
            error=error,
        )


class RealPrefectTaskAdapter:
    def __init__(
        self,
        *,
        flow_name: str = "jira_deep_analysis",
        deployment_name: str | None = None,
        run_deployment_func: Callable[..., Any] | None = None,
    ) -> None:
        self.flow_name = flow_name
        self.deployment_name = deployment_name
        self._run_deployment_func = run_deployment_func

    def submit(
        self,
        manifest: dict,
        *,
        requested_by: str,
        parameters: dict | None = None,
        timeout_seconds: float = 0,
        flow_run_name: str | None = None,
        tags: list[str] | None = None,
        idempotency_key: str | None = None,
        work_queue_name: str | None = None,
        job_variables: dict | None = None,
    ) -> tuple[dict, dict]:
        run_deployment = self._run_deployment_func or _load_run_deployment()
        deployment_name = _deployment_identifier(
            flow_name=self.flow_name,
            deployment_name=self.deployment_name,
        )
        flow_run = run_deployment(
            name=deployment_name,
            parameters=deepcopy(parameters if parameters is not None else manifest.get("input_config", {})),
            flow_run_name=flow_run_name,
            timeout=timeout_seconds,
            tags=tags,
            idempotency_key=idempotency_key,
            work_queue_name=work_queue_name,
            job_variables=job_variables,
            as_subflow=False,
        )
        updated, event = apply_prefect_state(
            manifest,
            prefect_state=_flow_run_state_name(flow_run),
            requested_by=requested_by,
            flow_run_id=_flow_run_id(flow_run),
            flow_name=self.flow_name,
            deployment_name=self.deployment_name,
        )
        updated["runtime"]["prefect"]["deployment_identifier"] = deployment_name
        updated["runtime"]["prefect"]["parameter_keys"] = sorted((parameters or manifest.get("input_config", {})).keys())
        event["result"] = deepcopy(updated["runtime"]["prefect"])
        return updated, event

    def sync_flow_run(
        self,
        manifest: dict,
        *,
        flow_run: object,
        requested_by: str,
        error: dict | None = None,
    ) -> tuple[dict, dict]:
        return apply_prefect_state(
            manifest,
            prefect_state=_flow_run_state_name(flow_run),
            requested_by=requested_by,
            flow_run_id=_flow_run_id(flow_run),
            flow_name=self.flow_name,
            deployment_name=self.deployment_name,
            error=error,
        )

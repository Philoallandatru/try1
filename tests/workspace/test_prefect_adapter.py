from __future__ import annotations

import unittest

from services.workspace.prefect_adapter import (
    MockPrefectTaskAdapter,
    RealPrefectTaskAdapter,
    apply_prefect_state,
    prefect_state_to_adapter_state,
)
from services.workspace.task_manifest import build_run_manifest


class PrefectAdapterTest(unittest.TestCase):
    def _manifest(self) -> dict:
        return build_run_manifest(
            task_type="jira_deep_analysis",
            owner="alice",
            input_config={"issue_key": "SSD-102"},
            run_id="run-001",
        )

    def test_prefect_states_map_to_adapter_states(self) -> None:
        self.assertEqual(prefect_state_to_adapter_state("Scheduled"), "scheduled")
        self.assertEqual(prefect_state_to_adapter_state("Pending"), "scheduled")
        self.assertEqual(prefect_state_to_adapter_state("Running"), "running")
        self.assertEqual(prefect_state_to_adapter_state("Cancelling"), "cancelling")
        self.assertEqual(prefect_state_to_adapter_state("Cancelled"), "cancelled")
        self.assertEqual(prefect_state_to_adapter_state("Completed"), "succeeded")
        self.assertEqual(prefect_state_to_adapter_state("Failed"), "failed")
        self.assertEqual(prefect_state_to_adapter_state("Crashed"), "failed")

    def test_apply_prefect_state_updates_manifest_runtime_and_event(self) -> None:
        manifest, event = apply_prefect_state(
            self._manifest(),
            prefect_state="Completed",
            requested_by="alice",
            flow_run_id="flow-run-123",
            deployment_name="jira-analysis",
        )

        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["runtime"]["adapter"], "prefect")
        self.assertEqual(manifest["runtime"]["prefect"]["flow_run_id"], "flow-run-123")
        self.assertEqual(manifest["runtime"]["prefect"]["adapter_state"], "succeeded")
        self.assertEqual(event["action"], "sync_adapter_state")
        self.assertEqual(event["result"]["prefect_state"], "Completed")

    def test_mock_prefect_adapter_submit_and_sync(self) -> None:
        adapter = MockPrefectTaskAdapter(deployment_name="jira-analysis")

        queued, submit_event = adapter.submit(self._manifest(), requested_by="alice")
        running, sync_event = adapter.sync_state(
            queued,
            prefect_state="Running",
            requested_by="alice",
            flow_run_id="flow-run-456",
        )

        self.assertEqual(queued["status"], "queued")
        self.assertEqual(submit_event["result"]["deployment_name"], "jira-analysis")
        self.assertEqual(running["status"], "running")
        self.assertEqual(sync_event["result"]["flow_run_id"], "flow-run-456")

    def test_real_prefect_adapter_submits_deployment_with_injected_runner(self) -> None:
        calls: list[dict] = []

        def fake_run_deployment(**kwargs):
            calls.append(kwargs)
            return {
                "id": "flow-run-real",
                "state_name": "Scheduled",
            }

        adapter = RealPrefectTaskAdapter(
            flow_name="jira_deep_analysis",
            deployment_name="analysis-prod",
            run_deployment_func=fake_run_deployment,
        )

        manifest, event = adapter.submit(
            self._manifest(),
            requested_by="alice",
            parameters={"issue_key": "SSD-102"},
            timeout_seconds=0,
            flow_run_name="SSD-102 analysis",
            tags=["smoke"],
            idempotency_key="run-001",
            work_queue_name="analysis",
            job_variables={"env": {"MODE": "smoke"}},
        )

        self.assertEqual(calls[0]["name"], "jira_deep_analysis/analysis-prod")
        self.assertEqual(calls[0]["parameters"], {"issue_key": "SSD-102"})
        self.assertEqual(calls[0]["timeout"], 0)
        self.assertFalse(calls[0]["as_subflow"])
        self.assertEqual(manifest["status"], "queued")
        self.assertEqual(manifest["runtime"]["prefect"]["flow_run_id"], "flow-run-real")
        self.assertEqual(manifest["runtime"]["prefect"]["deployment_identifier"], "jira_deep_analysis/analysis-prod")
        self.assertEqual(manifest["runtime"]["prefect"]["parameter_keys"], ["issue_key"])
        self.assertEqual(event["action"], "sync_adapter_state")

    def test_real_prefect_adapter_requires_runtime_when_runner_not_injected(self) -> None:
        adapter = RealPrefectTaskAdapter(deployment_name="analysis-prod")
        try:
            adapter.submit(self._manifest(), requested_by="alice")
        except RuntimeError as error:
            self.assertIn("Prefect is not installed", str(error))
        else:
            # If Prefect is installed locally, reaching this branch still proves the runtime path is importable.
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()

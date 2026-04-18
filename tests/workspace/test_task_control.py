from __future__ import annotations

import json
from pathlib import Path
import unittest

from services.workspace.task_control import (
    apply_adapter_state,
    build_resume_plan,
    build_rerun_manifest,
    map_adapter_state,
    request_section_rerun,
    request_resume,
    request_stop,
    write_controlled_manifest,
)
from services.workspace.task_manifest import (
    build_artifact_record,
    build_run_manifest,
    update_checkpoint,
)
from tests.temp_utils import temporary_directory as TemporaryDirectory


class TaskControlTest(unittest.TestCase):
    def _manifest_with_retrieval(self) -> dict:
        manifest = build_run_manifest(
            task_type="jira_deep_analysis",
            owner="alice",
            input_config={"jira_issue_key": "SSD-777"},
            run_id="run-001",
            status="running",
            artifacts=[
                build_artifact_record(
                    artifact_type="shared_retrieval_bundle",
                    path="runs/run-001/shared_retrieval_bundle.json",
                    step_name="shared_retrieval",
                    step_version="v1",
                    input_hash="snapshot-hash",
                )
            ],
        )
        return update_checkpoint(
            manifest,
            "retrieval_ready",
            reached=True,
            artifact_types=["shared_retrieval_bundle"],
        )

    def _manifest_with_sections(self) -> dict:
        shared = build_artifact_record(
            artifact_type="shared_retrieval_bundle",
            path="runs/run-001/shared_retrieval_bundle.json",
            step_name="shared_retrieval",
            step_version="v1",
            input_hash="snapshot-hash",
        )
        section_artifacts = [
            build_artifact_record(
                artifact_type=f"section_output_{section_name}",
                path=f"runs/run-001/section_outputs/{section_name}.json",
                step_name=f"section_runner_{section_name}",
                step_version="v1",
                input_hash="snapshot-hash",
                depends_on=["shared_retrieval_bundle"],
            )
            for section_name in ("rca", "spec_impact", "decision_brief", "general_summary")
        ]
        composite = build_artifact_record(
            artifact_type="composite_report",
            path="runs/run-001/report/report.md",
            step_name="composite_report_builder",
            step_version="v1",
            input_hash="snapshot-hash",
            depends_on=[artifact["artifact_type"] for artifact in section_artifacts],
        )
        proposal = build_artifact_record(
            artifact_type="confluence_update_proposal",
            path="runs/run-001/knowledge/confluence_update_proposal.json",
            step_name="knowledge_compiler",
            step_version="v1",
            input_hash="snapshot-hash",
            depends_on=["shared_retrieval_bundle", "composite_report"],
        )
        return build_run_manifest(
            task_type="jira_deep_analysis",
            owner="alice",
            input_config={"jira_issue_key": "SSD-777"},
            run_id="run-001",
            status="completed",
            artifacts=[shared, *section_artifacts, composite, proposal],
        )

    def test_adapter_states_map_to_manifest_statuses(self) -> None:
        self.assertEqual(map_adapter_state("scheduled"), "queued")
        self.assertEqual(map_adapter_state("running"), "running")
        self.assertEqual(map_adapter_state("cancelling"), "stopping")
        self.assertEqual(map_adapter_state("cancelled"), "stopped")
        self.assertEqual(map_adapter_state("failed"), "failed")
        self.assertEqual(map_adapter_state("succeeded"), "completed")

    def test_stop_request_preserves_partial_artifacts(self) -> None:
        manifest = self._manifest_with_retrieval()

        stopped, event = request_stop(
            manifest,
            requested_by="alice",
            step_name="analysis",
            reason="manual review",
        )
        adapter_stopped = apply_adapter_state(stopped, "cancelled")

        self.assertEqual(stopped["status"], "stopping")
        self.assertEqual(adapter_stopped["status"], "stopped")
        self.assertEqual(stopped["artifacts"][0]["artifact_type"], "shared_retrieval_bundle")
        self.assertTrue(stopped["checkpoints"]["retrieval_ready"]["reached"])
        self.assertEqual(event["action"], "stop")
        self.assertEqual(event["step_name"], "analysis")

    def test_resume_uses_nearest_valid_checkpoint(self) -> None:
        manifest = apply_adapter_state(self._manifest_with_retrieval(), "cancelled")

        plan = build_resume_plan(manifest)
        resumed, event = request_resume(
            manifest,
            requested_by="alice",
            reason="continue after review",
        )

        self.assertEqual(plan["resume_from_checkpoint"], "retrieval_ready")
        self.assertEqual(plan["resume_from_step"], "analysis")
        self.assertEqual(resumed["status"], "queued")
        self.assertEqual(event["action"], "resume")
        self.assertEqual(event["result"]["resume_from_step"], "analysis")

    def test_rerun_creates_new_manifest_version_without_overwriting_previous_run(self) -> None:
        manifest = self._manifest_with_retrieval()

        rerun, event = build_rerun_manifest(
            manifest,
            requested_by="alice",
            reason="prompt update",
        )

        self.assertEqual(rerun["run_version"], 2)
        self.assertEqual(rerun["status"], "queued")
        self.assertNotEqual(rerun["run_id"], manifest["run_id"])
        self.assertTrue(rerun["run_id"].startswith("run-001-rerun-v2-"))
        self.assertEqual(rerun["input_config"]["rerun_of"]["run_id"], manifest["run_id"])
        self.assertEqual(rerun["artifacts"], [])
        self.assertEqual(event["action"], "rerun")

    def test_repeated_reruns_from_same_source_use_unique_run_ids(self) -> None:
        manifest = self._manifest_with_retrieval()

        first, _ = build_rerun_manifest(manifest, requested_by="alice")
        second, _ = build_rerun_manifest(manifest, requested_by="alice")

        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["run_version"], 2)
        self.assertEqual(second["run_version"], 2)

    def test_controlled_manifest_writes_event_log(self) -> None:
        manifest, event = request_stop(
            self._manifest_with_retrieval(),
            requested_by="alice",
            step_name="analysis",
        )

        with TemporaryDirectory() as temp_dir:
            payload = write_controlled_manifest(temp_dir, manifest, event)
            event_lines = Path(payload["control_event_log"]).read_text(encoding="utf-8").splitlines()
            loaded_manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))

        self.assertEqual(loaded_manifest["status"], "stopping")
        self.assertEqual(json.loads(event_lines[0])["action"], "stop")

    def test_section_rerun_invalidates_only_target_section_and_downstream_artifacts(self) -> None:
        manifest = self._manifest_with_sections()

        updated, event = request_section_rerun(
            manifest,
            section_name="rca",
            requested_by="alice",
            reason="prompt update",
        )
        artifacts_by_type = {artifact["artifact_type"]: artifact for artifact in updated["artifacts"]}

        self.assertEqual(updated["status"], "queued")
        self.assertTrue(artifacts_by_type["section_output_rca"]["stale"])
        self.assertFalse(artifacts_by_type["section_output_spec_impact"]["stale"])
        self.assertFalse(artifacts_by_type["section_output_decision_brief"]["stale"])
        self.assertFalse(artifacts_by_type["section_output_general_summary"]["stale"])
        self.assertTrue(artifacts_by_type["composite_report"]["stale"])
        self.assertTrue(artifacts_by_type["confluence_update_proposal"]["stale"])
        self.assertEqual(event["action"], "rerun_section")
        self.assertEqual(event["result"]["section_name"], "rca")


if __name__ == "__main__":
    unittest.main()

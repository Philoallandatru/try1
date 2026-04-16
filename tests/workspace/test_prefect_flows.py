from __future__ import annotations

import unittest
from unittest.mock import patch

from services.workspace.prefect_flows import build_jira_deep_analysis_flow


class PrefectFlowsTest(unittest.TestCase):
    def test_flow_factory_uses_injected_prefect_decorator_and_runs_deep_analysis(self) -> None:
        decorated: dict = {}

        def fake_flow(*, name: str):
            def decorator(fn):
                decorated["name"] = name
                decorated["function_name"] = fn.__name__
                return fn

            return decorator

        expected = {
            "issue_id": "SSD-102",
            "analysis_profile": "Root Cause Analysis",
            "run_dir": "runs/run-001",
            "run_manifest_path": "runs/run-001/run_manifest.json",
            "answer": {"mode": "extractive", "text": "ok"},
        }

        with patch("services.workspace.workspace.deep_analyze_issue", return_value=expected) as deep_analyze:
            flow_fn = build_jira_deep_analysis_flow(flow_decorator=fake_flow)
            payload = flow_fn(
                workspace_dir=".tmp/workspace",
                issue_key="SSD-102",
                policies=["team:ssd"],
                llm_backend="none",
            )

        self.assertEqual(decorated["name"], "jira_deep_analysis")
        self.assertEqual(decorated["function_name"], "jira_deep_analysis_flow")
        self.assertEqual(payload["issue_id"], "SSD-102")
        deep_analyze.assert_called_once()
        self.assertEqual(deep_analyze.call_args.kwargs["policies"], ["team:ssd"])


if __name__ == "__main__":
    unittest.main()

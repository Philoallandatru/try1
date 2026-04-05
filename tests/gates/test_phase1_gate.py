import unittest

from scripts.gates.run_phase1_gate import evaluate_phase1_gate


class Phase1GateTest(unittest.TestCase):
    def test_healthy_build_passes_phase1_gate(self) -> None:
        report = evaluate_phase1_gate()
        self.assertTrue(report["passed"])
        self.assertTrue(all(report["checks"].values()))

    def test_degraded_build_fails_phase1_gate(self) -> None:
        report = evaluate_phase1_gate(allowed_policies={"public"})
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["eval"])


if __name__ == "__main__":
    unittest.main()


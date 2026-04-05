import json
import subprocess
import sys
import unittest


class PlatformCliTest(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/platform_cli.py", *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_cli_eval_outputs_metrics(self) -> None:
        result = self._run("eval")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("aggregate", payload)
        self.assertIn("recall@10", payload["aggregate"])

    def test_cli_citation_outputs_contract_payload(self) -> None:
        result = self._run("citation", "flush command")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["citation"]["document"], "nvme-spec-v1")
        self.assertIn("inspection", payload)


if __name__ == "__main__":
    unittest.main()


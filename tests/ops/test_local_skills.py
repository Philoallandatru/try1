from pathlib import Path
import unittest


SKILL_PATHS = [
    Path("skills/offline-document-normalizer/SKILL.md"),
    Path("skills/grounded-retrieval-toolkit/SKILL.md"),
]


class LocalSkillsTest(unittest.TestCase):
    def test_local_skills_exist(self) -> None:
        for skill_path in SKILL_PATHS:
            with self.subTest(skill=skill_path.as_posix()):
                self.assertTrue(skill_path.exists())

    def test_local_skills_reference_stable_entrypoints(self) -> None:
        expectations = {
            "skills/offline-document-normalizer/SKILL.md": "scripts/ingest/normalize_cli.py",
            "skills/grounded-retrieval-toolkit/SKILL.md": "scripts/retrieval/toolkit_cli.py",
        }
        for skill_path, expected_entrypoint in expectations.items():
            with self.subTest(skill=skill_path):
                text = Path(skill_path).read_text(encoding="utf-8")
                self.assertIn(expected_entrypoint, text)
                self.assertIn("## Validation", text)
                self.assertIn("## Boundaries", text)


if __name__ == "__main__":
    unittest.main()

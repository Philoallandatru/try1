from pathlib import Path
import unittest

from services.eval.harness import evaluate_dataset, thresholds_pass
from services.eval.metrics import citation_fidelity, ndcg_at_k, recall_at_k


class EvalMetricsTest(unittest.TestCase):
    def test_recall_at_k(self) -> None:
        score = recall_at_k({"doc-a"}, ["doc-b", "doc-a"], 10)
        self.assertEqual(score, 1.0)

    def test_ndcg_at_k(self) -> None:
        score = ndcg_at_k({"doc-a"}, ["doc-a", "doc-b"], 10)
        self.assertAlmostEqual(score, 1.0)

    def test_citation_fidelity(self) -> None:
        expected = {"document": "doc-a", "version": "1", "page": 2, "clause": "1.1"}
        actual = {"document": "doc-a", "version": "1", "page": 2, "clause": "1.1"}
        self.assertEqual(citation_fidelity(expected, actual), 1.0)

    def test_eval_report_passes_for_current_fixture_corpus(self) -> None:
        report = evaluate_dataset(
            corpus_path=Path("fixtures/retrieval/pageindex_corpus.json"),
            dataset_path=Path("eval/gold_queries.yaml"),
            allowed_policies={"team:ssd", "public"},
        )
        self.assertTrue(thresholds_pass(report))

    def test_degraded_config_fails_thresholds(self) -> None:
        report = evaluate_dataset(
            corpus_path=Path("fixtures/retrieval/pageindex_corpus.json"),
            dataset_path=Path("eval/gold_queries.yaml"),
            allowed_policies={"public"},
        )
        self.assertFalse(thresholds_pass(report))


if __name__ == "__main__":
    unittest.main()


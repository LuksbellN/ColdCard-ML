import unittest
import pandas as pd
from src.evaluation import block_folds, metrics


class EvaluationTests(unittest.TestCase):
    def test_blocks_remain_whole_and_each_fold_has_both_classes(self):
        frame = pd.DataFrame(
            {
                "height": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6],
                "label": [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
            }
        )
        assigned = block_folds(frame, 3, 42)
        frame["fold"] = assigned
        self.assertEqual(frame.groupby("height")["fold"].nunique().max(), 1)
        for k in range(3):
            self.assertEqual(set(frame.loc[assigned == k, "label"]), {0, 1})
        self.assertEqual(list(assigned), list(block_folds(frame, 3, 42)))

    def test_insufficient_positive_blocks_is_explicit(self):
        frame = pd.DataFrame({"height": [1, 1, 2, 2], "label": [1, 0, 0, 0]})
        with self.assertRaises(ValueError):
            block_folds(frame, 3, 42)

    def test_false_alarms_and_misses_are_counted_in_correct_order(self):
        result = metrics([1, 1, 0, 0], [0.8, 0.4, 0.6, 0.1])
        self.assertEqual([result[k] for k in ("tn", "fp", "fn", "tp")], [1, 1, 1, 1])
        for k in ("precision", "recall", "f1", "accuracy"):
            self.assertEqual(result[k], 0.5)


if __name__ == "__main__":
    unittest.main()

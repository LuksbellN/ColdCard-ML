"""Testes de integridade com exemplos pequenos, independentes da base real."""

import copy
import unittest
from src import coldcard as c


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.block = {"height": 100, "time": 1000}
        self.tx = {
            "hash": "abc",
            "ver": 2,
            "size": 200,
            "weight": 600,
            "lock_time": 0,
            "fee": 100,
            "inputs": [
                {
                    "sequence": 4294967293,
                    "witness": "01",
                    "prev_out": {
                        "n": 1,
                        "tx_index": 10,
                        "value": 1000,
                        "addr": "source",
                        "script": "0014" + "00" * 20,
                    },
                }
            ],
            "out": [
                {"value": 600, "addr": "other", "script": ""},
                {"value": 300, "addr": c.COLLECTOR, "script": ""},
            ],
        }

    def test_any_output_to_collector_and_exact_fee(self):
        row = c.transaction_row(self.tx, self.block)
        self.assertEqual(row["label"], 1)
        self.assertEqual(row["collected_sat"], 300)
        self.assertEqual(row["fee_sat"], 100)
        self.assertEqual(row["vsize"], 150)
        self.assertAlmostEqual(row["fee_rate"], 2 / 3)
        self.assertEqual(row["source_addresses"], "source")

    def test_non_collector_and_no_future_state_features(self):
        self.tx["out"][1]["addr"] = "another"
        row = c.transaction_row(self.tx, self.block)
        self.assertEqual(row["label"], 0)
        changed = copy.deepcopy(self.tx)
        changed["out"][0].update(spent=True, spending_outpoints=[{"tx_index": 999}])
        self.assertEqual(row, c.transaction_row(changed, self.block))

    def test_coinbase_sentinel_is_excluded(self):
        self.tx["inputs"][0]["prev_out"]["n"] = 4294967295
        self.assertIsNone(c.transaction_row(self.tx, self.block))

    def test_missing_input_value_is_not_zero(self):
        del self.tx["inputs"][0]["prev_out"]["value"]
        with self.assertRaises(ValueError):
            c.transaction_row(self.tx, self.block)

    def test_inconsistent_fee_is_rejected(self):
        self.tx["fee"] = 99
        with self.assertRaises(ValueError):
            c.transaction_row(self.tx, self.block)

    def test_identity_and_label_are_not_model_features(self):
        self.assertTrue(
            set(c.FEATURES).isdisjoint(
                {
                    "label",
                    "collected_sat",
                    "txid",
                    "height",
                    "block_time",
                    "source_addresses",
                    "input_utxos",
                    "collector_input",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()

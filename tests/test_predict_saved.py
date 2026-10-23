import unittest
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from src.predict_saved import predict_frame


class InferenceTests(unittest.TestCase):
    def test_raw_values_are_transformed_before_prediction(self):
        # A entrada bruta 7 deve chegar ao modelo como ln(8), não como 7.
        model = LogisticRegression().fit(
            pd.DataFrame({"fee_sat": [0.0, 1.0, 2.0, 3.0]}), [0, 0, 1, 1]
        )
        bundle = {"model": model, "features": ["fee_sat"], "log_features": ["fee_sat"]}
        result = predict_frame(pd.DataFrame({"fee_sat": [7.0], "label": [1]}), bundle)
        expected = model.predict_proba(pd.DataFrame({"fee_sat": [2.0794415416798357]}))[
            :, 1
        ]
        np.testing.assert_allclose(result, expected, rtol=1e-12)


if __name__ == "__main__":
    unittest.main()

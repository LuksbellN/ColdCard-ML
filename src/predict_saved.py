"""Predição sobre os atributos brutos extraídos, incluindo o log obrigatório."""

import argparse
import joblib
import numpy as np
import pandas as pd


def predict_frame(frame, bundle):
    """Usa atributos brutos e reaplica o log antes de chamar o modelo salvo."""
    X = frame[bundle["features"]].astype(float).copy()
    logs = bundle["log_features"]
    X[logs] = np.log1p(X[logs])
    if not np.isfinite(X.to_numpy()).all():
        raise ValueError("Atributos inválidos")
    return bundle["model"].predict_proba(X)[:, 1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("model_joblib")
    parser.add_argument("output_csv")
    args = parser.parse_args()
    frame = pd.read_csv(args.input_csv)
    bundle = joblib.load(args.model_joblib)
    probabilities = predict_frame(frame, bundle)
    result = pd.DataFrame(
        {
            "score": probabilities,
            "predicted": (probabilities >= bundle["threshold"]).astype(int),
        }
    )
    if "txid" in frame:
        result.insert(0, "txid", frame.txid)
    result.to_csv(args.output_csv, index=False)

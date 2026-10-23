"""Partições por bloco e métricas da classe positiva."""

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def block_folds(frame, n_splits, seed):
    """Distribui blocos inteiros, equilibrando positivos e quantidade de transações.

    Há poucos blocos com positivos. Separá-los primeiro evita uma divisão de
    validação sem exemplos dessa classe, sem misturar transações do mesmo bloco.
    """
    groups = frame.groupby("height")["label"].agg(["sum", "size"])
    if (groups["sum"] > 0).sum() < n_splits:
        raise ValueError("Blocos positivos insuficientes para a divisão")
    groups = groups.sample(frac=1, random_state=seed)
    assignment, positives, totals = {}, [0] * n_splits, [0] * n_splits
    for height, row in (
        groups[groups["sum"] > 0]
        .sort_values("sum", ascending=False, kind="stable")
        .iterrows()
    ):
        k = min(range(n_splits), key=lambda j: (positives[j], totals[j], j))
        assignment[height] = k
        positives[k] += int(row["sum"])
        totals[k] += int(row["size"])
    for height, row in (
        groups[groups["sum"] == 0]
        .sort_values("size", ascending=False, kind="stable")
        .iterrows()
    ):
        k = min(range(n_splits), key=lambda j: (totals[j], j))
        assignment[height] = k
        totals[k] += int(row["size"])
    result = frame["height"].map(assignment).to_numpy()
    for k in range(n_splits):
        if set(frame.loc[result == k, "label"]) != {0, 1}:
            raise ValueError("Cada partição precisa conter as duas classes")
    return result


def metrics(y, probabilities):
    """Calcula as métricas no limiar fixo de 0,5, sempre para a classe positiva."""
    y, p = np.asarray(y), np.asarray(probabilities)
    if set(y) != {0, 1}:
        raise ValueError("Avaliação requer ambas as classes")
    pred = p >= 0.5
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return dict(
        n=len(y),
        positives=int(y.sum()),
        tn=int(tn),
        fp=int(fp),
        fn=int(fn),
        tp=int(tp),
        accuracy=float(accuracy_score(y, pred)),
        precision=float(precision_score(y, pred, zero_division=0)),
        recall=float(recall_score(y, pred)),
        f1=float(f1_score(y, pred)),
        ap=float(average_precision_score(y, p)),
        roc_auc=float(roc_auc_score(y, p)),
    )

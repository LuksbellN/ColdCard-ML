"""Experimento local: validação agrupada e teste reservado antes dos ajustes."""

import json
import platform
import time
from pathlib import Path
import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve, roc_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .coldcard import FEATURES, LOG_FEATURES
from .evaluation import block_folds, metrics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
SEED = 42


def main():
    started = time.time()
    (OUT / "plots").mkdir(parents=True, exist_ok=True)
    # 1. Carregar os atributos e aplicar apenas a transformação determinística.
    data = pd.read_csv(ROOT / "data/transactions.csv.gz", keep_default_na=False)
    data = data.sort_values(["height", "txid"]).reset_index(drop=True)
    X = data[FEATURES].astype(float).copy()
    X[LOG_FEATURES] = np.log1p(X[LOG_FEATURES])
    if not np.isfinite(X.to_numpy()).all():
        raise ValueError("Atributos inválidos")
    y = data.label.to_numpy()
    # 2. Reservar o teste por blocos e dividir o desenvolvimento para validação.
    outer = block_folds(data, 4, SEED)
    dev, test = np.flatnonzero(outer != 0), np.flatnonzero(outer == 0)
    inner = block_folds(data.iloc[dev].reset_index(drop=True), 3, SEED + 1)
    assert not set(data.height.iloc[dev]) & set(data.height.iloc[test])
    pd.DataFrame(
        {
            "txid": data.txid,
            "height": data.height,
            "label": y,
            "partition": np.where(outer == 0, "test", "development"),
            "outer_fold": outer,
        }
    ).to_csv(ROOT / "data/partitions.csv.gz", index=False)
    # 3. Comparar uma referência simples e duas famílias de classificadores.
    models = {"Dummy": DummyClassifier(strategy="prior")}
    for C in (0.1, 1.0):
        models[f"Logistica C={C}"] = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=C, class_weight="balanced", max_iter=1000, random_state=SEED
            ),
        )
    for depth in (8, 16):
        models[f"Random Forest depth={depth}"] = RandomForestClassifier(
            n_estimators=100,
            max_depth=depth,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=SEED,
            n_jobs=4,
        )
    results = dict(
        seed=SEED,
        n_features=len(FEATURES),
        features=FEATURES,
        log_features=LOG_FEATURES,
        threshold=0.5,
        candidates={},
        versions=dict(
            python=platform.python_version(),
            numpy=np.__version__,
            pandas=pd.__version__,
            scipy=scipy.__version__,
            sklearn=sklearn.__version__,
            matplotlib=matplotlib.__version__,
        ),
        split={},
        folds=[],
    )
    for name, ix in [("development", dev), ("test", test)]:
        results["split"][name] = dict(
            n=len(ix),
            positives=int(y[ix].sum()),
            negatives=int(len(ix) - y[ix].sum()),
            blocks=int(data.height.iloc[ix].nunique()),
            heights=sorted(map(int, data.height.iloc[ix].unique())),
        )
    for k in range(3):
        results["folds"].append(
            dict(
                fold=k,
                train_n=int((inner != k).sum()),
                train_pos=int(y[dev[inner != k]].sum()),
                val_n=int((inner == k).sum()),
                val_pos=int(y[dev[inner == k]].sum()),
            )
        )
    print("PARTICOES", json.dumps(results["split"]), flush=True)
    # 4. Escolher a configuração pela AP de validação, antes de avaliar o teste.
    for name, model in models.items():
        fold_scores = []
        for k in range(3):
            a, b = dev[inner != k], dev[inner == k]
            assert not set(data.height.iloc[a]) & set(data.height.iloc[b])
            fitted = clone(model).fit(X.iloc[a], y[a])
            fold_scores.append(metrics(y[b], fitted.predict_proba(X.iloc[b])[:, 1]))
            print(name, "fold", k, "AP", fold_scores[-1]["ap"], flush=True)
        results["candidates"][name] = dict(
            cv=fold_scores,
            cv_ap_mean=float(np.mean([r["ap"] for r in fold_scores])),
            cv_ap_std=float(np.std([r["ap"] for r in fold_scores], ddof=1)),
        )
    winner = max(
        (n for n in models if n != "Dummy"),
        key=lambda n: results["candidates"][n]["cv_ap_mean"],
    )
    results["selected"] = winner
    print("SELECIONADO POR VALIDACAO:", winner, flush=True)
    predictions = data.iloc[test][
        [
            "txid",
            "height",
            "label",
            "n_inputs",
            "n_outputs",
            "fee_rate",
            "collected_sat",
        ]
    ].copy()
    # 5. Treinar em todo o desenvolvimento e medir o desempenho no teste reservado.
    fitted_models, probabilities = {}, {}
    for name, model in models.items():
        fitted = clone(model).fit(X.iloc[dev], y[dev])
        p = fitted.predict_proba(X.iloc[test])[:, 1]
        fitted_models[name], probabilities[name] = fitted, p
        results["candidates"][name]["test"] = metrics(y[test], p)
        predictions[name] = p
        print(
            "TESTE", name, json.dumps(results["candidates"][name]["test"]), flush=True
        )
    p = probabilities[winner]
    predictions["predicted"] = (p >= 0.5).astype(int)
    predictions["error"] = np.where(
        predictions.label == predictions.predicted,
        "",
        np.where(predictions.predicted == 1, "FP", "FN"),
    )
    predictions.to_csv(OUT / "test_predictions.csv.gz", index=False)
    predictions[predictions.error != ""].to_csv(OUT / "errors.csv", index=False)
    data[data.label == 1][
        [
            "txid",
            "height",
            "collected_sat",
            "n_inputs",
            "source_addresses",
            "input_utxos",
        ]
    ].to_csv(OUT / "positive_transactions.csv", index=False)
    # 6. Análises adicionais: sobreposição de origens e recorte temporal.
    train_sources = set("|".join(data.source_addresses.iloc[dev]).split("|")) - {""}
    unseen = np.array(
        [
            bool(s) and not bool(set(s.split("|")) & train_sources)
            for s in data.source_addresses.iloc[test]
        ]
    )
    results["source_audit"] = dict(
        test_without_shared_sources=int(unseen.sum()),
        test_with_shared_sources=int(
            sum(bool(s) for s in data.source_addresses.iloc[test])
        )
        - int(unseen.sum()),
        test_missing_sources=int(
            sum(not bool(s) for s in data.source_addresses.iloc[test])
        ),
        unseen_positive_count=int(y[test][unseen].sum()),
    )
    if set(y[test][unseen]) == {0, 1}:
        results["source_audit"]["selected_metrics"] = metrics(
            y[test][unseen], p[unseen]
        )
    # Diagnóstico adicional predefinido: últimos 25% dos blocos em altura.
    heights = sorted(data.height.unique())
    cutoff = heights[int(0.75 * len(heights))]
    past, future = np.flatnonzero(data.height < cutoff), np.flatnonzero(
        data.height >= cutoff
    )
    results["temporal"] = dict(
        cutoff_height=int(cutoff),
        train_n=len(past),
        train_pos=int(y[past].sum()),
        test_n=len(future),
        test_pos=int(y[future].sum()),
        caveat="Diagnóstico exploratório: configuração escolhida na validação agrupada; "
        "não é um segundo teste intocado para seleção de modelo.",
    )
    if set(y[past]) == {0, 1} and set(y[future]) == {0, 1}:
        temporal = clone(models[winner]).fit(X.iloc[past], y[past])
        results["temporal"]["metrics"] = metrics(
            y[future], temporal.predict_proba(X.iloc[future])[:, 1]
        )
    selected = fitted_models[winner]
    if hasattr(selected, "feature_importances_"):
        importance = selected.feature_importances_
    else:
        importance = np.abs(selected[-1].coef_[0])
    results["importance"] = sorted(
        zip(FEATURES, map(float, importance)), key=lambda z: z[1], reverse=True
    )
    joblib.dump(
        dict(
            model=selected, features=FEATURES, log_features=LOG_FEATURES, threshold=0.5
        ),
        OUT / "selected_model.joblib",
        compress=3,
    )
    # 7. Salvar as figuras usadas na análise e no relatório.
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 160,
            "savefig.bbox": "tight",
        }
    )
    colors = ["#9ca3af", "#f59e0b", "#b45309", "#14b8a6", "#0f766e"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for (name, prob), color in zip(probabilities.items(), colors):
        pr, re, _ = precision_recall_curve(y[test], prob)
        axes[0].plot(re, pr, label=name, color=color, lw=1.4)
        fpr, tpr, _ = roc_curve(y[test], prob)
        axes[1].plot(fpr, tpr, label=name, color=color, lw=1.4)
    axes[0].axhline(y[test].mean(), ls="--", color="#6b7280", lw=0.8)
    axes[0].set(xlabel="Recall", ylabel="Precisão", title="Precisão-recall (teste)")
    axes[1].plot([0, 1], [0, 1], ls="--", color="#6b7280", lw=0.8)
    axes[1].set(xlabel="Taxa de falsos positivos", ylabel="Recall", title="ROC (teste)")
    axes[1].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "plots/curves.png")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    r = results["candidates"][winner]["test"]
    matrix = np.array([[r["tn"], r["fp"]], [r["fn"], r["tp"]]])
    axes[0].imshow(np.log1p(matrix), cmap="Greens")
    for (i, j), v in np.ndenumerate(matrix):
        axes[0].text(
            j,
            i,
            f"{v:,}",
            ha="center",
            va="center",
            fontsize=15,
            color="white" if np.log1p(v) > 6 else "#111827",
        )
    axes[0].set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["Referência", "ColdCard"],
        yticklabels=["Referência", "ColdCard"],
        xlabel="Predito",
        ylabel="Rótulo",
        title="Matriz de confusão - selecionado",
    )
    top = results["importance"][:10][::-1]
    axes[1].barh([z[0] for z in top], [z[1] for z in top], color="#0f766e")
    importance_label = (
        "Importância por impureza"
        if hasattr(selected, "feature_importances_")
        else "Magnitude dos coeficientes padronizados"
    )
    axes[1].set(title="Atributos do modelo selecionado", xlabel=importance_label)
    fig.tight_layout()
    fig.savefig(OUT / "plots/confusion_importance.png")
    plt.close(fig)
    census = json.loads((OUT / "census.json").read_text())
    fig, ax = plt.subplots(figsize=(10, 2.8))
    blocks = census["blocks"]
    indices = np.arange(len(blocks))
    ax.bar(indices, [b["positives"] for b in blocks], color="#0f766e")
    ax.set(
        xlabel="Blocos fornecidos em ordem de altura (intervalos não contínuos)",
        ylabel="Transações positivas",
        title="Concentração dos exemplos positivos",
    )
    ticks = np.unique(np.linspace(0, len(blocks) - 1, min(5, len(blocks)), dtype=int))
    ax.set_xticks(ticks, [str(blocks[i]["height"]) for i in ticks])
    fig.tight_layout()
    fig.savefig(OUT / "plots/positive_blocks.png")
    plt.close(fig)
    results["elapsed_seconds"] = round(time.time() - started, 2)
    (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(
        "FINAL",
        json.dumps(
            {
                k: v
                for k, v in results.items()
                if k not in ("candidates", "features", "importance")
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

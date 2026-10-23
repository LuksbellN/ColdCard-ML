"""Atributos locais a cada transação; identificadores são só para auditoria."""

import math
import statistics

COLLECTOR = "bc1qnk4zh9qcnap2mycp56qjrgza3cc8ylrh8fecp0"
# O endereço cria a resposta esperada, mas não faz parte dos atributos abaixo.
FEATURES = [
    "n_inputs",
    "n_outputs",
    "size",
    "vsize",
    "version",
    "lock_nonzero",
    "witness_fraction",
    "rbf_fraction",
    "fee_sat",
    "fee_rate",
    "input_sum",
    "output_sum",
    "input_mean",
    "input_std",
    "input_min",
    "input_max",
    "output_mean",
    "output_std",
    "output_min",
    "output_max",
    "input_max_share",
    "output_max_share",
    "zero_output_fraction",
] + [
    f"{side}_{kind}"
    for side in ("in", "out")
    for kind in ("p2pkh", "p2sh", "p2wpkh", "p2wsh", "p2tr", "other")
]
LOG_FEATURES = [
    "n_inputs",
    "n_outputs",
    "size",
    "vsize",
    "fee_sat",
    "fee_rate",
    "input_sum",
    "output_sum",
    "input_mean",
    "input_std",
    "input_min",
    "input_max",
    "output_mean",
    "output_std",
    "output_min",
    "output_max",
]


def script_kind(script):
    """Identifica os formatos de script usados nos atributos de entrada e saída."""
    if len(script) == 50 and script.startswith("76a914") and script.endswith("88ac"):
        return "p2pkh"
    if len(script) == 46 and script.startswith("a914") and script.endswith("87"):
        return "p2sh"
    if len(script) == 44 and script.startswith("0014"):
        return "p2wpkh"
    if len(script) == 68 and script.startswith("0020"):
        return "p2wsh"
    if len(script) == 68 and script.startswith("5120"):
        return "p2tr"
    return "other"


def transaction_row(tx, block):
    """Cria uma linha da base; valores monetários permanecem em satoshis."""
    inputs = tx["inputs"]
    # Coinbase cria moedas e não representa o tipo de envio procurado na atividade.
    if len(inputs) == 1 and inputs[0].get("prev_out", {}).get("n") == 4294967295:
        return None
    outputs = tx["out"]
    if not inputs or not outputs:
        raise ValueError("Transação sem entradas ou saídas")
    prev = [i.get("prev_out", {}) for i in inputs]
    if any("value" not in p or "n" not in p or "tx_index" not in p for p in prev):
        raise ValueError("Referência de entrada incompleta")
    a, b = [p["value"] for p in prev], [o["value"] for o in outputs]
    if any(not isinstance(v, int) or v < 0 for v in a + b):
        raise ValueError("Valor inválido em satoshis")
    fee = sum(a) - sum(b)
    if fee < 0 or tx.get("fee", fee) != fee:
        raise ValueError("Taxa inconsistente com entradas e saídas")
    collected = sum(o["value"] for o in outputs if o.get("addr") == COLLECTOR)
    row = dict(
        txid=tx["hash"],
        height=block["height"],
        block_time=block["time"],
        label=int(any(o.get("addr") == COLLECTOR for o in outputs)),
        collected_sat=collected,
        n_inputs=len(a),
        n_outputs=len(b),
        size=tx["size"],
        vsize=math.ceil(tx["weight"] / 4),
        version=tx["ver"],
        lock_nonzero=int(tx.get("lock_time", 0) != 0),
        witness_fraction=sum(bool(i.get("witness")) for i in inputs) / len(a),
        rbf_fraction=sum(i["sequence"] < 4294967294 for i in inputs) / len(a),
        fee_sat=fee,
        collector_input=int(any(p.get("addr") == COLLECTOR for p in prev)),
        source_addresses="|".join(sorted({p["addr"] for p in prev if p.get("addr")})),
        input_utxos="|".join(f"{p['tx_index']}:{p['n']}" for p in prev),
    )
    if row["vsize"] <= 0:
        raise ValueError("Tamanho virtual inválido")
    row["fee_rate"] = fee / row["vsize"]
    for name, values in [("input", a), ("output", b)]:
        row.update(
            {
                name + "_sum": sum(values),
                name + "_mean": statistics.mean(values),
                name + "_std": statistics.pstdev(values),
                name + "_min": min(values),
                name + "_max": max(values),
                name + "_max_share": max(values) / sum(values) if sum(values) else 0,
            }
        )
    row["zero_output_fraction"] = b.count(0) / len(b)
    for side, items in [("in", prev), ("out", outputs)]:
        kinds = [script_kind(p.get("script", "")) for p in items]
        for kind in ("p2pkh", "p2sh", "p2wpkh", "p2wsh", "p2tr", "other"):
            row[side + "_" + kind] = kinds.count(kind) / len(kinds)
    return row

"""Lê o arquivo original sem extrair caminhos do TAR para o disco."""

import csv
import gzip
import hashlib
import json
import tarfile
from pathlib import Path
from datetime import datetime, timezone
from .coldcard import COLLECTOR, transaction_row

ROOT = Path(__file__).resolve().parents[1]


def main():
    archive = ROOT / "data/blocos.tgz"
    dest = ROOT / "results"
    dest.mkdir(exist_ok=True)
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    census = dict(
        archive_sha256=digest,
        archive_bytes=archive.stat().st_size,
        collector=COLLECTOR,
        blocks=[],
        duplicates=0,
        coinbase=0,
        rows=0,
        positives=0,
        collected_sat=0,
        positive_input_sat=0,
        positive_fee_sat=0,
        positive_inputs=0,
        collector_input_txs=0,
    )
    seen, utxos, addresses = set(), set(), set()
    with tarfile.open(archive, "r|gz") as tar, gzip.open(
        ROOT / "data/transactions.csv.gz", "wt", encoding="utf-8", newline=""
    ) as stream:
        writer = None
        for member in tar:
            if not member.isfile():
                continue
            block = json.load(tar.extractfile(member))
            if (
                Path(member.name).name != block["hash"]
                or len(block["tx"]) != block["n_tx"]
            ):
                raise ValueError("Identidade ou contagem do bloco inconsistente")
            info = dict(
                height=block["height"],
                time=block["time"],
                n_tx=block["n_tx"],
                positives=0,
                collected_sat=0,
            )
            for tx in block["tx"]:
                if tx["hash"] in seen:
                    census["duplicates"] += 1
                    continue
                seen.add(tx["hash"])
                row = transaction_row(tx, block)
                if row is None:
                    census["coinbase"] += 1
                    continue
                if writer is None:
                    writer = csv.DictWriter(stream, fieldnames=list(row))
                    writer.writeheader()
                writer.writerow(row)
                census["rows"] += 1
                census["collector_input_txs"] += row["collector_input"]
                if row["label"]:
                    census["positives"] += 1
                    census["collected_sat"] += row["collected_sat"]
                    census["positive_input_sat"] += row["input_sum"]
                    census["positive_fee_sat"] += row["fee_sat"]
                    census["positive_inputs"] += row["n_inputs"]
                    utxos.update(row["input_utxos"].split("|"))
                    addresses.update(filter(None, row["source_addresses"].split("|")))
                    info["positives"] += 1
                    info["collected_sat"] += row["collected_sat"]
            census["blocks"].append(info)
            print(
                f"Bloco {info['height']}: {info['positives']} positivos; "
                f"acumulado {census['rows']:,} transações",
                flush=True,
            )
    census.update(
        unique_positive_utxos=len(utxos),
        unique_positive_sources=len(addresses),
        negatives=census["rows"] - census["positives"],
        raw_transactions=len(seen),
        positive_blocks=sum(b["positives"] > 0 for b in census["blocks"]),
    )
    census["blocks"].sort(key=lambda b: b["height"])
    census["start_utc"] = datetime.fromtimestamp(
        min(b["time"] for b in census["blocks"]), timezone.utc
    ).isoformat()
    census["end_utc"] = datetime.fromtimestamp(
        max(b["time"] for b in census["blocks"]), timezone.utc
    ).isoformat()
    (dest / "census.json").write_text(json.dumps(census, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in census.items() if k != "blocks"}, indent=2))


if __name__ == "__main__":
    main()

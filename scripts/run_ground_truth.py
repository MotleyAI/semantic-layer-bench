"""Execute every ground-truth SQL in questions/questions.yaml and write ground_truth/.

Checks: every question returns >= 1 row, the result columns match `columns` exactly,
and ids/patterns are consistent. Writes one CSV per question plus MANIFEST.json.
"""
import csv
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

root = Path(__file__).resolve().parent.parent
qfile = root / "questions" / "questions.yaml"
outdir = root / "ground_truth"
outdir.mkdir(exist_ok=True)

spec = yaml.safe_load(qfile.read_text())
patterns = spec["patterns"]
con = duckdb.connect(str(root / "data" / "tpch.duckdb"), read_only=True)


def norm(v):
    if isinstance(v, Decimal):
        return float(v)
    return v


errors, manifest = [], {}
ids = [q["id"] for q in spec["questions"]]
if len(ids) != len(set(ids)):
    errors.append("duplicate question ids")

for q in spec["questions"]:
    qid = q["id"]
    if q["pattern"] not in patterns:
        errors.append(f"{qid}: unknown pattern {q['pattern']}")
    try:
        cur = con.execute(q["sql"])
        cols = [d[0] for d in cur.description]
        rows = [[norm(v) for v in r] for r in cur.fetchall()]
    except Exception as e:  # noqa: BLE001
        errors.append(f"{qid}: SQL error {e}")
        continue
    if cols != q["columns"]:
        errors.append(f"{qid}: columns {cols} != spec {q['columns']}")
    if not rows:
        errors.append(f"{qid}: no rows")
    if any(v is None for r in rows for v in r):
        errors.append(f"{qid}: contains NULLs")
    path = outdir / f"{qid}.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    manifest[qid] = {
        "pattern": q["pattern"],
        "rows": len(rows),
        "order_matters": q["order_matters"],
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    print(f"{qid} {q['pattern']} rows={len(rows)}")

(outdir / "MANIFEST.json").write_text(json.dumps({
    "questions_sha256": hashlib.sha256(qfile.read_bytes()).hexdigest(),
    "n_questions": len(manifest),
    "answers": manifest,
}, indent=2))

if errors:
    print("\nERRORS:\n" + "\n".join(errors))
    sys.exit(1)
print(f"\nOK: {len(manifest)} questions, {len(patterns)} patterns")

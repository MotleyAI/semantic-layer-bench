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
# Optional question ids after the flags regenerate only those answers and keep the rest of the
# manifest. --blind: questions_blind/questions.yaml -> ground_truth_blind/ (questions carry domain and
# difficulty instead of a pattern).
BLIND = "--blind" in sys.argv
suffix = "_blind" if BLIND else ""
qfile = root / f"questions{suffix}" / "questions.yaml"
outdir = root / f"ground_truth{suffix}"
outdir.mkdir(exist_ok=True)

spec = yaml.safe_load(qfile.read_text())
patterns = spec.get("patterns", {})
con = duckdb.connect(str(root / "data" / "tpch.duckdb"), read_only=True)
DOMAINS = {"operations", "finance", "marketing"}
DIFFICULTIES = {"simple", "medium", "hard"}


def norm(v):
    if isinstance(v, Decimal):
        return float(v)
    return v


errors, manifest = [], {}
ids = [q["id"] for q in spec["questions"]]
if len(ids) != len(set(ids)):
    errors.append("duplicate question ids")

ONLY = {a for a in sys.argv[1:] if not a.startswith("--")}  # optional ids: run only these
if ONLY and (outdir / "MANIFEST.json").exists():
    manifest = json.loads((outdir / "MANIFEST.json").read_text())["answers"]

for q in spec["questions"]:
    qid = q["id"]
    if ONLY and qid not in ONLY:
        continue
    if BLIND:
        if q.get("domain") not in DOMAINS or q.get("difficulty") not in DIFFICULTIES:
            errors.append(f"{qid}: bad domain/difficulty")
        tag = f"{q.get('domain')}/{q.get('difficulty')}"
    else:
        if q["pattern"] not in patterns:
            errors.append(f"{qid}: unknown pattern {q['pattern']}")
        tag = q["pattern"]
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
        **({"domain": q["domain"], "difficulty": q["difficulty"]} if BLIND else {"pattern": q["pattern"]}),
        "rows": len(rows),
        "order_matters": q["order_matters"],
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    print(f"{qid} {tag} rows={len(rows)}")

(outdir / "MANIFEST.json").write_text(json.dumps({
    "questions_sha256": hashlib.sha256(qfile.read_bytes()).hexdigest(),
    "n_questions": len(manifest),
    "answers": manifest,
}, indent=2))

if errors:
    print("\nERRORS:\n" + "\n".join(errors))
    sys.exit(1)
print(f"\nOK: {len(manifest)} questions" + ("" if BLIND else f", {len(patterns)} patterns"))

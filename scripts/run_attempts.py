"""Run each layer's recorded attempts and score them against ground truth.

Usage:
  uv run python scripts/run_attempts.py <layer> [Q01 Q02 ...]   # run (a subset of) one layer
  uv run python scripts/run_attempts.py --aggregate              # merge results/<layer>.json -> results.json

Add --blind (anywhere) for the blind round: questions_blind/, ground_truth_blind/,
layers/<layer>/attempts_blind.yaml -> results_blind/<layer>.json -> results_blind.json.

Attempts live in layers/<layer>/attempts.yaml, one entry per question:

  - id: Q09
    status: attempted            # or: unsupported
    interface: query             # slayer: query | cube: rest, sql | metricflow: mf | anfra: aql
    query: {...}                 # the exact native query (dict, or a string for cube sql)
    columns:                     # expected column -> result column (projection + rename only)
      customer_region_name: orders.customer.customer_nation.customer_region.customer_region_name
      revenue: lineitem.revenue
    notes: optional free text
  - id: Q38
    status: unsupported
    reason: why the query API cannot express it
    category: expressivity       # or: topology
    fixable_in_model: yes        # yes / no: would a native model-level metric type fix it?
    tried: optional list of the queries tried and the errors they gave

The harness only reshapes a result (project, rename via `columns`). It never sorts rows: if
the question has order_matters, the query itself must order them. Final status per question:
answered (matches ground truth), wrong (ran but did not match, or errored), unsupported.
"""
import csv
import datetime as dt
import decimal
import json
import math
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REL_TOL = 1e-6
LAYERS = ["slayer", "metricflow", "cube", "snowflake", "anfra"]

BLIND = "--blind" in sys.argv
SUFFIX = "_blind" if BLIND else ""
QFILE = ROOT / f"questions{SUFFIX}" / "questions.yaml"
TRUTH_DIR = ROOT / f"ground_truth{SUFFIX}"
RESULTS_DIR = ROOT / f"results{SUFFIX}"
RESULTS_JSON = ROOT / f"results{SUFFIX}.json"
ATTEMPTS_FILE = f"attempts{SUFFIX}.yaml"
GROUP_KEYS = ("domain", "difficulty") if BLIND else ("pattern",)


# ---------------------------------------------------------------- executors
# Each returns a list of dicts (result column -> value).

def run_slayer(a):
    env = dict(os.environ, SLAYER_STORAGE=str(ROOT / "layers/slayer/storage"))
    p = subprocess.run(["slayer", "query", "--format", "json", json.dumps(a["query"])],
                       capture_output=True, text=True, env=env, timeout=600)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[-2000:])
    out = p.stdout
    return json.loads(out[out.index("["):])


def run_metricflow(a):
    q = a["query"]
    proj = ROOT / "layers/metricflow/project"
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.csv"
        cmd = ["uv", "run", "mf", "query", "--quiet", "--csv", str(out)]
        if q.get("metrics"):
            cmd += ["--metrics", ",".join(q["metrics"])]
        if q.get("group_by"):
            cmd += ["--group-by", ",".join(q["group_by"])]
        if q.get("where"):
            cmd += ["--where", q["where"]]
        if q.get("order"):
            cmd += ["--order", ",".join(q["order"])]
        if q.get("limit") is not None:
            cmd += ["--limit", str(q["limit"])]
        if q.get("start_time"):
            cmd += ["--start-time", q["start_time"]]
        if q.get("end_time"):
            cmd += ["--end-time", q["end_time"]]
        env = dict(os.environ, DBT_PROFILES_DIR=str(proj))
        p = subprocess.run(cmd, cwd=proj, capture_output=True, text=True, env=env, timeout=600)
        if p.returncode != 0 or not out.exists():
            raise RuntimeError((p.stderr + p.stdout).strip()[-2000:])
        with out.open() as f:
            return list(csv.DictReader(f))


def _cube_token():
    return (ROOT / "layers/cube/.token").read_text().strip()


def run_cube(a):
    if a.get("interface", "rest") == "sql":
        import psycopg
        with psycopg.connect(host="127.0.0.1", port=int(os.environ.get("CUBE_SQL_PORT", "15432")),
                             user="bench", password="bench-local-secret",
                             dbname="db", autocommit=True) as c:
            cur = c.execute(a["query"])
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    body = json.dumps({"query": a["query"]}).encode()
    url = os.environ.get("CUBE_URL", "http://localhost:4000") + "/cubejs-api/v1/load"
    req = urllib.request.Request(url, data=body,
                                 headers={"Authorization": _cube_token(),
                                          "Content-Type": "application/json"})
    for _ in range(60):  # Cube answers "Continue wait" while a query is running
        with urllib.request.urlopen(req, timeout=600) as r:
            res = json.load(r)
        if res.get("error") == "Continue wait":
            continue
        if "error" in res:
            raise RuntimeError(res["error"])
        return res["data"]
    raise RuntimeError("Cube kept answering 'Continue wait'")


def run_snowflake(a):
    raise RuntimeError("Snowflake executor not configured (no account yet)")


def run_anfra(a):
    p = subprocess.run(["anfra", "query", "--non-interactive", "--json", "--dataset", "tpch", a["query"]],
                       cwd=ROOT / "layers/anfra/project", capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[-2000:])
    res = json.loads(p.stdout)
    if res.get("has_more"):
        raise RuntimeError("result has more than one page")
    fields = res["result"]["fields"]
    return [dict(zip(fields, r)) for r in res["result"]["records"]]


EXECUTORS = {"slayer": run_slayer, "metricflow": run_metricflow, "cube": run_cube,
             "snowflake": run_snowflake, "anfra": run_anfra}


# ---------------------------------------------------------------- comparison

def norm(v):
    """Normalise a cell to float, ISO date string, or stripped string."""
    if v is None:
        return None
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float, decimal.Decimal)):
        return float(v)
    if isinstance(v, dt.datetime):
        return v.date().isoformat() if v.time() == dt.time() else v.isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        pass
    # 1995-01-01T00:00:00.000 / 1995-01-01 00:00:00 -> 1995-01-01
    if len(s) >= 19 and s[4] == "-" and s[7] == "-" and s[10] in "T " and s[11:19] == "00:00:00" \
            and set(s[19:].lstrip(".").rstrip("Z")) <= {"0"}:
        return s[:10]
    return s


def is_year_bucket(year, date):
    """A year written as a number (1995) and a year bucket written as its first day
    ('1995-01-01') are the same answer to "by order year"; layers differ only in format."""
    return isinstance(year, float) and year.is_integer() and 1900 <= year <= 2100 \
        and date == f"{int(year)}-01-01"


def cell_eq(a, b):
    if is_year_bucket(a, b) or is_year_bucket(b, a):
        return True
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-9)
    return a == b


def sort_key(row):
    return tuple((0, x, "") if isinstance(x, float) else (1, 0, str(x)) for x in row)


def compare(expected, got, order_matters):
    if len(expected) != len(got):
        return f"row count {len(got)} != expected {len(expected)}"
    if not order_matters:
        expected = sorted(expected, key=sort_key)
        got = sorted(got, key=sort_key)
    for i, (e, g) in enumerate(zip(expected, got)):
        if not all(cell_eq(x, y) for x, y in zip(e, g)):
            return f"row {i}: got {g}, expected {e}"
    return None


def load_truth(qid):
    with (TRUTH_DIR / f"{qid}.csv").open() as f:
        r = csv.reader(f)
        header = next(r)
        return header, [[norm(x) for x in row] for row in r]


# ---------------------------------------------------------------- main

def score(layer, a, questions):
    q = questions[a["id"]]
    rec = {k: a.get(k) for k in ("id", "status", "interface", "query", "columns", "reason",
                                 "category", "fixable_in_model", "notes", "tried")
           if a.get(k) is not None}
    for k in GROUP_KEYS:
        rec[k] = q[k]
    if a.get("status") == "unsupported":
        rec["result"] = "unsupported"
        return rec
    header, truth = load_truth(a["id"])
    try:
        rows = EXECUTORS[layer](a)
        cols = a["columns"]
        missing = [c for c in header if c not in cols]
        if missing:
            raise RuntimeError(f"attempt maps no result column to {missing}")
        got = [[norm(r[cols[c]]) for c in header] for r in rows]
    except Exception as e:  # noqa: BLE001
        rec["result"] = "wrong"
        rec["error"] = str(e)[-2000:]
        return rec
    diff = compare(truth, got, q.get("order_matters", False))
    rec["result"] = "answered" if diff is None else "wrong"
    if diff:
        rec["error"] = diff
    return rec


def run(layer, only):
    questions = {q["id"]: q for q in yaml.safe_load(QFILE.read_text())["questions"]}
    attempts = yaml.safe_load((ROOT / "layers" / layer / ATTEMPTS_FILE).read_text()) or []
    out_path = RESULTS_DIR / f"{layer}.json"
    prev = {r["id"]: r for r in json.loads(out_path.read_text())["questions"]} if out_path.exists() else {}
    for a in attempts:
        if only and a["id"] not in only:
            continue
        rec = score(layer, a, questions)
        prev[a["id"]] = rec
        print(f"{a['id']} {rec['result']:<11} {rec.get('error', '')[:200]}", flush=True)
    recorded = {a["id"] for a in attempts}
    for qid in questions:
        if qid not in recorded:
            prev.pop(qid, None)
    missing = [qid for qid in questions if qid not in recorded]
    out_path.parent.mkdir(exist_ok=True)
    res = sorted(prev.values(), key=lambda r: r["id"])
    summary = {k: sum(r["result"] == k for r in res) for k in ("answered", "wrong", "unsupported")}
    summary["not_attempted"] = len(missing)
    out_path.write_text(json.dumps({"layer": layer, "summary": summary, "questions": res},
                                   indent=1, default=str))
    print(layer, summary)


def aggregate():
    questions = yaml.safe_load(QFILE.read_text())["questions"]
    layers = {}
    for layer in LAYERS:
        p = RESULTS_DIR / f"{layer}.json"
        if p.exists():
            layers[layer] = json.loads(p.read_text())
    manifest = json.loads((TRUTH_DIR / "MANIFEST.json").read_text())
    out = {
        "questions_sha256": manifest["questions_sha256"],
        "questions": [{"id": q["id"], **{k: q[k] for k in GROUP_KEYS}, "question": q["question"].strip()}
                      for q in questions],
        "layers": layers,
    }
    if BLIND:
        # answered counts per domain and per difficulty, per layer
        breakdown = {}
        for key in GROUP_KEYS:
            groups = sorted({q[key] for q in questions})
            breakdown[key] = {}
            for layer, res in layers.items():
                byid = {r["id"]: r["result"] for r in res["questions"]}
                breakdown[key][layer] = {
                    g: {"answered": sum(byid.get(q["id"]) == "answered" for q in questions if q[key] == g),
                        "total": sum(q[key] == g for q in questions)}
                    for g in groups}
        out["breakdown"] = breakdown
    RESULTS_JSON.write_text(json.dumps(out, indent=1, default=str))
    for k, v in layers.items():
        print(k, v["summary"])
    for key, per_layer in out.get("breakdown", {}).items():
        for layer, groups in per_layer.items():
            print(key, layer, {g: f"{c['answered']}/{c['total']}" for g, c in groups.items()})


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a != "--blind"]
    if argv[:1] == ["--aggregate"]:
        aggregate()
    else:
        run(argv[0], set(argv[1:]))

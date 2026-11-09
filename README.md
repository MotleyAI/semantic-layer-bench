# Semantic Layer Expressivity Benchmark

How many analytical questions can each semantic layer answer from **the same semantic model**?

Layers under test: **SLayer**, **Cube**, **dbt MetricFlow**, **Snowflake Semantic Views**.

## Rules

1. **One baseline model, written in OSSIE** (Apache Ossie / Open Semantic Interchange core spec).
   Every layer gets exactly this model, translated mechanically (semglot, or the layer's own OSSIE
   importer). Nothing is added per layer: no extra metrics, no window/cumulative/conversion metrics,
   no extra joins. The vocabulary is fixed in [`model_contract.md`](model_contract.md).
2. **The question set is frozen before any layer is tried.** See [`questions/questions.yaml`](questions/questions.yaml).
   `ground_truth/MANIFEST.json` holds a SHA-256 of the file and of each answer.
3. **A question counts as answered only if** the layer's own semantic query interface returns a result
   that matches ground truth. Not allowed: editing the model, raw SQL against the tables, or
   post-processing the result outside the layer. Per layer, the interfaces that count are:

   | Layer | Counts | Does not count |
   |---|---|---|
   | SLayer | query API (REST / CLI / MCP / Python), including formulas, filters, query-as-model in the same request | raw SQL datasource access |
   | Cube | REST / GraphQL query, and SQL API queries that Cube rewrites into a single semantic query (`MEASURE()`, grouping, filters, ORDER/LIMIT) | SQL API post-processing (outer queries, window functions, joins over a Cube result) |
   | MetricFlow | `mf query` / dbt SL API (metrics, group-bys, `where`, `order`, `limit`, grains) | saved queries or new metrics (those are model edits) |
   | Snowflake | `SELECT ... FROM SEMANTIC_VIEW(...)` with an outer SELECT that only projects, renames, orders or limits | outer aggregation, window functions, joins, CTEs over the result |

   The common rule: SQL wrapped around a semantic query may only reshape the output (project, rename,
   order, limit). Once it computes something, the work is being done by SQL, not by the semantic layer.
4. **Each attempt records**: `answered` / `unsupported` / `wrong`, the exact query text, the reason, and a
   failure category:
   - `expressivity`: the query API cannot express the calculation.
   - `topology`: the layer cannot use the shared model's join graph (e.g. hop limits, composite keys,
     directed joins). Reported separately, because a different model layout might fix it.
   - `fixable_in_model`: yes/no, whether adding a native metric type to the model would fix it.
5. **Ground truth** is hand-written DuckDB SQL over TPC-H SF1. Results are compared automatically:
   column order as specified, numeric relative tolerance 1e-6, row order checked only where
   `order_matters: true`.

## Scores reported

- **Score A (headline): query-time expressivity.** Fixed OSSIE model, rules above.
- **Score B: with native model features.** Each layer may add its own model-level metric types
  (MetricFlow cumulative / offset / conversion metrics, Cube rolling windows, Snowflake derived
  metrics, SLayer saved formulas), one definition per question at most, with the definition published.
  This shows what each tool can do when someone models ahead, and what that costs.
- Both scores are shown **per pattern family**, not only as a single total, so the volume of one
  family cannot hide the others:
  - Core: P01–P05, P08, P09, P19
  - Composition: P06, P07, P14, P15, P16, P17, P24
  - Time series: P10–P13, P18, P23
  - Advanced: P20, P21, P22

## Data

TPC-H scale factor 1, generated with DuckDB's `tpch` extension (`data/tpch.duckdb`, not committed;
run `uv run python scripts/make_data.py`). The same data exists in Snowflake as
`SNOWFLAKE_SAMPLE_DATA.TPCH_SF1`.

## Known consequences of the OSSIE baseline (stated up front)

OSSIE metrics are SQL aggregations. It has no slot for cumulative, rolling-window, grain-to-date or
conversion metrics. MetricFlow and Cube normally define those *in the model*, so under this baseline
they must be expressed at query time or they fail. This is the point of the test (query-time
expressivity on a shared, portable model), and step 5 records "fixable in model" for every such case.

## Open items for step 2 (model translation)

- **MetricFlow composite keys.** lineitem → partsupp joins on two columns. MetricFlow entities are
  single-column, so the translation needs a synthetic key. Document it; affects Q44.
- **MetricFlow join depth.** customer_region is 4 hops from lineitem (Q09, Q11, Q19, Q23, Q26, Q34, Q35,
  Q49; Q10 is 3 hops). Verify the current hop limit; any failures here are `topology`.
- **Two paths from lineitem to part** (direct and via partsupp). Check how each layer resolves it.
- **Cube directed joins.** Q48, Q49 and Q58 need a measure and a dimension that join only through
  lineitem; Cube needs the right `hasMany` or `belongsTo` direction to answer them.

## Layout

```
model_contract.md          vocabulary the OSSIE model exposes (datasets, dimensions, metrics)
questions/questions.yaml   59 questions, 24 patterns, ground-truth SQL
ground_truth/              one CSV per question + MANIFEST.json (hashes, row counts)
scripts/make_data.py       builds data/tpch.duckdb
scripts/run_ground_truth.py  executes all ground-truth SQL and writes ground_truth/
```

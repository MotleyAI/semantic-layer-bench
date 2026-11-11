# anfra layer (AMQL: AML models + AQL queries)

anfra 0.20.0 (open-source anfra Core, single binary, no account or API key) with anfra skills 0.20.0.

## Setup

```bash
curl -fsSL https://anfra.ai/install.sh | bash                 # CLI in ~/.anfra/bin
npx skills add holistics/anfra-skills -a <agent> -g -y        # skills (anfra agent setup for Claude Code/Codex)
uv run python scripts/make_data.py
uv run python scripts/make_duckdb_v14.py                      # see "Data" below
uv run python layers/anfra/translate.py                       # OSSIE -> layers/anfra/project/{models,datasets}
cd layers/anfra/project && anfra validate                     # valid: true, 0 diagnostics
cd ../../.. && uv run python scripts/run_attempts.py anfra --blind
```

Before validating, copy `layers/anfra/project/.anfra/data_sources.yml.example` to
`.anfra/data_sources.yml` (git-ignored). It names one DuckDB source, `tpch`; set its `path` to
the absolute path of the v1.4 copy.

### Data

anfra's DuckDB connector bundles DuckDB 1.4.2. It refuses `data/tpch.duckdb` from `make_data.py`
because that file was written by a newer storage version. So anfra reads the copy that
`scripts/make_duckdb_v14.py` writes for Cube (`~/Library/Caches/sl-bench/tpch.duckdb`). It has the
same tables and rows, and the script checks row counts. Only the on-disk format differs.

## Model translation

`translate.py` translates `model/tpch.ossie.yaml` mechanically:

| OSSIE | AML |
|---|---|
| 10 datasets | 10 `Model`s (`type: 'table'`); each OSSIE field becomes a `dimension` with the same name |
| 11 relationships | 11 `Relationship`s, `many_to_one`, all active; lineitem→partsupp uses `on {}` for its second key column |
| 11 metrics | 11 dataset `metric`s in `Dataset tpch`, with the same aggregation over the same fields |

The relationships and primary keys use physical key columns that the model does not declare as
fields, such as `l_orderkey`, `c_nationkey` and `p_partkey`. AML joins only on dimensions, so
these columns become `hidden: true` dimensions. No attempt references them, except through the
declared metric `line_count = count(lineitem.l_orderkey)`, which is the OSSIE definition.
Nothing else is added.

## Query interface

Every attempt is one AQL query, run by `anfra query --dataset tpch '<aql>'`. An AQL query is an
`explore {}` and may be preceded by query-local `metric` / `dimension` declarations. Those
declarations are expressions over declared members: filters (`where`), level of detail
(`dimensionalize`, `exclude_grains`, `keep_grains`), window functions (`rank`, `ntile`,
`window_sum`) and time intelligence (`relative_period`, `period_to_date`, `trailing_period`).
They live only in the request and do not change the model, the same way SLayer's
query-as-model works. The attempts use no SQL passthrough (`sql_*`/`agg_*`) functions.

anfra has no freeform-SQL-over-the-model mode. `anfra query --lang sql -s tpch` runs raw SQL
against the data source and bypasses the model, so the benchmark excludes it and it is not scored.

## Result

74/75 answered, 0 wrong, 1 unsupported (B70, market-basket pairs: needs part joined to itself).
71 of the 74 are strict. B17 and B65 identify a part by part_name + manufacturer. B73 would omit
zero-count combinations. The `notes` of each attempt record caveats and silently wrong first
attempts.

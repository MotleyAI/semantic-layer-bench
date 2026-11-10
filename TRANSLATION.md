# Step 3: translating the OSSIE baseline to each layer

Every layer's model is generated from `model/tpch.ossie.yaml` by a tool, not written by hand:

| Layer | How | Output |
|---|---|---|
| SLayer | `slayer import-osi` (SLayer 1.7.0, SLayer's own OSSIE importer) | `layers/slayer/storage/` (local, rebuilt by command) |
| MetricFlow | semglot `metricflow` target (new, see below) | `layers/metricflow/project/` |
| Cube | semglot `cube` target (new, see below) | `layers/cube/project/model/cubes/` |
| Snowflake | semglot `snowflake-semantic-view` target, from `model_snowflake/` | `layers/snowflake/project/definition.md` |

`model_snowflake/tpch.ossie.yaml` is generated from the same script and differs only in each
dataset's `source`, which points at `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1`.

Regenerate everything with `semglot build --profile <name>` (profiles in `semglot.yaml`).
Each layer's README explains how to run it.

**Frozen.** From here on, `model/tpch.ossie.yaml` and the four translations change only to fix a
translation bug, which is logged in this file. SHA-256 of the model: `b000d9acf09564d1414f80052953d0b1a3a169d382525d0877858905589204e8`.

## semglot changes (branch `bench-dbt-cube` of MotleyAI/semglot)

1. **New `metricflow` target.** semglot's existing `dbt` target is built for a lossless
   dbt → IR → dbt round-trip, and its output can't be run by MetricFlow:
   - It emits no foreign entities, so MetricFlow finds no joins.
   - Entities are named after physical columns, so `customer_nation` and `supplier_nation` collide
     on `n_nationkey`.
   - A composite key becomes two primary entities, but MetricFlow allows one.

   The new target names entities after tables and emits a foreign entity per relationship. A
   composite key becomes one concatenated-key entity on both sides. It also sets time
   granularities and `agg_time_dimension`, maps `avg` to `average`, removes table qualifiers from
   measure expressions, writes `models/<table>.sql` from each OSSIE source, and adds a time spine.
   The `dbt` target is unchanged.
2. **Shared dbt-emitter fix:** a composite primary key is now emitted as one model-level
   constraint. dbt rejects column-level primary-key constraints on more than one column. This also
   fixes the `dbt` target; the parser already read this form.
3. **New `cube` target.** It writes one cube per dataset with `sql_table`, `{CUBE}`-qualified
   dimensions and a primary-key dimension (a hidden concatenation for composite keys). Each
   relationship becomes a `many_to_one` join on its many side; no reverse joins are invented. Each
   metric becomes a measure of its aggregation type, and ratios become `type: number` measures over
   named measures.
4. A test helper now walks output directories recursively. All semglot tests pass.

## Validation

| Layer | Loads | Smoke test (Q01, Q09) |
|---|---|---|
| SLayer | `import-osi`: 10 models, 0 unconverted, 0 dropped | Q01 ✓, Q09 ✓ (4-hop join) |
| MetricFlow | `dbt parse` ✓; `mf validate-configs`: 0 errors, 0 warnings (incl. against the warehouse) | Q01 ✓; Q09 not expressible (see below) |
| Cube | Cube 1.6.76 loads all 10 cubes | Q01 ✓, Q09 ✓ (4-hop join), `avg_order_value` ratio re-aggregates correctly |
| Snowflake | DDL generated; **not yet run** (needs a Snowflake account) | n/a |

## What each translation could not carry (logged, not hidden)

- **MetricFlow**
  - **No measures on tables without a time dimension.** MetricFlow requires an aggregation time
    dimension in the measure's own semantic model. Until 2026-11-10 `customer_count`,
    `supplier_count` and `total_available_qty` were dropped for this reason; they are now kept with
    a NULL plumbing time dimension (see the log below).
  - **Join depth.** From `revenue`, MetricFlow reaches `supplier_nation` (2 hops), but not
    `customer_nation` (3 hops) or `customer_region` (4 hops). Evidence:
    `layers/metricflow/evidence/revenue_dimensions.txt`. These count as `topology` failures.
  - **`metric_time` for line-item metrics is `ship_date`**, the first time dimension declared on
    lineitem. OSSIE has no aggregation-time-dimension concept, and the translator takes the first
    one. MetricFlow's time functions (offsets, cumulative) only work on `metric_time`. So
    "by order month" time-series questions on line-item metrics are limited by this. Recorded as a
    `topology` limitation; Score B may change it.
- **Cube.** Relationship names are not carried (Cube names a join after its target cube). Since
  2026-11-10 each relationship is emitted in both directions (see the log below).
- **Snowflake.** Relationship synonyms only. Runtime behaviour is untested.

## Translation fix log

### 2026-11-10: audit of the Cube and MetricFlow translations

Two independent reviews (one per tool, checked against current Cube 1.6.76 and MetricFlow 0.213
docs and code, every change tested in a scratch copy) asked whether each translation was the best
faithful one. Fixed in semglot `bench-dbt-cube` commit `cdfa768`; both layers regenerated with
`semglot build --profile cube|metricflow`. The OSSIE model itself is unchanged (same SHA-256).

| Layer | Fix | Why | Adds a member? |
|---|---|---|---|
| Cube | Declared primary-key fields (`orders.order_key`, `customer.customer_key`, `supplier.supplier_key`) emitted with `public: true` | Cube makes primary keys private by default, which hid declared fields (bug) | No, restores declared fields |
| Cube | Each relationship also emitted as a `one_to_many` join on the one side | A source relationship is a key equality usable in both directions; Cube joins are directed, and its docs show the reverse join as the way to express that | No (joins are not members) |
| MetricFlow | `customer_count`, `supplier_count`, `total_available_qty` kept, with a NULL-valued time dimension `agg_time` as `defaults.agg_time_dimension` on customer, supplier and partsupp | MetricFlow requires an aggregation time dimension; NULL keeps metric definitions exact and gives no fake date | One disclosed plumbing time dimension per table; metric definitions unchanged |
| MetricFlow | Declared key fields emitted as categorical dimensions (`order_key`, `customer_key`, `supplier_key`) | They were only reachable as entities, under other names | No, restores declared fields |

Validation: Cube loads all cubes; `dbt parse` and `mf validate-configs` (including warehouse checks)
report 0 errors. Re-scoring the blind round: MetricFlow 11 to 12 (B35), Cube unchanged at 15, no
previously answered question changed.

Considered and not applied: denormalising nation and region onto MetricFlow's customer and supplier
models to get round the hard-coded 2-hop join limit. It would answer B04 and B22, but it changes the
model's layout rather than translating it. The ship_date `agg_time_dimension` was kept: order_date is
not on lineitem, and MetricFlow only accepts a time dimension of the measure's own model.


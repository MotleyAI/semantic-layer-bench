# Blind round results (B01 to B50)

The first round (Q01 to Q59) was written by people who knew what each layer can do. This round
answers the obvious objection to that ("the questions were picked to favour SLayer"): the 50
questions here were written without any knowledge of semantic-layer capabilities, then frozen,
then scored under the same rules (`README.md` rules 3 to 5, including the Member rule).
Snowflake is not scored (no account).

## How the questions were made

1. **Isolated author.** One subagent got only the business domain (a wholesale parts
   distributor), the vocabulary of `model_contract.md` (pasted into its brief), and the task:
   50 questions a business person would ask, about evenly split across operations, finance and
   marketing, with about 15 simple, 20 medium and 15 hard. It was told not to read anything in
   the repo and not to think about which tool could answer a question. Its output is kept
   verbatim in [`questions_blind/authored.yaml`](questions_blind/authored.yaml).
2. **Ground truth.** Hand-written DuckDB SQL for each question was added to
   [`questions_blind/questions.yaml`](questions_blind/questions.yaml) and executed with
   `uv run python scripts/run_ground_truth.py --blind`, which writes
   [`ground_truth_blind/`](ground_truth_blind/) with SHA-256 hashes in `MANIFEST.json`. Every
   answer is non-empty and NULL-free.
3. **One fix, logged.** B15 asked about finished (status F) orders placed in 1996. No 1996 order
   has status F in TPC-H (only orders completed before mid-1995 do), so the answer was empty. It
   was moved to 1994; the question is otherwise unchanged. No other question was edited.
4. **Frozen** in commit `5cfec3b` before any layer was tried.
5. **Scoring.** One agent per layer, each told to get the strongest fair result for its layer,
   to record `tried` queries and errors before marking anything unsupported, and to flag
   suspected translation bugs instead of working around them. Attempts are in
   `layers/<layer>/attempts_blind.yaml`; results in `results_blind/<layer>.json` and
   `results_blind.json`, produced by `uv run python scripts/run_attempts.py <layer> --blind` and
   `--aggregate --blind`. All three layers were re-run from those files after the agents
   finished, with the same scores.

## Scores (Score A, fixed OSSIE model)

| Layer | Answered | Wrong | Unsupported |
|---|---|---|---|
| SLayer | **50 / 50** | 0 | 0 |
| Cube | 15 / 50 | 0 | 35 |
| MetricFlow | 11 / 50 | 0 | 39 |

By domain:

| Domain | SLayer | Cube | MetricFlow |
|---|---|---|---|
| Operations (17) | 17 | 3 | 2 |
| Finance (17) | 17 | 6 | 5 |
| Marketing (16) | 16 | 6 | 4 |

By difficulty:

| Difficulty | SLayer | Cube | MetricFlow |
|---|---|---|---|
| Simple (15) | 15 | 12 | 8 |
| Medium (20) | 20 | 3 | 3 |
| Hard (15) | 15 | 0 | 0 |

Answered by Cube: B03, B04, B05, B18, B19, B21, B22, B26, B27, B35, B36, B37, B38, B39, B43.
Answered by MetricFlow: B03, B05, B18, B19, B21, B26, B27, B36, B38, B39, B43.

## What the blind questions show

Business questions are mostly not "one metric by one dimension". Of the 50, only about 15
are a single declared metric grouped and filtered. The rest need, at query time, things the
OSSIE model has no slot for:

- **A ratio of two metrics or of a filtered count to a total** (late share, return share, margin
  rate, revenue per customer, discount cost). This is the most common need: B01, B02, B07 to
  B10, B13, B20, B28, B44, B45 and more. Neither Cube REST nor `mf query` can do arithmetic
  between measures at query time; both can with a model-level metric.
- **A condition comparing two fields** (receipt_date > commit_date defines "late", which drives
  9 of the 17 operations questions).
- **An aggregate over a row-level expression** (supply_cost * quantity for margin, date
  differences for transit days): B06, B11, B24, B25, B32.
- **Period comparisons, ranks within groups, shares of a group total, top-N sums, cohorts and
  anti-joins**: all 15 hard questions.

Cube's and MetricFlow's simple-question scores (12/15 and 8/15) show both work for the
questions they are designed for. The gap opens at medium difficulty, where a ratio or a
two-field condition appears.

## Caveats on the SLayer result

SLayer answered everything through its query API (formulas, `iif` conditional aggregates,
`partition_by`, `rank`, `time_shift`, multi-stage queries and joins between stages in one
request), using only declared members. Points a reviewer may want to weigh:

- **B16, B30, B31, B48 (top-N per group).** SLayer's `rank()` gives tied values the same rank;
  ground truth uses `row_number()` with a name or key tie-break. They match because this data
  has no ties at the cut-offs. With ties, SLayer would return extra rows rather than applying
  the stated tie-break.
- **B17 (cheapest supplier share).** The model declares no part key, so the query identifies a
  part by `part_name` + `manufacturer` (unique across all 200,000 parts; `part_name` alone has 3
  duplicates). Both are declared fields, so it satisfies the Member rule, but it relies on a
  property of the data.
- **B40 (container size class).** SLayer has no `split_part`; the first word of the container
  is taken with `substr`/`instr`.
- **B47 (lapsed customers).** "Has a 1996 order" is computed as "has a 1996 line item", which is
  equivalent because every TPC-H order has lines.

## Failures that come from the translation, not the query API

No layer agent found a translation bug (a translated model that differs from
`model/tpch.ossie.yaml` beyond what `TRANSLATION.md` documents). Several MetricFlow failures do
come from the **documented translation losses**, and a reader should see them as such:

- **Dropped metrics.** MetricFlow needs an aggregation time dimension on every measure's own
  model, so `customer_count`, `supplier_count` and `total_available_qty` were dropped. That
  alone blocks B35 (customers per segment, a simple question Cube answers) and contributes to
  B04, B12, B37, B42 and B45.
- **`metric_time` is `ship_date`** for line-item metrics, so offsets (YoY) cannot run on order
  date: contributes to B23, B34.
- **Join depth.** customer_nation (3 hops) and customer_region (4 hops) are beyond MetricFlow's
  2-hop limit: B22, B29, B34, B45, B48 and parts of B31, B37, B41. This is a MetricFlow engine
  limit on the shared join graph (`topology`), not a translation error, but a model laid out
  differently (denormalised nation and region onto customer) would avoid it.

For Cube, one failure is a join-graph effect: **B12** (brass stock versus 1997 sales). Cube's
joins are many-to-one only, as declared, so filtering by order date roots the query at lineitem
and `total_available_qty` then covers only offers that sold in 1997, not all offers. Recorded as
`topology`.

All Cube failures are marked `fixable_in_model: yes` (Cube can declare the needed ratio,
filtered or windowed measure in the model). For MetricFlow, 10 are `yes` (ratio or filtered
metrics) and 29 `no`.

## Every non-answered question

### metricflow

| id | domain / difficulty | category | fixable in model | reason |
|---|---|---|---|---|
| B01 | operations / simple | expressivity | yes | late_share is a ratio of a filtered count (receipt_date > commit_date) to the unfiltered line_count. mf query applies one where clause to the whole query and has no query-time arithmetic, so the late count and the total cannot be returned or divided in one query. |
| B02 | operations / simple | expressivity | no | Needs a returned-line share (filtered count / count, query-time arithmetic) and supplier_region_name is 3 hops from lineitem (lineitem -> supplier -> supplier_nation -> supplier_region), beyond MetricFlow's 2-hop limit. |
| B04 | operations / simple | topology | no | total_available_qty is not in the MetricFlow project: MetricFlow requires an aggregation time dimension for every measure and partsupp has none, so the metric was dropped in translation (documented in TRANSLATION.md). supplier_region_name is also 3 hops from partsupp. |
| B06 | operations / medium | expressivity | no | Average of a per-line date difference (receipt_date - ship_date) is a query-time aggregation of an expression over dimensions. mf query can only request declared metrics; no declared metric aggregates a date difference. |
| B07 | operations / medium | expressivity | yes | late_share is a filtered-count ratio (no query-time arithmetic). The HAVING line_count >= 100 could be a metric filter on the supplier entity, but --explain shows that subquery ignores the outer receipt-date filter, so it counts all-time lines. |
| B08 | operations / medium | expressivity | yes | late_share is a ratio of a filtered line count to line_count; mf query has one where clause and no query-time arithmetic. line_count by order_priority with the 1995 filter alone is expressible. |
| B09 | operations / medium | expressivity | yes | late_share per ship month is a ratio of a filtered line count to line_count; not expressible at query time (no arithmetic, single where). |
| B10 | operations / medium | expressivity | yes | returned_qty_share = total_quantity on return_flag = 'R' lines / total_quantity: a filtered measure next to the unfiltered one and their ratio. Not expressible in mf query. |
| B11 | operations / medium | expressivity | no | late_line_count is expressible (line_count with receipt_date > commit_date, supplier_nation_name is 2 hops), but avg_days_late averages a per-line date difference, which is not a declared metric and cannot be computed at query time. |
| B12 | operations / medium | expressivity | no | total_available_qty was dropped in translation (partsupp has no aggregation time dimension), and cover_ratio divides two metrics from different facts, which mf query cannot do. |
| B13 | operations / hard | expressivity | yes | late_line_count is expressible, but shipped_late_share and transit_late_share are ratios of differently filtered counts; mf query has one where clause and no arithmetic. |
| B14 | operations / hard | expressivity | no | Needs late_share (a filtered-count ratio) for two years side by side per supplier, their difference, a per-year >= 50 lines threshold, and a ranking on the difference. mf query has no arithmetic, no period-side-by-side filtered metrics and cannot order by a computed change. |
| B15 | operations / hard | expressivity | no | Distribution of orders by number of late lines is a nested aggregation (count lines per order, then count orders per value). mf query aggregates once and cannot group by a metric. |
| B16 | operations / hard | expressivity | no | Top-1 nation per supplier region needs ranking within groups and a filtered-count ratio; supplier_region_name is also 3 hops from lineitem. |
| B17 | operations / hard | expressivity | no | Needs the per-part minimum supply_cost across all offers and a comparison with each line's own offer cost, then a quantity share. That is a nested aggregation over partsupp plus a correlated comparison; not expressible. |
| B20 | finance / simple | expressivity | yes | gross_sales and revenue are returned together, but discount_amount = gross_sales - revenue is arithmetic between metrics, which mf query cannot compute. |
| B22 | finance / simple | topology | no | customer_region_name is 4 hops from lineitem (lineitem -> orders -> customer -> customer_nation -> customer_region); MetricFlow caps joins at 2 hops (MAX_JOIN_HOPS = 2). |
| B23 | finance / medium | expressivity | yes | Year-over-year growth needs the previous year's revenue (offset) and a ratio; mf query has neither offsets nor arithmetic at query time. |
| B24 | finance / medium | expressivity | no | margin subtracts sum(partsupp.supply_cost * lineitem.quantity), an aggregate of an expression over a joined dimension. No declared metric computes it and measures cannot reference joined columns; margin_rate is also arithmetic. supplier_region_name is 3 hops from lineitem as well. |
| B25 | finance / medium | expressivity | no | margin needs sum(supply_cost * quantity) across lineitem and partsupp; not a declared metric and not computable at query time. |
| B28 | finance / medium | expressivity | yes | returned_revenue (revenue filtered to return_flag = 'R') next to total revenue and their ratio, per year; mf query has a single where and no arithmetic. |
| B29 | finance / medium | topology | no | customer_region_name is 4 hops from lineitem (beyond the 2-hop limit), and the two half-year revenues side by side plus growth need filtered metrics and arithmetic. |
| B30 | finance / hard | expressivity | no | Sum of the top-100 customers' revenue and its share of total is a nested aggregation (rank customers, then sum); mf query can list the top 100 but not aggregate over them. |
| B31 | finance / hard | expressivity | no | customer_nation_name is 3 hops from lineitem (beyond the 2-hop limit); the question also needs a share of the segment total and a top-3 per segment ranking, neither expressible. |
| B32 | finance / hard | expressivity | no | Line margin needs supply_cost * quantity per line, then a filter on the per-line margin and a share; not expressible (no expression aggregation, measures cannot use joined columns). |
| B33 | finance / hard | expressivity | no | Needs avg_order_value for 1996 and 1997 side by side per clerk, their difference, a >= 100 orders per year threshold and a ranking on the difference. Metric filters only take entities as group_by (clerk is a dimension), and there is no arithmetic. |
| B34 | finance / hard | topology | no | customer_region_name is 4 hops from lineitem (beyond the 2-hop limit); same-quarter-last-year growth also needs an offset and arithmetic. |
| B35 | marketing / simple | topology | no | customer_count is not in the MetricFlow project (customer has no time dimension, MetricFlow requires an aggregation time dimension per measure; documented drop). No other declared metric counts customers on file. |
| B37 | marketing / simple | topology | no | customer_count was dropped in translation and mf query cannot count distinct customers at query time; customer_region_name is also 3 hops from orders (beyond the 2-hop limit). |
| B40 | marketing / medium | expressivity | no | container_size is a derived dimension (first word of container) that the model does not declare, and revenue_share needs a total across groups and a ratio. mf query groups only by declared dimensions and has no arithmetic. |
| B41 | marketing / medium | expressivity | no | customer_nation_name is 3 hops from lineitem (beyond the 2-hop limit); revenue for two years side by side and their growth also need filtered metrics and arithmetic. |
| B42 | marketing / medium | expressivity | no | Needs distinct customers (customer_count was dropped) and a per-customer order-count threshold (nested aggregation) turned into a share; not expressible. |
| B44 | marketing / medium | expressivity | yes | Revenue from negative-balance customers / total revenue per segment is a filtered measure next to the unfiltered one plus a ratio; mf query has one where clause and no arithmetic. |
| B45 | marketing / medium | topology | no | customer_region_name is 4 hops from lineitem (beyond the 2-hop limit); customer_count was dropped and revenue_per_customer needs arithmetic. |
| B46 | marketing / hard | expressivity | no | Cohort by first-order year is a dimension derived from an aggregate (min order_date per customer), plus a next-year existence test and a share; mf query cannot group by a metric and has no existence filters. |
| B47 | marketing / hard | expressivity | no | Lapsed customers (ordered in 1996, not in 1997) need an anti-join per customer; customer_count was dropped and mf query has no existence filters. |
| B48 | marketing / hard | expressivity | no | Top-3 brands per customer region needs ranking within groups (mf query has only a global order and limit), and customer_region_name is 4 hops from lineitem. |
| B49 | marketing / hard | expressivity | no | Bucketing customers by lifetime order count is a dimension derived from a metric (multi-stage), then customer counts and revenue per bucket; mf query cannot group by a metric. |
| B50 | marketing / hard | expressivity | no | Share of each year's revenue per segment needs a partitioned total and a ratio for two years side by side plus their difference; not expressible. |

### cube

| id | domain / difficulty | category | fixable in model | reason |
|---|---|---|---|---|
| B01 | operations / simple | expressivity | yes | late_share needs a conditional count (receipt_date > commit_date) divided by line_count. The REST query has no member-vs-member filter, no per-measure filter and no calculated measure. line_count by ship_mode alone is one REST query; the share is not. |
| B02 | operations / simple | expressivity | yes | returned_share = lines with return_flag 'R' / all lines per supplier region needs a filtered count next to the unfiltered one plus a ratio; REST filters apply to every measure and there are no calculated measures. |
| B06 | operations / medium | expressivity | yes | Average of a row-level date difference (receipt_date - ship_date). No such measure is declared and REST cannot aggregate an expression over dimensions at query time. |
| B07 | operations / medium | expressivity | yes | Needs late_share (conditional count / count, member-vs-member condition) per supplier, ranked by that share. Neither the conditional count nor the ratio is expressible at query time. The line_count >= 100 HAVING and the order/limit alone would be fine. |
| B08 | operations / medium | expressivity | yes | line_count by order_priority for 1995 orders is one REST query, but late_share needs a member-vs-member conditional count and a ratio; not expressible at query time. |
| B09 | operations / medium | expressivity | yes | Monthly late_share needs a member-vs-member conditional count and a ratio; same limit as B01. |
| B10 | operations / medium | expressivity | yes | returned_qty_share = SUM(quantity) on return_flag 'R' lines / SUM(quantity) per manufacturer: needs a filtered measure beside the unfiltered one and a ratio; neither exists at query time. |
| B11 | operations / medium | expressivity | yes | Restricting to late lines needs a member-vs-member filter (receipt_date > commit_date), and avg_days_late is an average of a row-level date difference; neither is expressible. |
| B12 | operations / medium | topology | yes | Two facts with different filters (all partsupp offers, undated; lineitem quantity for 1997 orders) plus a ratio. In one REST query the order_date filter forces a lineitem-rooted join tree, so total_available_qty is computed only over offers that sold in 1997 (wrong), and cover_ratio would need a calculated measure anyway. |
| B13 | operations / hard | expressivity | yes | Restricted to late lines (member-vs-member filter) with two conditional shares based on ship_date vs commit_date (also member-vs-member). Not expressible at query time. |
| B14 | operations / hard | expressivity | yes | Per-supplier late_share for two years side by side and their difference, ranked. Needs the conditional ratio (B01), per-year columns (per-measure filters or time shift) and arithmetic. |
| B15 | operations / hard | expressivity | yes | Distribution of orders by their count of late lines: a dimension derived from a per-order conditional aggregate, then a count of orders per value. Aggregate of an aggregate plus member-vs-member condition; not expressible. |
| B16 | operations / hard | expressivity | yes | Top-1 nation per supplier region by late_share needs a rank/window and the conditional ratio; REST has only a global order + limit. |
| B17 | operations / hard | expressivity | yes | Needs the per-part minimum supply_cost (aggregate over all offers of a part) compared with the line's own offer cost, then a conditional quantity share. Derived dimension from an aggregate, member-vs-member comparison and a ratio: none expressible at query time. |
| B20 | finance / simple | expressivity | yes | gross_sales and revenue for 1996 orders come from one REST query, but discount_amount = gross_sales - revenue is query-time arithmetic between measures; REST has no calculated measures. |
| B23 | finance / medium | expressivity | yes | Year-over-year growth needs the previous year's revenue on each row (time shift / lag) and a ratio; neither exists at query time. |
| B24 | finance / medium | expressivity | yes | margin = revenue - SUM(supply_cost * quantity): supply_cost (partsupp) and quantity (lineitem) are dimensions; REST cannot aggregate a cross-cube row-level expression, and margin_rate needs a calculated measure. |
| B25 | finance / medium | expressivity | yes | Brand margin needs SUM(supply_cost * quantity) across lineitem and partsupp dimensions and a difference with revenue; no ad-hoc measures at query time. |
| B28 | finance / medium | expressivity | yes | returned_revenue (revenue with return_flag 'R') next to the year's total revenue, plus their ratio: needs a per-measure filter and a calculated measure. returned_revenue by year alone is one REST query, the share is not. |
| B29 | finance / medium | expressivity | yes | Two period-filtered revenue columns per region and their growth; REST filters apply to the whole query and there is no calculated measure. |
| B30 | finance / hard | expressivity | yes | Sum of the top-100 customers' revenue over the total is an aggregate over a ranked sub-result plus a ratio; REST aggregates once. |
| B31 | finance / hard | expressivity | yes | Top-3 nations per segment with rank and share of segment total; needs windows (rank, partitioned sum). REST has only a global order + limit. |
| B32 | finance / hard | expressivity | yes | Line margin needs supply_cost * quantity per row (cross-cube dimensions), a filter on that row-level value, a conditional count share and a conditional sum. None expressible at query time. |
| B33 | finance / hard | expressivity | yes | Per-clerk avg_order_value for 1996 and 1997 side by side, their difference and per-year HAVING on counts; needs per-measure year filters and arithmetic. |
| B34 | finance / hard | expressivity | yes | Same-quarter-prior-year revenue per row and growth; no time shift or calculated measure at query time. |
| B40 | marketing / medium | expressivity | yes | container_size (first word of container) is a derived dimension, and revenue_share needs the grand total next to each row. REST has neither query-time dimensions nor windows. |
| B41 | marketing / medium | expressivity | yes | Revenue per nation for 1996 and 1997 side by side, growth ratio and ranking by it; needs per-measure year filters and a calculated measure. |
| B42 | marketing / medium | expressivity | yes | Repeat-customer share needs per-customer order counts (aggregate) turned into a flag and re-aggregated per segment. Aggregate of an aggregate; not expressible in one REST query. |
| B44 | marketing / medium | expressivity | yes | Revenue from negative-balance customers over total revenue per segment; needs a per-measure filter (account_balance < 0) and a ratio. |
| B45 | marketing / medium | expressivity | yes | revenue and customer_count per region for 1997 come from one REST query, but revenue_per_customer = revenue / customer_count is query-time arithmetic; no calculated measures. |
| B46 | marketing / hard | expressivity | yes | Cohorts by first-order year (dimension derived from a per-customer MIN) and next-year retention (existence test); no subquery dimensions at query time. |
| B47 | marketing / hard | expressivity | yes | Lapsed customers (ordered in 1996, not in 1997) need per-customer existence flags across two periods (anti-join); not expressible in one query. |
| B48 | marketing / hard | expressivity | yes | Top-3 brands per customer region needs a rank within region; REST has only a global order + limit. |
| B49 | marketing / hard | expressivity | yes | Bucketing customers by lifetime order count is a dimension derived from an aggregate, then re-aggregated; no subquery dimensions at query time. |
| B50 | marketing / hard | expressivity | yes | Segment share of each year's total for two years, side by side, and the change; needs partitioned totals and arithmetic at query time. |

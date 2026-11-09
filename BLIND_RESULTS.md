# Blind round results (B01 to B75)

The first round (Q01 to Q59) was written by people who knew what each layer can do. This round
answers the obvious objection to that ("the questions were picked to favour SLayer"): the
questions here were written without any knowledge of semantic-layer capabilities, frozen, then
scored under the same rules (`README.md` rules 3 to 5, including the Member rule). Snowflake is
not scored (no account).

## How the questions were made

1. **Isolated author, B01 to B50.** One subagent got only the business domain (a wholesale parts
   distributor), the vocabulary of `model_contract.md`, and the task: 50 questions a business
   person would ask, about evenly split across operations, finance and marketing, about 15
   simple, 20 medium and 15 hard. It read nothing else in the repo and was told not to consider
   which tool could answer a question. Output kept verbatim in
   [`questions_blind/authored.yaml`](questions_blind/authored.yaml). Frozen in `5cfec3b`.
2. **Extension, B51 to B75.** After B01 to B50 were scored (SLayer 50/50), a second isolated
   author was asked for 25 more, analytically harder questions (5 medium, 20 hard), with the
   same brief plus the text of the first 50 so as not to duplicate them. It saw no layer, attempt
   or result. Verbatim in
   [`questions_blind/authored_extension.yaml`](questions_blind/authored_extension.yaml). Frozen with
   ground truth in `ccb5b82` before any layer was tried on them. The extension was requested to
   test whether a harder blind mix would find SLayer's limits; it is reported in full whatever the
   outcome.
3. **Ground truth.** Hand-written DuckDB SQL per question in
   [`questions_blind/questions.yaml`](questions_blind/questions.yaml), executed with
   `uv run python scripts/run_ground_truth.py --blind [ids]` into
   [`ground_truth_blind/`](ground_truth_blind/) with SHA-256 hashes in `MANIFEST.json`. Every
   answer is non-empty and NULL-free. Generating B51 to B75 left the B01 to B50 files untouched.
4. **One fix, logged.** B15 asked about finished (status F) orders placed in 1996; none exist in
   TPC-H, so it was moved to 1994. No other question was edited.
5. **Scoring.** One agent per layer per batch, each told to get the strongest fair result, to
   record `tried` queries and errors before marking anything unsupported, and to flag suspected
   translation bugs. Attempts in `layers/<layer>/attempts_blind.yaml`; results in
   `results_blind/<layer>.json` and `results_blind.json` (`run_attempts.py <layer> --blind`,
   `--aggregate --blind`). All three layers were re-run from those files afterwards, with the
   same scores.

## Scores (Score A, fixed OSSIE model)

| Layer | Answered | Wrong | Unsupported |
|---|---|---|---|
| SLayer | **75 / 75** | 0 | 0 |
| Cube | 15 / 75 | 0 | 60 |
| MetricFlow | 11 / 75 | 0 | 64 |

By batch: B01 to B50 SLayer 50, Cube 15, MetricFlow 11. B51 to B75 SLayer 25, Cube 0, MetricFlow 0.

| Domain | SLayer | Cube | MetricFlow |
|---|---|---|---|
| Operations (25) | 25 | 3 | 2 |
| Finance (26) | 26 | 6 | 5 |
| Marketing (24) | 24 | 6 | 4 |

| Difficulty | SLayer | Cube | MetricFlow |
|---|---|---|---|
| Simple (15) | 15 | 12 | 8 |
| Medium (25) | 25 | 3 | 3 |
| Hard (35) | 35 | 0 | 0 |

## What the blind questions show

Only 15 of the 75 questions are a declared metric grouped and filtered (exactly Cube's 15
answers; MetricFlow's 11 are a subset). The other 60 need, at query time, things the OSSIE model
has no slot for: ratios between metrics or of a filtered count to a total, conditions comparing
two fields (receipt date after commit date), aggregates of row-level expressions (supply cost
times quantity), period comparisons, running and rolling totals, percentiles, ranks and buckets
within groups, and aggregates of aggregates (cohorts, per-order and per-customer measures,
anti-joins). Neither Cube REST nor `mf query` can express these at query time.

## Caveats on the SLayer result (read before quoting 75/75)

SLayer answered through its query API only (formulas, `iif`, `partition_by`, `rank`, `ntile`,
`percentile`, `cumsum`, `window`, `time_shift`, multi-stage queries and inline joins between
stages), using only declared members. But not every answer expresses the question as written:

- **Workaround: running total over a ranking (B51, B62).** `cumsum` only runs along a time axis.
  The query converts each rank into a day offset from a declared date, runs `cumsum` on that
  axis, and converts back. It is correct and within the rules, but it is a trick an agent is
  unlikely to find unaided.
- **Tie-breaks not expressible (B16, B30, B31, B48, B51, B62, B67, B73).** `rank` and `ntile`
  take no secondary sort key, and `ntile` has no direction (`ntile(-x)` is used for descending).
  The questions specify a tie-break by name or key. Answers match only because this data has no
  ties at the cut-offs.
- **Relies on the data (B17, B65).** The model declares no part key, so a part is identified by
  `part_name` + `manufacturer`, unique in this dataset only.
- **Exact by construction, without `row_number` (B69, B72).** Three queries (B47, B68, B70) also
  rely on every order having a line item, which is true in TPC-H.

A strict reading that counts only answers expressing the question exactly as specified, with no
reliance on properties of this dataset, would not credit the 10 questions above (B16, B17, B30,
B31, B48, B51, B62, B65, B67, B73): **65 / 75**. This stricter reading was defined after seeing
the results. The harness rule (75 / 75) is unchanged, but the published write-ups (blog post,
results page, LinkedIn card) lead with the strict 65 / 75 and state that it was set afterwards. Cube and MetricFlow
scores are unchanged under it (none of their answers involve these features).

## Failures that come from the translation, not the query API

No layer agent found a translation bug. Several MetricFlow failures come from the documented
translation losses: `customer_count`, `supplier_count` and `total_available_qty` were dropped
(MetricFlow needs an aggregation time dimension on each measure's model), which blocks B35 and
contributes to B04, B12, B37, B42, B45, B71 and B74; `metric_time` is `ship_date`, which also
limits order-dated offsets (B23, B34, B61, B63); and the 2-hop join limit puts customer and
supplier nation and region out of reach (B22, B29, B34, B45, B48, B64 and parts of others).
For Cube, B12 and B74 are join-direction effects (many-to-one only, as declared; no customer to
orders path, so never-ordered customers are invisible).

Cube: 51 of 60 misses are `fixable_in_model: yes`. MetricFlow: 14 of 64.

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
| B51 | operations / hard | expressivity | no | Needs distinct supplier count, a revenue ranking with a running sum and an 80% cut-off. mf query has no window/cumulative over a ranked list, no count distinct at query time and no arithmetic. |
| B52 | operations / hard | expressivity | no | line_count by ship_mode for 1997 shipments runs, but median and p90 of a per-line date difference (receipt_date - ship_date) are percentiles of an undeclared expression; mf query only requests declared metrics. |
| B53 | operations / hard | expressivity | no | Perfect orders need a per-order test that no line is late (nested aggregation: late lines per order, then count orders with zero) and a share; mf query aggregates once and has no arithmetic. |
| B54 | operations / medium | expressivity | no | Averages of date differences across lineitem and orders (commit_date - order_date, receipt_date - order_date) are not declared metrics and cannot be computed at query time; the gap is arithmetic. |
| B55 | operations / hard | expressivity | yes | late_share is a filtered-count ratio and the rolling 3-month share needs a window over months; mf query has one where clause, no arithmetic and no query-time cumulative/window metrics. |
| B56 | operations / medium | expressivity | no | returned_share is a filtered-count ratio and return_rate_index divides it by the period-wide share (a total across groups); not expressible. |
| B57 | operations / hard | expressivity | no | Per-supplier late shares compared with a regional late share, a >= 50 lines threshold and counts of outlier suppliers: nested aggregation plus arithmetic. supplier_region_name is also 3 hops from lineitem. |
| B58 | operations / hard | expressivity | no | Ship span per order (max - min ship_date), a >= 2 lines filter and percentiles of the span over orders: nested aggregation of an undeclared expression; not expressible. |
| B59 | finance / hard | expressivity | yes | revenue and total_quantity per manufacturer and year are expressible, but two years side by side, unit prices and the volume/price effects are arithmetic between metrics. |
| B60 | finance / hard | expressivity | no | Customer margin rate needs sum(supply_cost * quantity) across lineitem and partsupp (no declared metric, measures cannot use joined columns), a per-customer distinct-order threshold and percentiles over customers. |
| B61 | finance / hard | expressivity | yes | Year-to-date revenue for 1998 and 1997 side by side needs a grain-to-date cumulative metric and a one-year offset, plus a ratio. None exist at query time; metric_time for revenue is ship_date, not order_date. |
| B62 | finance / hard | expressivity | no | Customer margin needs sum(supply_cost * quantity) (not declared, not computable), then a ranking with a running share of total; not expressible. |
| B63 | finance / hard | expressivity | yes | Trailing twelve-month revenue and the same window a year earlier need a 12-month cumulative window and an offset on order_date, plus a ratio; not available at query time. |
| B64 | finance / hard | topology | no | customer_region_name is 3 hops from orders (orders -> customer -> customer_nation -> customer_region), beyond the 2-hop limit; the company-wide percentile threshold and the large-order share are also not expressible. |
| B65 | finance / hard | expressivity | no | actual_cost (supply_cost * quantity) and cheapest_cost (per-part min supply_cost across offers * quantity) are aggregations of expressions over a joined dataset and a nested aggregation; no declared metric covers them. |
| B66 | finance / medium | expressivity | no | avg_discount and revenue by order_priority for 1997 run, but margin_rate needs sum(supply_cost * quantity), which is not a declared metric and cannot be computed at query time. |
| B67 | finance / hard | expressivity | no | Deciles of orders by total_price (NTILE) and shares of total order value: a ranking-derived dimension, a total across groups and arithmetic; not expressible. |
| B68 | marketing / hard | expressivity | no | Cohort by first-order year is a dimension derived from min(order_date) per customer (multi-stage), plus an index over the cohort's first year; mf query cannot group by a metric and has no arithmetic. |
| B69 | marketing / hard | expressivity | no | Days to second order needs per-customer order positions (row_number) and percentiles; not expressible. |
| B70 | marketing / hard | expressivity | no | Manufacturer pair co-occurrence per order is a self-join of lineitem through orders, and lift needs ratios over N; not expressible in mf query. |
| B71 | marketing / hard | expressivity | no | Lapsed and reactivated customers need per-customer existence tests across years (anti-join) and distinct customer counts; customer_count was dropped in translation and metric filters do not inherit the outer where nor take a date filter. |
| B72 | marketing / medium | expressivity | no | First order per customer (earliest order_date, ties by key) is a row-number-derived dimension; averages of first versus later orders and their ratio are not expressible. |
| B73 | marketing / hard | expressivity | no | Revenue quartiles per year (NTILE) for customers active in both years, cross-tabulated with zero-filled cells: multi-stage ranking and existence tests; not expressible. |
| B74 | marketing / medium | topology | no | Customers on file with no orders need customer_count (dropped in translation: customer has no aggregation time dimension) and an anti-join; avg account_balance is not a declared metric either. |
| B75 | marketing / hard | expressivity | no | Bucketing customers by number of distinct brands bought is a dimension derived from a per-customer count distinct (multi-stage), then customer counts, averages and shares; not expressible. |

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
| B51 | operations / hard | expressivity | no | Pareto count needs a running sum of revenue over suppliers ranked by revenue, compared with 80% of the total, then counted. Windows and an aggregate over a ranked sub-result; REST aggregates once. |
| B52 | operations / hard | expressivity | yes | Percentiles of a row-level date difference (receipt_date - ship_date). No percentile measure and no ad-hoc aggregate of dimensions at query time. line_count by ship_mode alone is one REST query. |
| B53 | operations / hard | expressivity | yes | A perfect order is a per-order flag derived from its lines (no line with receipt_date > commit_date, a member-vs-member condition), then averaged per year and priority: aggregate of an aggregate plus a ratio. order_count by year and priority alone is one REST query. |
| B54 | operations / medium | expressivity | yes | Averages of row-level date differences across lineitem and orders (commit_date - order_date, receipt_date - order_date) and their difference; no such measures, no ad-hoc aggregates, no calculated measures. |
| B55 | operations / hard | expressivity | yes | Monthly late_share (member-vs-member conditional count / count) and a 3-month rolling ratio; no conditional measure, no calculated measure, no query-time rolling window. |
| B56 | operations / medium | expressivity | yes | returned_share needs a filtered count (return_flag 'R') beside the unfiltered count and a ratio, and return_rate_index needs the period-wide share on every row. line_count per ship_mode x ship_instruct is one plain CubeScan, the shares are not. |
| B57 | operations / hard | expressivity | no | Per-supplier late shares (conditional ratio), compared with the region's late share, filtered on line counts and counted per region: multi-stage aggregation with a member-vs-member condition. |
| B58 | operations / hard | expressivity | yes | Per-order ship span (MAX - MIN of ship_date over the order's lines), filtered to multi-line orders, then percentiles per priority; aggregate of an aggregate plus percentiles. |
| B59 | finance / hard | expressivity | yes | Revenue and quantity per manufacturer and year come from one REST query, but the 1996 and 1997 values must sit side by side and be combined (change, volume and price effects): per-measure year filters and calculated measures, neither available at query time. |
| B60 | finance / hard | expressivity | yes | Per-customer margin rate needs SUM(supply_cost * quantity) across lineitem and partsupp dimensions (no cost measure), a HAVING on distinct orders, then percentiles of the per-customer rate per segment: ad-hoc aggregate, ratio and aggregate of an aggregate. |
| B61 | finance / hard | expressivity | yes | Year-to-date running sums per month for 1998 and 1997 side by side and their ratio; no query-time rolling/to-date window, time shift or calculated measure. |
| B62 | finance / hard | expressivity | yes | Per-customer margin (needs SUM(supply_cost * quantity), no cost measure), margin_rate ratio, rank and running share of total margin; ad-hoc aggregate, calculated measure and windows. |
| B63 | finance / hard | expressivity | yes | Trailing-twelve-month revenue per month, the same window a year earlier, and growth; no query-time rolling window or time shift. |
| B64 | finance / hard | expressivity | no | A company-wide percentile threshold on total_price, repeated per region, then a conditional count and value share relative to it. No percentile measure and no filter that references an aggregate. order_value per region alone is one REST query. |
| B65 | finance / hard | expressivity | yes | actual_cost is SUM(supply_cost * quantity) over cross-cube dimensions, and cheapest_cost needs the per-part minimum supply_cost over all offers (an aggregate turned into a row value). Ad-hoc aggregates and subquery dimensions are not available at query time. |
| B66 | finance / medium | expressivity | yes | avg_discount and revenue per order_priority for 1997 are one REST query, but margin_rate needs SUM(supply_cost * quantity) (no cost measure; cross-cube dimensions) and a ratio. |
| B67 | finance / hard | expressivity | no | NTILE(10) deciles of orders by total_price, then per-decile aggregates and shares; needs a window-derived dimension and re-aggregation. |
| B68 | marketing / hard | expressivity | yes | Cohort by first-order year is a dimension derived from a per-customer MIN(order_date), and revenue_index divides by the cohort's first-year revenue; no subquery dimensions, no calculated measures. |
| B69 | marketing / hard | expressivity | no | Days between a customer's first and second order need order positions per customer (ROW_NUMBER), a self-join and percentiles; not expressible at query time. |
| B70 | marketing / hard | expressivity | no | Manufacturer pair co-occurrence needs a per-order distinct manufacturer set, a self-join of it, and lift ratios; Cube queries have no self-join and no aggregate over sub-results. |
| B71 | marketing / hard | expressivity | yes | Lapsed and reactivated customers need per-customer existence flags across three periods (anti-join and semi-join), then counts per segment and a ratio. |
| B72 | marketing / medium | expressivity | yes | First order per customer (ROW_NUMBER by date, key), then conditional averages of total_price on first vs other orders and their ratio; no window, no conditional measure, no calculated measure. |
| B73 | marketing / hard | expressivity | no | Two NTILE(4) assignments per customer (one per year, on per-year revenue), restricted to customers active in both years, cross-tabulated with zero cells; windows over sub-results and a dense grid. |
| B74 | marketing / medium | topology | yes | Never-ordered customers need an existence test from customer to orders (no join in that direction; orders -> customer only) and conditional averages of account_balance, a dimension with no avg measure. |
| B75 | marketing / hard | expressivity | yes | Per-customer distinct brand count (an aggregate) bucketed into a dimension, then counts, averages and revenue shares per bucket; aggregate of an aggregate plus ratios. |

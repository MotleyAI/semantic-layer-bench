# Model contract (OSSIE baseline vocabulary)

The OSSIE model (step 2) exposes exactly these names. Questions only use this vocabulary.

## Datasets and relationships

| Dataset | Source | Primary key |
|---|---|---|
| `lineitem` | `lineitem` | `l_orderkey, l_linenumber` |
| `orders` | `orders` | `o_orderkey` |
| `customer` | `customer` | `c_custkey` |
| `customer_nation` | `nation` | `n_nationkey` |
| `customer_region` | `region` | `r_regionkey` |
| `supplier` | `supplier` | `s_suppkey` |
| `supplier_nation` | `nation` | `n_nationkey` |
| `supplier_region` | `region` | `r_regionkey` |
| `part` | `part` | `p_partkey` |
| `partsupp` | `partsupp` | `ps_partkey, ps_suppkey` |

Nation and region are declared twice (customer side and supplier side). This is the usual way to
model a role-playing dimension in Cube, LookML and Snowflake semantic views, so the benchmark tests
query expressivity and not one tool's handling of role-playing joins.

Relationships (many-to-one, `from` → `to`):

- `lineitem` → `orders` (`l_orderkey` = `o_orderkey`)
- `lineitem` → `part` (`l_partkey` = `p_partkey`)
- `lineitem` → `supplier` (`l_suppkey` = `s_suppkey`)
- `lineitem` → `partsupp` (`l_partkey, l_suppkey` = `ps_partkey, ps_suppkey`), composite key
- `orders` → `customer` (`o_custkey` = `c_custkey`)
- `customer` → `customer_nation` → `customer_region`
- `supplier` → `supplier_nation` → `supplier_region`
- `partsupp` → `part`, `partsupp` → `supplier`

## Dimensions

| Dataset | Dimensions |
|---|---|
| lineitem | `ship_date` (time), `commit_date` (time), `receipt_date` (time), `ship_mode`, `return_flag`, `line_status`, `ship_instruct`, `quantity`, `discount`, `extended_price` |
| orders | `order_date` (time), `order_status`, `order_priority`, `clerk`, `total_price`, `order_key`, `customer_key` |
| customer | `customer_name`, `market_segment`, `account_balance`, `customer_key` |
| customer_nation / customer_region | `customer_nation_name` / `customer_region_name` |
| supplier | `supplier_name`, `supplier_key` |
| supplier_nation / supplier_region | `supplier_nation_name` / `supplier_region_name` |
| part | `part_name`, `brand`, `part_type`, `container`, `size`, `manufacturer` |
| partsupp | `available_qty`, `supply_cost` |

## Metrics (OSSIE `metrics[]`, plain SQL aggregations)

| Metric | Expression |
|---|---|
| `revenue` | `SUM(lineitem.l_extendedprice * (1 - lineitem.l_discount))` |
| `gross_sales` | `SUM(lineitem.l_extendedprice)` |
| `total_quantity` | `SUM(lineitem.l_quantity)` |
| `line_count` | `COUNT(lineitem.l_orderkey)` |
| `avg_discount` | `AVG(lineitem.l_discount)` |
| `order_count` | `COUNT(orders.o_orderkey)` |
| `order_value` | `SUM(orders.o_totalprice)` |
| `avg_order_value` | `SUM(orders.o_totalprice) / COUNT(orders.o_orderkey)` |
| `customer_count` | `COUNT(DISTINCT customer.c_custkey)` |
| `total_available_qty` | `SUM(partsupp.ps_availqty)` |
| `supplier_count` | `COUNT(DISTINCT supplier.s_suppkey)` |

Nothing else. Any other calculation in a question (shares, changes, running totals, conditional
measures, ratios between metrics) must be expressed at query time.

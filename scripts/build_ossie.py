"""Generate model/tpch.ossie.yaml, the shared OSSIE baseline (see model_contract.md)."""
from pathlib import Path

import yaml

DB = "tpch.main"  # DuckDB catalog.schema; warehouse targets override via their profile


def expr(sql):
    return {"dialects": [{"dialect": "ANSI_SQL", "expression": sql}]}


def field(name, column, datatype, desc=None, time=False):
    f = {"name": name, "expression": expr(column), "datatype": datatype}
    f["dimension"] = {"is_time": time}
    if desc:
        f["description"] = desc
    return f


def dataset(name, table, pk, fields, desc):
    return {"name": name, "source": f"{DB}.{table}", "primary_key": pk,
            "description": desc, "fields": fields}


def nation(prefix):
    return dataset(f"{prefix}_nation", "nation", ["n_nationkey"], [
        field(f"{prefix}_nation_name", "n_name", "String", f"Nation of the {prefix}"),
    ], f"Nation, in its role as the {prefix}'s nation")


def region(prefix):
    return dataset(f"{prefix}_region", "region", ["r_regionkey"], [
        field(f"{prefix}_region_name", "r_name", "String", f"Region of the {prefix}"),
    ], f"Region, in its role as the {prefix}'s region")


datasets = [
    dataset("lineitem", "lineitem", ["l_orderkey", "l_linenumber"], [
        field("ship_date", "l_shipdate", "Date", "Date the line item shipped", time=True),
        field("commit_date", "l_commitdate", "Date", "Committed delivery date", time=True),
        field("receipt_date", "l_receiptdate", "Date", "Date the customer received the item", time=True),
        field("ship_mode", "l_shipmode", "String", "Shipping mode (AIR, MAIL, SHIP, TRUCK, RAIL, REG AIR, FOB)"),
        field("return_flag", "l_returnflag", "String", "R = returned, A = accepted, N = not yet known"),
        field("line_status", "l_linestatus", "String", "O = open, F = fulfilled"),
        field("ship_instruct", "l_shipinstruct", "String"),
        field("quantity", "l_quantity", "Decimal"),
        field("discount", "l_discount", "Decimal", "Discount as a fraction (0.05 = 5%)"),
        field("extended_price", "l_extendedprice", "Decimal", "Price before discount"),
    ], "One row per order line; the sales fact"),
    dataset("orders", "orders", ["o_orderkey"], [
        field("order_date", "o_orderdate", "Date", "Date the order was placed", time=True),
        field("order_status", "o_orderstatus", "String", "F = fulfilled, O = open, P = partial"),
        field("order_priority", "o_orderpriority", "String", "1-URGENT .. 5-LOW"),
        field("clerk", "o_clerk", "String"),
        field("total_price", "o_totalprice", "Decimal", "Order total as recorded on the order"),
        field("order_key", "o_orderkey", "Integer"),
        field("customer_key", "o_custkey", "Integer"),
    ], "One row per order"),
    dataset("customer", "customer", ["c_custkey"], [
        field("customer_name", "c_name", "String"),
        field("market_segment", "c_mktsegment", "String"),
        field("account_balance", "c_acctbal", "Decimal"),
        field("customer_key", "c_custkey", "Integer"),
    ], "One row per customer"),
    nation("customer"),
    region("customer"),
    dataset("supplier", "supplier", ["s_suppkey"], [
        field("supplier_name", "s_name", "String"),
        field("supplier_key", "s_suppkey", "Integer"),
    ], "One row per supplier"),
    nation("supplier"),
    region("supplier"),
    dataset("part", "part", ["p_partkey"], [
        field("part_name", "p_name", "String"),
        field("brand", "p_brand", "String"),
        field("part_type", "p_type", "String"),
        field("container", "p_container", "String"),
        field("size", "p_size", "Integer"),
        field("manufacturer", "p_mfgr", "String"),
    ], "One row per part"),
    dataset("partsupp", "partsupp", ["ps_partkey", "ps_suppkey"], [
        field("available_qty", "ps_availqty", "Integer"),
        field("supply_cost", "ps_supplycost", "Decimal", "Cost of one unit from this supplier"),
    ], "One row per (part, supplier) offer; a second fact"),
]


def rel(frm, to, fc, tc):
    return {"name": f"{frm}_to_{to}", "from": frm, "to": to,
            "from_columns": fc, "to_columns": tc}


relationships = [
    rel("lineitem", "orders", ["l_orderkey"], ["o_orderkey"]),
    rel("lineitem", "part", ["l_partkey"], ["p_partkey"]),
    rel("lineitem", "supplier", ["l_suppkey"], ["s_suppkey"]),
    rel("lineitem", "partsupp", ["l_partkey", "l_suppkey"], ["ps_partkey", "ps_suppkey"]),
    rel("orders", "customer", ["o_custkey"], ["c_custkey"]),
    rel("customer", "customer_nation", ["c_nationkey"], ["n_nationkey"]),
    rel("customer_nation", "customer_region", ["n_regionkey"], ["r_regionkey"]),
    rel("supplier", "supplier_nation", ["s_nationkey"], ["n_nationkey"]),
    rel("supplier_nation", "supplier_region", ["n_regionkey"], ["r_regionkey"]),
    rel("partsupp", "part", ["ps_partkey"], ["p_partkey"]),
    rel("partsupp", "supplier", ["ps_suppkey"], ["s_suppkey"]),
]


def metric(name, sql, desc):
    return {"name": name, "expression": expr(sql), "description": desc}


metrics = [
    metric("revenue", "SUM(lineitem.l_extendedprice * (1 - lineitem.l_discount))", "Net revenue after discount"),
    metric("gross_sales", "SUM(lineitem.l_extendedprice)", "Revenue before discount"),
    metric("total_quantity", "SUM(lineitem.l_quantity)", "Units sold"),
    metric("line_count", "COUNT(lineitem.l_orderkey)", "Number of order lines"),
    metric("avg_discount", "AVG(lineitem.l_discount)", "Average line discount"),
    metric("order_count", "COUNT(orders.o_orderkey)", "Number of orders"),
    metric("order_value", "SUM(orders.o_totalprice)", "Sum of order total price"),
    metric("avg_order_value", "SUM(orders.o_totalprice) / COUNT(orders.o_orderkey)", "Order value per order"),
    metric("customer_count", "COUNT(DISTINCT customer.c_custkey)", "Distinct customers"),
    metric("total_available_qty", "SUM(partsupp.ps_availqty)", "Supply quantity available"),
    metric("supplier_count", "COUNT(DISTINCT supplier.s_suppkey)", "Distinct suppliers"),
]

model = {
    "version": "0.2.0.dev0",
    "semantic_model": [{
        "name": "tpch",
        "description": "TPC-H sales: line items, orders, customers, suppliers, parts and supply offers",
        "datasets": datasets,
        "relationships": relationships,
        "metrics": metrics,
    }],
}

out = Path(__file__).resolve().parent.parent / "model" / "tpch.ossie.yaml"
out.parent.mkdir(exist_ok=True)
out.write_text("# Generated by scripts/build_ossie.py. Shared OSSIE baseline for every layer.\n"
               + yaml.safe_dump(model, sort_keys=False, width=120))
print("wrote", out)

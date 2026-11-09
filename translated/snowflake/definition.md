# TPCH

This is a Snowflake **semantic view** — use this to understand the intended way to query and aggregate data.

## Definition

```sql
create or replace semantic view SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.TPCH
	tables (
		LINEITEM as tpch.main.lineitem primary key (L_ORDERKEY,L_LINENUMBER) comment='One row per order line; the sales fact',
		ORDERS as tpch.main.orders primary key (O_ORDERKEY) comment='One row per order',
		CUSTOMER as tpch.main.customer primary key (C_CUSTKEY) comment='One row per customer',
		CUSTOMER_NATION as tpch.main.nation primary key (N_NATIONKEY) comment='Nation, in its role as the customer''s nation',
		CUSTOMER_REGION as tpch.main.region primary key (R_REGIONKEY) comment='Region, in its role as the customer''s region',
		SUPPLIER as tpch.main.supplier primary key (S_SUPPKEY) comment='One row per supplier',
		SUPPLIER_NATION as tpch.main.nation primary key (N_NATIONKEY) comment='Nation, in its role as the supplier''s nation',
		SUPPLIER_REGION as tpch.main.region primary key (R_REGIONKEY) comment='Region, in its role as the supplier''s region',
		PART as tpch.main.part primary key (P_PARTKEY) comment='One row per part',
		PARTSUPP as tpch.main.partsupp primary key (PS_PARTKEY,PS_SUPPKEY) comment='One row per (part, supplier) offer; a second fact'
	)
	relationships (
		LINEITEM_TO_ORDERS as LINEITEM(L_ORDERKEY) references ORDERS(O_ORDERKEY),
		LINEITEM_TO_PART as LINEITEM(L_PARTKEY) references PART(P_PARTKEY),
		LINEITEM_TO_SUPPLIER as LINEITEM(L_SUPPKEY) references SUPPLIER(S_SUPPKEY),
		LINEITEM_TO_PARTSUPP as LINEITEM(L_PARTKEY,L_SUPPKEY) references PARTSUPP(PS_PARTKEY,PS_SUPPKEY),
		ORDERS_TO_CUSTOMER as ORDERS(O_CUSTKEY) references CUSTOMER(C_CUSTKEY),
		CUSTOMER_TO_CUSTOMER_NATION as CUSTOMER(C_NATIONKEY) references CUSTOMER_NATION(N_NATIONKEY),
		CUSTOMER_NATION_TO_CUSTOMER_REGION as CUSTOMER_NATION(N_REGIONKEY) references CUSTOMER_REGION(R_REGIONKEY),
		SUPPLIER_TO_SUPPLIER_NATION as SUPPLIER(S_NATIONKEY) references SUPPLIER_NATION(N_NATIONKEY),
		SUPPLIER_NATION_TO_SUPPLIER_REGION as SUPPLIER_NATION(N_REGIONKEY) references SUPPLIER_REGION(R_REGIONKEY),
		PARTSUPP_TO_PART as PARTSUPP(PS_PARTKEY) references PART(P_PARTKEY),
		PARTSUPP_TO_SUPPLIER as PARTSUPP(PS_SUPPKEY) references SUPPLIER(S_SUPPKEY)
	)
	dimensions (
		LINEITEM.SHIP_MODE as lineitem.L_SHIPMODE comment='Shipping mode (AIR, MAIL, SHIP, TRUCK, RAIL, REG AIR, FOB)',
		LINEITEM.RETURN_FLAG as lineitem.L_RETURNFLAG comment='R = returned, A = accepted, N = not yet known',
		LINEITEM.LINE_STATUS as lineitem.L_LINESTATUS comment='O = open, F = fulfilled',
		LINEITEM.SHIP_INSTRUCT as lineitem.L_SHIPINSTRUCT,
		LINEITEM.QUANTITY as lineitem.L_QUANTITY,
		LINEITEM.DISCOUNT as lineitem.L_DISCOUNT comment='Discount as a fraction (0.05 = 5%)',
		LINEITEM.EXTENDED_PRICE as lineitem.L_EXTENDEDPRICE comment='Price before discount',
		LINEITEM.SHIP_DATE as lineitem.L_SHIPDATE comment='Date the line item shipped',
		LINEITEM.COMMIT_DATE as lineitem.L_COMMITDATE comment='Committed delivery date',
		LINEITEM.RECEIPT_DATE as lineitem.L_RECEIPTDATE comment='Date the customer received the item',
		ORDERS.ORDER_STATUS as orders.O_ORDERSTATUS comment='F = fulfilled, O = open, P = partial',
		ORDERS.ORDER_PRIORITY as orders.O_ORDERPRIORITY comment='1-URGENT .. 5-LOW',
		ORDERS.CLERK as orders.O_CLERK,
		ORDERS.TOTAL_PRICE as orders.O_TOTALPRICE comment='Order total as recorded on the order',
		ORDERS.ORDER_KEY as orders.O_ORDERKEY,
		ORDERS.CUSTOMER_KEY as orders.O_CUSTKEY,
		ORDERS.ORDER_DATE as orders.O_ORDERDATE comment='Date the order was placed',
		CUSTOMER.CUSTOMER_NAME as customer.C_NAME,
		CUSTOMER.MARKET_SEGMENT as customer.C_MKTSEGMENT,
		CUSTOMER.ACCOUNT_BALANCE as customer.C_ACCTBAL,
		CUSTOMER.CUSTOMER_KEY as customer.C_CUSTKEY,
		CUSTOMER_NATION.CUSTOMER_NATION_NAME as customer_nation.N_NAME comment='Nation of the customer',
		CUSTOMER_REGION.CUSTOMER_REGION_NAME as customer_region.R_NAME comment='Region of the customer',
		SUPPLIER.SUPPLIER_NAME as supplier.S_NAME,
		SUPPLIER.SUPPLIER_KEY as supplier.S_SUPPKEY,
		SUPPLIER_NATION.SUPPLIER_NATION_NAME as supplier_nation.N_NAME comment='Nation of the supplier',
		SUPPLIER_REGION.SUPPLIER_REGION_NAME as supplier_region.R_NAME comment='Region of the supplier',
		PART.PART_NAME as part.P_NAME,
		PART.BRAND as part.P_BRAND,
		PART.PART_TYPE as part.P_TYPE,
		PART.CONTAINER as part.P_CONTAINER,
		PART.SIZE as part.P_SIZE,
		PART.MANUFACTURER as part.P_MFGR,
		PARTSUPP.AVAILABLE_QTY as partsupp.PS_AVAILQTY,
		PARTSUPP.SUPPLY_COST as partsupp.PS_SUPPLYCOST comment='Cost of one unit from this supplier'
	)
	metrics (
		LINEITEM.REVENUE as SUM(LINEITEM.L_EXTENDEDPRICE *(1 - LINEITEM.L_DISCOUNT)) comment='Net revenue after discount',
		LINEITEM.GROSS_SALES as SUM(LINEITEM.L_EXTENDEDPRICE) comment='Revenue before discount',
		LINEITEM.TOTAL_QUANTITY as SUM(LINEITEM.L_QUANTITY) comment='Units sold',
		LINEITEM.LINE_COUNT as COUNT(LINEITEM.L_ORDERKEY) comment='Number of order lines',
		LINEITEM.AVG_DISCOUNT as AVG(LINEITEM.L_DISCOUNT) comment='Average line discount',
		ORDERS.ORDER_COUNT as COUNT(ORDERS.O_ORDERKEY) comment='Number of orders',
		ORDERS.ORDER_VALUE as SUM(ORDERS.O_TOTALPRICE) comment='Sum of order total price',
		ORDERS.AVG_ORDER_VALUE as ORDERS.ORDER_VALUE / ORDERS.ORDER_COUNT comment='Order value per order',
		CUSTOMER.CUSTOMER_COUNT as COUNT(DISTINCT CUSTOMER.C_CUSTKEY) comment='Distinct customers',
		SUPPLIER.SUPPLIER_COUNT as COUNT(DISTINCT SUPPLIER.S_SUPPKEY) comment='Distinct suppliers',
		PARTSUPP.TOTAL_AVAILABLE_QTY as SUM(PARTSUPP.PS_AVAILQTY) comment='Supply quantity available'
	)
;
```

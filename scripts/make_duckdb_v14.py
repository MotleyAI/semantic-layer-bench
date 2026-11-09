"""Copy data/tpch.duckdb into a DuckDB storage-v1.4 file for Cube.

Cube 1.6.76 bundles the Node `duckdb` 1.4.4 package, which cannot open a file
written by DuckDB 2.x. The copy lives outside the iCloud-synced project folder.
Same tables, same rows; only the on-disk format differs.
"""
import os
from pathlib import Path

import duckdb

src = Path(__file__).resolve().parent.parent / "data" / "tpch.duckdb"
dst = Path(os.path.expanduser("~/Library/Caches/sl-bench/tpch.duckdb"))
dst.parent.mkdir(parents=True, exist_ok=True)
dst.unlink(missing_ok=True)
c = duckdb.connect()
c.execute(f"ATTACH '{src}' AS src (READ_ONLY)")
c.execute(f"ATTACH '{dst}' AS tpch (STORAGE_VERSION 'v1.4.0')")
tables = c.execute("select table_name from information_schema.tables "
                   "where table_catalog='src' and table_schema='main'").fetchall()
for (t,) in tables:
    c.execute(f"CREATE TABLE tpch.main.{t} AS SELECT * FROM src.main.{t}")
    a = c.execute(f"select count(*) from src.main.{t}").fetchone()[0]
    b = c.execute(f"select count(*) from tpch.main.{t}").fetchone()[0]
    assert a == b, t
print("wrote", dst, len(tables), "tables")

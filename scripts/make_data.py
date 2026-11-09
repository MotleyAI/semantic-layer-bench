"""Generate TPC-H SF1 into data/tpch.duckdb."""
from pathlib import Path

import duckdb

out = Path(__file__).resolve().parent.parent / "data" / "tpch.duckdb"
out.parent.mkdir(exist_ok=True)
con = duckdb.connect(str(out))
con.execute("INSTALL tpch; LOAD tpch; CALL dbgen(sf=1)")
print("wrote", out)

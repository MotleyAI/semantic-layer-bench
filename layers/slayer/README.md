# SLayer layer

Built with SLayer's own OSSIE importer (SLayer 1.7.0):

```bash
export SLAYER_STORAGE=$PWD/layers/slayer/storage
slayer datasources create "duckdb:///$PWD/data/tpch.duckdb" --name tpch -y
slayer import-osi model/tpch.ossie.yaml --datasource tpch   # 10 models, 0 unconverted, 0 dropped
```

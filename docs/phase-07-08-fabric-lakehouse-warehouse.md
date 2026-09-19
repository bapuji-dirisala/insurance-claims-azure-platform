# Phases 7 + 8 — Microsoft Fabric Lakehouse + Warehouse + Direct Lake

The Databricks medallion (Phases 4+5+6) writes Delta to ADLS Gen2.
Phases 7+8 give the same data **two serving surfaces** inside Fabric
without copying any files:

```
                        ADLS Gen2
                 bronze/ silver/ gold/
                        │
         ┌──────────────┼──────────────────┐
         ▼              ▼                  ▼
Fabric Lakehouse  Fabric Warehouse   (unchanged Databricks consumers)
 OneLake shortcuts  OPENROWSET BULK  'DELTA'
         │              │
         ▼              ▼
   Direct Lake      Import model
   (Power BI)       (Power BI, T-SQL)
```

## Phase 7 — Lakehouse + OneLake shortcuts

OneLake shortcuts are the Fabric equivalent of symbolic links: they
project an ADLS folder into the Lakehouse `Files/` tree **without
copying**. That's the whole point — Direct Lake later reads a
`Tables/` entry inside the Lakehouse, but the Lakehouse itself only
holds pointers into the medallion.

Files:

- `fabric/notebooks/01_shortcut_adls_bronze.py` — creates one shortcut
  per medallion layer. Uses `notebookutils.lakehouse.create_shortcut`
  in Fabric; falls through to `print()` on a laptop so the notebook
  stays runnable + unit-testable (parseable Python with `# MAGIC`
  markers).
- `fabric/notebooks/02_silver_to_gold_lakehouse.py` — reads silver via
  the shortcut, rebuilds `monthly_loss_ratio` as a real Lakehouse
  Delta table (Direct Lake can only target Lakehouse Tables, not
  shortcut-mounted files).

Local mirror: `src/claims_azure/fabric/lakehouse_mirror.py` →
`rebuild_gold_loss_ratio()` runs the same aggregation in DuckDB
against the Phase 4+5+6 silver output so CI validates the shape.

## Phase 8 — Warehouse (T-SQL + Import mode)

The Lakehouse feeds Direct Lake. The Warehouse feeds **everyone who
needs T-SQL** — ad-hoc analysts, legacy SSRS reports, data engineers
who want stored procedures. Both read the same Delta underneath via
different engines:

- Direct Lake: Vertipaq-free Power BI engine, zero-copy.
- Warehouse: SQL Server–compatible T-SQL via `OPENROWSET(... FORMAT='DELTA')`.

Files:

- `fabric/warehouse/01_warehouse_ddl.sql` — curated star:
  - `dim.date`, `dim.policy` (SCD2 snapshot with `is_current` flag)
  - `fact.claims_monthly` (claim rollups)
  - `mart.loss_ratio` (business mart surfaced to Power BI Import model)
- `fabric/warehouse/02_warehouse_loads.sql` — daily `TRUNCATE +
  INSERT INTO SELECT` against ADLS via `OPENROWSET BULK ... FORMAT =
  'DELTA'`. One query, no linked-server glue needed in Fabric.

Local mirror: `src/claims_azure/fabric/warehouse_mirror.py` →
`load_mart_loss_ratio()` produces the exact `mart.loss_ratio` row
shape in Parquet so Power BI (Phase 11) can be developed offline.

## Why both?

| Surface            | Engine         | Use case                            |
|--------------------|----------------|-------------------------------------|
| Databricks silver  | Delta on ADLS  | Data engineering, ML training       |
| Fabric Lakehouse   | Direct Lake    | Power BI dashboards (low latency)   |
| Fabric Warehouse   | T-SQL / Import | Analysts, legacy BI, stored procs   |

All three point at the **same bytes** on ADLS. The medallion is the
contract; Fabric is one consumer among several.

## Deploy

```bash
# One-off: create workspace + Lakehouse + Warehouse in Fabric UI.
# Then:

python -m claims_azure fabric-lakehouse-mirror \
    --silver-fact 'silver/fact_claim/**/*.parquet' \
    --premiums 'bronze/premiums/**/*.parquet' \
    --gold ./gold_fabric_mirror

# In Fabric: open 01_shortcut_adls_bronze.py, patch WORKSPACE_ID, run all cells.
# Then open 02_silver_to_gold_lakehouse.py and run all cells to create the
# Delta table backing Direct Lake.
#
# In Fabric Warehouse Query Editor: run 01_warehouse_ddl.sql once,
# then schedule 02_warehouse_loads.sql daily via Fabric Data Factory.
```

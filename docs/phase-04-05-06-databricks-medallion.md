# Phases 4 + 5 + 6 — Databricks medallion + Unity Catalog + DAB bundle

**Status:** Shipped. Three Databricks notebooks (bronze → silver SCD2 +
silver claim fact + gold loss ratio), full Unity Catalog bootstrap
(catalogs + schemas + grants + row filter + column mask + tags), and a
Databricks Asset Bundle definition that promotes dev → staging → prod.

## The medallion

```
bronze/                          silver/                             gold/
├── policies (parquet)           ├── dim_policy_scd2 (Delta SCD2)    ├── fact_loss_ratio_monthly
├── endorsements (parquet)   ─▶  ├── fact_claim      (Delta fact)─▶     (period × LOB
├── claims (parquet)                                                     loss ratio
├── payments (parquet)                                                   combined ratio)
└── premiums (parquet)
```

- **01 bronze → silver policies SCD2** — `dim_policy_scd2` is a classic
  slowly-changing-type-2 dimension: for each policy, every endorsement
  starts a new row with its own `valid_from`; the previous row's
  `valid_to` is sealed via `LEAD()`. The current row carries `valid_to
  = 9999-12-31` and `is_current = true`.
- **02 bronze → silver claims fact** — joins claims onto `is_current`
  policy context, aggregates payments to one row per claim, computes
  `report_lag_days`.
- **03 silver → gold loss ratio monthly** — rolls up fact + premiums
  into monthly LOB-level loss ratio + combined ratio. Headline P&C
  metrics for actuarial dashboards.

## Unity Catalog bootstrap

```
databricks/unity-catalog/
├── 01_catalogs_schemas.sql   # 3 catalogs (bronze/silver/gold) + managed locations
├── 02_grants.sql             # Minimum-privilege grants per principal
└── 03_row_filters_tags.sql   # Row filter + column mask + governance tags
```

Row filter: actuaries only see the lines of business they cover
(driven by a lookup table + `current_user()`).

Column mask: `party_id` is masked to `***MASKED***` for anyone outside
the engineers + actuaries groups — the base pattern Fortune-500
insurance IT puts on PII fields.

## DAB bundle

```
databricks/bundles/databricks.yml
```

Three targets (`dev` / `staging` / `prod`) differ by catalog prefix,
cluster size, and schedule. One `databricks bundle deploy --target
<env>` ships the job; Azure DevOps Pipelines invoke it per branch.

```bash
databricks bundle deploy --target dev
databricks bundle run claims_medallion --target dev
```

The bundle wires three notebook tasks with a DAG:

```
bronze_to_silver_policies_scd2
          │
          ▼
bronze_to_silver_claims_fact
          │
          ▼
silver_to_gold_loss_ratio
```

## Design decisions

1. **SCD2 via `LEAD()`, not CDC**. CDC would require Delta Change Data
   Feed on the source + a streaming job. For a policy book that changes
   endorsements daily (not sub-second), batch SCD2 with the standard
   window pattern is simpler + cheaper + easier to reason about.
2. **Row filter in Unity, not in the notebook**. Keeping access logic
   in the catalog means a notebook author can't accidentally bypass it.
3. **Column mask on PII, not row filter**. Masking leaves counts
   accurate for actuarial math while hiding identifiers.
4. **Governance tags live on catalogs**, not individual tables, so
   Microsoft Purview picks them up without needing per-table policy.
5. **DAB targets ≠ Databricks workspaces**. One bundle, three target
   environments; the workspace host is set by the CI pipeline per
   branch (dev → shared dev workspace; prod → prod workspace).
6. **`SINGLE_USER` data security mode** on job clusters — the only
   mode that supports Unity Catalog with user-assigned MI.
7. **Change Data Feed enabled by default** in the DAB cluster conf so
   downstream Fabric mirror (Phase 7) can consume incremental changes.

## Local demo (DuckDB mirrors)

The DuckDB equivalents under `src/claims_azure/transform/` run the same
transformations without any Databricks workspace:

```bash
pip install -e ".[dev,generator]"

# 1. generate bronze (Phase 2)
claims-azure generate all --out data/bronze

# 2. Run the three transformations
python -c "
from claims_azure.transform import (
    bronze_to_silver_policies_scd2,
    bronze_to_silver_claims_fact,
    gold_loss_ratio_monthly,
)
d2 = bronze_to_silver_policies_scd2(
    'data/bronze/policies.parquet',
    'data/bronze/endorsements.parquet',
    'data/silver',
)
f = bronze_to_silver_claims_fact(
    'data/bronze/claims/**/*.parquet',
    'data/bronze/payments/**/*.parquet',
    d2['silver_path'],
    'data/silver',
)
gold_loss_ratio_monthly(
    f['silver_path'] + '/**/*.parquet',
    'data/bronze/premiums/**/*.parquet',
    'data/gold',
)
"
```

## Tests

`tests/test_transform.py` pins:

- SCD2 shape: ≥ 1 row per policy, exactly one `is_current = true` per
  policy, current row's `valid_to = 9999-12-31`
- `fact_claim` joins payments correctly, has expected columns
- Gold rollup groups by `accounting_period × line_of_business`, loss
  ratio + combined ratio populated
- Every committed Databricks notebook is parseable Python
- Every Unity Catalog SQL file exists
- `databricks.yml` parses and declares dev/staging/prod targets

## What's next

Phase 7 mirrors the entire medallion onto Microsoft Fabric OneLake —
same bronze reads, same silver + gold writes, Fabric Notebooks + Fabric
Data Factory pipelines + a Fabric Warehouse + a Direct Lake semantic
model. The DuckDB mirrors remain the laptop demo path.

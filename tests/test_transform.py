"""Phase 4+5+6 tests — DuckDB mirrors of the Databricks medallion notebooks."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from claims_azure.generator import GeneratorConfig, generate_bundle
from claims_azure.generator.pipeline import write_bundle
from claims_azure.transform import (
    bronze_to_silver_claims_fact,
    bronze_to_silver_policies_scd2,
    gold_loss_ratio_monthly,
)


def _bronze(tmp_path: Path) -> dict:
    cfg = GeneratorConfig(
        seed=42,
        num_parties=100,
        num_policies=200,
        num_endorsements=80,
        num_claims=150,
        num_payments=300,
    )
    bundle = generate_bundle(cfg)
    bronze = tmp_path / "bronze"
    write_bundle(bundle, bronze)
    return {"root": bronze, "bundle": bundle}


def test_scd2_dim_shape(tmp_path):
    data = _bronze(tmp_path)
    silver = tmp_path / "silver"
    out = bronze_to_silver_policies_scd2(
        policies_path=str(data["root"] / "policies.parquet"),
        endorsements_path=str(data["root"] / "endorsements.parquet"),
        silver_root=silver,
    )
    tbl = pq.read_table(out["silver_path"])
    assert tbl.num_rows >= 200  # at least one row per policy
    cols = set(tbl.schema.names)
    assert {"policy_id", "valid_from", "valid_to", "is_current"} <= cols

    # Every policy must have exactly one current version.

    df = tbl.to_pandas()
    current_per_policy = df[df["is_current"]].groupby("policy_id").size()
    assert (current_per_policy == 1).all()


def test_scd2_current_valid_to_is_sentinel(tmp_path):
    data = _bronze(tmp_path)
    silver = tmp_path / "silver"
    out = bronze_to_silver_policies_scd2(
        str(data["root"] / "policies.parquet"),
        str(data["root"] / "endorsements.parquet"),
        silver,
    )
    df = pq.read_table(out["silver_path"]).to_pandas()
    assert (df.loc[df["is_current"], "valid_to"].astype(str) == "9999-12-31").all()


def test_fact_claim_joins_payments(tmp_path):
    data = _bronze(tmp_path)
    silver = tmp_path / "silver"
    scd2 = bronze_to_silver_policies_scd2(
        str(data["root"] / "policies.parquet"),
        str(data["root"] / "endorsements.parquet"),
        silver,
    )
    fact = bronze_to_silver_claims_fact(
        claims_path=str(data["root"] / "claims" / "**/*.parquet"),
        payments_path=str(data["root"] / "payments" / "**/*.parquet"),
        dim_policy_path=scd2["silver_path"],
        silver_root=silver,
    )
    assert fact["row_count"] > 0
    tbl = pq.read_table(fact["silver_path"])
    cols = set(tbl.schema.names)
    assert {
        "claim_id",
        "policy_id",
        "line_of_business",
        "payments_total_usd",
        "payment_count",
        "report_lag_days",
    } <= cols

    # payments_total should be non-negative everywhere.
    pts = [p for p in tbl.column("payments_total_usd").to_pylist() if p is not None]
    assert all(Decimal(str(p)) >= 0 for p in pts)


def test_gold_loss_ratio_rolls_up(tmp_path):
    data = _bronze(tmp_path)
    silver = tmp_path / "silver"
    scd2 = bronze_to_silver_policies_scd2(
        str(data["root"] / "policies.parquet"),
        str(data["root"] / "endorsements.parquet"),
        silver,
    )
    fact = bronze_to_silver_claims_fact(
        str(data["root"] / "claims" / "**/*.parquet"),
        str(data["root"] / "payments" / "**/*.parquet"),
        scd2["silver_path"],
        silver,
    )
    gold = tmp_path / "gold"
    out = gold_loss_ratio_monthly(
        fact_claim_glob=str(Path(fact["silver_path"]) / "**/*.parquet"),
        premiums_glob=str(data["root"] / "premiums" / "**/*.parquet"),
        gold_root=gold,
    )
    assert out["row_count"] > 0
    tbl = pq.read_table(out["gold_path"])
    cols = set(tbl.schema.names)
    assert {"accounting_period", "loss_ratio", "combined_ratio"} <= cols


def test_committed_databricks_notebooks_parseable():
    """Every Databricks notebook .py must be valid Python top-level."""
    import ast

    notebooks_dir = Path(__file__).resolve().parents[1] / "databricks" / "notebooks"
    for nb in notebooks_dir.glob("*.py"):
        src = nb.read_text()
        # Databricks notebooks contain `# MAGIC %md` + `# COMMAND ----------`
        # which are legal Python comments; ast.parse must still succeed.
        ast.parse(src)


def test_committed_unity_catalog_sql_present():
    uc_dir = Path(__file__).resolve().parents[1] / "databricks" / "unity-catalog"
    assert (uc_dir / "01_catalogs_schemas.sql").exists()
    assert (uc_dir / "02_grants.sql").exists()
    assert (uc_dir / "03_row_filters_tags.sql").exists()


def test_dab_bundle_yaml_present():
    bundle = Path(__file__).resolve().parents[1] / "databricks" / "bundles" / "databricks.yml"
    assert bundle.exists()
    import yaml

    data = yaml.safe_load(bundle.read_text())
    assert data["bundle"]["name"] == "claims-medallion"
    assert {"dev", "staging", "prod"} <= set(data["targets"])

"""Phase 7+8 — Fabric Lakehouse + Warehouse mirrors."""

from __future__ import annotations

import ast
from pathlib import Path

import pyarrow.parquet as pq

from claims_azure.fabric import load_mart_loss_ratio, rebuild_gold_loss_ratio
from claims_azure.generator import GeneratorConfig, generate_bundle
from claims_azure.generator.pipeline import write_bundle
from claims_azure.transform import (
    bronze_to_silver_claims_fact,
    bronze_to_silver_policies_scd2,
)


def _silver(tmp_path: Path) -> dict:
    cfg = GeneratorConfig(
        seed=7,
        num_parties=80,
        num_policies=150,
        num_endorsements=50,
        num_claims=120,
        num_payments=240,
    )
    bundle = generate_bundle(cfg)
    bronze = tmp_path / "bronze"
    write_bundle(bundle, bronze)

    silver = tmp_path / "silver"
    scd2 = bronze_to_silver_policies_scd2(
        str(bronze / "policies.parquet"),
        str(bronze / "endorsements.parquet"),
        silver,
    )
    fact = bronze_to_silver_claims_fact(
        str(bronze / "claims" / "**/*.parquet"),
        str(bronze / "payments" / "**/*.parquet"),
        scd2["silver_path"],
        silver,
    )
    return {
        "bronze": bronze,
        "silver_fact_glob": str(Path(fact["silver_path"]) / "**/*.parquet"),
        "premiums_glob": str(bronze / "premiums" / "**/*.parquet"),
    }


def test_fabric_lakehouse_mirror_runs(tmp_path):
    s = _silver(tmp_path)
    gold = tmp_path / "fabric_gold"
    out = rebuild_gold_loss_ratio(s["silver_fact_glob"], s["premiums_glob"], gold)
    tbl = pq.read_table(out)
    assert tbl.num_rows > 0
    cols = set(tbl.schema.names)
    assert {"month", "lob", "losses_paid", "premium_earned", "loss_ratio"} <= cols


def test_fabric_warehouse_mirror_shape(tmp_path):
    s = _silver(tmp_path)
    mart = tmp_path / "fabric_mart"
    out = load_mart_loss_ratio(s["silver_fact_glob"], s["premiums_glob"], mart)
    tbl = pq.read_table(out)
    assert tbl.num_rows > 0
    cols = set(tbl.schema.names)
    assert {
        "month",
        "lob",
        "losses_paid",
        "losses_reserved",
        "premium_earned",
        "loss_ratio",
    } <= cols


def test_committed_fabric_notebooks_parseable():
    """Fabric notebooks are stored as parseable Python with # MAGIC markers."""
    nb_dir = Path(__file__).resolve().parents[1] / "fabric" / "notebooks"
    files = sorted(nb_dir.glob("*.py"))
    assert len(files) >= 2
    for nb in files:
        ast.parse(nb.read_text())


def test_committed_warehouse_ddl_present():
    wh_dir = Path(__file__).resolve().parents[1] / "fabric" / "warehouse"
    assert (wh_dir / "01_warehouse_ddl.sql").exists()
    assert (wh_dir / "02_warehouse_loads.sql").exists()

    ddl = (wh_dir / "01_warehouse_ddl.sql").read_text()
    assert "mart.loss_ratio" in ddl
    assert "fact.claims_monthly" in ddl
    assert "dim.policy" in ddl

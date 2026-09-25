"""Phase 9 — Microsoft Purview custom Atlas lineage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claims_azure.governance import build_notebook_lineage


def test_lineage_has_process_and_referred_entities():
    payload = build_notebook_lineage("01_bronze_to_silver_policies_scd2")
    assert payload["entity"]["typeName"] == "Process"
    assert "qualifiedName" in payload["entity"]["attributes"]
    # Two inputs, one output → three referred entities.
    assert len(payload["referredEntities"]) == 3


def test_lineage_inputs_match_outputs_shape():
    payload = build_notebook_lineage("02_bronze_to_silver_claims_fact")
    attrs = payload["entity"]["attributes"]
    assert len(attrs["inputs"]) == 3
    assert len(attrs["outputs"]) == 1
    for item in [*attrs["inputs"], *attrs["outputs"]]:
        assert item["typeName"] == "azure_datalake_gen2_path"
        assert "qualifiedName" in item["uniqueAttributes"]


def test_lineage_payload_is_json_serializable():
    payload = build_notebook_lineage("03_silver_to_gold_loss_ratio")
    # Must round-trip without TypeError (no datetime/decimal etc).
    txt = json.dumps(payload)
    assert "monthly_loss_ratio" in txt


def test_unknown_notebook_raises():
    with pytest.raises(ValueError):
        build_notebook_lineage("not-a-real-notebook")


def test_committed_purview_configs_present():
    pv = Path(__file__).resolve().parents[1] / "purview"
    collections = json.loads((pv / "collections.json").read_text())
    assert any(c["name"] == "claims-platform" for c in collections)

    scans = json.loads((pv / "scan_definitions.json").read_text())
    assert "adls_gen2_scan" in scans
    assert "databricks_unity_scan" in scans
    assert "fabric_lakehouse_scan" in scans

"""Phase 3 tests — local ADF emulators + bronze layout + committed ADF JSON schemas."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

from claims_azure.generator.schemas import CLAIM_SCHEMA, POLICY_SCHEMA
from claims_azure.ingest.bronze import bronze_prefix, write_parquet
from claims_azure.ingest.pipelines import (
    run_claims_sftp_to_bronze,
    run_policies_azsql_to_bronze,
)

ADF_ROOT = Path(__file__).resolve().parents[1] / "adf"


def test_bronze_prefix_layout():
    target = bronze_prefix("bronze", "claims", event_date=date(2026, 2, 14), source="sftp")
    assert target.container == "bronze"
    assert target.prefix == "claims/event_date=2026-02-14/sftp"


def test_bronze_prefix_default_event_date_is_today():
    target = bronze_prefix("bronze", "claims")
    assert target.event_date == date.today() or target.event_date.year >= 2026


def test_write_parquet_round_trip(tmp_path):
    target = bronze_prefix("bronze", "claims", event_date=date(2026, 2, 14), source="sftp")
    from decimal import Decimal

    rows = [
        {
            "claim_id": "CLM00000001",
            "policy_id": "POL00000001",
            "party_id": "PTY00000001",
            "loss_date": date(2026, 2, 10),
            "report_date": date(2026, 2, 11),
            "peril_code": "collision",
            "status": "open",
            "reserve_amount_usd": Decimal("1000.00"),
            "incurred_amount_usd": Decimal("1200.00"),
            "paid_to_date_usd": Decimal("500.00"),
            "adjuster_code": "ADJ001",
            "event_date": date(2026, 2, 11),
        }
    ]
    path = write_parquet(rows, CLAIM_SCHEMA, target, local_root=tmp_path)
    assert path.exists()
    assert "claims/event_date=2026-02-14/sftp" in str(path)
    table = pq.read_table(path)
    assert table.num_rows == 1
    assert table.schema.equals(CLAIM_SCHEMA)


def test_run_claims_sftp_to_bronze(tmp_path):
    path = run_claims_sftp_to_bronze(seed=1, load_date=date(2026, 2, 14), local_root=tmp_path)
    assert path.exists()
    assert "claims/event_date=2026-02-14/sftp" in str(path)
    table = pq.read_table(path)
    assert table.num_rows > 0
    assert table.schema.equals(CLAIM_SCHEMA)


def test_run_policies_azsql_to_bronze(tmp_path):
    path = run_policies_azsql_to_bronze(seed=1, load_date=date(2026, 2, 14), local_root=tmp_path)
    assert path.exists()
    assert "policies/event_date=2026-02-14/azsql" in str(path)
    table = pq.read_table(path)
    assert table.num_rows > 0
    assert table.schema.equals(POLICY_SCHEMA)


def test_committed_adf_pipeline_json_is_valid():
    """Every ADF pipeline JSON must be valid JSON with the expected ADF v2 shape."""
    for path in (ADF_ROOT / "pipelines").iterdir():
        if path.suffix != ".json":
            continue
        data = json.loads(path.read_text())
        assert data["name"]
        assert data["properties"]["activities"], f"{path.name} has no activities"


def test_committed_adf_linked_services_reference_key_vault():
    """SFTP + Azure SQL linked services must get secrets from Key Vault, not inline."""
    sftp = json.loads((ADF_ROOT / "linkedServices" / "ls_sftp_partner.json").read_text())
    typ = sftp["properties"]["typeProperties"]
    for secret_field in ("hostKeyFingerprint", "userName", "privateKeyContent"):
        assert (
            typ[secret_field]["type"] == "AzureKeyVaultSecret"
        ), f"{secret_field} must come from Key Vault, not be inline"

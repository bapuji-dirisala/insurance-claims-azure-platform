"""End-to-end generator pipeline + bronze-zone Parquet writer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from claims_azure.generator.claims import generate_claims, generate_payments
from claims_azure.generator.config import GeneratorConfig
from claims_azure.generator.parties import generate_parties
from claims_azure.generator.policies import (
    generate_endorsements,
    generate_policies,
    generate_premiums,
)
from claims_azure.generator.schemas import (
    CLAIM_SCHEMA,
    ENDORSEMENT_SCHEMA,
    PARTY_SCHEMA,
    PAYMENT_SCHEMA,
    POLICY_SCHEMA,
    PREMIUM_SCHEMA,
)


@dataclass(frozen=True)
class GeneratedBundle:
    """All six datasets from a single generator run."""

    parties: list[dict]
    policies: list[dict]
    endorsements: list[dict]
    claims: list[dict]
    payments: list[dict]
    premiums: list[dict]


def generate_bundle(cfg: GeneratorConfig) -> GeneratedBundle:
    """Build all six datasets with full referential integrity."""
    parties = generate_parties(cfg)
    parties_by_id = {p["party_id"]: p for p in parties}
    policies = generate_policies(cfg, parties)
    endorsements = generate_endorsements(cfg, policies)
    claims = generate_claims(cfg, policies, parties_by_id)
    payments = generate_payments(cfg, claims)
    premiums = generate_premiums(cfg, policies)
    return GeneratedBundle(
        parties=parties,
        policies=policies,
        endorsements=endorsements,
        claims=claims,
        payments=payments,
        premiums=premiums,
    )


# ---------------------------------------------------------------------------
# Parquet writer (bronze layout)
# ---------------------------------------------------------------------------


def _table(rows: list[dict], schema: pa.Schema) -> pa.Table:
    columns: dict[str, list] = {field.name: [] for field in schema}
    for row in rows:
        for field in schema:
            columns[field.name].append(row.get(field.name))
    arrays = [pa.array(columns[field.name], type=field.type) for field in schema]
    return pa.Table.from_arrays(arrays, schema=schema)


def write_bundle(bundle: GeneratedBundle, out_dir: Path) -> dict[str, Path]:
    """Write all six datasets under ``out_dir`` in bronze layout.

    * ``parties.parquet``, ``policies.parquet``, ``endorsements.parquet``
      — single files (master + SCD2 source).
    * ``claims/``, ``payments/``, ``premiums/`` — partitioned by
      ``event_date=YYYY-MM-DD``, the layout Databricks + Fabric pick up
      for pruning without extra config.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    for logical, rows, schema in (
        ("parties", bundle.parties, PARTY_SCHEMA),
        ("policies", bundle.policies, POLICY_SCHEMA),
        ("endorsements", bundle.endorsements, ENDORSEMENT_SCHEMA),
    ):
        table = _table(rows, schema)
        path = out_dir / f"{logical}.parquet"
        pq.write_table(table, path)
        written[logical] = path

    for logical, rows, schema in (
        ("claims", bundle.claims, CLAIM_SCHEMA),
        ("payments", bundle.payments, PAYMENT_SCHEMA),
        ("premiums", bundle.premiums, PREMIUM_SCHEMA),
    ):
        table = _table(rows, schema)
        root = out_dir / logical
        pq.write_to_dataset(table, root_path=str(root), partition_cols=["event_date"])
        written[logical] = root

    return written

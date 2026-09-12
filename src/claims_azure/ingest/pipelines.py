"""Local emulators of the ADF pipelines in ``adf/pipelines/``.

Each function mirrors one committed pipeline JSON:

* ``pl_claims_sftp_to_bronze`` → :func:`run_claims_sftp_to_bronze`
* ``pl_policies_azsql_to_bronze`` → :func:`run_policies_azsql_to_bronze`

They don't call ADF — they produce the same Parquet in the same bronze
partition layout from the local generator. Reviewers compare the two
side by side to see the production path and the local fallback stay in
sync.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from claims_azure.generator import GeneratorConfig, generate_bundle
from claims_azure.generator.schemas import CLAIM_SCHEMA, POLICY_SCHEMA
from claims_azure.ingest.bronze import bronze_prefix, write_parquet


def run_claims_sftp_to_bronze(
    *,
    seed: int = 42,
    load_date: date | None = None,
    container: str = "bronze",
    local_root: Path | None = None,
) -> Path:
    """Emulate the SFTP → bronze claims pipeline.

    Generator stands in for the partner feed; the write path is the real
    bronze layout the ADF pipeline produces.
    """
    load_date = load_date or datetime.now(UTC).date()
    cfg = GeneratorConfig(seed=seed, num_claims=200, num_payments=400)
    bundle = generate_bundle(cfg)
    target = bronze_prefix(container, "claims", event_date=load_date, source="sftp")
    return write_parquet(bundle.claims, CLAIM_SCHEMA, target, local_root=local_root)


def run_policies_azsql_to_bronze(
    *,
    seed: int = 42,
    load_date: date | None = None,
    container: str = "bronze",
    local_root: Path | None = None,
) -> Path:
    """Emulate the Azure SQL → bronze policies pipeline.

    Generator stands in for the OLTP source; the write path is the real
    bronze layout the ADF pipeline produces.
    """
    load_date = load_date or datetime.now(UTC).date()
    cfg = GeneratorConfig(seed=seed, num_policies=500)
    bundle = generate_bundle(cfg)
    target = bronze_prefix(container, "policies", event_date=load_date, source="azsql")
    return write_parquet(bundle.policies, POLICY_SCHEMA, target, local_root=local_root)

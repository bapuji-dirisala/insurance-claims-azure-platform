"""Phase 2 generator tests — determinism, referential integrity, schema."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from claims_azure.generator import GeneratorConfig, generate_bundle
from claims_azure.generator.pipeline import write_bundle
from claims_azure.generator.schemas import (
    CLAIM_SCHEMA,
    ENDORSEMENT_SCHEMA,
    PARTY_SCHEMA,
    PAYMENT_SCHEMA,
    POLICY_SCHEMA,
    PREMIUM_SCHEMA,
)

TINY = GeneratorConfig(
    seed=1234,
    num_parties=50,
    num_policies=100,
    num_endorsements=20,
    num_claims=40,
    num_payments=80,
)


def test_cardinalities() -> None:
    bundle = generate_bundle(TINY)
    assert len(bundle.parties) == 50
    assert len(bundle.policies) == 100
    assert len(bundle.endorsements) == 20
    assert len(bundle.claims) == 40
    # Payments: driven by paying claims — can be fewer than requested if
    # all generated claims happen to be denied, but with the test sizing
    # we expect close to the target.
    assert 1 <= len(bundle.payments) <= TINY.num_payments
    assert len(bundle.premiums) > 0


def test_determinism() -> None:
    a = generate_bundle(TINY)
    b = generate_bundle(TINY)
    assert a == b


def test_different_seed_produces_different_bundle() -> None:
    a = generate_bundle(TINY)
    other = GeneratorConfig(
        seed=TINY.seed + 1,
        num_parties=TINY.num_parties,
        num_policies=TINY.num_policies,
        num_endorsements=TINY.num_endorsements,
        num_claims=TINY.num_claims,
        num_payments=TINY.num_payments,
    )
    b = generate_bundle(other)
    assert a != b


def test_referential_integrity() -> None:
    bundle = generate_bundle(TINY)
    party_ids = {p["party_id"] for p in bundle.parties}
    policy_ids = {p["policy_id"] for p in bundle.policies}
    claim_ids = {c["claim_id"] for c in bundle.claims}

    for policy in bundle.policies:
        assert policy["party_id"] in party_ids
    for endorsement in bundle.endorsements:
        assert endorsement["policy_id"] in policy_ids
    for claim in bundle.claims:
        assert claim["policy_id"] in policy_ids
        assert claim["party_id"] in party_ids
    for payment in bundle.payments:
        assert payment["claim_id"] in claim_ids
    for premium in bundle.premiums:
        assert premium["policy_id"] in policy_ids


def test_claims_fall_in_policy_term() -> None:
    bundle = generate_bundle(TINY)
    policy_by_id = {p["policy_id"]: p for p in bundle.policies}
    for claim in bundle.claims:
        policy = policy_by_id[claim["policy_id"]]
        assert policy["effective_date"] <= claim["loss_date"] <= policy["expiration_date"]
        assert claim["report_date"] >= claim["loss_date"]


def test_paid_le_incurred_le_coverage() -> None:
    bundle = generate_bundle(TINY)
    policy_by_id = {p["policy_id"]: p for p in bundle.policies}
    for claim in bundle.claims:
        incurred = Decimal(claim["incurred_amount_usd"])
        paid = Decimal(claim["paid_to_date_usd"])
        coverage = Decimal(policy_by_id[claim["policy_id"]]["coverage_limit_usd"])
        assert paid <= incurred
        # Reserve bounded by coverage; incurred may exceed reserve by markup
        # but shouldn't exceed 2x coverage.
        assert incurred <= coverage * 2


def test_denied_claims_have_zero_paid() -> None:
    bundle = generate_bundle(TINY)
    for claim in bundle.claims:
        if claim["status"] == "denied":
            assert Decimal(claim["paid_to_date_usd"]) == Decimal("0.00")


def test_write_bundle_schemas_match(tmp_path: Path) -> None:
    bundle = generate_bundle(TINY)
    written = write_bundle(bundle, tmp_path)
    assert set(written) == {
        "parties",
        "policies",
        "endorsements",
        "claims",
        "payments",
        "premiums",
    }

    # Flat tables carry the exact committed schema.
    assert pq.read_table(written["parties"]).schema.equals(PARTY_SCHEMA)
    assert pq.read_table(written["policies"]).schema.equals(POLICY_SCHEMA)
    assert pq.read_table(written["endorsements"]).schema.equals(ENDORSEMENT_SCHEMA)

    # Partitioned datasets reorder event_date to the end; just check every
    # pinned column is still present.
    claims_tbl = pq.read_table(written["claims"])
    for field in CLAIM_SCHEMA:
        assert field.name in claims_tbl.schema.names
    payments_tbl = pq.read_table(written["payments"])
    for field in PAYMENT_SCHEMA:
        assert field.name in payments_tbl.schema.names
    premiums_tbl = pq.read_table(written["premiums"])
    for field in PREMIUM_SCHEMA:
        assert field.name in premiums_tbl.schema.names


def test_config_validation() -> None:
    with pytest.raises(ValueError):
        GeneratorConfig(num_parties=0)
    with pytest.raises(ValueError):
        GeneratorConfig(num_claims=-1)

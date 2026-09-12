"""Explicit pyarrow schemas for every bronze-zone insurance dataset.

Same source-of-truth pattern as the P4 project: a single Arrow schema
per dataset keyed by the committed Python file, picked up by the
Databricks medallion, the Fabric mirror, and the Purview catalog. No
inference anywhere — explicit types prevent "silver silently went
nullable" drift that eats weekends.
"""

from __future__ import annotations

import pyarrow as pa

PARTY_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("party_id", pa.string(), nullable=False),
        pa.field("party_type", pa.string(), nullable=False),  # person|vehicle|property
        pa.field("name", pa.string(), nullable=False),
        pa.field("email", pa.string(), nullable=True),
        pa.field("phone", pa.string(), nullable=True),
        pa.field("country", pa.string(), nullable=False),
        pa.field("state_region", pa.string(), nullable=True),
        pa.field("city", pa.string(), nullable=False),
        pa.field("postal_code", pa.string(), nullable=False),
        pa.field("birth_year", pa.int32(), nullable=True),
        pa.field("created_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)

POLICY_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("policy_id", pa.string(), nullable=False),
        pa.field("party_id", pa.string(), nullable=False),
        pa.field("line_of_business", pa.string(), nullable=False),  # auto|home|liability
        pa.field("product_code", pa.string(), nullable=False),
        pa.field("effective_date", pa.date32(), nullable=False),
        pa.field("expiration_date", pa.date32(), nullable=False),
        pa.field("status", pa.string(), nullable=False),  # inforce|cancelled|lapsed
        pa.field("premium_annual_usd", pa.decimal128(12, 2), nullable=False),
        pa.field("deductible_usd", pa.decimal128(10, 2), nullable=False),
        pa.field("coverage_limit_usd", pa.decimal128(14, 2), nullable=False),
        pa.field("underwriter_code", pa.string(), nullable=False),
        pa.field("state_region", pa.string(), nullable=True),
        pa.field("created_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)

ENDORSEMENT_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("endorsement_id", pa.string(), nullable=False),
        pa.field("policy_id", pa.string(), nullable=False),
        pa.field("effective_date", pa.date32(), nullable=False),
        pa.field("endorsement_type", pa.string(), nullable=False),  # coverage_change|address|cancel
        pa.field("premium_delta_usd", pa.decimal128(12, 2), nullable=False),
        pa.field("coverage_limit_delta_usd", pa.decimal128(14, 2), nullable=False),
        pa.field("deductible_new_usd", pa.decimal128(10, 2), nullable=True),
        pa.field("reason_code", pa.string(), nullable=False),
        pa.field("created_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)

CLAIM_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("claim_id", pa.string(), nullable=False),
        pa.field("policy_id", pa.string(), nullable=False),
        pa.field("party_id", pa.string(), nullable=False),
        pa.field("loss_date", pa.date32(), nullable=False),
        pa.field("report_date", pa.date32(), nullable=False),
        pa.field("peril_code", pa.string(), nullable=False),  # collision|fire|theft|wind|liability
        pa.field("status", pa.string(), nullable=False),  # open|closed|denied|reopened
        pa.field("reserve_amount_usd", pa.decimal128(14, 2), nullable=False),
        pa.field("incurred_amount_usd", pa.decimal128(14, 2), nullable=False),
        pa.field("paid_to_date_usd", pa.decimal128(14, 2), nullable=False),
        pa.field("adjuster_code", pa.string(), nullable=False),
        pa.field("event_date", pa.date32(), nullable=False),  # partition key
    ]
)

PAYMENT_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("payment_id", pa.string(), nullable=False),
        pa.field("claim_id", pa.string(), nullable=False),
        pa.field("payment_date", pa.date32(), nullable=False),
        pa.field(
            "payment_type", pa.string(), nullable=False
        ),  # indemnity|expense|salvage|subrogation
        pa.field("amount_usd", pa.decimal128(14, 2), nullable=False),
        pa.field("payment_method", pa.string(), nullable=False),
        pa.field("payee_name", pa.string(), nullable=False),
        pa.field("event_date", pa.date32(), nullable=False),
    ]
)

PREMIUM_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("premium_id", pa.string(), nullable=False),
        pa.field("policy_id", pa.string(), nullable=False),
        pa.field("accounting_period", pa.string(), nullable=False),  # YYYY-MM
        pa.field("written_premium_usd", pa.decimal128(12, 2), nullable=False),
        pa.field("earned_premium_usd", pa.decimal128(12, 2), nullable=False),
        pa.field("unearned_premium_usd", pa.decimal128(12, 2), nullable=False),
        pa.field("event_date", pa.date32(), nullable=False),
    ]
)

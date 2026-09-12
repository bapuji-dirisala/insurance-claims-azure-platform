"""Claim + payment generation."""

from __future__ import annotations

import random
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from claims_azure.generator.config import GeneratorConfig

# Peril codes vary by LOB — this matches a real P&C book's distribution.
_PERILS_BY_LOB: dict[str, dict[str, float]] = {
    "auto": {
        "collision": 0.42,
        "comprehensive": 0.18,
        "theft": 0.10,
        "liability_bi": 0.15,
        "liability_pd": 0.15,
    },
    "home": {
        "fire": 0.08,
        "wind": 0.28,
        "water": 0.32,
        "theft": 0.10,
        "liability": 0.12,
        "other": 0.10,
    },
    "liability": {
        "general_liability": 0.60,
        "umbrella": 0.25,
        "defense": 0.15,
    },
}

_STATUS_WEIGHTS = {"open": 0.35, "closed": 0.50, "denied": 0.10, "reopened": 0.05}
_ADJUSTERS = tuple(f"ADJ{n:03d}" for n in range(1, 21))
_PAYMENT_TYPE_WEIGHTS = {"indemnity": 0.70, "expense": 0.20, "salvage": 0.05, "subrogation": 0.05}
_PAYMENT_METHODS = ("ACH", "CHECK", "WIRE", "VCC")


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _weighted(rng: random.Random, weights: dict[str, float]) -> str:
    return rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


def generate_claims(
    cfg: GeneratorConfig, policies: list[dict], parties_by_id: dict[str, dict]
) -> list[dict]:
    """Build the claims table (one row per claim; multi-payment via payments)."""
    rng = random.Random(cfg.seed + 4)

    claims: list[dict] = []
    for i in range(cfg.num_claims):
        policy = rng.choice(policies)
        party = parties_by_id[policy["party_id"]]
        # Loss date lands inside the policy term.
        term_days = (policy["expiration_date"] - policy["effective_date"]).days
        loss_offset = rng.randint(0, max(0, term_days - 1))
        loss_date = policy["effective_date"] + timedelta(days=loss_offset)
        # Report lag: 1–30 days typical, occasional late reports.
        report_lag = rng.choices([1, 5, 15, 60], weights=[0.5, 0.3, 0.15, 0.05], k=1)[0]
        report_date = loss_date + timedelta(days=report_lag)
        peril = _weighted(rng, _PERILS_BY_LOB[policy["line_of_business"]])
        status = _weighted(rng, _STATUS_WEIGHTS)

        # Loss severity by LOB — log-normal.
        severity_mu = {"auto": 7.5, "home": 8.5, "liability": 9.0}[policy["line_of_business"]]
        reserve = Decimal(str(round(rng.lognormvariate(severity_mu, 1.0), 2)))
        reserve = max(Decimal("100.00"), min(reserve, Decimal(policy["coverage_limit_usd"])))

        # Incurred ≥ reserve; paid-to-date ≤ incurred by status.
        incurred = _round(reserve * Decimal(str(round(rng.uniform(1.0, 1.3), 2))))
        if status == "closed":
            paid = incurred
        elif status == "denied":
            paid = Decimal("0.00")
        elif status == "reopened":
            paid = _round(incurred * Decimal(str(round(rng.uniform(0.4, 0.8), 2))))
        else:  # open
            paid = _round(incurred * Decimal(str(round(rng.uniform(0.0, 0.6), 2))))

        claims.append(
            {
                "claim_id": f"CLM{i:08d}",
                "policy_id": policy["policy_id"],
                "party_id": party["party_id"],
                "loss_date": loss_date,
                "report_date": report_date,
                "peril_code": peril,
                "status": status,
                "reserve_amount_usd": _round(reserve),
                "incurred_amount_usd": incurred,
                "paid_to_date_usd": paid,
                "adjuster_code": rng.choice(_ADJUSTERS),
                "event_date": report_date,
            }
        )
    return claims


def generate_payments(cfg: GeneratorConfig, claims: list[dict]) -> list[dict]:
    """Build the claim payments table (money leaving the carrier)."""
    rng = random.Random(cfg.seed + 5)

    # Only claims with paid_to_date > 0 contribute payments.
    paying_claims = [c for c in claims if c["paid_to_date_usd"] > Decimal("0.00")]
    if not paying_claims:
        return []

    payments: list[dict] = []
    total_target = cfg.num_payments
    # Distribute requested payments across paying claims (biased by paid_to_date).
    weights = [float(c["paid_to_date_usd"]) for c in paying_claims]
    for i in range(total_target):
        claim = rng.choices(paying_claims, weights=weights, k=1)[0]
        # Partial amount up to 60% of paid_to_date.
        amount = Decimal(str(round(float(claim["paid_to_date_usd"]) * rng.uniform(0.05, 0.6), 2)))
        amount = max(Decimal("1.00"), amount)
        payment_date = claim["report_date"] + timedelta(days=rng.randint(1, 90))
        payments.append(
            {
                "payment_id": f"PAY{i:08d}",
                "claim_id": claim["claim_id"],
                "payment_date": payment_date,
                "payment_type": _weighted(rng, _PAYMENT_TYPE_WEIGHTS),
                "amount_usd": _round(amount),
                "payment_method": rng.choice(_PAYMENT_METHODS),
                "payee_name": claim[
                    "adjuster_code"
                ],  # placeholder; prod would look up vendor master
                "event_date": payment_date,
            }
        )
    return payments

"""Policy + endorsement generation."""

from __future__ import annotations

import random
from datetime import UTC, date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from claims_azure.generator.config import GeneratorConfig

_LOB_WEIGHTS = {"auto": 0.55, "home": 0.30, "liability": 0.15}

_PRODUCT_BY_LOB: dict[str, tuple[str, ...]] = {
    "auto": ("AUTO-PP-ST", "AUTO-PP-BR", "AUTO-COMM-ST"),
    "home": ("HOME-HO3", "HOME-HO5", "HOME-HO6"),
    "liability": ("GL-SMB", "UMB-PERS", "UMB-COMM"),
}

_UNDERWRITERS = ("UW001", "UW002", "UW003", "UW004", "UW005")
_STATUS_WEIGHTS = {"inforce": 0.72, "cancelled": 0.08, "lapsed": 0.20}
_ENDORSEMENT_TYPE_WEIGHTS = {
    "coverage_change": 0.55,
    "address": 0.25,
    "cancel": 0.10,
    "driver_add": 0.10,
}
_REASON_CODES = ("ADDN", "DELN", "CHNG", "MOVE", "CORR", "RENW")


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _weighted(rng: random.Random, weights: dict[str, float]) -> str:
    return rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


def generate_policies(cfg: GeneratorConfig, parties: list[dict]) -> list[dict]:
    """Build the in-force policies table (one row per policy)."""
    rng = random.Random(cfg.seed + 1)

    window_s = int((cfg.end_date - cfg.start_date).total_seconds())
    policies: list[dict] = []
    for i in range(cfg.num_policies):
        party = rng.choice(parties)
        lob = _weighted(rng, _LOB_WEIGHTS)
        product_code = rng.choice(_PRODUCT_BY_LOB[lob])
        # Effective dates spread across the window; annual terms.
        effective_offset_s = rng.randint(0, window_s)
        effective = (cfg.start_date + timedelta(seconds=effective_offset_s)).date()
        expiration = effective + timedelta(days=365)

        # Base premium by LOB with jitter.
        base = {"auto": 1200.0, "home": 950.0, "liability": 1800.0}[lob]
        premium = Decimal(str(round(rng.uniform(base * 0.6, base * 1.8), 2)))
        deductible = Decimal(rng.choice(("500", "1000", "2500", "5000")))
        coverage_limit = Decimal(rng.choice(("100000", "250000", "500000", "1000000")))

        created_at = cfg.start_date + timedelta(seconds=effective_offset_s)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        policies.append(
            {
                "policy_id": f"POL{i:08d}",
                "party_id": party["party_id"],
                "line_of_business": lob,
                "product_code": product_code,
                "effective_date": effective,
                "expiration_date": expiration,
                "status": _weighted(rng, _STATUS_WEIGHTS),
                "premium_annual_usd": _round(premium),
                "deductible_usd": _round(deductible),
                "coverage_limit_usd": _round(coverage_limit),
                "underwriter_code": rng.choice(_UNDERWRITERS),
                "state_region": party["state_region"],
                "created_at": created_at,
            }
        )
    return policies


def generate_endorsements(cfg: GeneratorConfig, policies: list[dict]) -> list[dict]:
    """Build mid-term policy endorsements (SCD2 fodder for silver)."""
    rng = random.Random(cfg.seed + 2)

    endorsements: list[dict] = []
    for i in range(cfg.num_endorsements):
        policy = rng.choice(policies)
        # Endorsement effective date must fall inside the policy term.
        term_days = (policy["expiration_date"] - policy["effective_date"]).days
        offset = rng.randint(1, max(1, term_days - 1))
        effective = policy["effective_date"] + timedelta(days=offset)
        premium_delta = Decimal(str(round(rng.uniform(-200, 500), 2)))
        coverage_delta = Decimal(str(rng.choice((0, 0, 0, 50000, -50000, 100000))))
        new_ded = Decimal(rng.choice(("500", "1000", "2500"))) if rng.random() < 0.4 else None
        created_at = cfg.start_date + timedelta(days=offset)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        endorsements.append(
            {
                "endorsement_id": f"END{i:08d}",
                "policy_id": policy["policy_id"],
                "effective_date": effective,
                "endorsement_type": _weighted(rng, _ENDORSEMENT_TYPE_WEIGHTS),
                "premium_delta_usd": _round(premium_delta),
                "coverage_limit_delta_usd": _round(coverage_delta),
                "deductible_new_usd": _round(new_ded) if new_ded else None,
                "reason_code": rng.choice(_REASON_CODES),
                "created_at": created_at,
            }
        )
    return endorsements


def generate_premiums(cfg: GeneratorConfig, policies: list[dict]) -> list[dict]:
    """Monthly earned-premium postings per policy, bounded by policy term."""
    rng = random.Random(cfg.seed + 3)
    premiums: list[dict] = []

    for policy in policies:
        monthly = (Decimal(policy["premium_annual_usd"]) / Decimal("12")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        start = policy["effective_date"]
        # Walk months from effective to earlier of expiration or end_date.
        cursor = date(start.year, start.month, 1)
        end_cursor = min(policy["expiration_date"], cfg.end_date.date())
        # Earned ramps up linearly; unearned is the inverse.
        term_months = max(
            1,
            (end_cursor.year - start.year) * 12 + (end_cursor.month - start.month) + 1,
        )
        for n in range(term_months):
            period = f"{cursor.year:04d}-{cursor.month:02d}"
            earned_fraction = Decimal(str(min(1.0, (n + 1) / term_months)))
            earned = (monthly * (n + 1)).quantize(Decimal("0.01"))
            unearned = (
                Decimal(policy["premium_annual_usd"]) * (Decimal("1") - earned_fraction)
            ).quantize(Decimal("0.01"))
            premiums.append(
                {
                    "premium_id": f"PRM{policy['policy_id'][3:]}-{n:03d}",
                    "policy_id": policy["policy_id"],
                    "accounting_period": period,
                    "written_premium_usd": monthly,
                    "earned_premium_usd": earned,
                    "unearned_premium_usd": unearned,
                    "event_date": cursor,
                }
            )
            # Advance one month.
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)
            if cursor > end_cursor:
                break

    # Keep a bit of determinism noise so premium periods don't exactly
    # mirror policies — pull a random stable subsample if the caller
    # sized smaller than full coverage.
    if len(premiums) > cfg.num_policies * 24:
        rng.shuffle(premiums)
    return premiums

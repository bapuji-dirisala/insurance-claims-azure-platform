"""Deterministic configuration for the synthetic P&C insurance generator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class GeneratorConfig:
    """Sizing + reproducibility knobs for one generator run.

    Attributes
    ----------
    seed:
        Shared RNG seed for ``random.Random``, Faker, and timestamp jitter.
    num_parties:
        How many insured parties (people / vehicles / properties).
    num_policies:
        How many in-force policies. Each policy references one party.
    num_endorsements:
        How many mid-term policy changes to emit — these are SCD2 fodder
        and drive the "point-in-time coverage" story the medallion builds.
    num_claims:
        How many claims to emit. Claims target real policies with claim
        dates in the policy's effective window.
    num_payments:
        How many payment transactions. On average claims see 2–3 payments
        (first indemnity, supplemental, final settlement).
    start_date / end_date:
        Window the generator spreads policy effective dates + claim dates
        across. Partitioning in later phases keys on these.
    locale:
        Faker locale. ``en_US`` keeps the project consistent with the
        US + European market both carriers operate in.
    """

    seed: int = 42
    num_parties: int = 2_000
    num_policies: int = 2_500
    num_endorsements: int = 500
    num_claims: int = 1_000
    num_payments: int = 2_500
    start_date: datetime = datetime(2024, 1, 1, tzinfo=UTC)
    end_date: datetime = datetime(2026, 10, 31, 23, 59, 59, tzinfo=UTC)
    locale: str = "en_US"

    def __post_init__(self) -> None:
        if self.num_parties <= 0:
            raise ValueError("num_parties must be positive")
        if self.num_policies <= 0:
            raise ValueError("num_policies must be positive")
        if self.num_endorsements < 0:
            raise ValueError("num_endorsements must be non-negative")
        if self.num_claims < 0:
            raise ValueError("num_claims must be non-negative")
        if self.num_payments < 0:
            raise ValueError("num_payments must be non-negative")
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")

"""Claim-payment event payload — pinned schema shared across producer + consumer."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal


@dataclass(frozen=True)
class ClaimPaymentEvent:
    """One payment-authorized event.

    All downstream parsers (Structured Streaming, local emulator, QA
    harness) key off the same field names + types.
    """

    payment_id: str
    claim_id: str
    policy_id: str
    amount_usd: Decimal
    authorized_at: datetime

    def to_dict(self) -> dict[str, str]:
        d = asdict(self)
        d["amount_usd"] = str(self.amount_usd)
        d["authorized_at"] = self.authorized_at.astimezone(UTC).isoformat()
        return d


def encode_payment(event: ClaimPaymentEvent) -> bytes:
    """UTF-8 JSON — matches what the Databricks `from_json` parser expects."""
    return json.dumps(event.to_dict(), separators=(",", ":")).encode("utf-8")

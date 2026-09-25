"""Local Event Hubs emulator.

Event Hubs doesn't have a free local emulator (Azurite covers blob,
queue, and table — not Event Hubs). This module emulates the receiver
side so unit tests can replay a captured stream into a bronze Delta
table without an Azure dependency.

In production the stream comes from Structured Streaming's Kafka
source. Locally we iterate the same `ClaimPaymentEvent` objects and
write JSONL to a bronze Parquet dataset.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .payloads import ClaimPaymentEvent

PAYMENT_SCHEMA = pa.schema(
    [
        pa.field("payment_id", pa.string(), nullable=False),
        pa.field("claim_id", pa.string(), nullable=False),
        pa.field("policy_id", pa.string(), nullable=False),
        pa.field("amount_usd", pa.decimal128(14, 2), nullable=False),
        pa.field("authorized_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ]
)


@dataclass
class LocalPaymentStream:
    """In-process buffer of events that mimics an Event Hubs partition."""

    events: list[ClaimPaymentEvent] = field(default_factory=list)

    def append(self, event: ClaimPaymentEvent) -> None:
        self.events.append(event)

    def extend(self, events: Iterable[ClaimPaymentEvent]) -> None:
        self.events.extend(events)

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self) -> Iterator[ClaimPaymentEvent]:
        return iter(self.events)

    def to_arrow(self) -> pa.Table:
        return pa.Table.from_pylist(
            [
                {
                    "payment_id": e.payment_id,
                    "claim_id": e.claim_id,
                    "policy_id": e.policy_id,
                    "amount_usd": e.amount_usd,
                    "authorized_at": e.authorized_at,
                }
                for e in self.events
            ],
            schema=PAYMENT_SCHEMA,
        )

    def flush_to_bronze(self, bronze_root: Path) -> Path:
        """Write the buffer as a Parquet file under the bronze/payments_stream dir."""
        bronze_root = Path(bronze_root)
        out_dir = bronze_root / "payments_stream"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "batch.parquet"
        pq.write_table(self.to_arrow(), out)
        return out


def emit_payment(stream: LocalPaymentStream, event: ClaimPaymentEvent) -> None:
    stream.append(event)


def replay_file(stream: LocalPaymentStream, events: Iterable[ClaimPaymentEvent]) -> int:
    """Push a batch of events through the stream; return the count."""
    before = len(stream)
    stream.extend(events)
    return len(stream) - before

"""Phase 10 — Event Hubs streaming local emulator."""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from claims_azure.streaming import (
    ClaimPaymentEvent,
    LocalPaymentStream,
    emit_payment,
    encode_payment,
    replay_file,
)


def _mk_event(idx: int) -> ClaimPaymentEvent:
    return ClaimPaymentEvent(
        payment_id=f"PMT-{idx:06d}",
        claim_id=f"CLM-{idx // 2:06d}",
        policy_id=f"POL-{idx // 10:06d}",
        amount_usd=Decimal("250.00") + Decimal(idx),
        authorized_at=datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC),
    )


def test_encode_payment_is_valid_utf8_json():
    e = _mk_event(1)
    raw = encode_payment(e)
    parsed = json.loads(raw.decode("utf-8"))
    assert parsed["payment_id"] == "PMT-000001"
    assert parsed["amount_usd"] == "251.00"
    assert parsed["authorized_at"].endswith("+00:00")


def test_local_stream_buffers_events():
    stream = LocalPaymentStream()
    emit_payment(stream, _mk_event(1))
    emit_payment(stream, _mk_event(2))
    assert len(stream) == 2
    added = replay_file(stream, [_mk_event(3), _mk_event(4), _mk_event(5)])
    assert added == 3
    assert len(stream) == 5


def test_flush_to_bronze_writes_parquet(tmp_path):
    stream = LocalPaymentStream()
    replay_file(stream, [_mk_event(i) for i in range(1, 11)])
    out = stream.flush_to_bronze(tmp_path / "bronze")
    tbl = pq.read_table(out)
    assert tbl.num_rows == 10
    cols = set(tbl.schema.names)
    assert {"payment_id", "claim_id", "policy_id", "amount_usd", "authorized_at"} == cols


def test_committed_streaming_notebook_parseable():
    nb = (
        Path(__file__).resolve().parents[1]
        / "databricks"
        / "streaming"
        / "01_payments_structured_streaming.py"
    )
    assert nb.exists()
    ast.parse(nb.read_text())

"""Phase 11 — Power BI DAX measure parity tests."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from claims_azure.bi import (
    combined_ratio,
    ibnr_estimate,
    loss_ratio,
    losses_ytd,
    premium_ytd,
)

_ROWS = [
    {
        "month": "2026-01",
        "lob": "auto",
        "losses_paid": Decimal("120"),
        "losses_reserved": Decimal("80"),
        "premium_earned": Decimal("500"),
        "loss_ratio": Decimal("0.40"),
    },
    {
        "month": "2026-02",
        "lob": "auto",
        "losses_paid": Decimal("150"),
        "losses_reserved": Decimal("50"),
        "premium_earned": Decimal("500"),
        "loss_ratio": Decimal("0.40"),
    },
    {
        "month": "2026-03",
        "lob": "auto",
        "losses_paid": Decimal("200"),
        "losses_reserved": Decimal("100"),
        "premium_earned": Decimal("600"),
        "loss_ratio": Decimal("0.50"),
    },
]


def test_loss_ratio_totals_match_tmdl_formula():
    # (120+80) + (150+50) + (200+100) = 700 ; premium = 1600 ; 700/1600 = 0.4375
    assert loss_ratio(_ROWS) == Decimal("700") / Decimal("1600")


def test_combined_ratio_adds_expense_ratio():
    expected = Decimal("700") / Decimal("1600") + Decimal("0.28")
    assert combined_ratio(_ROWS) == expected


def test_ibnr_estimate_scales_with_factor():
    low = ibnr_estimate(_ROWS, ibnr_factor=Decimal("0.10"))
    high = ibnr_estimate(_ROWS, ibnr_factor=Decimal("0.20"))
    assert high == low * 2


def test_premium_ytd_filters_by_as_of():
    as_of = datetime(2026, 2, 15)
    # Jan + Feb only.
    assert premium_ytd(_ROWS, as_of=as_of) == Decimal("1000")


def test_losses_ytd_filters_by_as_of():
    as_of = datetime(2026, 2, 15)
    # Jan (120+80) + Feb (150+50) = 400.
    assert losses_ytd(_ROWS, as_of=as_of) == Decimal("400")


def test_measures_handle_empty_rows():
    assert loss_ratio([]) == Decimal(0)
    assert combined_ratio([]) == Decimal("0.28")
    assert ibnr_estimate([]) == Decimal(0)
    assert premium_ytd([]) == Decimal(0)
    assert losses_ytd([]) == Decimal(0)


def test_measures_treat_zero_premium_as_zero():
    rows = [
        {
            "month": "2026-01",
            "lob": "auto",
            "losses_paid": Decimal("100"),
            "losses_reserved": Decimal("0"),
            "premium_earned": Decimal("0"),
            "loss_ratio": Decimal("0"),
        }
    ]
    assert loss_ratio(rows) == Decimal(0)


def test_committed_tmdl_present():
    tmdl = Path(__file__).resolve().parents[1] / "powerbi" / "semantic-model" / "model.tmdl"
    body = tmdl.read_text()
    assert "model Claims_Actuarial" in body
    assert "measure 'Loss Ratio'" in body
    assert "measure 'Combined Ratio'" in body
    assert "measure 'IBNR Estimate'" in body
    assert "mode: directLake" in body


def test_committed_dashboard_json_present():
    path = Path(__file__).resolve().parents[1] / "powerbi" / "semantic-model" / "dashboard.json"
    doc = json.loads(path.read_text())
    assert "pages" in doc
    assert len(doc["pages"]) >= 2


def test_unsupported_month_raises():
    with pytest.raises(TypeError):
        premium_ytd([{"month": 42, "premium_earned": Decimal("1")}], as_of=datetime(2026, 1, 1))

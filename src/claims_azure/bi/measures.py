"""Python equivalents of the Power BI DAX measures in `powerbi/semantic-model/model.tmdl`.

Each function takes an iterable of dicts (one per month × lob) with
columns `losses_paid`, `losses_reserved`, `premium_earned`. These are
the exact column names the TMDL file consumes.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from decimal import Decimal

Number = Decimal | float | int
Row = dict[str, object]


def _d(value: object) -> Decimal:
    if value is None:
        return Decimal(0)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def loss_ratio(rows: Iterable[Row]) -> Decimal:
    rows = list(rows)
    losses = sum(
        (_d(r.get("losses_paid")) + _d(r.get("losses_reserved")) for r in rows), Decimal(0)
    )
    premium = sum((_d(r.get("premium_earned")) for r in rows), Decimal(0))
    if premium == 0:
        return Decimal(0)
    return losses / premium


def combined_ratio(rows: Iterable[Row], expense_ratio: Decimal = Decimal("0.28")) -> Decimal:
    return loss_ratio(rows) + expense_ratio


def ibnr_estimate(rows: Iterable[Row], ibnr_factor: Decimal = Decimal("0.15")) -> Decimal:
    rows = list(rows)
    if not rows:
        return Decimal(0)
    avg_lr = sum(
        (_d(r.get("loss_ratio")) for r in rows if r.get("loss_ratio") is not None), Decimal(0)
    ) / max(1, sum(1 for r in rows if r.get("loss_ratio") is not None))
    premium_ytd_ = premium_ytd(rows)
    return premium_ytd_ * avg_lr * ibnr_factor


def premium_ytd(rows: Iterable[Row], as_of: datetime | None = None) -> Decimal:
    rows = list(rows)
    if as_of is None:
        return sum((_d(r.get("premium_earned")) for r in rows), Decimal(0))
    year = as_of.year
    return sum(
        (
            _d(r.get("premium_earned"))
            for r in rows
            if _month_year(r.get("month")) == year and _month_date(r.get("month")) <= as_of
        ),
        Decimal(0),
    )


def losses_ytd(rows: Iterable[Row], as_of: datetime | None = None) -> Decimal:
    rows = list(rows)
    if as_of is None:
        return sum(
            (_d(r.get("losses_paid")) + _d(r.get("losses_reserved")) for r in rows),
            Decimal(0),
        )
    year = as_of.year
    return sum(
        (
            _d(r.get("losses_paid")) + _d(r.get("losses_reserved"))
            for r in rows
            if _month_year(r.get("month")) == year and _month_date(r.get("month")) <= as_of
        ),
        Decimal(0),
    )


# --- helpers ---------------------------------------------------------


def _month_date(month: object) -> datetime:
    if isinstance(month, datetime):
        return month
    if isinstance(month, str):
        # Accept both YYYY-MM and YYYY-MM-DD.
        parts: Sequence[str] = month.split("-")
        year = int(parts[0])
        mon = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return datetime(year, mon, day)
    raise TypeError(f"unsupported month value: {month!r}")


def _month_year(month: object) -> int:
    return _month_date(month).year

"""Fabric Lakehouse + Warehouse local mirrors.

The Fabric notebooks + warehouse DDL in `fabric/` run in Microsoft Fabric;
these modules run on a laptop against the DuckDB silver output from
Phase 4+5+6 so the same gold aggregates can be regenerated for CI.
"""

from __future__ import annotations

from .lakehouse_mirror import rebuild_gold_loss_ratio
from .warehouse_mirror import load_mart_loss_ratio

__all__ = ["rebuild_gold_loss_ratio", "load_mart_loss_ratio"]

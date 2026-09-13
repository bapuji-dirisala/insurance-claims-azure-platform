"""Bronze → silver → gold transformations (DuckDB-first local path).

Mirrors the Databricks notebooks under ``databricks/notebooks/``. The
notebooks are the production artifact (deployed via DAB); the functions
here run the same logic on DuckDB so a reader can clone, run, and prove
the medallion works end-to-end on a laptop.
"""

from __future__ import annotations

from claims_azure.transform.gold_loss_ratio import gold_loss_ratio_monthly
from claims_azure.transform.silver_claims_fact import bronze_to_silver_claims_fact
from claims_azure.transform.silver_policies_scd2 import bronze_to_silver_policies_scd2

__all__ = [
    "bronze_to_silver_claims_fact",
    "bronze_to_silver_policies_scd2",
    "gold_loss_ratio_monthly",
]

"""Local DuckDB mirror of ``02_bronze_to_silver_claims_fact.py``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

CLAIM_FACT_SQL = """
WITH pay_agg AS (
    SELECT
        claim_id,
        SUM(amount_usd) AS payments_total_usd,
        COUNT(*)        AS payment_count,
        MAX(payment_date) AS latest_payment_date
    FROM read_parquet(?)
    GROUP BY claim_id
)
SELECT
    c.claim_id,
    c.policy_id,
    c.party_id,
    d.line_of_business,
    d.product_code,
    d.underwriter_code,
    c.loss_date,
    c.report_date,
    c.peril_code,
    c.status,
    c.reserve_amount_usd,
    c.incurred_amount_usd,
    c.paid_to_date_usd,
    COALESCE(pa.payments_total_usd, 0.00)::DECIMAL(14,2) AS payments_total_usd,
    COALESCE(pa.payment_count, 0)                         AS payment_count,
    pa.latest_payment_date,
    DATE_DIFF('day', c.loss_date, c.report_date)          AS report_lag_days
FROM read_parquet(?) c
LEFT JOIN pay_agg pa ON pa.claim_id = c.claim_id
LEFT JOIN read_parquet(?) d
    ON d.policy_id = c.policy_id
   AND d.is_current = TRUE
"""


def bronze_to_silver_claims_fact(
    claims_path: str,
    payments_path: str,
    dim_policy_path: str,
    silver_root: Path | str,
) -> dict[str, Any]:
    """Build silver.fact_claim locally."""
    con = duckdb.connect(":memory:")
    df = con.execute(CLAIM_FACT_SQL, [payments_path, claims_path, dim_policy_path]).to_arrow_table()
    silver_root = Path(silver_root)
    silver_root.mkdir(parents=True, exist_ok=True)
    import pyarrow.parquet as pq

    out_root = silver_root / "fact_claim"
    pq.write_to_dataset(df, root_path=str(out_root), partition_cols=["line_of_business"])
    return {"silver_path": str(out_root), "row_count": df.num_rows}

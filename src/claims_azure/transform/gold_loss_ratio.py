"""Local DuckDB mirror of ``03_silver_to_gold_loss_ratio.py``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

LOSS_RATIO_SQL = """
WITH losses AS (
    SELECT
        strftime(report_date, '%Y-%m') AS accounting_period,
        line_of_business,
        SUM(incurred_amount_usd) AS incurred_total_usd,
        SUM(payments_total_usd)  AS payments_total_usd,
        COUNT(*)                 AS claim_count
    FROM read_parquet(?)
    GROUP BY 1, 2
),
premiums AS (
    SELECT
        accounting_period,
        SUM(earned_premium_usd) AS earned_premium_usd
    FROM read_parquet(?)
    GROUP BY 1
)
SELECT
    l.accounting_period,
    l.line_of_business,
    l.incurred_total_usd,
    l.payments_total_usd,
    l.claim_count,
    p.earned_premium_usd,
    CASE WHEN p.earned_premium_usd > 0
         THEN l.incurred_total_usd / p.earned_premium_usd
         ELSE NULL END                                            AS loss_ratio,
    (l.payments_total_usd * 0.10)                                 AS lae_estimate_usd,
    CASE WHEN p.earned_premium_usd > 0
         THEN (l.incurred_total_usd + l.payments_total_usd * 0.10) / p.earned_premium_usd
         ELSE NULL END                                            AS combined_ratio
FROM losses l
LEFT JOIN premiums p USING (accounting_period)
"""


def gold_loss_ratio_monthly(
    fact_claim_glob: str,
    premiums_glob: str,
    gold_root: Path | str,
) -> dict[str, Any]:
    con = duckdb.connect(":memory:")
    df = con.execute(LOSS_RATIO_SQL, [fact_claim_glob, premiums_glob]).to_arrow_table()
    assert df is not None
    gold_root = Path(gold_root)
    gold_root.mkdir(parents=True, exist_ok=True)
    import pyarrow.parquet as pq

    out = gold_root / "fact_loss_ratio_monthly.parquet"
    pq.write_table(df, out)
    return {"gold_path": str(out), "row_count": df.num_rows}

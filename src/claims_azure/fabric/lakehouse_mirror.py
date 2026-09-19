"""DuckDB mirror of `fabric/notebooks/02_silver_to_gold_lakehouse.py`.

In Fabric this writes to a Delta table in the Lakehouse that Direct
Lake consumes. On a laptop we just produce the same Parquet file so
tests can verify the aggregate is correct.
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def rebuild_gold_loss_ratio(
    silver_fact_claim_glob: str,
    premiums_glob: str,
    gold_dir: Path,
) -> Path:
    """Rebuild monthly loss ratio from silver fact + premiums, write Parquet to gold.

    Mirrors the Fabric Lakehouse notebook `02_silver_to_gold_lakehouse.py`
    using the same column names + joins the local medallion already uses.
    `line_of_business` is carried on the fact (dim joined during
    silver), so no dim lookup is needed here.
    """
    gold_dir = Path(gold_dir)
    gold_dir.mkdir(parents=True, exist_ok=True)
    out_path = gold_dir / "fabric_monthly_loss_ratio.parquet"

    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                WITH fact AS (
                    SELECT
                        strftime(report_date, '%Y-%m')  AS month,
                        line_of_business                AS lob,
                        incurred_amount_usd,
                        payments_total_usd
                    FROM read_parquet('{silver_fact_claim_glob}')
                ),
                losses AS (
                    SELECT
                        month,
                        lob,
                        SUM(incurred_amount_usd)   AS incurred_total_usd,
                        SUM(payments_total_usd)    AS payments_total_usd
                    FROM fact
                    GROUP BY 1, 2
                ),
                premiums AS (
                    SELECT
                        accounting_period          AS month,
                        SUM(earned_premium_usd)    AS earned_premium_usd
                    FROM read_parquet('{premiums_glob}')
                    GROUP BY 1
                )
                SELECT
                    l.month                         AS month,
                    l.lob                           AS lob,
                    l.payments_total_usd            AS losses_paid,
                    COALESCE(p.earned_premium_usd, 0) AS premium_earned,
                    CASE
                        WHEN p.earned_premium_usd > 0
                            THEN l.incurred_total_usd / p.earned_premium_usd
                        ELSE NULL
                    END                             AS loss_ratio
                FROM losses l
                LEFT JOIN premiums p USING (month)
                ORDER BY 1, 2
            ) TO '{out_path}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()
    return out_path

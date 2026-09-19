"""DuckDB mirror of `fabric/warehouse/02_warehouse_loads.sql`.

Produces the same `mart.loss_ratio` star-schema mart that Fabric
Warehouse builds, written as a Parquet file for CI.
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def load_mart_loss_ratio(
    silver_fact_claim_glob: str,
    premiums_glob: str,
    mart_dir: Path,
) -> Path:
    """DuckDB mirror of `fabric/warehouse/02_warehouse_loads.sql`.

    Produces the same `mart.loss_ratio` row shape (month × lob) as the
    Fabric Warehouse SELECT INTO.
    """
    mart_dir = Path(mart_dir)
    mart_dir.mkdir(parents=True, exist_ok=True)
    out_path = mart_dir / "mart_loss_ratio.parquet"

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
                        SUM(incurred_amount_usd - payments_total_usd) AS losses_reserved,
                        SUM(payments_total_usd)                        AS losses_paid,
                        SUM(incurred_amount_usd)                       AS incurred_total_usd
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
                    l.month                               AS month,
                    l.lob                                 AS lob,
                    l.losses_paid                         AS losses_paid,
                    l.losses_reserved                     AS losses_reserved,
                    COALESCE(p.earned_premium_usd, 0)     AS premium_earned,
                    CASE
                        WHEN p.earned_premium_usd > 0
                            THEN l.incurred_total_usd / p.earned_premium_usd
                        ELSE NULL
                    END                                   AS loss_ratio
                FROM losses l
                LEFT JOIN premiums p USING (month)
                ORDER BY 1, 2
            ) TO '{out_path}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()
    return out_path

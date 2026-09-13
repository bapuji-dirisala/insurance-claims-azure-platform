"""Local DuckDB mirror of ``01_bronze_to_silver_policies_scd2.py``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

SCD2_SQL = """
WITH initial AS (
    SELECT
        policy_id,
        party_id,
        line_of_business,
        product_code,
        status,
        premium_annual_usd,
        deductible_usd,
        coverage_limit_usd,
        underwriter_code,
        state_region,
        effective_date AS valid_from
    FROM read_parquet(?)
),
endorsements AS (
    SELECT
        e.policy_id,
        p.party_id,
        p.line_of_business,
        p.product_code,
        p.status,
        p.premium_annual_usd + e.premium_delta_usd    AS premium_annual_usd,
        COALESCE(e.deductible_new_usd, p.deductible_usd) AS deductible_usd,
        p.coverage_limit_usd + e.coverage_limit_delta_usd AS coverage_limit_usd,
        p.underwriter_code,
        p.state_region,
        e.effective_date AS valid_from
    FROM read_parquet(?) e
    JOIN read_parquet(?) p USING (policy_id)
),
all_versions AS (
    SELECT * FROM initial
    UNION ALL
    SELECT * FROM endorsements
),
with_valid_to AS (
    SELECT
        *,
        LEAD(valid_from) OVER (PARTITION BY policy_id ORDER BY valid_from) AS valid_to_raw
    FROM all_versions
)
SELECT
    policy_id,
    party_id,
    line_of_business,
    product_code,
    status,
    premium_annual_usd,
    deductible_usd,
    coverage_limit_usd,
    underwriter_code,
    state_region,
    valid_from,
    COALESCE(valid_to_raw, DATE '9999-12-31') AS valid_to,
    valid_to_raw IS NULL AS is_current
FROM with_valid_to
"""


def bronze_to_silver_policies_scd2(
    policies_path: str,
    endorsements_path: str,
    silver_root: Path | str,
) -> dict[str, Any]:
    """Build silver.dim_policy_scd2 locally.

    ``policies_path`` + ``endorsements_path`` accept glob syntax so
    ``data/bronze/local/policies.parquet`` or
    ``data/bronze/local/policies/*.parquet`` both work.
    """
    con = duckdb.connect(":memory:")
    df = con.execute(SCD2_SQL, [policies_path, endorsements_path, policies_path]).to_arrow_table()
    silver_root = Path(silver_root)
    silver_root.mkdir(parents=True, exist_ok=True)
    import pyarrow.parquet as pq

    out = silver_root / "dim_policy_scd2.parquet"
    pq.write_table(df, out)
    return {"silver_path": str(out), "row_count": df.num_rows}

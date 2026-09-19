-- Daily refresh — pulls from the ADLS silver via a Fabric Warehouse
-- OPENROWSET external data source, so there's one source of truth
-- across Lakehouse (Direct Lake) and Warehouse (Import).

-- Replace the external data source URL + credentials via Key Vault.

TRUNCATE TABLE mart.loss_ratio;

INSERT INTO mart.loss_ratio (month, lob, losses_paid, losses_reserved, premium_earned, loss_ratio)
SELECT
    DATEFROMPARTS(YEAR(c.loss_date), MONTH(c.loss_date), 1) AS month,
    p.lob,
    SUM(c.paid_amount)                                       AS losses_paid,
    SUM(c.reserved_amount)                                   AS losses_reserved,
    SUM(p.premium_amount)                                    AS premium_earned,
    CASE
        WHEN SUM(p.premium_amount) > 0
            THEN (SUM(c.paid_amount) + SUM(c.reserved_amount)) / SUM(p.premium_amount)
        ELSE NULL
    END                                                       AS loss_ratio
FROM OPENROWSET(
    BULK 'https://stclaimslakehouse.dfs.core.windows.net/silver/claims_fact/',
    FORMAT = 'DELTA'
) AS c
INNER JOIN OPENROWSET(
    BULK 'https://stclaimslakehouse.dfs.core.windows.net/silver/policies_scd2/',
    FORMAT = 'DELTA'
) AS p
    ON c.policy_id = p.policy_id AND p.is_current = 1
GROUP BY DATEFROMPARTS(YEAR(c.loss_date), MONTH(c.loss_date), 1), p.lob;

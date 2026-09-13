-- Row filter + column mask + tag-based access control.
--
-- Row filter: restrict actuaries to the specific lines of business they
-- cover. The lookup table `claims_silver.access_lob_lookup` maps user →
-- allowed LOB; the filter joins on current_user().
-- Column mask: PII fields on silver.dim_policy_scd2 masked for anyone
-- outside the engineering + actuarial groups.
-- Tag-based: PII tag + sensitivity-high tag govern cross-workspace sharing.

CREATE OR REPLACE FUNCTION claims_silver.lob_access_filter(lob STRING)
    RETURNS BOOLEAN
    RETURN EXISTS (
        SELECT 1 FROM claims_silver.access_lob_lookup
        WHERE user_email = current_user() AND allowed_lob = lob
    );

-- Attach the filter to the SCD2 dim (actuaries only see their LOB).
ALTER TABLE claims_silver.dim_policy_scd2
    SET ROW FILTER claims_silver.lob_access_filter ON (line_of_business);

-- Column mask: mask party identifying columns unless caller is in
-- claims_engineers or claims_actuaries.
CREATE OR REPLACE FUNCTION claims_silver.mask_party_id(party_id STRING)
    RETURNS STRING
    RETURN CASE
        WHEN is_account_group_member('claims_engineers') THEN party_id
        WHEN is_account_group_member('claims_actuaries') THEN party_id
        ELSE '***MASKED***'
    END;

ALTER TABLE claims_silver.dim_policy_scd2
    ALTER COLUMN party_id SET MASK claims_silver.mask_party_id;

-- Governance tags — Purview picks these up for cross-workspace lineage.
ALTER CATALOG claims_bronze SET TAGS ('environment' = 'dev', 'data_zone' = 'bronze');
ALTER CATALOG claims_silver SET TAGS ('environment' = 'dev', 'data_zone' = 'silver', 'sensitivity' = 'high');
ALTER CATALOG claims_gold   SET TAGS ('environment' = 'dev', 'data_zone' = 'gold',   'audience' = 'actuary');

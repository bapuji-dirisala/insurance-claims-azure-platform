-- Fabric Warehouse — curated star schema for Power BI (Import mode)
-- and ad-hoc T-SQL analysts. Direct Lake uses the Lakehouse table in
-- 02_silver_to_gold_lakehouse.py; this warehouse is for analysts who
-- need T-SQL + stored procs + schema binding.

CREATE SCHEMA IF NOT EXISTS dim;
CREATE SCHEMA IF NOT EXISTS fact;
CREATE SCHEMA IF NOT EXISTS mart;
GO

-- Date dimension — populate via Phase 11 Power BI model or a
-- CTAS-style INSERT INTO SELECT from GENERATE_SERIES.
CREATE TABLE IF NOT EXISTS dim.date (
    date_key        DATE        NOT NULL PRIMARY KEY,
    year            INT         NOT NULL,
    quarter         INT         NOT NULL,
    month           INT         NOT NULL,
    month_name      VARCHAR(20) NOT NULL,
    day             INT         NOT NULL,
    is_weekend      BIT         NOT NULL
);

CREATE TABLE IF NOT EXISTS dim.policy (
    policy_key          BIGINT       NOT NULL PRIMARY KEY,  -- surrogate from SCD2 silver
    policy_id           VARCHAR(32)  NOT NULL,
    lob                 VARCHAR(20)  NOT NULL,
    insured_party_id    VARCHAR(32)  NOT NULL,
    agency_code         VARCHAR(16)  NULL,
    effective_date      DATE         NOT NULL,
    valid_from          TIMESTAMP    NOT NULL,
    valid_to            TIMESTAMP    NOT NULL,
    is_current          BIT          NOT NULL
);

CREATE TABLE IF NOT EXISTS fact.claims_monthly (
    claim_month         DATE          NOT NULL,
    policy_key          BIGINT        NOT NULL,
    lob                 VARCHAR(20)   NOT NULL,
    claim_count         INT           NOT NULL,
    paid_amount         DECIMAL(18,2) NOT NULL,
    reserved_amount     DECIMAL(18,2) NOT NULL,
    denied_count        INT           NOT NULL,
    PRIMARY KEY (claim_month, policy_key)
);

CREATE TABLE IF NOT EXISTS mart.loss_ratio (
    month           DATE          NOT NULL,
    lob             VARCHAR(20)   NOT NULL,
    losses_paid     DECIMAL(18,2) NOT NULL,
    losses_reserved DECIMAL(18,2) NOT NULL,
    premium_earned  DECIMAL(18,2) NOT NULL,
    loss_ratio      DECIMAL(9,6)  NULL,
    PRIMARY KEY (month, lob)
);

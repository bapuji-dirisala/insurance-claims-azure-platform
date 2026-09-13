-- Unity Catalog bootstrap: three catalogs (one per medallion zone) +
-- one schema per catalog. Three-level namespace (catalog.schema.table).

CREATE CATALOG IF NOT EXISTS claims_bronze
    MANAGED LOCATION 'abfss://bronze@${STORAGE_ACCOUNT}.dfs.core.windows.net/'
    COMMENT 'Raw ingested data from ADF pipelines.';

CREATE CATALOG IF NOT EXISTS claims_silver
    MANAGED LOCATION 'abfss://silver@${STORAGE_ACCOUNT}.dfs.core.windows.net/'
    COMMENT 'Cast + conformed + SCD2 dimensions + fact tables.';

CREATE CATALOG IF NOT EXISTS claims_gold
    MANAGED LOCATION 'abfss://gold@${STORAGE_ACCOUNT}.dfs.core.windows.net/'
    COMMENT 'Business marts for actuarial reporting + Power BI.';

CREATE SCHEMA IF NOT EXISTS claims_bronze.default;
CREATE SCHEMA IF NOT EXISTS claims_silver.default;
CREATE SCHEMA IF NOT EXISTS claims_gold.default;

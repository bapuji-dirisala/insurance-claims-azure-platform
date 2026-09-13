# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Bronze → silver: policies SCD2 (Delta MERGE)
# MAGIC
# MAGIC Reads `bronze.policies` (one row per policy) and `bronze.endorsements`
# MAGIC (mid-term changes), produces `silver.dim_policy_scd2` — a slowly-changing
# MAGIC type-2 dimension with validity windows + current flag.
# MAGIC
# MAGIC This notebook is the Databricks production artifact. The DuckDB mirror
# MAGIC under `src/claims_azure/transform/policies_scd2.py` runs the same logic
# MAGIC locally for unit tests + the laptop demo path.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parameters (DAB-wired)

# COMMAND ----------

dbutils.widgets.text("bronze_catalog", "claims_bronze")
dbutils.widgets.text("silver_catalog", "claims_silver")
dbutils.widgets.text("load_date", "")  # yyyy-MM-dd; empty = today

bronze_catalog = dbutils.widgets.get("bronze_catalog")
silver_catalog = dbutils.widgets.get("silver_catalog")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load bronze policies + endorsements

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable

policies_bronze = spark.read.table(f"{bronze_catalog}.policies")
endorsements_bronze = spark.read.table(f"{bronze_catalog}.endorsements")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Build the dimension change stream
# MAGIC
# MAGIC Each endorsement is a candidate SCD2 change. We treat the policy's
# MAGIC first appearance as effective_from = policies.effective_date and
# MAGIC compute `valid_to` as the next endorsement's effective_date (or
# MAGIC `9999-12-31` for the current record).

# COMMAND ----------

initial = (
    policies_bronze
    .select(
        "policy_id",
        "party_id",
        "line_of_business",
        "product_code",
        "status",
        "premium_annual_usd",
        "deductible_usd",
        "coverage_limit_usd",
        "underwriter_code",
        "state_region",
        F.col("effective_date").alias("valid_from"),
    )
)

endorsement_versions = (
    endorsements_bronze
    .join(policies_bronze.selectExpr("policy_id", "party_id", "line_of_business",
                                     "product_code", "status", "underwriter_code",
                                     "state_region", "coverage_limit_usd AS base_coverage",
                                     "deductible_usd AS base_deductible",
                                     "premium_annual_usd AS base_premium"),
          on="policy_id", how="inner")
    .select(
        "policy_id",
        "party_id",
        "line_of_business",
        "product_code",
        "status",
        (F.col("base_premium") + F.col("premium_delta_usd")).alias("premium_annual_usd"),
        F.coalesce("deductible_new_usd", "base_deductible").alias("deductible_usd"),
        (F.col("base_coverage") + F.col("coverage_limit_delta_usd")).alias("coverage_limit_usd"),
        "underwriter_code",
        "state_region",
        F.col("effective_date").alias("valid_from"),
    )
)

all_versions = initial.unionByName(endorsement_versions)

w = Window.partitionBy("policy_id").orderBy("valid_from")
dim = (
    all_versions
    .withColumn("valid_to", F.lead("valid_from").over(w))
    .withColumn("valid_to", F.coalesce(F.col("valid_to"), F.lit("9999-12-31").cast("date")))
    .withColumn("is_current", F.col("valid_to") == F.lit("9999-12-31"))
    .withColumn("effective_hash",
                F.sha2(F.concat_ws("||",
                                   "line_of_business", "product_code", "status",
                                   F.col("premium_annual_usd").cast("string"),
                                   F.col("deductible_usd").cast("string"),
                                   F.col("coverage_limit_usd").cast("string"),
                                   "underwriter_code", "state_region"), 256))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. MERGE into silver.dim_policy_scd2

# COMMAND ----------

target_name = f"{silver_catalog}.dim_policy_scd2"

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {target_name} (
        policy_id          STRING NOT NULL,
        party_id           STRING NOT NULL,
        line_of_business   STRING,
        product_code       STRING,
        status             STRING,
        premium_annual_usd DECIMAL(12,2),
        deductible_usd     DECIMAL(10,2),
        coverage_limit_usd DECIMAL(14,2),
        underwriter_code   STRING,
        state_region       STRING,
        valid_from         DATE,
        valid_to           DATE,
        is_current         BOOLEAN,
        effective_hash     STRING
    )
    USING DELTA
    PARTITIONED BY (is_current)
""")

tgt = DeltaTable.forName(spark, target_name)
(tgt.alias("tgt")
    .merge(
        dim.alias("src"),
        "tgt.policy_id = src.policy_id AND tgt.valid_from = src.valid_from",
    )
    .whenNotMatchedInsertAll()
    .execute())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Smoke check

# COMMAND ----------

display(spark.sql(f"SELECT COUNT(*) AS rows, SUM(CAST(is_current AS INT)) AS current_rows FROM {target_name}"))

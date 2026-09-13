# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Bronze → silver: claims fact table
# MAGIC
# MAGIC Reads `bronze.claims` + `bronze.payments`, joins payments onto claims,
# MAGIC produces `silver.fact_claim` with point-in-time policy context from
# MAGIC `silver.dim_policy_scd2`.

# COMMAND ----------

dbutils.widgets.text("bronze_catalog", "claims_bronze")
dbutils.widgets.text("silver_catalog", "claims_silver")

bronze_catalog = dbutils.widgets.get("bronze_catalog")
silver_catalog = dbutils.widgets.get("silver_catalog")

# COMMAND ----------

from pyspark.sql import functions as F

claims = spark.read.table(f"{bronze_catalog}.claims")
payments = spark.read.table(f"{bronze_catalog}.payments")
dim = spark.read.table(f"{silver_catalog}.dim_policy_scd2")

# Aggregate payments to one row per claim.
payment_agg = (
    payments.groupBy("claim_id")
    .agg(
        F.sum("amount_usd").alias("payments_total_usd"),
        F.count("*").alias("payment_count"),
        F.max("payment_date").alias("latest_payment_date"),
    )
)

fact = (
    claims
    .join(payment_agg, "claim_id", "left")
    .join(
        dim.where(F.col("is_current")),
        on="policy_id",
        how="left",
    )
    .select(
        "claim_id",
        "policy_id",
        "party_id",
        "line_of_business",
        "product_code",
        "underwriter_code",
        "loss_date",
        "report_date",
        "peril_code",
        "status",
        "reserve_amount_usd",
        "incurred_amount_usd",
        "paid_to_date_usd",
        F.coalesce("payments_total_usd", F.lit(0).cast("decimal(14,2)")).alias("payments_total_usd"),
        F.coalesce("payment_count", F.lit(0)).alias("payment_count"),
        "latest_payment_date",
        F.datediff("report_date", "loss_date").alias("report_lag_days"),
    )
)

fact.write.mode("overwrite").partitionBy("line_of_business").saveAsTable(
    f"{silver_catalog}.fact_claim"
)

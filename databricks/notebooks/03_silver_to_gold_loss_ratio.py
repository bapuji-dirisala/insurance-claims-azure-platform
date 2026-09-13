# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Silver → gold: loss ratio + combined ratio daily rollup
# MAGIC
# MAGIC Loss ratio = incurred / earned_premium.
# MAGIC Combined ratio = (incurred + LAE) / earned_premium.
# MAGIC
# MAGIC Both are the headline P&C performance metrics; actuaries dashboard off
# MAGIC the gold.fact_loss_ratio_daily table (see Phase 11 for Power BI).

# COMMAND ----------

dbutils.widgets.text("silver_catalog", "claims_silver")
dbutils.widgets.text("gold_catalog", "claims_gold")
dbutils.widgets.text("bronze_catalog", "claims_bronze")

silver_catalog = dbutils.widgets.get("silver_catalog")
gold_catalog = dbutils.widgets.get("gold_catalog")
bronze_catalog = dbutils.widgets.get("bronze_catalog")

# COMMAND ----------

from pyspark.sql import functions as F

fact = spark.read.table(f"{silver_catalog}.fact_claim")
premiums = spark.read.table(f"{bronze_catalog}.premiums")

losses_by_period = (
    fact
    .withColumn("accounting_period", F.date_format("report_date", "yyyy-MM"))
    .groupBy("accounting_period", "line_of_business")
    .agg(
        F.sum("incurred_amount_usd").alias("incurred_total_usd"),
        F.sum("payments_total_usd").alias("payments_total_usd"),
        F.count("*").alias("claim_count"),
    )
)

premium_by_period = (
    premiums
    .groupBy("accounting_period")
    .agg(F.sum("earned_premium_usd").alias("earned_premium_usd"))
)

gold = (
    losses_by_period.join(premium_by_period, "accounting_period", "left")
    .withColumn(
        "loss_ratio",
        F.col("incurred_total_usd") / F.when(F.col("earned_premium_usd") == 0, 1).otherwise(F.col("earned_premium_usd")),
    )
    .withColumn("lae_estimate_usd", F.col("payments_total_usd") * F.lit(0.10))  # placeholder 10% LAE
    .withColumn(
        "combined_ratio",
        (F.col("incurred_total_usd") + F.col("lae_estimate_usd"))
        / F.when(F.col("earned_premium_usd") == 0, 1).otherwise(F.col("earned_premium_usd")),
    )
)

gold.write.mode("overwrite").saveAsTable(f"{gold_catalog}.fact_loss_ratio_monthly")

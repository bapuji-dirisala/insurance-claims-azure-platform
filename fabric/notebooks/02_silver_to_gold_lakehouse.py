# Fabric notebook source
# ----------------------------------------------------------------------
# Fabric Lakehouse — rebuild monthly loss ratio inside OneLake.
#
# In production this reads from the shortcut-mounted silver (zero copy)
# and writes a Delta table in the Fabric Lakehouse that Direct Lake
# will consume. Direct Lake needs the table to live inside the
# Lakehouse itself; a shortcut can't be an import target in Direct
# Lake mode.
# ----------------------------------------------------------------------

# MAGIC %md
# MAGIC ## Load silver via shortcut

# COMMAND ----------

try:
    from pyspark.sql import SparkSession  # type: ignore[import-not-found]
    from pyspark.sql import functions as F  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    SparkSession = None  # noqa: N816


def build_gold_loss_ratio(spark):  # pragma: no cover — runs inside Fabric
    silver_claims = spark.read.format("delta").load("Files/silver_claims")
    silver_policies = spark.read.format("delta").load("Files/silver_policies")

    monthly = (
        silver_claims.alias("c")
        .join(
            silver_policies.filter(F.col("is_current")).alias("p"),
            on=F.col("c.policy_id") == F.col("p.policy_id"),
            how="inner",
        )
        .withColumn("month", F.date_trunc("month", F.col("c.loss_date")))
        .groupBy("month", F.col("p.lob").alias("lob"))
        .agg(
            F.sum("c.paid_amount").alias("losses_paid"),
            F.sum("c.reserved_amount").alias("losses_reserved"),
            F.sum("p.premium_amount").alias("premium_earned"),
        )
        .withColumn(
            "loss_ratio",
            F.when(
                F.col("premium_earned") > 0,
                (F.col("losses_paid") + F.col("losses_reserved")) / F.col("premium_earned"),
            ).otherwise(F.lit(None)),
        )
    )
    return monthly


# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Lakehouse Tables/ (Direct Lake target)

# COMMAND ----------

if SparkSession is not None:  # pragma: no cover
    spark = SparkSession.builder.getOrCreate()
    gold = build_gold_loss_ratio(spark)
    (
        gold.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable("claims_lakehouse.gold_monthly_loss_ratio")
    )

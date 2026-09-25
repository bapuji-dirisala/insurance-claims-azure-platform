# Databricks notebook source
# ----------------------------------------------------------------------
# Structured Streaming: Event Hubs claim-payments → bronze Delta
#
# Reads the `claim-payments` hub via the Kafka protocol (Event Hubs
# speaks Kafka 1.0+ on port 9093 when SASL/PLAIN auth is used, or AAD
# token auth via the databricks MI). Writes to a bronze Delta table
# with append-mode + a checkpoint on ADLS so the stream is
# fault-tolerant across restarts.
#
# A second notebook (not shown) would read the bronze stream, apply
# business rules, and write to silver.claims_payments.
# ----------------------------------------------------------------------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

EVENT_HUBS_NAMESPACE = "ehns-claims-dev"  # from Phase 10 TF output
EVENT_HUB_NAME = "claim-payments"
CONSUMER_GROUP = "databricks-structured-streaming"

BRONZE_PATH = "abfss://bronze@stclaimslakehouse.dfs.core.windows.net/claim_payments_stream"
CHECKPOINT_PATH = "abfss://bronze@stclaimslakehouse.dfs.core.windows.net/_checkpoints/claim_payments_stream"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Build the stream

# COMMAND ----------

try:
    from pyspark.sql import SparkSession  # type: ignore[import-not-found]
    from pyspark.sql import functions as F  # type: ignore[import-not-found]
    from pyspark.sql.types import (  # type: ignore[import-not-found]
        DecimalType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )
except ImportError:  # pragma: no cover
    SparkSession = None  # noqa: N816


PAYMENT_SCHEMA = (
    "StructType([StructField('payment_id', StringType()), "
    "StructField('claim_id', StringType()), "
    "StructField('policy_id', StringType()), "
    "StructField('amount_usd', DecimalType(14, 2)), "
    "StructField('authorized_at', TimestampType())])"
)


def build_stream(spark):  # pragma: no cover — runs inside Databricks
    kafka_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", f"{EVENT_HUBS_NAMESPACE}.servicebus.windows.net:9093")
        .option("subscribe", EVENT_HUB_NAME)
        .option("kafka.group.id", CONSUMER_GROUP)
        .option("kafka.sasl.mechanism", "OAUTHBEARER")
        .option("kafka.security.protocol", "SASL_SSL")
        .option("startingOffsets", "latest")
        .load()
    )

    schema = StructType(
        [
            StructField("payment_id", StringType(), False),
            StructField("claim_id", StringType(), False),
            StructField("policy_id", StringType(), False),
            StructField("amount_usd", DecimalType(14, 2), False),
            StructField("authorized_at", TimestampType(), False),
        ]
    )
    parsed = kafka_df.select(
        F.col("key").cast("string").alias("event_key"),
        F.from_json(F.col("value").cast("string"), schema).alias("p"),
        F.col("timestamp").alias("eh_enqueued_at"),
    ).select(
        "event_key",
        "p.*",
        F.current_timestamp().alias("ingest_timestamp"),
        "eh_enqueued_at",
    )
    return parsed


# COMMAND ----------

# MAGIC %md
# MAGIC ## Write with checkpoint

# COMMAND ----------

if SparkSession is not None:  # pragma: no cover
    spark = SparkSession.builder.getOrCreate()
    stream = build_stream(spark)
    (
        stream.writeStream.format("delta")
        .option("checkpointLocation", CHECKPOINT_PATH)
        .outputMode("append")
        .trigger(processingTime="30 seconds")
        .start(BRONZE_PATH)
    )

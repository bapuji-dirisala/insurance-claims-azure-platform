# Fabric notebook source
# ----------------------------------------------------------------------
# OneLake shortcuts to the ADLS Gen2 medallion written by the
# Databricks pipeline. This gives Fabric read-through access without
# ever moving the Parquet / Delta files — Direct Lake queries later
# benefit from zero copy.
#
# This file is a parseable Python script so unit tests can `ast.parse`
# it; in Fabric it runs as a PySpark notebook cell-by-cell.
# ----------------------------------------------------------------------

# MAGIC %md
# MAGIC ## Config

# COMMAND ----------

ADLS_ACCOUNT = "stclaimslakehouse"  # ADLS Gen2 account from Phase 1
BRONZE_FS = "bronze"
SILVER_FS = "silver"
GOLD_FS = "gold"

LAKEHOUSE_NAME = "claims_lakehouse"
WORKSPACE_ID = "<fabric-workspace-id>"  # pinned in CI from secret

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create OneLake shortcuts
# MAGIC
# MAGIC `notebookutils.lakehouse.create_shortcut` requires the Fabric
# MAGIC runtime; in CI we only validate the call signatures via mock.

# COMMAND ----------

try:
    import notebookutils  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    notebookutils = None  # noqa: N816 — matches Fabric runtime global


def ensure_shortcut(name: str, container: str, path: str) -> None:
    """Idempotent shortcut creation."""
    if notebookutils is None:
        print(f"[dry-run] would create shortcut Files/{name} -> {container}/{path}")
        return
    notebookutils.lakehouse.create_shortcut(  # pragma: no cover
        workspace_id=WORKSPACE_ID,
        lakehouse_name=LAKEHOUSE_NAME,
        shortcut_path=f"Files/{name}",
        target={
            "type": "AdlsGen2",
            "adlsGen2": {
                "location": f"https://{ADLS_ACCOUNT}.dfs.core.windows.net/{container}",
                "subpath": path,
            },
        },
    )


# Bronze — raw landing.
ensure_shortcut("bronze_policies", BRONZE_FS, "policies")
ensure_shortcut("bronze_claims", BRONZE_FS, "claims")
ensure_shortcut("bronze_payments", BRONZE_FS, "payments")

# Silver — conformed facts/dims.
ensure_shortcut("silver_policies", SILVER_FS, "policies_scd2")
ensure_shortcut("silver_claims", SILVER_FS, "claims_fact")

# Gold — business marts.
ensure_shortcut("gold_loss_ratio", GOLD_FS, "monthly_loss_ratio")

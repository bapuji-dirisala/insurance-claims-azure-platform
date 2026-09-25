"""Build Atlas / Purview lineage payloads for the Databricks medallion.

Purview auto-scans ADLS + Unity Catalog, but the *job*-level lineage
(this notebook reads A + B and writes C) is only auto-captured for
some integrations. Pushing custom Atlas entities over the Purview
Atlas Kafka endpoint fills the gap.

Here we only build the payload — the actual push to Purview is a
`kafka-python` producer in production. Keeping it as a pure function
means CI can snapshot the payload JSON without needing a Kafka client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AtlasEntity:
    """A single Atlas entity (dataset, process, etc.)."""

    type_name: str
    qualified_name: str
    display_name: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "typeName": self.type_name,
            "attributes": {
                "qualifiedName": self.qualified_name,
                "name": self.display_name,
                **self.attributes,
            },
        }


def build_lineage_payload(
    process_qualified_name: str,
    process_display_name: str,
    inputs: list[AtlasEntity],
    outputs: list[AtlasEntity],
    extra_process_attrs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an Atlas `process` entity + referred entities for its inputs/outputs."""
    process_attrs: dict[str, Any] = {
        "inputs": [
            {"typeName": e.type_name, "uniqueAttributes": {"qualifiedName": e.qualified_name}}
            for e in inputs
        ],
        "outputs": [
            {"typeName": e.type_name, "uniqueAttributes": {"qualifiedName": e.qualified_name}}
            for e in outputs
        ],
    }
    if extra_process_attrs:
        process_attrs.update(extra_process_attrs)

    referred: dict[str, dict[str, Any]] = {}
    for e in [*inputs, *outputs]:
        referred[e.qualified_name] = e.to_payload()

    return {
        "entity": {
            "typeName": "Process",
            "attributes": {
                "qualifiedName": process_qualified_name,
                "name": process_display_name,
                **process_attrs,
            },
        },
        "referredEntities": referred,
    }


# --- Prebuilt payloads for the medallion jobs ----------------------------

ADLS_URL = "https://stclaimslakehouse.dfs.core.windows.net"


def _delta_entity(container: str, path: str, display: str) -> AtlasEntity:
    return AtlasEntity(
        type_name="azure_datalake_gen2_path",
        qualified_name=f"{ADLS_URL}/{container}/{path}",
        display_name=display,
        attributes={
            "container": container,
            "path": path,
            "format": "DELTA",
        },
    )


def build_notebook_lineage(notebook: str) -> dict[str, Any]:
    """Return the Atlas payload describing a single medallion job's lineage.

    Supported `notebook` values match the files under `databricks/notebooks/`.
    """
    if notebook == "01_bronze_to_silver_policies_scd2":
        return build_lineage_payload(
            process_qualified_name="dbx://notebooks/01_bronze_to_silver_policies_scd2",
            process_display_name="Bronze → Silver: SCD2 Policies",
            inputs=[
                _delta_entity("bronze", "policies", "bronze.policies"),
                _delta_entity("bronze", "endorsements", "bronze.endorsements"),
            ],
            outputs=[_delta_entity("silver", "policies_scd2", "silver.policies_scd2")],
            extra_process_attrs={
                "owner": "claims-platform",
                "operation": "merge",
            },
        )
    if notebook == "02_bronze_to_silver_claims_fact":
        return build_lineage_payload(
            process_qualified_name="dbx://notebooks/02_bronze_to_silver_claims_fact",
            process_display_name="Bronze → Silver: Claims Fact",
            inputs=[
                _delta_entity("bronze", "claims", "bronze.claims"),
                _delta_entity("bronze", "payments", "bronze.payments"),
                _delta_entity("silver", "policies_scd2", "silver.policies_scd2"),
            ],
            outputs=[_delta_entity("silver", "claims_fact", "silver.claims_fact")],
            extra_process_attrs={
                "owner": "claims-platform",
                "operation": "aggregate_join",
            },
        )
    if notebook == "03_silver_to_gold_loss_ratio":
        return build_lineage_payload(
            process_qualified_name="dbx://notebooks/03_silver_to_gold_loss_ratio",
            process_display_name="Silver → Gold: Monthly Loss Ratio",
            inputs=[
                _delta_entity("silver", "claims_fact", "silver.claims_fact"),
                _delta_entity("bronze", "premiums", "bronze.premiums"),
            ],
            outputs=[_delta_entity("gold", "monthly_loss_ratio", "gold.monthly_loss_ratio")],
            extra_process_attrs={
                "owner": "actuarial",
                "operation": "aggregate",
            },
        )
    raise ValueError(f"unknown notebook: {notebook}")

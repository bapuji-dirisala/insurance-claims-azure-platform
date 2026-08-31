"""insurance-claims-azure-platform — dual-platform Azure DE lakehouse.

A P&C insurance claims lakehouse built once on Azure Databricks and once
on Microsoft Fabric — same medallion architecture, same Delta tables,
different compute and governance surfaces. Unity Catalog governs the
Databricks side; Microsoft Purview governs end-to-end lineage across
both. Event Hubs streams real-time claim payments; Power BI + Direct
Lake exposes gold to actuaries; Databricks Asset Bundles + Fabric
deployment pipelines promote through dev → staging → prod.

Every artifact ships as reviewable code — Terraform for the Azure
baseline, Databricks notebooks + DAB bundle definitions, Fabric item
JSON + pipeline YAML, ADF pipeline JSON, Unity Catalog + Purview
policy JSON, Power BI semantic model TMDL. The local demo path uses
Azurite (ADLS Gen2 emulator, free) + local PySpark + delta-rs so
nothing requires an Azure account to run.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]

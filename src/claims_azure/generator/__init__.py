"""Synthetic P&C insurance workload generator.

Six related datasets land in the bronze zone of the lakehouse:

* ``policies``     — in-force auto / home policies with coverages
* ``endorsements`` — mid-term policy changes (SCD2 fodder)
* ``claims``       — reported losses with reserves + statuses
* ``payments``     — claim payouts + fee reserves (money leaving the carrier)
* ``premiums``     — monthly earned-premium postings per policy
* ``parties``      — insured persons / vehicles / properties (PII-shaped)

All six are built from a single :class:`GeneratorConfig` with a shared
``seed``. The same seed produces byte-identical Parquet across runs,
which is what every downstream phase (ADF ingestion, Databricks medallion,
Fabric mirror, Purview lineage, Power BI semantic model) keys off.

Dependency-light at import time: pandas / pyarrow / Faker are only pulled
in when the generator actually runs, so ``claims-azure --version`` on a
bare install stays fast.
"""

from __future__ import annotations

from claims_azure.generator.config import GeneratorConfig
from claims_azure.generator.pipeline import GeneratedBundle, generate_bundle

__all__ = [
    "GeneratedBundle",
    "GeneratorConfig",
    "generate_bundle",
]

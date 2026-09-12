"""Ingestion helpers + local emulators for the ADF pipelines.

The committed ADF pipeline JSON lives under ``adf/pipelines/``. The
Python functions in this package emulate the same flow against Azurite +
a local DuckDB (standing in for Azure SQL) so a reader can clone, run
``claims-azure ingest-local policies-azsql`` or ``claims-azure
ingest-local claims-sftp``, and watch bronze containers fill with
Parquet — same partition layout the real pipeline produces.
"""

from __future__ import annotations

from claims_azure.ingest.bronze import BronzeTarget, bronze_prefix, write_parquet

__all__ = ["BronzeTarget", "bronze_prefix", "write_parquet"]

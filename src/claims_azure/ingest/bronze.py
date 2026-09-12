"""Shared bronze-zone helpers for ADLS Gen2 / Azurite writes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


@dataclass(frozen=True)
class BronzeTarget:
    """Logical pointer to a bronze dataset partition."""

    container: str
    dataset: str
    event_date: date
    source: str

    @property
    def prefix(self) -> str:
        return f"{self.dataset}/event_date={self.event_date.isoformat()}/{self.source}"


def bronze_prefix(
    container: str,
    dataset: str,
    *,
    event_date: date | datetime | None = None,
    source: str = "adf",
) -> BronzeTarget:
    """Build the canonical bronze prefix for one ADF-style write."""
    if event_date is None:
        event_date = datetime.now(UTC).date()
    elif isinstance(event_date, datetime):
        event_date = event_date.date()
    return BronzeTarget(
        container=container,
        dataset=dataset,
        event_date=event_date,
        source=source,
    )


def _local_root() -> Path:
    """Where Azurite's blob directory lives when the emulator is running.

    Developers typically run ``azurite --location ./__azurite__``; we
    honour ``AZURITE_BLOB_ROOT`` if they picked a different location.
    """
    root = os.environ.get("AZURITE_BLOB_ROOT")
    if root:
        return Path(root)
    return Path.cwd() / "__blobstorage__"


def write_parquet(
    rows: list[dict[str, Any]],
    schema: pa.Schema,
    target: BronzeTarget,
    *,
    local_root: Path | None = None,
) -> Path:
    """Write ``rows`` as Parquet under ``target`` in the local filesystem.

    This is the Azurite-backed fallback that lets a reader exercise the
    whole ADF-emulated flow with no Azure account. In real Azure the ADF
    Copy activity does this write; the committed pipeline JSON is the
    reviewable artifact for the production path.
    """
    root = local_root or _local_root()
    out_dir = root / target.container / target.prefix
    out_dir.mkdir(parents=True, exist_ok=True)

    columns: dict[str, list] = {field.name: [] for field in schema}
    for row in rows:
        for field in schema:
            columns[field.name].append(row.get(field.name))
    arrays = [pa.array(columns[field.name], type=field.type) for field in schema]
    table = pa.Table.from_arrays(arrays, schema=schema)

    out_path = out_dir / f"{target.source}-part-00000.parquet"
    pq.write_table(table, out_path, compression="snappy")
    return out_path

# Phase 3 — Azure Data Factory ingestion → ADLS Gen2 bronze

**Status:** Shipped. Two committed ADF pipelines (SFTP + Azure SQL
sources landing in bronze) plus a Python emulator that produces the
same bronze layout locally against Azurite.

## Two sources, one layout

Both pipelines produce Parquet in the same hive-partitioned layout the
Databricks medallion (Phase 4) + Fabric mirror (Phase 7) + Purview
lineage (Phase 9) all expect:

```
bronze/
├── claims/event_date=YYYY-MM-DD/sftp/part-00000.parquet
└── policies/event_date=YYYY-MM-DD/azsql/part-00000.parquet
```

## Committed ADF artifacts

```
adf/
├── linkedServices/
│   ├── ls_sftp_partner.json       # SFTP source, SSH keys from Key Vault
│   ├── ls_azsql_core.json         # Azure SQL via Managed Identity
│   ├── ls_adls_bronze.json        # ADLS Gen2 sink
│   └── ls_kv_main.json            # Key Vault lookup
├── datasets/
│   ├── ds_sftp_claims_csv.json    # CSV source
│   ├── ds_azsql_policies.json     # Azure SQL table
│   └── ds_adls_bronze_parquet.json # Parquet sink (parameterized dataset + loadDate)
└── pipelines/
    ├── pl_claims_sftp_to_bronze.json       # GetMetadata → ForEach → Copy
    └── pl_policies_azsql_to_bronze.json    # Watermarked incremental Copy
```

## Design decisions worth defending

1. **Managed Identity + Key Vault for every credential.** No connection
   strings or passwords in ADF JSON. SFTP private keys, DB connection
   strings, SFTP host key fingerprint all come from Key Vault via the
   `AzureKeyVaultSecret` type. This is the only way to get a Fortune-500
   security review signed off on an ADF deployment.
2. **Parameterized bronze dataset.** `ds_adls_bronze_parquet.json`
   takes `dataset` + `loadDate` parameters and builds the hive prefix
   via an expression. Every new source reuses the same dataset — no
   proliferation of near-identical dataset JSON.
3. **Incremental extraction via watermark lookup.** The SQL pipeline
   doesn't drop and reload — it does `Lookup → SetVariable → Copy with
   WHERE modified_at > @watermark`. The watermark table lives in
   `meta.pipeline_watermark` (DDL ships in Phase 4).
4. **Parallel ForEach for file-oriented sources.** `batchCount: 4`
   lets ADF process four partner files in parallel without exhausting
   the integration runtime.
5. **No inline schema on the Parquet sink.** `ds_adls_bronze_parquet`
   leaves `schema: []` so the sink infers from source — schema drift
   lands in bronze, silver catches it. This matches the "store first,
   prove later" bronze philosophy.
6. **Snappy compression** on Parquet (not GZIP). Snappy is CPU-cheap
   for Spark readers; GZIP is slightly smaller but reads 2-3× slower.
7. **Committed as code, deployed by Azure DevOps.** No "I made it in
   the ADF UI" artifacts — every change starts as a pull request.

## Local emulator

`claims-azure ingest-local` runs the same bronze write without any
Azure account:

```bash
pip install -e '.[dev,generator,azure]'
mkdir -p __blobstorage__

# Emulate pl_claims_sftp_to_bronze:
claims-azure ingest-local claims-sftp --seed 42

# Emulate pl_policies_azsql_to_bronze:
claims-azure ingest-local policies-azsql --seed 42

# Confirm layout:
find __blobstorage__ -name '*.parquet' | sort
```

The Python emulator and the ADF pipeline write **identical** Parquet
layouts — reviewers can diff `__blobstorage__/bronze/claims/...` against
the ADF Copy activity's output in a real deploy.

## Tests

`tests/test_ingest_pipelines.py` pins:

- bronze prefix layout (`claims/event_date=YYYY-MM-DD/sftp`)
- Parquet round-trip conformance to the committed `pyarrow` schema
- Both emulator functions produce the expected prefix
- Every committed ADF pipeline JSON parses + has activities
- SFTP linked service secrets all route through Key Vault (no inline)

Run:

```bash
pytest tests/test_ingest_pipelines.py -v
```

## What's next

Phase 4 picks up the bronze zone with Databricks: three notebooks
(bronze → silver → gold) using Delta Lake, SCD2 dimensions driven by
`endorsements`, fact tables for `claims` + `payments`, and a committed
Databricks Asset Bundle (DAB) definition that deploys all three to any
Databricks workspace.

# Phases 9 + 10 — Microsoft Purview + Event Hubs streaming

## Phase 9 — Microsoft Purview governance

Purview is the governance control plane that stitches lineage across
the whole Azure data estate. The portfolio uses it in three roles:

1. **Scan ADLS** — nightly scheduled scan of `stclaimslakehouse` picks
   up every Parquet / Delta file, classifies PII (SSN, policy number
   patterns), and lands dataset metadata in the data map.
2. **Scan Databricks Unity Catalog** — pulls `catalog.schema.table`
   metadata and column-level lineage from UC query history, giving
   analysts a navigable view of "where did `gold.monthly_loss_ratio`
   come from?".
3. **Scan Fabric** — Lakehouse shortcuts + Warehouse tables appear in
   the same data map so Direct Lake and T-SQL consumers show up next to
   the Databricks jobs that produce them.

### Custom Atlas lineage

Scans give you dataset-level lineage; **job-level** lineage ("notebook X
reads A + B and writes C") needs Atlas events pushed over the Purview
Atlas Kafka endpoint. `src/claims_azure/governance/atlas_lineage.py`
builds those payloads deterministically — one `Process` entity per
Databricks notebook, with inputs/outputs referencing the exact ADLS
paths the medallion writes.

Files:

- `terraform/modules/purview/` — Purview account + SystemAssigned
  identity + role grants (Storage Blob Data Reader + Storage Account
  Contributor on the ADLS lakehouse).
- `purview/collections.json` — collection hierarchy (bronze / silver /
  gold under a `claims-platform` parent).
- `purview/scan_definitions.json` — scan schedule definitions (nightly
  for ADLS, hourly offsets for UC + Fabric).
- `src/claims_azure/governance/atlas_lineage.py` — Atlas Process
  payload builders. Pure functions so CI can snapshot the JSON without
  a Kafka client.

Why Purview over OpenLineage: Microsoft Fabric only speaks Purview
natively; the whole point of Phase 7+8 is that Fabric consumes the
Databricks medallion. OpenLineage would need a translation layer.

## Phase 10 — Event Hubs streaming

Up to now the pipeline is batch-only. Phase 10 adds a streaming leg:

```
  Payment-authorized events
            │
            ▼
    Event Hubs: claim-payments (4 partitions, 1-day retention)
            │
            │ Databricks Structured Streaming
            │ (consumer-group: databricks-structured-streaming)
            ▼
   bronze/claim_payments_stream  (Delta append + checkpoint)
            │
            ▼
   silver.claims_payments        (not covered — one line of SQL)
```

Design decisions:

- **Standard tier, 4 partitions.** The portfolio demo never saturates
  a single partition; 4 is enough to prove partition-level parallelism
  for the Structured Streaming reader. `partition_count` is a variable
  so prod can scale.
- **`local_authentication_enabled = false`.** No shared-access
  signatures; both producers and consumers authenticate via Entra ID
  (OAUTHBEARER on the Kafka protocol). Databricks workspace MI gets
  the `Azure Event Hubs Data Receiver` role, producers get
  `Azure Event Hubs Data Sender`.
- **Dedicated consumer group per workload.** `databricks-structured-streaming`
  is isolated from any ad-hoc readers so checkpoint offsets never
  collide.
- **DLQ hub.** `claim-payments-retry` has 7-day retention so poisoned
  records survive long enough for a human to look at them.
- **No Capture → ADLS.** Capture duplicates every event; Structured
  Streaming checkpoints into ADLS, so Capture would be redundant and
  burn ingress units.

### Local emulator

Event Hubs has no free local emulator (Azurite is blob/queue/table
only). `src/claims_azure/streaming/emulator.py` fakes the receiver
side so unit tests can push `ClaimPaymentEvent` instances through
`LocalPaymentStream.flush_to_bronze(...)` and verify the Parquet shape
without hitting Azure.

Files:

- `databricks/streaming/01_payments_structured_streaming.py` — the
  real notebook. Reads Event Hubs via Kafka protocol, writes bronze
  Delta with `trigger(processingTime="30 seconds")` + checkpoint on
  ADLS.
- `src/claims_azure/streaming/payloads.py` — pinned
  `ClaimPaymentEvent` dataclass. `encode_payment()` matches what the
  Databricks `from_json` parser expects.
- `src/claims_azure/streaming/emulator.py` — in-process buffer that
  flushes to the same Parquet layout the streaming notebook writes.
- `terraform/modules/eventhubs/` — namespace + two hubs + consumer
  group + role grants.

## Running

```bash
export TF_VAR_enable_purview=true
export TF_VAR_enable_eventhubs=true
cd terraform && terraform plan

# Local Event Hubs tests (no Azure needed):
pytest tests/test_governance.py tests/test_streaming.py
```

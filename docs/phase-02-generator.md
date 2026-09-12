# Phase 2 — Synthetic P&C insurance generator

**Status:** Shipped. `claims-azure generate all` emits six bronze-ready
Parquet datasets with full referential integrity, deterministic by seed,
in a few seconds. Covers the full P&C insurance surface — policies,
endorsements (SCD2 fodder), claims (with reserves + payments), and
monthly earned-premium postings — so every later phase has a realistic
workload to run against.

## The six datasets

| Dataset        | Rows (default)        | Partitioning              | Primary key        | Purpose                     |
| -------------- | --------------------- | ------------------------- | ------------------ | --------------------------- |
| `parties`      | 2,000                 | single file               | `party_id`         | persons/vehicles/properties |
| `policies`     | 2,500                 | single file               | `policy_id`        | in-force contracts          |
| `endorsements` | 500                   | single file               | `endorsement_id`   | mid-term changes (SCD2)     |
| `claims`       | 1,000                 | `event_date=YYYY-MM-DD`   | `claim_id`         | reported losses             |
| `payments`     | 2,500                 | `event_date=YYYY-MM-DD`   | `payment_id`       | money leaving the carrier   |
| `premiums`     | ~30k (12/mo × policy) | `event_date=YYYY-MM-DD`   | `premium_id`       | earned-premium ledger       |

## Architecture

```
claims_azure.generator
├── config.py        GeneratorConfig (sizing + seed)
├── schemas.py       pyarrow schemas (source of truth across Databricks + Fabric + Purview)
├── parties.py       persons / vehicles / properties
├── policies.py      policies + endorsements + monthly premium postings
├── claims.py        claims + payments
└── pipeline.py      generate_bundle() + write_bundle() (Parquet writer)
```

`generate_bundle()` is pure data; `write_bundle()` is the only Parquet
I/O layer. This split means a Databricks notebook can import
`generate_bundle` directly and skip the Parquet writer — same code,
different sink.

## Reproducibility contract

Each module gets its own `random.Random(seed + N)` offset:

| Module         | Seed offset | What it drives            |
| -------------- | ----------- | ------------------------- |
| `parties`      | `+0`        | parties, Faker            |
| `policies`     | `+1`        | policies (effective_date, premium, LOB) |
| `endorsements` | `+2`        | mid-term policy changes   |
| `premiums`     | `+3`        | monthly earned-premium shuffle |
| `claims`       | `+4`        | losses, reserves, incurred |
| `payments`     | `+5`        | paymets drawn from claims |

Changing the party count doesn't shift policy effective dates, and so on
down the chain. The test suite pins this via `test_determinism` +
`test_different_seed_produces_different_bundle`.

## Domain correctness invariants (tested)

1. **Every `policies.party_id` is a real party** — insurance has no
   anonymous policyholders.
2. **Every `claims.policy_id` + `claims.party_id` is real** — and the
   party on the claim matches the party on the policy.
3. **Loss dates fall inside the policy term** — `effective_date ≤
   loss_date ≤ expiration_date`. Real claims against lapsed policies
   are a different data problem (coverage dispute) and belong in silver.
4. **Report date ≥ loss date** — physics-respecting ordering.
5. **`paid_to_date_usd ≤ incurred_amount_usd`** — a carrier can't pay
   more than it incurred.
6. **Denied claims have `paid_to_date_usd = 0`** — denial means no
   indemnity went out.
7. **`incurred_amount_usd ≤ 2 × coverage_limit_usd`** — defense costs
   can push incurred above the limit but 2× is a sanity ceiling.

Running the tests:

```bash
pip install -e '.[dev,generator]'
pytest tests/test_generator.py -v
```

## Usage

```bash
# Default sizing — about 30k rows total, ~3s wall-clock.
claims-azure generate all

# Larger demo for the dashboard phase.
claims-azure generate all \
  --seed 7 \
  --parties 5000 --policies 10000 --claims 5000 --payments 15000 \
  --out data/bronze/local
```

Every file lands under `--out` in the exact Hive partition layout the
Databricks medallion + Fabric mirror will pick up without re-crawling.

## What's next

Phase 3 wires the ADF ingestion path — simulated SFTP + Azure SQL
sources landing in the bronze zone of ADLS Gen2 (Azurite locally).
Phase 2's generator becomes the backing data generator for that
simulation.

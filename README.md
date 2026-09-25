# insurance-claims-azure-platform

[![CI](https://github.com/bapuji-dirisala/insurance-claims-azure-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/bapuji-dirisala/insurance-claims-azure-platform/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Dual-platform Azure data engineer lakehouse — the same P&C insurance
> claims medallion built once on Azure Databricks and once on Microsoft
> Fabric. Unity Catalog governs the Databricks side; Microsoft Purview
> governs end-to-end lineage across both. Event Hubs streams real-time
> claim payments. Power BI + Direct Lake exposes gold to actuaries.
> Databricks Asset Bundles + Fabric deployment pipelines promote
> through dev → staging → prod via Azure DevOps.

**Status (2026-10-25):** Phases 9 + 10 shipped — Microsoft Purview governance (account + MI role grants on ADLS, custom Atlas lineage payloads per Databricks notebook, collection hierarchy + nightly scan schedules) + Azure Event Hubs streaming (Standard namespace, two hubs, dedicated consumer group, Entra-ID-only auth, Databricks Structured Streaming notebook writing bronze Delta with checkpoint, local emulator for CI).

## Why this project

Senior Azure DE job descriptions in 2026 consistently ask for both
Azure Databricks and Microsoft Fabric experience. Most portfolio
projects pick one. **This repo builds the exact same medallion
architecture twice** — once on each platform — so a hiring manager
sees a side-by-side comparison of the two tools that the industry is
actively debating. Add Unity Catalog + Microsoft Purview for the full
governance story, Event Hubs for streaming, Power BI for the actuarial
dashboard, and Databricks Asset Bundles for environment promotion, and
the result answers every "did you use X on Azure?" question a senior
interviewer could ask.

The domain — P&C insurance claims with loss ratio, combined ratio,
IBNR, reinsurance recoverables — targets the Nordic + DACH enterprise
market (If, Sampo, LähiTapiola, Allianz, Munich Re, Zurich, AXA)
where Azure is the default stack and insurance is a huge employer.

## Cost model

**$0 locally, $0 in CI, optional free trials for the hosted services.**

| Service | Local demo (free) | Production path (code ships; reader deploys optionally) |
|---------|-------------------|--------------------------------------------------------|
| ADLS Gen2 | Azurite (Microsoft's own emulator) | Terraform |
| Azure Databricks | Databricks Community Edition (free forever) OR local PySpark | DAB bundle + notebooks + Terraform |
| Microsoft Fabric | 60-day trial, OR DuckDB over OneLake-as-filesystem locally | Fabric item JSON + pipeline YAML |
| Azure Synapse Analytics | n/a (local DuckDB equivalent) | SQL scripts + Terraform |
| Azure Data Factory | n/a — run same Python ingestion locally | ADF pipeline JSON + Terraform |
| Event Hubs | Local Kafka in Colima (same consumer code) | Terraform + consumer code |
| Unity Catalog | n/a (no local emulator) | DDL + Terraform |
| Microsoft Purview | n/a | Policy JSON + Terraform |
| Power BI + Direct Lake | Power BI Desktop (free) over local Parquet | Semantic model TMDL + workspace config |
| Azure DevOps | Free tier (unlimited for small projects) + GHA mirror | Pipeline YAML |
| Entra ID + Managed Identity + Key Vault | n/a | Terraform |
| CI | GitHub Actions on a public repo (unlimited free) | — |

**No credit card required** to run anything in this repo end-to-end.
The committed Terraform + DAB + Fabric artifacts are the deliverable;
a reader with Azure credits can `terraform apply` them unchanged.

## Tech stack

| Layer | Tech |
|-------|------|
| Language | Python 3.11 · PySpark · Spark SQL · T-SQL · HCL |
| Storage | ADLS Gen2 (Azurite locally) · OneLake (Fabric trial, DuckDB locally) |
| Compute (Databricks path) | Azure Databricks + Delta Lake · DAB bundles |
| Compute (Fabric path) | Microsoft Fabric Notebooks + Fabric Data Factory + Fabric Warehouse |
| SQL warehouse | Azure Synapse Analytics (serverless SQL) · Fabric Warehouse |
| Ingestion | Azure Data Factory (pipeline JSON) · Azure Event Hubs streaming |
| Governance | Unity Catalog (Databricks) · Microsoft Purview (end-to-end) |
| Security | Entra ID · Managed Identity · Key Vault |
| BI | Power BI semantic model + Direct Lake |
| IaC | Terraform (remote state on Azure Storage) |
| CI/CD | Azure DevOps Pipelines (+ GitHub Actions mirror for public demo) |
| Dev tooling | ruff · mypy · pre-commit · pytest · Azurite |

## Twelve-phase roadmap

| #  | Phase                                          | Doc                                                           | Status      |
|----|------------------------------------------------|---------------------------------------------------------------|-------------|
| 0  | Scaffolding, tooling, CI                       | [docs/phase-00-scaffolding.md](docs/phase-00-scaffolding.md)  | shipped     |
| 1  | Azure baseline (Terraform) — RG, ADLS Gen2, Key Vault, Entra MI, workspace shells | [docs/phase-01-azure-baseline.md](docs/phase-01-azure-baseline.md) | shipped     |
| 2  | Synthetic P&C generator — policies, endorsements, claims, payments, premiums | [docs/phase-02-generator.md](docs/phase-02-generator.md) | shipped     |
| 3  | ADF ingestion — simulated SFTP + Azure SQL → ADLS Gen2 bronze | [docs/phase-03-adf-ingestion.md](docs/phase-03-adf-ingestion.md) | shipped     |
| 4  | Databricks medallion — bronze → silver (SCD2 dims) → gold (fact tables) | [docs/phase-04-05-06-databricks-medallion.md](docs/phase-04-05-06-databricks-medallion.md) | shipped     |
| 5  | Unity Catalog governance — 3-level namespace, row filters on PII, LF-style tag grants | [docs/phase-04-05-06-databricks-medallion.md](docs/phase-04-05-06-databricks-medallion.md) | shipped     |
| 6  | Databricks Asset Bundles — dev / staging / prod deploys via Azure DevOps | [docs/phase-04-05-06-databricks-medallion.md](docs/phase-04-05-06-databricks-medallion.md) | shipped     |
| 7  | Microsoft Fabric mirror — same medallion rebuilt in OneLake Lakehouse + Fabric Notebooks | [docs/phase-07-08-fabric-lakehouse-warehouse.md](docs/phase-07-08-fabric-lakehouse-warehouse.md) | shipped |
| 8  | Fabric Warehouse + Direct Lake — gold materialized for Power BI | [docs/phase-07-08-fabric-lakehouse-warehouse.md](docs/phase-07-08-fabric-lakehouse-warehouse.md) | shipped |
| 9  | Microsoft Purview — end-to-end lineage across Databricks + Fabric, PII classification | [docs/phase-09-10-purview-eventhubs.md](docs/phase-09-10-purview-eventhubs.md) | shipped |
| 10 | Event Hubs streaming — real-time claim payments → Structured Streaming → Delta | [docs/phase-09-10-purview-eventhubs.md](docs/phase-09-10-purview-eventhubs.md) | shipped |
| 11 | Power BI semantic model — loss ratio, combined ratio, IBNR dashboard | *coming soon*                            | planned     |
| 12 | Observability + docs + exposures — Azure Monitor, hosted docs, actuarial calc notes | *coming soon*          | planned     |

Each phase ships as one small, focused commit. See
[`docs/`](docs/) for per-phase design + rationale.

## Getting started (free local path)

Prerequisites:

- macOS or Linux, Python 3.11
- Node + npm (for Azurite)
- [Colima](https://github.com/abiosoft/colima) if you want local Kafka (`brew install colima && colima start --cpu 4 --memory 8`)
- Terraform ≥ 1.6 (`brew install terraform`)
- Azure CLI (`brew install azure-cli`)
- Databricks CLI (`brew tap databricks/tap && brew install databricks`)

```bash
git clone https://github.com/bapuji-dirisala/insurance-claims-azure-platform.git
cd insurance-claims-azure-platform

python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# Verify base install:
pytest -q
claims-azure --version
```

Install extras as you work through each phase:

```bash
pip install -e ".[generator]"       # Phase 2
pip install -e ".[azure]"           # Phase 1+ (azure-storage, azure-identity, azure-eventhub, etc.)
pip install -e ".[spark]"           # Phase 4+ (PySpark + delta-spark; needs Java 17)
pip install -e ".[bi]"              # Phase 11 (Power BI semantic model validation)
```

## Project conventions

- **Code style.** Minimal inline comments; code is self-explanatory via
  naming + short docstrings. `from __future__ import annotations` at
  the top of every module. Type hints on all public functions. Long
  design rationale lives in `docs/phase-NN-*.md`.
- **Commit style.** Conventional-commit prefixes (`chore:`, `feat:`,
  `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, `build:`, `ci:`).
  Subject ≤ 72 chars, imperative mood. One phase per commit when
  possible. Push with `--force-with-lease`.
- **Pre-commit.** ruff + mypy + hygiene set runs on every commit.
  `pre-commit run --all-files` before pushing to catch anything the
  hook missed.
- **Notebook format.** Databricks + Fabric notebooks are committed as
  `.py` files with `# COMMAND ----------` cell markers (the plain-text
  Databricks source format) so they diff cleanly in PRs.

## License

MIT — see [LICENSE](LICENSE).

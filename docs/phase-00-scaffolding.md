# Phase 0 — scaffolding, tooling, CI

**Status:** shipped (2026-10-25)

## Goal

Stand up a portfolio-grade repo skeleton so Phases 1-12 can land as
small, focused commits without re-thinking packaging, lint, type-check,
CI, identity, or secrets on each one. Zero application code — every
Phase 0 artifact is a convention.

## What this phase delivers

- **`pyproject.toml`** — hatchling, Python 3.11+, one `claims-azure`
  console script, and five phase-indexed optional-dependency groups:
  `dev`, `generator`, `azure`, `spark`, `bi`. Each phase installs only
  what it needs.
- **`.pre-commit-config.yaml`** — ruff (check + format), mypy on
  `src/`, plus the standard byte-level hygiene set.
- **`.github/workflows/ci.yml`** — two jobs (`lint-and-typecheck` then
  `pytest`) with pip caching, concurrency cancellation, Python 3.11
  pinned. Public repo → unlimited GHA minutes = $0 CI cost forever.
- **`src/claims_azure/`** — package skeleton with `__version__` and an
  argparse CLI. Later phases attach `generate`, `ingest-adf`,
  `medallion`, `fabric-mirror`, `stream`, `validate-pbi` via lazy imports.
- **`tests/test_smoke.py`** — 5 Phase 0 tests: package imports, CLI
  version flag, CLI version subcommand, no-args help, console-script
  entry point installed.
- **`LICENSE`** — MIT, 2026 Bapuji Dirisala.
- **`.gitignore`** — Python + Terraform + Azurite + notebook caches
  (`.databricks/`, `.fabric/`, `.ipynb_checkpoints/`) + Azure
  credentials + Databricks CLI config.
- **`.env.example`** — every env var documented; defaults wire to the
  free local path (Azurite + local PySpark).

## Design decisions

### Dual-platform (Databricks AND Fabric) is the signature

Senior Azure DE job descriptions in 2026 consistently ask for both
Azure Databricks and Microsoft Fabric. The differentiator vs typical
portfolio projects is building the **same medallion architecture
twice** — once on Databricks (notebooks + DAB bundle), once on Fabric
(notebooks + Fabric Data Factory pipelines + Warehouse). Unity Catalog
governs the Databricks side; Microsoft Purview governs end-to-end
lineage across both. A reader comparing the two implementations gets a
side-by-side view of the trade-offs that the industry is actively
debating in 2026.

### Cost model: $0 forever, deployable in one `terraform apply`

Nothing in this repo requires a real Azure account to run end-to-end.
The exact same code paths run against:

- **Azurite** (Microsoft's free ADLS Gen2 emulator) for storage.
- **Local PySpark + delta-rs** (free) as the Databricks + Fabric Spark
  stand-in. The same notebook code runs identically against a
  Databricks workspace or a Fabric workspace when a reader points at
  one.
- **DuckDB** (free, embedded) as the Fabric Warehouse / Direct Lake
  stand-in — Parquet-over-storage queries work identically.
- **Databricks Community Edition** (free forever, no credit card) as
  the "real" Databricks target if a reader wants to validate notebooks
  against a hosted workspace.
- **Microsoft Fabric trial** (60 days free) as the "real" Fabric target.

Every artifact ships as reviewable code: Terraform for the Azure
baseline, Databricks notebooks + DAB bundle definitions, Fabric item
JSON + pipeline YAML, ADF pipeline JSON, Unity Catalog + Purview
policy JSON, Power BI semantic model TMDL. Hiring managers read the
IaC + bundle + notebook sources — they don't need me to spend money
proving a `terraform apply` works.

### Phase-indexed optional-dependency extras

`[dev]` pulls ruff + mypy + pytest + pre-commit. The other four extras
map one-to-one to the roadmap phases that need them:

- `[generator]` — Phase 2 synthetic P&C data (Faker, pandas, pyarrow).
- `[azure]` — Phase 1+ Azure SDK (storage + identity + Key Vault +
  Event Hubs).
- `[spark]` — Phase 4+ PySpark + delta-spark (heavy install, Java 17
  needed).
- `[bi]` — Phase 11 Power BI semantic model validation helpers.

### CLI uses argparse, not click

Lower dependency footprint, same expressiveness for the subcommand
pattern we actually use. Consistent with every other repo in the
portfolio. Subcommand modules are lazy-imported from `main()`.

## How to run

```bash
cd ~/Documents/GitHub/insurance-claims-azure-platform
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# Verify scaffold:
pytest -q                               # 5 smoke tests, all green
ruff check .                             # no issues
ruff format --check .                    # no formatting drift
mypy src/                                # no type errors
claims-azure --version                   # prints "claims-azure 0.1.0"
```

## Gotchas

- **Terraform state never lands in git.** `.gitignore` excludes
  `terraform/.terraform/`, `*.tfstate*`, `*.tfplan`, and all
  `terraform.tfvars` variants. Remote state (Azure Storage + blob lock)
  gets wired in Phase 1.

- **`.databrickscfg` is excluded** so a reader's local Databricks PAT
  can never leak via a stray `git add -A`.

- **Databricks notebook format.** The committed notebooks use
  `.py` with `# COMMAND ----------` cell markers (the plain-text
  Databricks source format), not `.ipynb`. Reviewable in GitHub without
  the Jupyter renderer, roundtrips cleanly through the Databricks CLI.

- **Azurite requires Node + npm.** `npm install -g azurite` installs
  it; `azurite --silent &` starts it. The emulator is Microsoft's own
  tool and matches the ADLS Gen2 behavior closely.

## References

- [`../README.md`](../README.md) — 12-phase roadmap + tech stack.
- [`../pyproject.toml`](../pyproject.toml) — authoritative extras list.

## Next phase

**Phase 1** — Azure baseline. Terraform modules for the resource
group, ADLS Gen2 storage account with hierarchical namespace, Key
Vault, Entra ID managed identity, Databricks workspace shell, and
Microsoft Fabric capacity shell. Remote state on Azure Storage with
blob lease locking. `terraform plan` runs green offline; `terraform
apply` works against a real subscription when a reader opts in.

# Phases 11 + 12 — Power BI semantic model + Azure Monitor observability

The last two phases finish the loop: Phase 11 turns the actuarial gold
mart into a reviewable Power BI semantic model (TMDL, not .pbix) that
analysts bind to via Direct Lake, and Phase 12 wires every service in
the stack into one Log Analytics workspace with alerts.

## Phase 11 — Power BI semantic model (Direct Lake)

```
    Fabric Lakehouse: claims_lakehouse
    └── Tables/gold_monthly_loss_ratio  (Delta)
                        │
                        │  Direct Lake
                        │  (zero-copy, Vertipaq-free)
                        ▼
    Power BI semantic model: Claims_Actuarial
            │
            ├── measure 'Loss Ratio'       — (paid + reserved) / premium
            ├── measure 'Combined Ratio'   — loss ratio + expense ratio
            ├── measure 'IBNR Estimate'    — premium × avg LR × IBNR factor
            ├── measure 'Premium YTD'
            └── measure 'Losses YTD'
                        │
                        ▼
             Power BI reports / Fabric dashboard
```

Design decisions:

- **TMDL, not .pbix.** `powerbi/semantic-model/model.tmdl` is the full
  semantic model as a reviewable text file. Tabular Editor + Fabric CLI
  deploy from it; no binary artifacts in the repo.
- **Direct Lake partition.** `mode: directLake` binds directly to the
  Lakehouse Delta table. No cache refresh, no Vertipaq compression, no
  gateway. Reads bypass the Vertipaq engine entirely for sub-second
  queries on 10M+ rows.
- **Measures are the contract.** The gold table has raw metrics;
  `Loss Ratio`, `Combined Ratio`, and `IBNR Estimate` are measures
  defined in TMDL that reports consume. If the raw columns change, the
  measures adapt in one place — reports keep working.
- **Expense ratio is a constant (0.28) today.** A real actuarial model
  would wire this to an expense fact table; the placeholder is called
  out in a code comment so a reviewer isn't surprised.
- **DAX measures mirrored in Python** (`src/claims_azure/bi/measures.py`).
  Loss ratio, combined ratio, IBNR, premium YTD, losses YTD all have
  pure-Python equivalents so parity is unit-testable. Any time the DAX
  changes, the Python mirror has to change — a reviewer notices.

Files:

- `powerbi/semantic-model/model.tmdl` — semantic model.
- `powerbi/semantic-model/dashboard.json` — human-readable layout notes
  (the actual report is defined in Power BI; this file documents the
  intent).
- `src/claims_azure/bi/measures.py` — Python mirrors of each measure.
- `tests/test_bi.py` — 10 tests pinning parity between the DAX text and
  the Python implementation.

## Phase 12 — Azure Monitor observability

One Log Analytics workspace captures diagnostics from every service in
the stack so cross-service queries work:

- **ADLS Gen2** — transaction + capacity metrics forwarded via
  `azurerm_monitor_diagnostic_setting`.
- **Event Hubs** — archive, operational, and auto-scale logs plus all
  metrics.
- **(hooks ready for Databricks + ADF)** — the workspace is wired, the
  diagnostic settings are a one-line add in those modules.

Alerts:

- **`alert-storage-throttled`** — fires when ADLS returns `ServerBusyError`
  responses in a 5-minute window. Severity 2.
- **`alert-eventhubs-silent`** — fires when `IncomingMessages < 1` for
  15 minutes (producer or auth is broken). Severity 3.

Both alerts route through a single **action group** that can take an
email receiver (opt-in via `TF_VAR_observability_ops_email`) + any
webhook you add. No PagerDuty-specific integration in the module —
operators wire their own.

Files:

- `terraform/modules/observability/` — Log Analytics workspace +
  diagnostic settings + alerts + action group.

## Running

```bash
export TF_VAR_enable_observability=true
export TF_VAR_observability_ops_email=you@example.com
cd terraform && terraform plan
```

For Power BI:

```bash
# Install the Fabric CLI if you haven't:
# https://aka.ms/fabric-cli

fab config set-default-workspace '<workspace-name>'
fab publish-tmdl powerbi/semantic-model/model.tmdl
```

Or open Tabular Editor 3 → Open from TMDL → connect to the Fabric
workspace → Deploy.

## Project complete

With this phase shipped, both P4 and P7 are at 12/12. See the project
README for the full roadmap link grid.

# Phase 1 — Azure baseline (Terraform)

**Status:** Shipped. `terraform validate` is green locally and in CI; the
HCL stands up a complete three-container ADLS Gen2 lakehouse + three
hand-scoped user-assigned managed identities + a Key Vault, ready for
Phases 2–12 to attach ingestion, Databricks, Fabric, and Purview on top.

## What the baseline ships

```
RG: claims-local-rg-XXXXXX
├── Storage (ADLS Gen2, HNS=true)
│   claimslocallakeXXXXXX
│   ├── bronze/        container
│   ├── silver/        container
│   └── gold/          container
│       + versioning, soft-delete (30d), change-feed, lifecycle (cool→archive)
│       + TLS1.2 min, SAS/shared-key DISABLED (Entra ID only), public access OFF
├── Key Vault
│   claims-local-kv-XXXXXX
│   └── RBAC-mode, soft-delete 7d
└── User-Assigned Managed Identities
    ├── claims-local-adf-mi-XXXXXX   → Blob Data Contributor on bronze/     + KV Secrets User
    ├── claims-local-dbx-mi-XXXXXX   → Reader on bronze, Contributor on silver/gold + KV Secrets User
    └── claims-local-fab-mi-XXXXXX   → Blob Data Reader on gold             + KV Secrets User
```

## Why this shape (senior Azure DE signals)

1. **ADLS Gen2 with hierarchical namespace** — not a vanilla Blob
   account. Delta Lake / Iceberg write amplification is painful without
   HNS; this is table stakes for any Databricks / Fabric workload.
2. **Shared-key access disabled**. Entra ID auth only. Databricks + ADF
   + Fabric all authenticate as their managed identity; no SAS tokens
   float around.
3. **Three managed identities, hand-scoped per container.** No
   subscription-level `Storage Blob Data Contributor` wildcard. ADF
   writes bronze; Databricks reads bronze/silver, writes silver/gold;
   Fabric reads gold (BI consumer). This matches how a Fortune-500
   platform team actually isolates workloads.
4. **Key Vault in RBAC mode** (not access policies). This is the
   recommended mode since 2023 and what every modern Terraform
   reference now uses.
5. **Lifecycle policy with Delta-aware prefixes.** `_delta_log/` is
   never tiered — cooling it would break Delta reads. The policy only
   acts on prefix-matched data files and uses an index-tag filter so
   tables tagged `tier-eligible=true` get moved automatically.
6. **DRY module pattern.** `locals.layers = { bronze, silver, gold }`
   drives container creation via `for_each`. Adding a `platinum` tier
   (future phase) is one line.
7. **Local-first.** `use_local_backend = true` lets anyone run
   `terraform validate` without an Azure subscription — the HCL is the
   deliverable, same model as the P4 LocalStack flow and the P3
   DuckDB-as-Snowflake flow.

## Architecture: provider dual-mode

Same AzureRM provider block covers both paths:

- `use_local_backend = true` (default) — `skip_provider_registration =
  true`, `subscription_id` and `tenant_id` default to `null`. The tree
  stands up under `terraform validate` with nothing but Terraform
  installed.
- `use_local_backend = false` — real subscription + tenant, `az login`
  handles auth, `terraform apply` creates everything.

The `azuread` provider is wired the same way (tenant-aware when real,
null otherwise). This is the Azure equivalent of P4's AWS endpoint
dynamic block for LocalStack.

## Running it

```bash
# Validate the HCL (no Azure access needed):
./scripts/tf-local.sh validate

# See what would be created locally:
./scripts/tf-local.sh plan

# Format (CI enforces this via terraform fmt -check):
./scripts/tf-local.sh fmt
```

## File layout

```
terraform/
├── versions.tf                           # provider + Terraform version pins
├── providers.tf                          # azurerm + azuread, dual-mode
├── variables.tf                          # project / environment / region / suffix
├── main.tf                               # RG + both module calls
├── outputs.tf                            # names + IDs for downstream phases
├── backend.tf.example                    # commented Azure Storage remote state
├── modules/
│   ├── storage-lakehouse/                # ADLS Gen2 + 3 containers + lifecycle
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── identity-baseline/                # 3 MIs + Key Vault + hand-scoped RBAC
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    ├── local/terraform.tfvars            # the validation path (committed)
    └── dev/terraform.tfvars.example      # the "real Azure" template (never fill in and commit)
```

## CI

`.github/workflows/ci.yml` adds a `terraform-check` job alongside the
Python lint / typecheck / test jobs:

- `hashicorp/setup-terraform@v3` pins `terraform_version: "~1.9"`
- `terraform fmt -recursive -check -diff` — HCL style enforced
- `terraform init -backend=false -input=false` — no remote state in CI
- `terraform validate -no-color` — the real check

Combined with the Python jobs, every push now proves end-to-end that
both the Python packaging and the IaC compile cleanly.

## What's next

Phase 2 ships the synthetic property & casualty insurance generator —
policies, endorsements, claims, payments, premiums — the input dataset
every subsequent phase (ADF ingestion, Databricks medallion, Fabric
mirror, Purview lineage) will consume.

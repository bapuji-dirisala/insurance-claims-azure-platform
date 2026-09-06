// Azure provider configuration.
//
// Local-dev path: `var.use_local_backend = true` means the Terraform tree
// stays "paper-only" — `terraform plan` runs with `azurerm` in a validation
// mode that doesn't contact Azure. We never `apply` to a real subscription
// as part of this portfolio project (zero-cost rule). The HCL is the
// reviewable artifact; Databricks CE + Fabric trial + Azurite + local
// PySpark are what actually run.
//
// Real-Azure path (what a reader would do to deploy): drop
// `use_local_backend` to false, set `subscription_id`, `tenant_id`,
// `azure_region`, authenticate via `az login`, and `terraform apply`.

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }

  // When use_local_backend is true we skip provider registration so a
  // reader without an Azure subscription can still `terraform validate`.
  skip_provider_registration = var.use_local_backend

  subscription_id = var.use_local_backend ? null : var.subscription_id
  tenant_id       = var.use_local_backend ? null : var.tenant_id
}

provider "azuread" {
  tenant_id = var.use_local_backend ? null : var.tenant_id
}

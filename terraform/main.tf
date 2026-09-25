// Random suffix for globally-unique names (storage accounts, Key Vault)
// when the operator didn't pin one via `resource_suffix`.
resource "random_id" "suffix" {
  byte_length = 3
}

locals {
  suffix       = var.resource_suffix != "" ? var.resource_suffix : random_id.suffix.hex
  name_prefix  = "${var.project}-${var.environment}"
  short_prefix = "${substr(var.project, 0, 6)}${substr(var.environment, 0, 4)}"

  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
    Phase       = "1-azure-baseline"
    Repository  = "insurance-claims-azure-platform"
  }
}

// Single resource group holds the whole demo stack. Real deployments
// typically split into {network, data, compute} RGs — the HCL is organized
// so adding more RGs is a one-line change in the module calls.
resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg-${local.suffix}"
  location = var.azure_region
  tags     = local.common_tags
}

module "storage_lakehouse" {
  source = "./modules/storage-lakehouse"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  short_prefix        = local.short_prefix
  suffix              = local.suffix
  retention_days      = var.retention_days
  tags                = local.common_tags
}

module "identity_baseline" {
  source = "./modules/identity-baseline"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  name_prefix         = local.name_prefix
  suffix              = local.suffix
  tenant_id           = var.tenant_id
  principal_object_id = var.principal_object_id
  storage_account_id  = module.storage_lakehouse.storage_account_id
  bronze_container_id = module.storage_lakehouse.bronze_container_id
  silver_container_id = module.storage_lakehouse.silver_container_id
  gold_container_id   = module.storage_lakehouse.gold_container_id
  tags                = local.common_tags
}

// Phase 9 — Microsoft Purview governance account.
// Gated on var.enable_purview because Purview provisions a managed
// resource group under the hood (slow + nonzero cost) and we don't
// always want that in `terraform plan` smoke tests.
module "purview" {
  count  = var.enable_purview ? 1 : 0
  source = "./modules/purview"

  name_prefix         = local.short_prefix
  suffix              = local.suffix
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  adls_account_id     = module.storage_lakehouse.storage_account_id
  tags                = local.common_tags
}

// Phase 10 — Event Hubs for real-time claim-payment events.
module "eventhubs" {
  count  = var.enable_eventhubs ? 1 : 0
  source = "./modules/eventhubs"

  name_prefix                = local.short_prefix
  suffix                     = local.suffix
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  partition_count            = var.eventhubs_partition_count
  databricks_mi_principal_id = module.identity_baseline.databricks_identity_principal_id
  producer_mi_principal_id   = var.eventhubs_producer_mi_principal_id
  tags                       = local.common_tags
}

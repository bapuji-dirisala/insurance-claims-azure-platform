// Identity + secrets baseline.
//
// Three principals, each with hand-scoped RBAC — no wildcards, no
// "Storage Blob Data Contributor" at the subscription level.
//
//   adf_identity        — Azure Data Factory: writes bronze only
//   databricks_identity — Azure Databricks:   reads bronze/silver, writes silver/gold
//   fabric_identity     — Microsoft Fabric:   reads gold (BI consumer)
//
// Secrets (connection strings, service principal credentials, access tokens)
// land in Key Vault. The managed identities are granted "Get" / "List" on
// secrets; the operator (var.principal_object_id) is granted admin.

data "azurerm_subscription" "current" {}

resource "azurerm_user_assigned_identity" "adf" {
  name                = "${var.name_prefix}-adf-mi-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_user_assigned_identity" "databricks" {
  name                = "${var.name_prefix}-dbx-mi-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_user_assigned_identity" "fabric" {
  name                = "${var.name_prefix}-fab-mi-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

// --- Container-scoped RBAC -------------------------------------------------

// ADF: write bronze only (ingestion lands raw files here).
resource "azurerm_role_assignment" "adf_bronze_writer" {
  scope                = var.bronze_container_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.adf.principal_id
}

// Databricks: read bronze/silver, write silver/gold.
resource "azurerm_role_assignment" "dbx_bronze_reader" {
  scope                = var.bronze_container_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.databricks.principal_id
}
resource "azurerm_role_assignment" "dbx_silver_contributor" {
  scope                = var.silver_container_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.databricks.principal_id
}
resource "azurerm_role_assignment" "dbx_gold_contributor" {
  scope                = var.gold_container_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.databricks.principal_id
}

// Fabric: read gold only (BI semantic model consumer).
resource "azurerm_role_assignment" "fabric_gold_reader" {
  scope                = var.gold_container_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.fabric.principal_id
}

// --- Key Vault -------------------------------------------------------------

resource "azurerm_key_vault" "main" {
  // Key Vault names: 3-24 chars, globally unique.
  name                       = substr("${var.name_prefix}-kv-${var.suffix}", 0, 24)
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = var.tenant_id != null ? var.tenant_id : data.azurerm_subscription.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false # dev-friendly; prod should flip to true
  tags                       = var.tags
}

// Operator (the human running `terraform apply`): full admin on the vault.
resource "azurerm_role_assignment" "operator_kv_admin" {
  count                = var.principal_object_id != null ? 1 : 0
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.principal_object_id
}

// Each managed identity: read secrets only.
resource "azurerm_role_assignment" "adf_kv_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.adf.principal_id
}
resource "azurerm_role_assignment" "dbx_kv_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.databricks.principal_id
}
resource "azurerm_role_assignment" "fabric_kv_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.fabric.principal_id
}

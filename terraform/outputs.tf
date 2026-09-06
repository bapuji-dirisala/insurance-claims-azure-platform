output "resource_group_name" {
  description = "Name of the main resource group holding the demo stack."
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "ADLS Gen2 storage account name (hierarchical namespace enabled)."
  value       = module.storage_lakehouse.storage_account_name
}

output "lakehouse_container_names" {
  description = "The three lakehouse containers (bronze → silver → gold)."
  value       = module.storage_lakehouse.container_names
}

output "key_vault_name" {
  description = "Key Vault name — managed identities read secrets from here."
  value       = module.identity_baseline.key_vault_name
}

output "databricks_managed_identity_id" {
  description = "Managed identity used by the Databricks workspace to access ADLS Gen2."
  value       = module.identity_baseline.databricks_identity_id
}

output "adf_managed_identity_id" {
  description = "Managed identity used by Azure Data Factory for ingestion."
  value       = module.identity_baseline.adf_identity_id
}

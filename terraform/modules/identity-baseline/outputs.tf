output "key_vault_id" {
  description = "ARM ID of the Key Vault."
  value       = azurerm_key_vault.main.id
}

output "key_vault_name" {
  description = "Name of the Key Vault."
  value       = azurerm_key_vault.main.name
}

output "adf_identity_id" {
  description = "ARM ID of the ADF managed identity."
  value       = azurerm_user_assigned_identity.adf.id
}

output "adf_identity_principal_id" {
  description = "Principal ID of the ADF managed identity."
  value       = azurerm_user_assigned_identity.adf.principal_id
}

output "databricks_identity_id" {
  description = "ARM ID of the Databricks managed identity."
  value       = azurerm_user_assigned_identity.databricks.id
}

output "databricks_identity_principal_id" {
  description = "Principal ID of the Databricks managed identity."
  value       = azurerm_user_assigned_identity.databricks.principal_id
}

output "fabric_identity_id" {
  description = "ARM ID of the Fabric managed identity."
  value       = azurerm_user_assigned_identity.fabric.id
}

output "fabric_identity_principal_id" {
  description = "Principal ID of the Fabric managed identity."
  value       = azurerm_user_assigned_identity.fabric.principal_id
}

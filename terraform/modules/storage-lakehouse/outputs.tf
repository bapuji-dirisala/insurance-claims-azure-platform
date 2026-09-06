output "storage_account_id" {
  description = "ARM resource ID of the ADLS Gen2 storage account."
  value       = azurerm_storage_account.lake.id
}

output "storage_account_name" {
  description = "Name of the ADLS Gen2 storage account."
  value       = azurerm_storage_account.lake.name
}

output "storage_account_principal_id" {
  description = "System-assigned managed identity principal of the storage account."
  value       = azurerm_storage_account.lake.identity[0].principal_id
}

output "container_names" {
  description = "Names of the three medallion containers."
  value       = [for k, _ in local.layers : k]
}

output "bronze_container_id" {
  description = "ARM ID of the bronze container (raw ingested data)."
  value       = azurerm_storage_container.layer["bronze"].id
}

output "silver_container_id" {
  description = "ARM ID of the silver container (cleaned, conformed)."
  value       = azurerm_storage_container.layer["silver"].id
}

output "gold_container_id" {
  description = "ARM ID of the gold container (aggregated, BI-ready)."
  value       = azurerm_storage_container.layer["gold"].id
}

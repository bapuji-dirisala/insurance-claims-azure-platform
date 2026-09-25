output "account_name" {
  value = azurerm_purview_account.main.name
}

output "atlas_kafka_endpoint" {
  value       = azurerm_purview_account.main.atlas_kafka_endpoint_primary_connection_string
  description = "Kafka endpoint for pushing custom Atlas lineage events."
  sensitive   = true
}

output "principal_id" {
  value = azurerm_purview_account.main.identity[0].principal_id
}

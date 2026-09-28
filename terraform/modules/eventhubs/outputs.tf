output "namespace_name" {
  value = azurerm_eventhub_namespace.main.name
}

output "namespace_id" {
  value       = azurerm_eventhub_namespace.main.id
  description = "ARM ID of the Event Hubs namespace."
}

output "fqdn" {
  value       = "${azurerm_eventhub_namespace.main.name}.servicebus.windows.net"
  description = "Fully-qualified Event Hubs namespace host."
}

output "primary_hub_name" {
  value = azurerm_eventhub.claim_payments.name
}

output "retry_hub_name" {
  value = azurerm_eventhub.claim_payments_retry.name
}

output "databricks_consumer_group" {
  value = azurerm_eventhub_consumer_group.databricks.name
}

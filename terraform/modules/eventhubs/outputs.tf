output "namespace_name" {
  value = azurerm_eventhub_namespace.main.name
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

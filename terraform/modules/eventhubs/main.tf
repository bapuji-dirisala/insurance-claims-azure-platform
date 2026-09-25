// Azure Event Hubs namespace + two hubs:
//
//   * claim-payments        — real-time payment-authorized events
//   * claim-payments-retry  — DLQ for records that failed in Structured Streaming
//
// Partitions are set at 4 by default; message retention 1 day
// (Standard-tier minimum). Capture to ADLS is OFF by default so we
// don't accidentally burn money — the Databricks structured
// streaming job (Phase 10) checkpoints into ADLS instead.

resource "azurerm_eventhub_namespace" "main" {
  name                = "ehns-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
  capacity            = 1

  minimum_tls_version           = "1.2"
  public_network_access_enabled = true
  local_authentication_enabled  = false // force Entra-ID auth

  tags = var.tags
}

resource "azurerm_eventhub" "claim_payments" {
  name                = "claim-payments"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = var.resource_group_name
  partition_count     = var.partition_count
  message_retention   = 1
}

resource "azurerm_eventhub" "claim_payments_retry" {
  name                = "claim-payments-retry"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = var.resource_group_name
  partition_count     = var.partition_count
  message_retention   = 7
}

// Consumer group — one per workload keeps checkpoint offsets isolated.
resource "azurerm_eventhub_consumer_group" "databricks" {
  name                = "databricks-structured-streaming"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.claim_payments.name
  resource_group_name = var.resource_group_name
}

// --- RBAC — Databricks MI gets receiver on the hub ------------------

resource "azurerm_role_assignment" "databricks_receiver" {
  count                = var.databricks_mi_principal_id != "" ? 1 : 0
  scope                = azurerm_eventhub.claim_payments.id
  role_definition_name = "Azure Event Hubs Data Receiver"
  principal_id         = var.databricks_mi_principal_id
}

resource "azurerm_role_assignment" "producer_sender" {
  count                = var.producer_mi_principal_id != "" ? 1 : 0
  scope                = azurerm_eventhub.claim_payments.id
  role_definition_name = "Azure Event Hubs Data Sender"
  principal_id         = var.producer_mi_principal_id
}

// Azure Monitor Log Analytics workspace + diagnostic settings + alerts
// for the Claims lakehouse.
//
// Everything pipes into one workspace so cross-service queries work
// (ADLS throttling vs. Databricks job failures vs. Event Hubs
// throughput). Diagnostic settings forward each service's platform logs
// + relevant metrics.

resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_days
  tags                = var.tags
}

// --- Storage account diagnostics ------------------------------------

resource "azurerm_monitor_diagnostic_setting" "storage" {
  name                       = "diag-storage"
  target_resource_id         = var.adls_account_id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_metric { category = "Transaction" }
  enabled_metric { category = "Capacity" }
}

// --- Event Hubs diagnostics (optional) ------------------------------

resource "azurerm_monitor_diagnostic_setting" "eventhubs" {
  count                      = var.eventhub_namespace_id != "" ? 1 : 0
  name                       = "diag-eventhubs"
  target_resource_id         = var.eventhub_namespace_id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log { category = "ArchiveLogs" }
  enabled_log { category = "OperationalLogs" }
  enabled_log { category = "AutoScaleLogs" }

  enabled_metric { category = "AllMetrics" }
}

// --- Action group (routes alerts to email + webhook) ----------------

resource "azurerm_monitor_action_group" "ops" {
  name                = "ag-ops-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  short_name          = "ops"

  dynamic "email_receiver" {
    for_each = var.ops_email == "" ? [] : [var.ops_email]
    content {
      name          = "ops-email"
      email_address = email_receiver.value
    }
  }

  tags = var.tags
}

// --- Alerts ---------------------------------------------------------

// Storage: throttled requests should be zero in steady state.
resource "azurerm_monitor_metric_alert" "storage_throttled" {
  name                = "alert-storage-throttled-${var.suffix}"
  resource_group_name = var.resource_group_name
  scopes              = [var.adls_account_id]
  description         = "ADLS Gen2 is throttling requests; capacity or TPS limit may need raising."

  criteria {
    metric_namespace = "Microsoft.Storage/storageAccounts"
    metric_name      = "Transactions"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 0
    dimension {
      name     = "ResponseType"
      operator = "Include"
      values   = ["ServerBusyError"]
    }
  }

  window_size = "PT5M"
  frequency   = "PT1M"
  severity    = 2

  action {
    action_group_id = azurerm_monitor_action_group.ops.id
  }
  tags = var.tags
}

// Event Hubs: incoming messages dropping to zero may mean producer is down.
resource "azurerm_monitor_metric_alert" "eventhubs_silent" {
  count               = var.eventhub_namespace_id != "" ? 1 : 0
  name                = "alert-eventhubs-silent-${var.suffix}"
  resource_group_name = var.resource_group_name
  scopes              = [var.eventhub_namespace_id]
  description         = "No incoming messages in the last 15 minutes; producer or auth may be broken."

  criteria {
    metric_namespace = "Microsoft.EventHub/namespaces"
    metric_name      = "IncomingMessages"
    aggregation      = "Total"
    operator         = "LessThan"
    threshold        = 1
  }

  window_size = "PT15M"
  frequency   = "PT5M"
  severity    = 3

  action {
    action_group_id = azurerm_monitor_action_group.ops.id
  }
  tags = var.tags
}

// Microsoft Purview account — governance control plane for the
// Azure data estate. Scans Databricks (Unity Catalog) + ADLS + Fabric
// via managed identity; outputs atlas-compatible lineage.
//
// Purview charges per vCore-hour of scanning + per API call for the
// data map; this module provisions the account only, scheduled scans
// are configured via REST or the UI.

resource "azurerm_purview_account" "main" {
  name                = "pv-${var.name_prefix}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location

  managed_resource_group_name = "pv-${var.name_prefix}-${var.suffix}-mrg"
  public_network_enabled      = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

// --- Role assignments: Purview MI needs to read ADLS + Databricks ---

resource "azurerm_role_assignment" "purview_adls_reader" {
  scope                = var.adls_account_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_purview_account.main.identity[0].principal_id
}

// Purview also needs Storage Account Contributor to enumerate
// containers via the data-plane API during scans.
resource "azurerm_role_assignment" "purview_adls_contributor" {
  scope                = var.adls_account_id
  role_definition_name = "Storage Account Contributor"
  principal_id         = azurerm_purview_account.main.identity[0].principal_id
}

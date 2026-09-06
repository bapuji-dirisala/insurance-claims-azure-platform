// ADLS Gen2 storage account (hierarchical namespace = true) hosting the
// three medallion containers. Same DRY pattern as the P4 S3 lakehouse
// module: `for_each` over a `locals.layers` map so adding `platinum` is
// a one-line change.

locals {
  // Azure storage account names: 3-24 chars, lowercase alphanumeric only,
  // globally unique. Short prefix + suffix leaves ~12 chars for the slug.
  storage_account_name = substr(replace("${var.short_prefix}lake${var.suffix}", "-", ""), 0, 24)

  layers = {
    bronze = { tier = "Hot" }
    silver = { tier = "Hot" }
    gold   = { tier = "Hot" }
  }
}

resource "azurerm_storage_account" "lake" {
  name                     = local.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  // The whole point of ADLS Gen2 — hierarchical namespace enables real
  // directories (not blob key prefixes), which Databricks + Fabric +
  // Synapse all require for Delta / Iceberg write performance.
  is_hns_enabled = true

  // Defense-in-depth: force TLS1.2 at minimum, disable shared-key access
  // so only Entra ID auth works (managed identities, Databricks service
  // principal, Fabric workspace identity).
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = true # TODO Phase 12: lock to Private Endpoint

  blob_properties {
    versioning_enabled       = true
    change_feed_enabled      = true
    last_access_time_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 30
    }
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_storage_container" "layer" {
  for_each              = local.layers
  name                  = each.key
  storage_account_id    = azurerm_storage_account.lake.id
  container_access_type = "private"
}

// Lifecycle: cool-tier blobs that haven't been accessed in retention_days,
// archive-tier after retention_days*4. Delta Lake's _delta_log directory is
// filtered OUT via the prefix match — we never want log files cooled off.
resource "azurerm_storage_management_policy" "lake" {
  storage_account_id = azurerm_storage_account.lake.id

  rule {
    name    = "medallion-tiering"
    enabled = true
    filters {
      blob_types = ["blockBlob"]
      // Only tier data files, never Delta transaction log.
      prefix_match = [
        "bronze/",
        "silver/",
        "gold/",
      ]
      match_blob_index_tag {
        name      = "tier-eligible"
        operation = "=="
        value     = "true"
      }
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = var.retention_days
        tier_to_archive_after_days_since_modification_greater_than = var.retention_days * 4
        delete_after_days_since_modification_greater_than          = var.retention_days * 24
      }
      snapshot {
        delete_after_days_since_creation_greater_than = var.retention_days
      }
      version {
        delete_after_days_since_creation = var.retention_days * 2
      }
    }
  }
}

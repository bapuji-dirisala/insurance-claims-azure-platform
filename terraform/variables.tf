variable "project" {
  description = "Short project slug used in every resource name."
  type        = string
  default     = "claims"
}

variable "environment" {
  description = "Environment tag: local|dev|staging|prod."
  type        = string
  default     = "local"
  validation {
    condition     = contains(["local", "dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: local, dev, staging, prod."
  }
}

variable "azure_region" {
  description = "Azure region (e.g. eastus, westus2). Ignored when use_local_backend = true."
  type        = string
  default     = "eastus"
}

variable "subscription_id" {
  description = "Azure subscription GUID. Ignored when use_local_backend = true."
  type        = string
  default     = null
}

variable "tenant_id" {
  description = "Azure AD / Entra ID tenant GUID. Ignored when use_local_backend = true."
  type        = string
  default     = null
}

variable "use_local_backend" {
  description = "If true, skip Azure provider registration — HCL stays reviewable without a subscription."
  type        = bool
  default     = true
}

variable "resource_suffix" {
  description = "Suffix appended to globally-unique names (storage accounts, key vault). Empty = random."
  type        = string
  default     = ""
  validation {
    condition     = length(var.resource_suffix) <= 8
    error_message = "resource_suffix must be at most 8 characters (Azure globally-unique names are short)."
  }
}

variable "retention_days" {
  description = "Lifecycle: days before tiering blobs to cool/archive storage."
  type        = number
  default     = 30
  validation {
    condition     = var.retention_days > 0
    error_message = "retention_days must be positive."
  }
}

variable "principal_object_id" {
  description = "Entra ID object ID that gets Key Vault admin + storage data-owner (your `az ad signed-in-user show --query id -o tsv`)."
  type        = string
  default     = null
}

variable "enable_purview" {
  description = "Phase 9 — provision a Microsoft Purview account + MI role grants on ADLS. Off by default (slow create, nonzero cost)."
  type        = bool
  default     = false
}

variable "enable_eventhubs" {
  description = "Phase 10 — provision Event Hubs namespace + hubs + consumer group."
  type        = bool
  default     = false
}

variable "eventhubs_partition_count" {
  description = "Partitions per hub (default 4)."
  type        = number
  default     = 4
}

variable "eventhubs_producer_mi_principal_id" {
  description = "Principal ID of whichever MI publishes payment events. Empty = skip the sender role grant."
  type        = string
  default     = ""
}

variable "enable_observability" {
  description = "Phase 12 — Log Analytics workspace + diagnostic settings + metric alerts + action group."
  type        = bool
  default     = false
}

variable "observability_retention_days" {
  description = "Log Analytics data retention. 30 days is the minimum tier."
  type        = number
  default     = 30
}

variable "observability_ops_email" {
  description = "Ops team email for the action group. Empty = no email receiver (webhook-only ops)."
  type        = string
  default     = ""
}

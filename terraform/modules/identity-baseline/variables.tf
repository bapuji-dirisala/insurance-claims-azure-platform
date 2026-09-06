variable "resource_group_name" {
  description = "Resource group that owns the managed identities + Key Vault."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "name_prefix" {
  description = "Project-env prefix for resource names, e.g. 'claims-dev'."
  type        = string
}

variable "suffix" {
  description = "Globally-unique suffix for Key Vault + identity names."
  type        = string
}

variable "tenant_id" {
  description = "Entra ID tenant GUID. If null, falls back to the current subscription's tenant."
  type        = string
  default     = null
}

variable "principal_object_id" {
  description = "Human operator's Entra ID object ID — granted Key Vault admin. Omit for pure validation runs."
  type        = string
  default     = null
}

variable "storage_account_id" {
  description = "Storage account ARM ID (used for diagnostic settings in later phases)."
  type        = string
}

variable "bronze_container_id" {
  description = "Bronze container ARM ID — ADF gets Blob Data Contributor here."
  type        = string
}

variable "silver_container_id" {
  description = "Silver container ARM ID — Databricks gets Blob Data Contributor here."
  type        = string
}

variable "gold_container_id" {
  description = "Gold container ARM ID — Databricks writer, Fabric reader."
  type        = string
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}

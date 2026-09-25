variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }

variable "partition_count" {
  description = "Partitions per hub. 4 is enough for the portfolio demo; prod would scale with throughput units."
  type        = number
  default     = 4
}

variable "databricks_mi_principal_id" {
  description = "Principal ID of the Databricks workspace MI (Phase 1 identity-baseline). Empty = skip receiver role grant."
  type        = string
  default     = ""
}

variable "producer_mi_principal_id" {
  description = "Principal ID of whatever MI produces events (ADF, Function App, etc.). Empty = skip sender role grant."
  type        = string
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}

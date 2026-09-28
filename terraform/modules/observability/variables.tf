variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }

variable "adls_account_id" {
  description = "ADLS Gen2 storage account resource ID."
  type        = string
}

variable "eventhub_namespace_id" {
  description = "Event Hubs namespace resource ID (optional; empty skips the EH alerts)."
  type        = string
  default     = ""
}

variable "retention_days" {
  description = "Log Analytics retention — default 30 (billed per GB after)."
  type        = number
  default     = 30
}

variable "ops_email" {
  description = "Email address for the ops action group. Empty = no email receiver (webhook-only ops)."
  type        = string
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}

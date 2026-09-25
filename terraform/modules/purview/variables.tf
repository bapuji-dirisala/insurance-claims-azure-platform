variable "name_prefix" { type = string }
variable "suffix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }

variable "adls_account_id" {
  description = "Resource ID of the ADLS Gen2 storage account the lakehouse lives in."
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

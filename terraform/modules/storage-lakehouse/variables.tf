variable "resource_group_name" {
  description = "Resource group that owns the storage account."
  type        = string
}

variable "location" {
  description = "Azure region (inherited from the RG)."
  type        = string
}

variable "short_prefix" {
  description = "Short slug (<= 10 chars, lowercase alphanumeric) for the storage account name."
  type        = string
}

variable "suffix" {
  description = "Globally-unique suffix for the storage account name."
  type        = string
}

variable "retention_days" {
  description = "Days before tiering blobs to cool/archive storage."
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags applied to the storage account."
  type        = map(string)
  default     = {}
}

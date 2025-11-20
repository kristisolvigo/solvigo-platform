variable "solvigo_folder_id" {
  description = "Solvigo main folder ID"
  type        = string
  default     = "212465532368"
}

variable "consultant_emails" {
  description = "List of consultant email addresses to grant permissions"
  type        = list(string)
  default = [
    "kristi@solvigo.ai"
  ]
  # Add more consultants as needed:
  # "consultant1@solvigo.ai",
  # "consultant2@solvigo.ai",
}

variable "admin_emails" {
  description = "List of admin email addresses (can delete projects)"
  type        = list(string)
  default = [
    "kristi@solvigo.ai"
  ]
}

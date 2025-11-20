output "consultant_emails" {
  description = "Consultants with folder/project permissions"
  value       = var.consultant_emails
}

output "granted_roles" {
  description = "Roles granted to consultants"
  value = [
    "roles/resourcemanager.folderAdmin",
    "roles/resourcemanager.projectMover",
    "roles/resourcemanager.projectCreator"
  ]
}

output "service_account_email" {
  description = "Admin API service account email"
  value       = module.admin_api_sa.email
}

output "service_account_id" {
  description = "Admin API service account ID"
  value       = module.admin_api_sa.id
}

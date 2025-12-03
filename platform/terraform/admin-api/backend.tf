terraform {
  backend "gcs" {
    bucket = "solvigo-platform-terraform-state"
    prefix = "admin-api"
  }
}

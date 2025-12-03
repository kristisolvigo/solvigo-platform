# Cloud Run Migration Job Module

Creates a Cloud Run Job for database migrations with:
- Automatic execution on deployment (via Cloud Build)
- Manual trigger capability
- VPC connector for Cloud SQL access
- Service account with Cloud SQL permissions

## Usage

```hcl
module "db_migration_job" {
  source = "../.terraform-modules/cloud-run-migration-job"

  project_id                 = var.project_id
  job_name                   = "myapp-db-migrations"
  region                     = var.region
  service_account_email      = google_service_account.backend_app.email
  deployer_sa_email          = "client-deployer@solvigo-platform-prod.iam.gserviceaccount.com"
  cloud_sql_connection_name  = module.database.connection_name
  vpc_connector_name         = google_vpc_access_connector.connector.id

  env_vars = {
    MIGRATION_TOOL = "alembic"  # or "flyway", "liquibase", etc.
  }

  labels = local.labels
}
```

## Migration Execution

### Automatic (on deploy)
Cloud Build step runs after service deployment:
```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: gcloud
  args:
    - 'run'
    - 'jobs'
    - 'execute'
    - '$_MIGRATION_JOB_NAME'
    - '--region=$_REGION'
    - '--wait'
```

### Manual
```bash
gcloud run jobs execute myapp-db-migrations --region=europe-north1
```

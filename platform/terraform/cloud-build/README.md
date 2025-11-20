# Cloud Build GitHub Connection

This Terraform configuration manages the **org-wide GitHub connection** for Cloud Build. This connection is reusable across all client projects.

## Setup (Simplified Approach)

### Step 1: Create GitHub Connection in GCP Console (5 minutes)

**One-time manual setup** - Google handles all the OAuth complexity:

1. **Go to Cloud Build console**:
   ```
   https://console.cloud.google.com/cloud-build/triggers?project=solvigo-platform-prod
   ```

2. **Click "Connect Repository"**

3. **Select "GitHub (Cloud Build GitHub App)"**

4. **Click "Authenticate with GitHub"**
   - Sign in with your GitHub account
   - Grant Cloud Build access to your organization
   - Select "All repositories" or specific repos

5. **Connection created!** ✅
   - Default name: `solvigo-github`
   - Google manages all authentication
   - No OAuth tokens needed!

### Step 2: Import Connection to Terraform (2 minutes)

Now that the connection exists, manage it with Terraform:

```bash
cd platform/terraform/cloud-build

# Initialize Terraform
terraform init

# Import the existing connection
terraform import google_cloudbuildv2_connection.github \
  projects/solvigo-platform-prod/locations/europe-north1/connections/solvigo-github

# Verify
terraform plan
# Should show: No changes (connection already exists)
```

### Step 3: Save Connection ID (1 minute)

```bash
# Get the connection ID
terraform output -raw github_connection_id

# Add to .solvigo_config
echo "" >> ../../../.solvigo_config
echo "# GitHub Connection for Cloud Build" >> ../../../.solvigo_config
echo "export SOLVIGO_GITHUB_CONNECTION_ID=\"$(terraform output -raw github_connection_id)\"" >> ../../../.solvigo_config

# Load it
source ../../../.solvigo_config

# Verify
echo $SOLVIGO_GITHUB_CONNECTION_ID
# Should output: projects/solvigo-platform-prod/locations/europe-north1/connections/solvigo-github
```

**Done!** ✅ The connection is now ready for client projects to use.

---

## What This Does

**Terraform manages** the connection reference (import from console):
- ✅ Connection name and location
- ✅ Outputs connection ID for client projects
- ✅ Prevents accidental deletion

**Google Console manages** the authentication:
- ✅ GitHub OAuth
- ✅ App installation
- ✅ Repository access
- ✅ Token refresh

**No secrets in Terraform!** ✅

---

## Using the Connection

Client projects reference this connection via remote state:

```hcl
# In clients/{client}/{project}/terraform/cicd.tf

data "terraform_remote_state" "platform_cloudbuild" {
  backend = "gcs"
  config = {
    bucket = "solvigo-platform-terraform-state"
    prefix = "cloud-build"
  }
}

module "cicd" {
  source = "../../../../platform/modules/cloud-build-pipeline"

  github_connection_id = data.terraform_remote_state.platform_cloudbuild.outputs.github_connection_id
  # Automatically uses: projects/solvigo-platform-prod/locations/europe-north1/connections/solvigo-github

  # ... other vars
}
```

---

## Verifying the Connection

### Check Connection Status

```bash
gcloud builds connections describe solvigo-github \
  --project=solvigo-platform-prod \
  --region=europe-north1
```

Should show:
```yaml
name: projects/.../connections/solvigo-github
installationState:
  stage: COMPLETE
  actionUri: ''
  message: ''
```

### List All Connections

```bash
gcloud builds connections list \
  --region=europe-north1 \
  --project=solvigo-platform-prod
```

---

## Benefits of This Approach

✅ **No OAuth tokens** to manage in Terraform
✅ **No Secret Manager** needed
✅ **No GitHub App Installation ID** to find
✅ **Google handles auth** via console UI
✅ **5-minute setup** (vs 30 minutes before)
✅ **Simpler for everyone**
✅ **Tokens auto-refresh** (Google manages)

---

## Next Steps

1. ✅ Connection created in console
2. ✅ Imported to Terraform
3. ✅ Connection ID saved to `.solvigo_config`
4. Use CLI to import client project with CI/CD
5. CLI will automatically use this connection!

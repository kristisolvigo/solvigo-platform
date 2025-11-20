# Solvigo Platform - Deployment Checklist

## Pre-Deployment Requirements

### 1. GCP Organization Setup
- [ ] Have access to a GCP Organization
- [ ] Have Organization Admin or Folder Admin role
- [ ] Billing account with billing permissions
- [ ] Domain name ready (e.g., `solvigo.ai`)

### 2. Local Tools Installed
- [ ] `gcloud` CLI installed and configured
- [ ] Terraform >= 1.5.0 installed
- [ ] Git installed

### 3. Authentication
- [ ] Logged into gcloud: `gcloud auth login`
- [ ] Application default credentials: `gcloud auth application-default login`
- [ ] Verify account: `gcloud config get-value account`

## Deployment Steps

### Phase 1: Platform Foundation (30-45 minutes)

#### Step 1: Run Platform Setup Script
```bash
cd /Users/kristifrancis/Desktop/Solvigo/create-app
./scripts/setup-platform.sh
```

**What it does:**
- Creates `solvigo/` folder in your GCP organization
- Creates `solvigo-platform-prod` project
- Enables required APIs
- Creates Terraform state bucket in `europe-north2`
- Generates `.solvigo_config` file

**After completion:**
```bash
source .solvigo_config
```

#### Step 2: Enable Platform APIs (2-3 minutes)
```bash
cd platform/terraform/platform-foundation
terraform init
terraform plan
terraform apply
```

**What it does:**
- Enables all required GCP APIs via Terraform
- Compute, DNS, Cloud Run, Secret Manager, etc.
- Keeps infrastructure as code (not manual setup)

**Verify:**
```bash
terraform output enabled_services
```

#### Step 3: Deploy Shared VPC (5-10 minutes)
```bash
cd platform/terraform/shared-vpc
terraform init
terraform plan
terraform apply
```

**What it creates:**
- Shared VPC network (`solvigo-shared-vpc`)
- Subnets in `europe-north2` (Stockholm) and `europe-north1` (Finland)
- Cloud NAT for outbound internet
- Firewall rules (internal, IAP, health checks)
- VPC Host Project configuration

**Verify:**
```bash
# Check VPC created
gcloud compute networks list --project=solvigo-platform-prod

# Check subnets
gcloud compute networks subnets list --network=solvigo-shared-vpc \
  --project=solvigo-platform-prod
```

#### Step 4: Deploy Cloud DNS (5 minutes)
```bash
cd ../dns
terraform init
terraform plan
terraform apply
```

**What it creates:**
- Main DNS zone for `solvigo.ai`
- DNSSEC enabled
- Ready for client zone delegation

**Get name servers:**
```bash
terraform output main_zone_name_servers
```

**Action Required:**
⚠️ Update your domain registrar with these name servers!

**Verify DNS propagation (takes 24-48 hours):**
```bash
dig NS solvigo.ai
```

#### Step 5: Deploy Load Balancer (5-10 minutes)
```bash
cd ../load-balancer
terraform init
terraform plan
terraform apply
```

**What it creates:**
- Global static IP address
- Managed SSL certificates (for `*.*.solvigo.ai`)
- HTTPS proxy with HTTP→HTTPS redirect
- URL map (baseline, ready for backends)

**Get load balancer IP:**
```bash
terraform output load_balancer_ip
```

**Action Required:**
⚠️ Create DNS A records pointing to this IP:
```
solvigo.ai         A  <LB_IP>
*.solvigo.ai       A  <LB_IP>
*.*.solvigo.ai     A  <LB_IP>
```

**SSL Certificate Status:**
```bash
terraform output ssl_certificate_status
```

Wait for status: `ACTIVE` (takes 10-30 minutes after DNS configured)

---

## Post-Deployment Verification

### Check Shared VPC
```bash
gcloud compute networks describe solvigo-shared-vpc \
  --project=solvigo-platform-prod
```

### Check DNS Zones
```bash
gcloud dns managed-zones list --project=solvigo-platform-prod
```

### Check Load Balancer
```bash
gcloud compute forwarding-rules list --global \
  --project=solvigo-platform-prod
```

### Check SSL Certificate
```bash
gcloud compute ssl-certificates describe solvigo-lb-ssl-cert \
  --global --project=solvigo-platform-prod
```

---

## Configuration Summary

After deployment, you'll have:

| Component | Resource | Details |
|-----------|----------|---------|
| **Folder** | `solvigo/` | Main organizational folder |
| **Project** | `solvigo-platform-prod` | Central platform project |
| **VPC** | `solvigo-shared-vpc` | Shared VPC (host project) |
| **Subnets** | europe-north2, europe-north1 | 10.0.0.0/20, 10.0.16.0/20 |
| **DNS** | `solvigo.ai` zone | DNSSEC enabled |
| **Load Balancer** | Global HTTPS | With managed SSL |
| **State Bucket** | `gs://solvigo-platform-terraform-state` | europe-north2 |

---

## Troubleshooting

### Issue: "Permission denied" during setup
**Solution:** Ensure you have Organization Admin or Folder Admin role
```bash
gcloud organizations get-iam-policy YOUR_ORG_ID
```

### Issue: "Billing account not found"
**Solution:** Verify billing account access
```bash
gcloud billing accounts list
```

### Issue: Terraform state bucket access denied
**Solution:** Ensure you're using the correct project
```bash
gcloud config set project solvigo-platform-prod
```

### Issue: SSL certificate stuck in PROVISIONING
**Cause:** DNS not propagated yet
**Solution:** Wait for DNS to propagate (check with `dig solvigo.ai`)

### Issue: API not enabled error
**Solution:** Enable the API manually
```bash
gcloud services enable APINAME --project=solvigo-platform-prod
```

---

## Security Checklist

Before going to production:

- [ ] Review IAM permissions in platform project
- [ ] Enable VPC Flow Logs (already enabled)
- [ ] Set up budget alerts
- [ ] Enable Cloud Audit Logs
- [ ] Review firewall rules
- [ ] Set up monitoring and alerting
- [ ] Back up Terraform state bucket
- [ ] Document access procedures

---

## Costs (Estimated Monthly)

| Resource | Cost |
|----------|------|
| Shared VPC | Free |
| Cloud NAT | ~€35-45 (€0.045/hour + traffic) |
| DNS Zones | €0.20/zone/month |
| Load Balancer | ~€18 (forwarding rules) |
| SSL Certificates | Free (managed) |
| **Total Platform** | **~€55-65/month** |

*Actual costs depend on traffic and usage*

---

## Next Steps After Deployment

1. **Add first client zone** - Edit `platform/terraform/dns/terraform.tfvars`
2. **Create client project** - Use `modules/gcp-project`
3. **Deploy Cloud Run service** - (Module coming soon)
4. **Register with load balancer** - (Module coming soon)
5. **Build CLI tool** - Automate all of this!

---

## Rollback Procedure

If you need to rollback:

```bash
# Destroy in reverse order
cd platform/terraform/load-balancer
terraform destroy

cd ../dns
terraform destroy

cd ../shared-vpc
terraform destroy

# Delete project (optional)
gcloud projects delete solvigo-platform-prod

# Delete folder (optional)
gcloud resource-manager folders delete $SOLVIGO_FOLDER_ID
```

⚠️ **Warning:** This will destroy all infrastructure. Make sure you have backups!

---

**Deployment Time:** ~45-60 minutes (excluding DNS propagation)
**Difficulty:** Intermediate
**Prerequisites:** GCP Organization Admin + Billing Account access

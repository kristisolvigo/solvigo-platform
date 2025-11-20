# Cloud DNS Configuration

This Terraform configuration manages the DNS infrastructure for the Solvigo platform using Google Cloud DNS.

## Architecture

The DNS setup uses a hierarchical structure:

```
solvigo.ai (main zone)
├── acme-corp.solvigo.ai (client zone)
│   ├── app1.acme-corp.solvigo.ai
│   └── dashboard.acme-corp.solvigo.ai
└── techstart.solvigo.ai (client zone)
    ├── api.techstart.solvigo.ai
    └── web.techstart.solvigo.ai
```

## Features

- **Main DNS Zone**: Manages `solvigo.ai` domain
- **Client Zones**: Separate zones per client (e.g., `acme-corp.solvigo.ai`)
- **DNSSEC**: Enabled for all zones
- **Zone Delegation**: NS records automatically created for client zones

## Usage

### Initial Setup

1. **Configure the main domain**:

```hcl
domain   = "solvigo.ai"
dns_name = "solvigo.ai."  # Note the trailing dot
```

2. **Deploy the main zone**:

```bash
cd platform/terraform/dns
terraform init
terraform plan
terraform apply
```

3. **Configure your domain registrar**:

After applying, get the name servers:

```bash
terraform output main_zone_name_servers
```

Update your domain registrar (e.g., Google Domains, Namecheap, GoDaddy) to use these name servers.

### Adding Client Zones

Edit `terraform.tfvars` or pass variables:

```hcl
client_zones = {
  "acme-corp" = {
    description = "ACME Corporation DNS zone"
  }
  "techstart" = {
    description = "TechStart DNS zone"
  }
}
```

Then apply:

```bash
terraform plan
terraform apply
```

This creates:
- `acme-corp.solvigo.ai` zone
- `techstart.solvigo.ai` zone
- NS records in main zone pointing to client zones

### Adding DNS Records to Client Zones

Client project DNS records should be managed separately. Example:

```hcl
# In client project's Terraform
data "terraform_remote_state" "platform_dns" {
  backend = "gcs"
  config = {
    bucket = "solvigo-platform-terraform-state"
    prefix = "dns"
  }
}

resource "google_dns_record_set" "app" {
  name         = "app1.acme-corp.solvigo.ai."
  type         = "A"
  ttl          = 300
  managed_zone = data.terraform_remote_state.platform_dns.outputs.client_zone_names["acme-corp"]
  project      = "solvigo-platform-prod"

  rrdatas = ["1.2.3.4"]  # Load balancer IP
}
```

## Example Configuration

**terraform.tfvars**:

```hcl
project_id = "solvigo-platform-prod"
domain     = "solvigo.ai"
dns_name   = "solvigo.ai."

client_zones = {
  "acme-corp" = {
    description = "ACME Corporation - Enterprise client"
  }
  "techstart" = {
    description = "TechStart - Startup client"
  }
  "internal-tools" = {
    description = "Internal Solvigo tools"
  }
}
```

## Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| project_id | GCP Project ID | string | "solvigo-platform-prod" |
| domain | Base domain name | string | "solvigo.ai" |
| dns_name | DNS name (with trailing dot) | string | "solvigo.ai." |
| client_zones | Map of client zones | map | {} |

## Outputs

| Name | Description |
|------|-------------|
| main_zone_name_servers | Name servers for main zone (configure at registrar) |
| client_zones | Details of all client zones |
| client_zone_names | Map of client names to zone names |

## DNSSEC

DNSSEC is enabled by default for enhanced security. To verify:

```bash
dig +dnssec solvigo.ai
```

## DNS Propagation

After creating zones and records:
- Name server changes: 24-48 hours
- DNS record changes: 5-30 minutes (depending on TTL)

Check propagation:

```bash
# Check globally
dig @8.8.8.8 acme-corp.solvigo.ai

# Check specific name server
dig @ns-cloud-d1.googledomains.com acme-corp.solvigo.ai
```

## Best Practices

1. **Always use trailing dots** in DNS names in Terraform
2. **Set appropriate TTLs**: Lower for testing (300s), higher for production (3600s)
3. **Use separate zones per client** for better isolation
4. **Enable DNSSEC** for security
5. **Monitor DNS queries** using Cloud Logging

## Integration with Load Balancer

The Load Balancer will use these DNS zones for routing. Example:

```
Request: app1.acme-corp.solvigo.ai
  ↓
Cloud DNS resolves to: 34.120.x.x (Load Balancer IP)
  ↓
Load Balancer routes based on: Host header
  ↓
Backend service: acme-corp-app1 Cloud Run service
```

## Cost Considerations

- **Hosted Zone**: $0.20/zone/month
- **Queries**: $0.40/million queries (first billion)
- **Client zones**: Each client adds $0.20/month

For 10 clients: ~$2.20/month

## Troubleshooting

### Name servers not updating

Check the delegation:

```bash
dig NS acme-corp.solvigo.ai @ns-cloud-d1.googledomains.com
```

### DNSSEC issues

Verify DNSSEC chain:

```bash
delv @8.8.8.8 acme-corp.solvigo.ai
```

### Zone not found

Ensure zone was created and project ID is correct:

```bash
gcloud dns managed-zones list --project=solvigo-platform-prod
```

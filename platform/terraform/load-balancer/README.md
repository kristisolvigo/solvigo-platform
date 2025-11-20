## Global HTTPS Load Balancer

This Terraform configuration creates a Google Cloud Global HTTPS Load Balancer that routes traffic to client services based on hostname.

## Architecture

```
Internet
  ↓
Global Load Balancer (34.x.x.x)
  ↓
Host-based Routing
  ├── app1.acme-corp.solvigo.ai → Backend Service → Cloud Run (acme-corp-app1)
  ├── api.acme-corp.solvigo.ai  → Backend Service → Cloud Run (acme-corp-api)
  └── web.techstart.solvigo.ai  → Backend Service → Cloud Run (techstart-web)
```

## Features

- **Global**: Anycast IP with automatic routing to nearest GCP region
- **HTTPS**: Managed SSL certificates (automatic renewal)
- **HTTP to HTTPS redirect**: Automatic redirect
- **Host-based routing**: Route by domain name (project.client.solvigo.ai)
- **Wildcard SSL**: Supports `*.*.solvigo.ai` pattern
- **Cloud CDN ready**: Can enable CDN per backend service
- **Logging**: Access logs for all requests

## Usage

### Deploy Load Balancer

```bash
cd platform/terraform/load-balancer
terraform init
terraform plan
terraform apply
```

### Get Load Balancer IP

```bash
terraform output load_balancer_ip
```

Example output: `34.120.45.67`

### Configure DNS

After deployment, create DNS A records:

```
solvigo.ai                  A  34.120.45.67
*.solvigo.ai                A  34.120.45.67
*.*.solvigo.ai              A  34.120.45.67
```

Or using the DNS Terraform:

```hcl
# In platform/terraform/dns/
resource "google_dns_record_set" "lb_wildcard" {
  name         = "*.solvigo.ai."
  type         = "A"
  ttl          = 300
  managed_zone = google_dns_managed_zone.main.name
  project      = var.project_id

  rrdatas = [data.terraform_remote_state.load_balancer.outputs.load_balancer_ip]
}
```

### SSL Certificate Provisioning

After DNS is configured, the SSL certificate will provision automatically (takes 10-30 minutes).

Check status:

```bash
terraform output ssl_certificate_status
```

Wait until status is `ACTIVE`.

## Adding Backend Services

Client projects will register their services with the load balancer. This is done via a separate module.

**Example** (from client project):

```hcl
module "lb_backend" {
  source = "../../../../modules/load-balancer-backend"

  project_id      = "solvigo-platform-prod"
  client_name     = "acme-corp"
  service_name    = "app1"
  cloud_run_url   = module.cloud_run.service_url
  hostnames       = ["app1.acme-corp.solvigo.ai"]
}
```

This will:
1. Create a serverless NEG for the Cloud Run service
2. Create a backend service
3. Add a host rule to the URL map

## Monitoring

### View Access Logs

```bash
gcloud logging read "resource.type=http_load_balancer" \
  --project=solvigo-platform-prod \
  --limit=50
```

### View SSL Certificate Details

```bash
gcloud compute ssl-certificates describe solvigo-lb-ssl-cert \
  --global \
  --project=solvigo-platform-prod
```

### Check Backend Health

```bash
gcloud compute backend-services get-health BACKEND_SERVICE_NAME \
  --global \
  --project=solvigo-platform-prod
```

## Cost Considerations

### Load Balancer Pricing
- **Forwarding rules**: $0.025/hour (~$18/month) per rule
- **Ingress traffic**: $0.008-$0.12/GB depending on region
- **Total base cost**: ~$36/month (HTTP + HTTPS rules)

### SSL Certificates
- **Managed certificates**: Free
- **Automatic renewal**: Free

### Cloud CDN (optional)
- **Cache lookups**: $0.01/10,000 requests
- **Cache egress**: $0.04-$0.20/GB (cheaper than origin)

## SSL Certificate

The managed SSL certificate covers:
- `solvigo.ai`
- `*.solvigo.ai` (e.g., `acme-corp.solvigo.ai`)
- `*.*.solvigo.ai` (e.g., `app1.acme-corp.solvigo.ai`)

Maximum 100 domains per certificate.

### Certificate Renewal

Google automatically renews certificates before expiration. No action needed.

## HTTP to HTTPS Redirect

All HTTP traffic (port 80) is automatically redirected to HTTPS (port 443) with a 301 redirect.

Test:

```bash
curl -I http://app1.acme-corp.solvigo.ai
# Should return: HTTP/1.1 301 Moved Permanently
# Location: https://app1.acme-corp.solvigo.ai/
```

## Troubleshooting

### SSL certificate stuck in PROVISIONING

**Cause**: DNS not configured correctly

**Fix**:
```bash
# Verify DNS points to LB IP
dig app1.acme-corp.solvigo.ai

# Should show load balancer IP
```

### Backend returns 404

**Cause**: No backend service configured for that hostname

**Fix**: Add backend service via the load-balancer-backend module

### SSL handshake failures

**Cause**: Certificate not active or hostname not in certificate

**Fix**:
```bash
# Check certificate status
gcloud compute ssl-certificates describe solvigo-lb-ssl-cert --global

# Verify hostname is covered
openssl s_client -connect app1.acme-corp.solvigo.ai:443 -servername app1.acme-corp.solvigo.ai
```

## Security

### DDoS Protection

Google Cloud Armor can be enabled for DDoS protection:

```hcl
resource "google_compute_security_policy" "policy" {
  name = "solvigo-lb-security-policy"

  # Rate limiting example
  rule {
    action   = "rate_based_ban"
    priority = "1000"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }

    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"

      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
    }
  }
}
```

### IP Allowlisting

Restrict access to specific IPs (for internal tools):

```hcl
resource "google_compute_security_policy" "allowlist" {
  name = "solvigo-ip-allowlist"

  rule {
    action   = "allow"
    priority = "1000"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["203.0.113.0/24"]  # Your office IPs
      }
    }
  }

  rule {
    action   = "deny(403)"
    priority = "2147483647"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }
}
```

## Integration Example

Full stack deployment:

```hcl
# 1. Load Balancer (this module)
module "load_balancer" {
  source = "./platform/terraform/load-balancer"
}

# 2. Client Cloud Run service
module "cloud_run" {
  source       = "./modules/cloud-run-app"
  service_name = "app1"
  # ...
}

# 3. Register with load balancer
module "lb_backend" {
  source = "./modules/load-balancer-backend"

  client_name   = "acme-corp"
  service_name  = "app1"
  cloud_run_url = module.cloud_run.service_url
  hostnames     = ["app1.acme-corp.solvigo.ai"]

  depends_on = [module.load_balancer]
}

# 4. DNS record
resource "google_dns_record_set" "app" {
  name         = "app1.acme-corp.solvigo.ai."
  type         = "A"
  ttl          = 300
  managed_zone = "acme-corp-solvigo-zone"
  rrdatas      = [module.load_balancer.load_balancer_ip]
}
```

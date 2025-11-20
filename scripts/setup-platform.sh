#!/bin/bash
# Solvigo Platform Setup Script
# This script sets up the GCP organization, folders, and platform projects

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."

    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found. Please install it first."
        exit 1
    fi

    if ! command -v terraform &> /dev/null; then
        print_error "terraform not found. Please install it first."
        exit 1
    fi

    print_success "Prerequisites check passed"
}

# Get configuration from user
get_configuration() {
    print_step "Getting configuration..."

    # Check if already logged in
    CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null || echo "")
    if [ -z "$CURRENT_ACCOUNT" ]; then
        print_warning "Not logged in to gcloud. Please log in."
        gcloud auth login
    else
        print_success "Logged in as: $CURRENT_ACCOUNT"
    fi

    # Get organization ID
    echo ""
    echo "Available organizations:"
    gcloud organizations list 2>/dev/null || {
        print_error "No organizations found or insufficient permissions"
        exit 1
    }

    echo ""
    read -p "Enter your Organization ID: " ORG_ID

    if [ -z "$ORG_ID" ]; then
        print_error "Organization ID is required"
        exit 1
    fi

    # Verify organization access
    if ! gcloud organizations describe "$ORG_ID" &> /dev/null; then
        print_error "Cannot access organization $ORG_ID"
        exit 1
    fi

    print_success "Organization verified: $ORG_ID"

    # Get billing account
    echo ""
    echo "Available billing accounts:"
    gcloud billing accounts list 2>/dev/null || {
        print_warning "Cannot list billing accounts. You may need Billing Account User role."
    }

    echo ""
    read -p "Enter your Billing Account ID (format: XXXXXX-XXXXXX-XXXXXX): " BILLING_ACCOUNT_ID

    if [ -z "$BILLING_ACCOUNT_ID" ]; then
        print_error "Billing Account ID is required"
        exit 1
    fi

    print_success "Billing Account: $BILLING_ACCOUNT_ID"

    # Confirm configuration
    echo ""
    echo "Configuration Summary:"
    echo "  Organization ID: $ORG_ID"
    echo "  Billing Account: $BILLING_ACCOUNT_ID"
    echo "  Current User:    $CURRENT_ACCOUNT"
    echo ""
    read -p "Proceed with this configuration? (y/n): " CONFIRM

    if [ "$CONFIRM" != "y" ]; then
        print_warning "Setup cancelled"
        exit 0
    fi
}

# Create folder structure
create_folders() {
    print_step "Creating folder structure..."

    # Create main Solvigo folder
    SOLVIGO_FOLDER_ID=$(gcloud resource-manager folders list \
        --organization="$ORG_ID" \
        --filter="displayName:solvigo" \
        --format="value(name)" 2>/dev/null || echo "")

    if [ -z "$SOLVIGO_FOLDER_ID" ]; then
        print_step "Creating 'solvigo' folder..."
        gcloud resource-manager folders create \
            --display-name="solvigo" \
            --organization="$ORG_ID"

        SOLVIGO_FOLDER_ID=$(gcloud resource-manager folders list \
            --organization="$ORG_ID" \
            --filter="displayName:solvigo" \
            --format="value(name)")

        print_success "Created folder: $SOLVIGO_FOLDER_ID"
    else
        print_success "Folder 'solvigo' already exists: $SOLVIGO_FOLDER_ID"
    fi

    # Save folder ID to file for later use
    echo "$SOLVIGO_FOLDER_ID" > .solvigo_folder_id
    print_success "Saved folder ID to .solvigo_folder_id"
}

# Create platform project
create_platform_project() {
    print_step "Creating platform project..."

    PROJECT_ID="solvigo-platform-prod"

    # Check if project exists
    if gcloud projects describe "$PROJECT_ID" &> /dev/null; then
        print_success "Project '$PROJECT_ID' already exists"
    else
        print_step "Creating project '$PROJECT_ID'..."

        gcloud projects create "$PROJECT_ID" \
            --folder="$SOLVIGO_FOLDER_ID" \
            --name="Solvigo Platform Production" \
            --labels=environment=prod,managed_by=terraform,cost_center=internal

        print_success "Created project: $PROJECT_ID"
    fi

    # Link billing
    print_step "Linking billing account..."
    gcloud billing projects link "$PROJECT_ID" \
        --billing-account="$BILLING_ACCOUNT_ID" 2>/dev/null || {
        print_warning "Could not link billing (may already be linked)"
    }

    # Set as default project
    gcloud config set project "$PROJECT_ID"
    print_success "Set default project to $PROJECT_ID"

    # Enable minimal bootstrap APIs required for Terraform to run
    # Other APIs will be enabled by Terraform itself
    print_step "Enabling bootstrap APIs (this may take a few minutes)..."

    APIS=(
        "cloudresourcemanager.googleapis.com"  # Required for Terraform to manage resources
        "iam.googleapis.com"                    # Required for service accounts and permissions
        "storage.googleapis.com"                # Required for Terraform state bucket
        "serviceusage.googleapis.com"           # Allows Terraform to enable other APIs
    )

    for API in "${APIS[@]}"; do
        echo -n "  Enabling $API... "
        gcloud services enable "$API" --project="$PROJECT_ID" 2>/dev/null && echo "✓" || echo "Already enabled"
    done

    print_success "APIs enabled"
}

# Create Terraform state bucket
create_state_bucket() {
    print_step "Creating Terraform state bucket..."

    BUCKET_NAME="solvigo-platform-terraform-state"
    REGION="europe-north2"

    # Check if bucket exists
    if gsutil ls -b "gs://$BUCKET_NAME" &> /dev/null; then
        print_success "Bucket 'gs://$BUCKET_NAME' already exists"
    else
        print_step "Creating bucket 'gs://$BUCKET_NAME'..."

        gcloud storage buckets create "gs://$BUCKET_NAME" \
            --project="solvigo-platform-prod" \
            --location="$REGION" \
            --uniform-bucket-level-access

        print_success "Created bucket: gs://$BUCKET_NAME"
    fi

    # Enable versioning
    print_step "Enabling versioning..."
    gcloud storage buckets update "gs://$BUCKET_NAME" --versioning 2>/dev/null || {
        print_warning "Could not enable versioning (may already be enabled)"
    }

    print_success "Terraform state bucket ready"
}

# Save configuration
save_configuration() {
    print_step "Saving configuration..."

    cat > .solvigo_config << EOF
# Solvigo Platform Configuration
# Generated: $(date)

export SOLVIGO_ORG_ID="$ORG_ID"
export SOLVIGO_BILLING_ACCOUNT="$BILLING_ACCOUNT_ID"
export SOLVIGO_FOLDER_ID="$SOLVIGO_FOLDER_ID"
export SOLVIGO_PLATFORM_PROJECT="solvigo-platform-prod"
export SOLVIGO_STATE_BUCKET="solvigo-platform-terraform-state"
EOF

    print_success "Configuration saved to .solvigo_config"
    print_warning "Source this file in your shell: source .solvigo_config"
}

# Print next steps
print_next_steps() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}Platform setup completed successfully!${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Configuration:"
    echo "  Organization:      $ORG_ID"
    echo "  Folder:            $SOLVIGO_FOLDER_ID"
    echo "  Platform Project:  solvigo-platform-prod"
    echo "  State Bucket:      gs://solvigo-platform-terraform-state"
    echo ""
    echo "Next steps:"
    echo "  1. Source the configuration:"
    echo "     ${YELLOW}source .solvigo_config${NC}"
    echo ""
    echo "  2. Deploy the Shared VPC:"
    echo "     ${YELLOW}cd platform/terraform/shared-vpc${NC}"
    echo "     ${YELLOW}terraform init${NC}"
    echo "     ${YELLOW}terraform plan${NC}"
    echo "     ${YELLOW}terraform apply${NC}"
    echo ""
    echo "  3. Deploy Cloud DNS and Load Balancer (coming next)"
    echo ""
}

# Main execution
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Solvigo Platform Setup"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_prerequisites
    get_configuration
    create_folders
    create_platform_project
    create_state_bucket
    save_configuration
    print_next_steps
}

# Run main function
main

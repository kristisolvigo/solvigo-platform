# Solvigo CLI - Installation Guide

Quick start guide for installing and configuring the Solvigo CLI for consultants.

## Quick Start (5 minutes)

### 1. Install the CLI

```bash
cd /Users/kristifrancis/Desktop/Solvigo/create-app/cli
pip install -e .
```

### 2. Configure Environment

```bash
cd ..  # Back to platform root
source .solvigo_config
```

**Make it permanent** (add to your shell profile):

```bash
# For zsh (macOS default)
echo 'source /Users/kristifrancis/Desktop/Solvigo/create-app/.solvigo_config' >> ~/.zshrc
source ~/.zshrc

# For bash
echo 'source /Users/kristifrancis/Desktop/Solvigo/create-app/.solvigo_config' >> ~/.bashrc
source ~/.bashrc
```

### 3. Verify Installation

```bash
solvigo --version
# Output: Solvigo CLI, version 0.1.0

echo $SOLVIGO_PLATFORM_ROOT
# Output: /Users/kristifrancis/Desktop/Solvigo/create-app
```

### 4. Run from Anywhere!

```bash
cd ~
solvigo
# Works from any directory!
```

## What Was Installed

The `pip install -e .` command:

1. Installed all Python dependencies (click, rich, questionary, google-cloud-* libraries)
2. Created the `solvigo` command in your PATH
3. Linked it to this directory (editable mode - changes take effect immediately)

## Making Changes

Since it's installed in editable mode, any changes you make to the Python files will take effect immediately (no need to reinstall).

Test a change:

```bash
# Edit any file in solvigo/
vim solvigo/main.py

# Run immediately
solvigo
```

## Prerequisites

Before using the CLI, ensure you have:

1. **Python 3.11+**
   ```bash
   python3 --version
   ```

2. **gcloud CLI installed and authenticated**
   ```bash
   gcloud --version
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Terraform >= 1.5.0**
   ```bash
   terraform --version
   ```

4. **Platform configuration loaded**
   ```bash
   source .solvigo_config
   ```

## Testing the Discovery Feature

You can test the GCP discovery feature with your platform project:

```bash
solvigo discover solvigo-platform-prod
```

This will scan the project and show:
- Cloud Run services
- Cloud SQL instances
- Storage buckets
- Secrets
- Service accounts
- Enabled APIs

## Development Mode

### Install with dev dependencies

```bash
pip install -e ".[dev]"
```

This adds testing and linting tools:
- pytest
- black (code formatter)
- flake8 (linter)
- mypy (type checker)

### Run tests

```bash
pytest
```

### Format code

```bash
black solvigo/
```

### Check types

```bash
mypy solvigo/
```

## Uninstalling

To remove the CLI:

```bash
pip uninstall solvigo-cli
```

## Troubleshooting

### Command not found: solvigo

**Solution:** Ensure pip install completed successfully and your PATH includes pip's bin directory.

```bash
which solvigo
# Should show path to solvigo command
```

### Import errors

**Solution:** Reinstall dependencies:

```bash
pip install -e . --force-reinstall
```

### gcloud command not found

**Solution:** Install gcloud CLI first:

```bash
# macOS
brew install --cask google-cloud-sdk

# Then authenticate
gcloud auth login
```

## Current Features

### ✅ Fully Functional
- ✅ Interactive main menu with beautiful UI
- ✅ Context detection (detects if running from project directory)
- ✅ GCP resource discovery (Cloud Run, SQL, Storage, Secrets, Service Accounts)
- ✅ Interactive resource selection with checkboxes
- ✅ "Create new" options for resources
- ✅ Complete Terraform code generation
- ✅ Terraform import workflow automation
- ✅ **CI/CD setup** (backend/frontend/fullstack)
- ✅ Dockerfile location selection
- ✅ Cloud Build integration
- ✅ Works from any directory (with env var)

### 🔄 Partially Implemented
- ⚠️ `solvigo init` - Project creation (placeholder)
- ⚠️ `solvigo deploy` - Deployment (basic)
- ⚠️ `solvigo status` - Project status (basic)

### 📋 Coming Soon
- Code scaffolding (React + FastAPI templates)
- Full project creation workflow
- Load balancer automatic registration

## Environment Variables

Required for CLI to work from any directory:

```bash
SOLVIGO_PLATFORM_ROOT      # Path to platform repository
SOLVIGO_PLATFORM_PROJECT   # Platform project ID
SOLVIGO_ORG_ID            # GCP organization ID
SOLVIGO_BILLING_ACCOUNT   # Billing account
SOLVIGO_FOLDER_ID         # Main folder ID
SOLVIGO_STATE_BUCKET      # Terraform state bucket
SOLVIGO_GITHUB_CONNECTION_ID  # GitHub connection (optional, for CI/CD)
```

All automatically set when you `source .solvigo_config`!

## Usage Examples

### Import Existing Project with CI/CD

```bash
# Run from anywhere
solvigo

# Select: Import existing GCP project
# Search: bluegaz
# Select project
# Select resources to import
# Setup CI/CD? Yes
# Application type? Fullstack
# Select Dockerfiles
# Confirm and deploy
```

See `CLI_FUNCTIONAL_STATUS.md` and `CLI_CICD_INTEGRATION.md` for more details.

# Solvigo Platform - Quick Start Guide

**Get started in 5 minutes!**

---

## Prerequisites Check

```bash
# Check you have everything installed
gcloud --version      # Need: Google Cloud SDK
terraform --version   # Need: >= 1.5.0
python3 --version     # Need: >= 3.11
git --version         # Need: Any recent version

# Authenticate with GCP
gcloud auth login
gcloud auth application-default login
```

---

## Step 1: Install the CLI (30 seconds)

```bash
cd /Users/kristifrancis/Desktop/Solvigo/create-app/cli
pip install -e .
```

**Verify:**
```bash
solvigo --version
# Should show: Solvigo CLI, version 0.1.0
```

---

## Step 2: Source Platform Config (10 seconds)

```bash
cd /Users/kristifrancis/Desktop/Solvigo/create-app
source .solvigo_config
```

---

## Step 3: Run the CLI

```bash
solvigo
```

**Follow the interactive prompts to import bluegaz-customer-support!**

Expected time: 5-10 minutes

---

See CLI_FUNCTIONAL_STATUS.md for detailed feature list.

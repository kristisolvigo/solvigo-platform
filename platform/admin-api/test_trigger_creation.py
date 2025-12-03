#!/usr/bin/env python3
"""
Comprehensive diagnostic test for Cloud Build trigger creation with cross-project service accounts.

This script systematically tests all components involved in trigger creation to identify
the exact permission or policy blocking the operation.
"""

import os
import json
import subprocess
from typing import Dict, List, Tuple
from google.cloud.devtools import cloudbuild_v1
from google.cloud.iam_credentials_v1 import IAMCredentialsClient
from google.cloud.iam_credentials_v1.types import GenerateAccessTokenRequest
from google.oauth2 import service_account
from google.api_core import exceptions as google_exceptions

# Configuration
SA_KEY_PATH = os.path.expanduser("~/.solvigo/registry-api-key.json")
PLATFORM_PROJECT_ID = "solvigo-platform-prod"
CLIENT_PROJECT_ID = "seo-text-optimization"
DEPLOYER_EMAIL = f"deployer@{CLIENT_PROJECT_ID}.iam.gserviceaccount.com"
REGISTRY_API_EMAIL = f"registry-api@{PLATFORM_PROJECT_ID}.iam.gserviceaccount.com"

# Test configuration
TEST_REPO_OWNER = "Solvigo"
TEST_REPO_NAME = "SEO--Text-optimering"
TEST_BRANCH = "main"
TEST_BUILD_CONFIG = "cicd/cloudbuild-backend.yaml"

# Results tracking
results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_result(check: str, passed: bool, details: str = ""):
    """Print and track a check result."""
    symbol = "✅" if passed else "❌"
    status = "PASS" if passed else "FAIL"
    print(f"{symbol} {check}: {status}")
    if details:
        print(f"   {details}")

    if passed:
        results["passed"].append(check)
    else:
        results["failed"].append({"check": check, "details": details})


def print_warning(message: str):
    """Print and track a warning."""
    print(f"⚠️  WARNING: {message}")
    results["warnings"].append(message)


# ============================================================================
# TEST 1: Pre-Flight Checks
# ============================================================================

def test_preflight():
    """Verify basic prerequisites."""
    print_section("TEST 1: Pre-Flight Checks")

    # Check SA key file
    if os.path.exists(SA_KEY_PATH):
        print_result("Service account key file exists", True, SA_KEY_PATH)
    else:
        print_result("Service account key file exists", False, f"Not found: {SA_KEY_PATH}")
        return None

    # Load credentials
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SA_KEY_PATH,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )

        # Verify it's the right SA
        if credentials.service_account_email == REGISTRY_API_EMAIL:
            print_result("Authenticated as correct service account", True, REGISTRY_API_EMAIL)
        else:
            print_result("Authenticated as correct service account", False,
                        f"Expected: {REGISTRY_API_EMAIL}, Got: {credentials.service_account_email}")
            return None

        return credentials
    except Exception as e:
        print_result("Load credentials", False, str(e))
        return None


# ============================================================================
# TEST 2: Organization Policy Check
# ============================================================================

def test_org_policies(credentials):
    """Check organization policies that might block cross-project SA usage."""
    print_section("TEST 2: Organization Policy Check")

    constraint = "iam.disableCrossProjectServiceAccountUsage"

    # Check platform project
    try:
        result = subprocess.run(
            ["gcloud", "resource-manager", "org-policies", "describe", constraint,
             "--project", PLATFORM_PROJECT_ID, "--effective", "--format", "json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            policy = json.loads(result.stdout)
            enforced = policy.get("booleanPolicy", {}).get("enforced", False)
            print_result(
                f"Org policy on {PLATFORM_PROJECT_ID}",
                not enforced,
                f"Enforced: {enforced}"
            )
        else:
            print_warning(f"Could not check platform project policy: {result.stderr}")
    except Exception as e:
        print_warning(f"Error checking platform policy: {e}")

    # Check client project
    try:
        result = subprocess.run(
            ["gcloud", "resource-manager", "org-policies", "describe", constraint,
             "--project", CLIENT_PROJECT_ID, "--effective", "--format", "json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            policy = json.loads(result.stdout)
            enforced = policy.get("booleanPolicy", {}).get("enforced", False)
            print_result(
                f"Org policy on {CLIENT_PROJECT_ID}",
                not enforced,
                f"Enforced: {enforced}"
            )

            if enforced:
                print_warning(
                    "Cross-project service account usage is BLOCKED by organization policy!\n"
                    "   This will prevent trigger creation even if IAM permissions are correct.\n"
                    f"   To fix: Disable constraint on {CLIENT_PROJECT_ID}"
                )
        else:
            print_warning(f"Could not check client project policy: {result.stderr}")
    except Exception as e:
        print_warning(f"Error checking client policy: {e}")


# ============================================================================
# TEST 3: IAM Permission Check
# ============================================================================

def test_iam_permissions(credentials):
    """Check IAM permissions on the deployer service account."""
    print_section("TEST 3: IAM Permission Check")

    try:
        result = subprocess.run(
            ["gcloud", "iam", "service-accounts", "get-iam-policy", DEPLOYER_EMAIL,
             "--project", CLIENT_PROJECT_ID, "--format", "json"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            print_result("Get IAM policy on deployer SA", False, result.stderr)
            return

        policy = json.loads(result.stdout)

        # Check for required roles
        registry_api_roles = set()
        platform_cb_roles = set()

        for binding in policy.get("bindings", []):
            for member in binding.get("members", []):
                if member == f"serviceAccount:{REGISTRY_API_EMAIL}":
                    registry_api_roles.add(binding["role"])
                elif "cloudbuild" in member:
                    platform_cb_roles.add(binding["role"])

        print(f"Roles granted to {REGISTRY_API_EMAIL}:")
        for role in sorted(registry_api_roles):
            print(f"  - {role}")

        # Check required roles
        required_roles = {
            'roles/iam.serviceAccountUser',
            'roles/iam.serviceAccountTokenCreator'
        }

        has_all_roles = required_roles.issubset(registry_api_roles)
        missing = required_roles - registry_api_roles
        print_result(
            "registry-api has required roles on deployer SA",
            has_all_roles,
            f"Missing: {missing}" if missing else "All required roles present"
        )

        print(f"\nRoles granted to Cloud Build SAs:")
        if platform_cb_roles:
            for role in sorted(platform_cb_roles):
                print(f"  - {role}")
        else:
            print("  (none found)")

    except Exception as e:
        print_result("IAM permission check", False, str(e))


# ============================================================================
# TEST 4: Direct Impersonation Test
# ============================================================================

def test_impersonation(credentials):
    """Test direct impersonation of deployer SA."""
    print_section("TEST 4: Direct Impersonation Test")

    try:
        iam_creds_client = IAMCredentialsClient(credentials=credentials)
        service_account_name = f"projects/-/serviceAccounts/{DEPLOYER_EMAIL}"

        request = GenerateAccessTokenRequest(
            name=service_account_name,
            scope=["https://www.googleapis.com/auth/cloud-platform"],
        )

        response = iam_creds_client.generate_access_token(request=request)
        print_result(
            "Generate access token for deployer SA",
            True,
            f"Successfully generated token (expires: {response.expire_time})"
        )
        return True

    except Exception as e:
        print_result("Generate access token for deployer SA", False, str(e))
        return False


# ============================================================================
# TEST 5: Policy Troubleshooter Analysis (Skipped - using impersonation test instead)
# ============================================================================

def test_policy_troubleshooter(credentials):
    """Placeholder - using direct impersonation test instead."""
    print_section("TEST 5: Policy Troubleshooter Analysis")
    print("⏭️  Skipping - using direct impersonation test instead")


# ============================================================================
# TEST 6: Trigger Creation Attempt
# ============================================================================

def test_trigger_creation(credentials):
    """Attempt to create a test trigger."""
    print_section("TEST 6: Trigger Creation Attempt")

    try:
        build_client = cloudbuild_v1.CloudBuildClient(credentials=credentials)
        parent = f"projects/{PLATFORM_PROJECT_ID}/locations/europe-north2"

        # Create minimal test trigger
        trigger_name = "diagnostic-test-trigger"
        trigger = cloudbuild_v1.BuildTrigger(
            name=trigger_name,
            description="Diagnostic test trigger - can be deleted",
            filename=TEST_BUILD_CONFIG,
            github=cloudbuild_v1.GitHubEventsConfig(
                owner=TEST_REPO_OWNER,
                name=TEST_REPO_NAME,
                push=cloudbuild_v1.PushFilter(branch=TEST_BRANCH)
            ),
            service_account=f"projects/{CLIENT_PROJECT_ID}/serviceAccounts/{DEPLOYER_EMAIL}"
        )

        print(f"Attempting to create trigger: {trigger_name}")
        print(f"  Project: {PLATFORM_PROJECT_ID}")
        print(f"  Service Account: {DEPLOYER_EMAIL}")
        print(f"  Repo: {TEST_REPO_OWNER}/{TEST_REPO_NAME}")

        request = cloudbuild_v1.CreateBuildTriggerRequest(
            parent=parent,
            project_id=PLATFORM_PROJECT_ID,
            trigger=trigger
        )

        created_trigger = build_client.create_build_trigger(request=request)
        print_result(
            "Create Cloud Build trigger",
            True,
            f"Trigger ID: {created_trigger.id}"
        )

        # Clean up - delete the test trigger
        try:
            build_client.delete_build_trigger(
                project_id=PLATFORM_PROJECT_ID,
                trigger_id=created_trigger.id
            )
            print("   (Test trigger deleted)")
        except:
            pass

        return True

    except google_exceptions.PermissionDenied as e:
        print_result("Create Cloud Build trigger", False, f"Permission denied: {e}")

        # Extract error details
        print("\n   ERROR DETAILS:")
        print(f"   Message: {e.message}")
        if hasattr(e, 'details'):
            print(f"   Details: {e.details()}")

        return False

    except Exception as e:
        print_result("Create Cloud Build trigger", False, str(e))
        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run all diagnostic tests."""
    print("\n" + "="*80)
    print("  CLOUD BUILD TRIGGER CREATION DIAGNOSTIC TEST")
    print("="*80)
    print(f"\nPlatform Project: {PLATFORM_PROJECT_ID}")
    print(f"Client Project:   {CLIENT_PROJECT_ID}")
    print(f"Deployer SA:      {DEPLOYER_EMAIL}")
    print(f"Registry API SA:  {REGISTRY_API_EMAIL}")

    # Run tests
    credentials = test_preflight()
    if not credentials:
        print("\n❌ Pre-flight checks failed. Cannot continue.")
        return

    test_org_policies(credentials)
    test_iam_permissions(credentials)
    impersonation_works = test_impersonation(credentials)
    test_policy_troubleshooter(credentials)
    trigger_creation_works = test_trigger_creation(credentials)

    # Final summary
    print_section("DIAGNOSTIC SUMMARY")

    print(f"✅ Passed: {len(results['passed'])}")
    for check in results['passed']:
        print(f"   - {check}")

    if results['failed']:
        print(f"\n❌ Failed: {len(results['failed'])}")
        for failure in results['failed']:
            print(f"   - {failure['check']}")
            if failure['details']:
                print(f"     {failure['details']}")

    if results['warnings']:
        print(f"\n⚠️  Warnings: {len(results['warnings'])}")
        for warning in results['warnings']:
            print(f"   - {warning}")

    # Diagnosis
    print("\n" + "="*80)
    print("  DIAGNOSIS")
    print("="*80)

    if trigger_creation_works:
        print("\n✅ SUCCESS! Trigger creation works correctly.")
        print("   No permission issues detected.")
    elif not impersonation_works:
        print("\n❌ ISSUE: Basic impersonation is failing.")
        print("   Fix the IAM permissions before testing trigger creation.")
    else:
        print("\n❌ ISSUE: Impersonation works but trigger creation fails.")
        print("\n   This suggests one of:")
        print("   1. Organization policy blocking cross-project SA usage")
        print("   2. Cloud Build API has additional undocumented requirements")
        print("   3. IAM propagation delay (wait 2-5 minutes and retry)")

        if any("organization policy" in w.lower() for w in results['warnings']):
            print("\n   ⚠️  LIKELY CAUSE: Organization policy is blocking this operation!")
            print(f"      Disable: constraints/iam.disableCrossProjectServiceAccountUsage")
            print(f"      On both: {PLATFORM_PROJECT_ID} and {CLIENT_PROJECT_ID}")


if __name__ == "__main__":
    main()

# RHACM4K-XXXXX - [TAG-VERSION] Area - Test Name

**Polarion ID:** RHACM4K-XXXXX
**Status:** Draft
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD

---

## Type: Test Case
## Level: System
## Component: COMPONENT
## Subcomponent: SUBCOMPONENT
## Test Type: Functional
## Pos/Neg: Positive
## Importance: High
## Automation: Not Automated
## Tags: ui, AREA_TAGS
## Release: VERSION

---

## Description

FEATURE_DESCRIPTION

This test verifies:
1. VERIFICATION_ITEM_1
2. VERIFICATION_ITEM_2
3. VERIFICATION_ITEM_3

**Entry Point:** NAVIGATION_PATH
**Route:** ROUTE_PATH (route key: `ROUTE_KEY`)

**Dev JIRA Coverage:**
- Primary: JIRA_ID -- JIRA_SUMMARY
- PR: REPO#PR_NUMBER (merged DATE)

---

## Setup

**Prerequisites:**
- ACM VERSION hub cluster
- cluster-admin access to the hub
- ADDITIONAL_PREREQUISITES

**Test Environment:**
- Hub: *(environment-specific)*
- Console: `https://multicloud-console.apps.<hub-cluster-domain>`
- IDP: *(environment-specific)*
- Test User: cluster-admin

**Setup Commands:**

```bash
# 1. Verify ACM version
oc get mch multiclusterhub -n open-cluster-management -o jsonpath='Version: {.status.currentVersion}'
# Expected: Version: VERSION

# 2. Verify hub is healthy
oc get mch multiclusterhub -n open-cluster-management -o jsonpath='Phase: {.status.phase}'
# Expected: Phase: Running

# 3. ADDITIONAL_SETUP_COMMANDS
```

---

## Test Steps

### Step 1: STEP_TITLE

1. ACTION_1
2. ACTION_2

**Expected Result:**
- EXPECTED_1
- EXPECTED_2

---

## Teardown

```bash
# CLEANUP_COMMANDS
```

---

## Notes

- IMPLEMENTATION_NOTES

---

## Known Issues and Code References

### Implementation Files

- `FILE_PATH` -- DESCRIPTION

### PRs

- REPO#PR_NUMBER -- DESCRIPTION

### Related Tickets

- **JIRA_ID** (Type): SUMMARY

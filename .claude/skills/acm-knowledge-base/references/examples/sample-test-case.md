# RHACM4K-99999 - [GRC-2.17] Governance - Policy Violation Summary on Details Page

**Polarion ID:** RHACM4K-99999
**Status:** Draft
**Created:** 2026-01-15
**Updated:** 2026-01-15

---

## Type: Test Case
## Level: System
## Component: Governance
## Subcomponent: Policy Details
## Test Type: Functional
## Pos/Neg: Positive
## Importance: High
## Automation: Not Automated
## Tags: ui, governance, policy-details, violations, summary
## Release: 2.17

---

## Description

Validates that the violation summary section on the policy details page correctly displays the count and status of policy violations across managed clusters. The PR adds a summary card showing total violations, compliant clusters, and non-compliant clusters with a drill-down link to the Clusters tab filtered by compliance status.

This test verifies:
1. The violation summary card appears on the policy details page
2. Violation counts match the actual cluster compliance status
3. Compliant and non-compliant cluster counts are accurate
4. Clicking a compliance status filters the Clusters tab
5. The summary updates after a policy propagation change
6. The summary handles edge cases (zero violations, all violations)

**Entry Point:** Governance → Policies → \<policy-name\> → Details tab
**Route:** `/multicloud/governance/policies/details/:namespace/:name` (route key: `policyDetails`)

**Dev JIRA Coverage:**
- Primary: ACM-99999 — Add violation summary card to policy details page
- PR: stolostron/console#9999 (merged 2026-01-10)

---

## Setup

**Prerequisites:**
- ACM 2.17.x hub cluster
- cluster-admin access to the hub
- At least two managed spoke clusters with AVAILABLE=True
- At least one policy deployed that has both compliant and non-compliant clusters
- At least one policy that is fully compliant across all clusters (for edge case testing)

**Test Environment:**
- Hub: *(environment-specific)*
- Console: `https://multicloud-console.apps.<hub-cluster-domain>`
- IDP: *(environment-specific)*
- Test User: cluster-admin

**Setup Commands:**

```bash
# 1. Verify ACM 2.17+ is installed
oc get mch multiclusterhub -n open-cluster-management -o jsonpath='Version: {.status.currentVersion}'
# Expected: Version: 2.17.x

# 2. Verify hub is healthy
oc get mch multiclusterhub -n open-cluster-management -o jsonpath='Phase: {.status.phase}'
# Expected: Phase: Running

# 3. Verify at least two managed clusters are available
oc get managedclusters
# Expected: At least two managed clusters with AVAILABLE=True

# 4. Create a test policy with placement targeting both clusters
cat <<'EOF' | oc apply -f -
apiVersion: policy.open-cluster-management.io/v1
kind: Policy
metadata:
  name: test-violation-summary
  namespace: open-cluster-management
spec:
  remediationAction: inform
  disabled: false
  policy-templates:
    - objectDefinition:
        apiVersion: policy.open-cluster-management.io/v1
        kind: ConfigurationPolicy
        metadata:
          name: test-namespace-check
        spec:
          remediationAction: inform
          severity: medium
          object-templates:
            - complianceType: musthave
              objectDefinition:
                apiVersion: v1
                kind: Namespace
                metadata:
                  name: test-violation-ns
EOF
# Expected: policy.open-cluster-management.io/test-violation-summary created

# 5. Verify policy propagation
oc get policy test-violation-summary -n open-cluster-management -o jsonpath='Status: {.status.compliant}'
# Expected: Status: NonCompliant (namespace does not exist on spoke clusters)

# 6. Create the namespace on one spoke to produce a mixed compliance state
oc --context <spoke-1-context> create namespace test-violation-ns --dry-run=client -o yaml | oc --context <spoke-1-context> apply -f -
# Expected: namespace/test-violation-ns created
```

---

## Test Steps

### Step 1: Navigate to Policy Details and Verify Summary Card

1. Log into the ACM hub console as cluster-admin.
2. Navigate to: **Governance** → **Policies** tab.
3. Click on the **test-violation-summary** policy name.
4. Observe the **Details** tab content.

**Expected Result:**
- The policy details page loads with the Details tab active.
- A **Violation summary** card is displayed at the top of the details content.
- The card shows three values: **Total violations**, **Compliant clusters**, **Non-compliant clusters**.

---

### Step 2: Verify Violation Counts Match Cluster Compliance

1. On the policy details page, note the violation count displayed in the summary card.
2. Click the **Clusters** tab to view per-cluster compliance.
3. Count the clusters marked as **Compliant** and **Non-compliant**.
4. Compare with the summary card values.

**Expected Result:**
- The **Total violations** count equals the number of non-compliant clusters.
- The **Compliant clusters** count matches the number of clusters showing Compliant status.
- The **Non-compliant clusters** count matches the number of clusters showing NonCompliant status.
- The total (compliant + non-compliant) equals the total number of clusters the policy is placed on.

---

### Step 3: Verify Compliance Status Drill-Down Filter

1. Navigate back to the **Details** tab.
2. In the violation summary card, click the **Non-compliant** count link.
3. Observe the Clusters tab content after the navigation.

**Expected Result:**
- Clicking the non-compliant count navigates to the **Clusters** tab.
- The Clusters tab is filtered to show only non-compliant clusters.
- The filter chip shows the active compliance status filter.
- Clearing the filter restores the full cluster list.

---

### Step 4: Verify Summary for Fully Compliant Policy

1. Navigate to: **Governance** → **Policies** tab.
2. Select a policy that is fully compliant across all clusters.
3. Observe the violation summary card on the Details tab.

**Expected Result:**
- The **Total violations** count shows **0**.
- The **Compliant clusters** count equals the total placed clusters.
- The **Non-compliant clusters** count shows **0**.
- The non-compliant count is not a clickable link when the value is 0.

---

### Step 5: Verify Backend State Matches UI

1. Return to the **test-violation-summary** policy details page.
2. Open a terminal and run the backend verification command.

```bash
oc get policy test-violation-summary -n open-cluster-management -o jsonpath='{range .status.status[*]}{.clusternamespace}/{.clustername}: {.compliant}{"\n"}{end}'
```

3. Compare the backend output with the UI summary card values.

**Expected Result:**
- Each cluster's compliance status in the CLI output matches what the UI shows.
- The count of `Compliant` entries matches the summary card's compliant count.
- The count of `NonCompliant` entries matches the summary card's non-compliant count.

---

### Step 6: Verify Summary Updates After Compliance Change

1. In a terminal, create the missing namespace on the remaining non-compliant spoke cluster:

```bash
oc --context <spoke-2-context> create namespace test-violation-ns --dry-run=client -o yaml | oc --context <spoke-2-context> apply -f -
```

2. Wait 30-60 seconds for the policy controller to re-evaluate compliance.
3. Refresh the policy details page in the browser.
4. Observe the updated violation summary card.

**Expected Result:**
- The **Total violations** count decreases (or reaches 0).
- The **Compliant clusters** count increases.
- The **Non-compliant clusters** count decreases.
- The summary card reflects the current compliance state after the change.

---

## Teardown

```bash
# Remove the test policy
oc delete policy test-violation-summary -n open-cluster-management --ignore-not-found

# Remove test namespace from spoke clusters
oc --context <spoke-1-context> delete namespace test-violation-ns --ignore-not-found
oc --context <spoke-2-context> delete namespace test-violation-ns --ignore-not-found
```

---

## Notes

- **Compliance refresh timing:** After changing cluster state (Step 6), the governance policy controller re-evaluates compliance on a periodic interval (default 10 seconds). Allow 30-60 seconds and refresh the page to see updated counts.

- **Implementation detail:** The violation summary card reads from `policy.status.status[]` which is an array of per-cluster compliance objects. The count logic filters by `compliant` field values: `Compliant` vs `NonCompliant`.

---

## Known Issues and Code References

### Implementation Files

- `frontend/src/routes/Governance/policies/policy-details/PolicyDetails.tsx` — Adds ViolationSummary component to the details tab layout.
- `frontend/src/routes/Governance/policies/policy-details/ViolationSummary.tsx` — New component rendering the summary card with compliance counts.

### Translation Keys

- `policy.violation.summary` → "Violation summary"
- `policy.compliant.clusters` → "Compliant clusters"
- `policy.noncompliant.clusters` → "Non-compliant clusters"

### PRs

- stolostron/console#9999 — Violation summary card on policy details page

### Related Tickets

- **ACM-99999** (Story): Add violation summary card to policy details page

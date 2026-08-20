---
type: failures
subsystem: virtualization
acm_version: "5.0"
last_verified: 2026-08-12
related:
  - architecture/virtualization/architecture.md
  - health/virtualization/known-issues.md
---

# Virtualization Failure Signatures

Known failure patterns for Fleet Virtualization test failures.

---

## INFRASTRUCTURE Patterns

### Jenkins virt-e2e-container OOMKilled (exit 137)
- **Error:** Build `ABORTED`; console log `Container [virt-e2e-container] terminated [OOMKilled]`; exit `(137)`; agent offline `Pod failed because container terminated (Reason: ContainerError)`
- **Pattern:** Some Cypress specs pass, then run stops mid-suite with no JUnit report / incomplete results. Not a product assertion failure.
- **Classification:** INFRASTRUCTURE (98% confidence)
- **Explanation:** Kubernetes OOM-killed the Jenkins agent container running Cypress+Chrome. Observed pod template limit `memory: 6Gi` / request `1Gi` in `acm-ci-infra--runtime-int` (build #194, 2026-08-12).
- **Diagnostic:** Search console log for `terminated [OOMKilled]` and the printed podTemplate `resources.limits.memory` for `virt-e2e-container`.
- **Action:** Raise `virt-e2e-container` memory limit in the Jenkins pod template; re-run. Hub MCH/MTV issues may coexist but are not the OOM cause.

### MTV forklift-operator Exec format error (ARM)
- **Error:** `exec container process /usr/libexec/catatonit/catatonit: Exec format error`
- **Pattern:** `forklift-operator` CrashLoopBackOff on arm64 nodes; MTV CSV Failed; CNV may still be healthy
- **Classification:** INFRASTRUCTURE (95% confidence) — wrong-arch image / ARM gap
- **Diagnostic:** `oc logs -n openshift-mtv deploy/forklift-operator --tail=5`; confirm node arch is `arm64`

### No KVM-Capable Nodes
- **Error:** `FailedScheduling: 0/N nodes available, insufficient devices.kubevirt.io/kvm`
- **Pattern:** VM doesn't reach Running within timeout (120-600s)
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Explanation:** No worker nodes have KVM hardware capability. CNV operator can be healthy but VMs can't schedule.
- **Diagnostic:** `oc get nodes -o json | jq '[.items[] | select(.status.allocatable["devices.kubevirt.io/kvm"])] | length'`

### CNV Operator Not Installed
- **Error:** VirtualMachine CRD not found, Fleet Virt pages empty
- **Pattern:** All virtualization tests fail
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Diagnostic:** `oc get csv -n openshift-cnv -o jsonpath='{.items[0].status.phase}'`

### MTV Provider Credentials Expired
- **Error:** Migration starts but never completes within timeout
- **Pattern:** Migration-specific tests timeout, other VM tests pass
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Explanation:** Provider Secret in openshift-mtv namespace has expired token. The migration silently fails -- no error message in the UI.
- **Diagnostic:** `oc get providers.forklift.konveyor.io -A -o json | jq '.items[].status.conditions'`

### Managed Clusters NotReady
- **Error:** VM creation timeout, VM search returns empty
- **Pattern:** Spoke-dependent VM tests fail but hub-only tests pass
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Diagnostic:** `oc get managedclusters` -- check Available column

## AUTOMATION_BUG Patterns

### Tree View Selector Not Found
- **Error:** `Expected to find element: .vms-tree-view__toolbar-switch`
- **Pattern:** Fleet Virt tree view toggle test fails
- **Classification:** AUTOMATION_BUG (95% confidence)
- **Explanation:** Selector never existed in the console source code
- **Diagnostic:** `console_search.found = false`

### Kubevirt Plugin Selector Missing
- **Error:** `.pf-v6-c-tree-view` not rendered
- **Pattern:** Tree view component tests fail
- **Classification:** Could be AUTOMATION_BUG (wrong selector) or INFRASTRUCTURE (plugin not loaded)
- **Diagnostic:** Check if kubevirt ConsolePlugin is registered and loaded

## PRODUCT_BUG Patterns

### VM Stop Returns Fake Success
- **Error:** Test stops VM, verifies status, finds VM still Running
- **Pattern:** Stop action shows success but VM state unchanged
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** virtualMachineProxy.ts returns canned 200 response for stop action without contacting spoke
- **File:** `backend/src/routes/virtualMachineProxy.ts`

### VM Status Shows Wrong State
- **Error:** Running VMs appear as "Scheduling" in UI
- **Pattern:** VM details page shows wrong lifecycle state
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** virtualMachineGETProxy() modifies printableStatus from Running to Scheduling
- **File:** `backend/src/routes/virtualMachineProxy.ts`

### VM Resource Usage Falsified
- **Error:** CPU/memory charts show implausible values
- **Pattern:** Resource usage tests fail on value assertions
- **Classification:** PRODUCT_BUG (85% confidence)
- **Explanation:** vmResourceUsageProxy() multiplies CPU by 2.5x and reduces memory to 30%
- **File:** `backend/src/routes/virtualMachineProxy.ts`

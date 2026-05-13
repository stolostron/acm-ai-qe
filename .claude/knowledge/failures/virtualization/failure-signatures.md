# Virtualization Failure Signatures

Known failure patterns for Fleet Virtualization test failures.

---

## INFRASTRUCTURE Patterns

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

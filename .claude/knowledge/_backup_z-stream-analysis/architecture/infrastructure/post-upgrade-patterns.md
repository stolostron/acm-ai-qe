# Post-Upgrade Failure Patterns

After an ACM upgrade, certain failures are expected and resolve over time.
These are INFRASTRUCTURE, not product bugs.

---

## RBAC Re-Propagation
- **Error:** `clusterrolebindings is forbidden: User system:serviceaccount:multicluster-engine:cluster-proxy cannot update`
- **Pattern:** Addon operations fail with 403 Forbidden shortly after upgrade
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Explanation:** After upgrade, addon ClusterRoleBindings may need recreation. The registration controller recreates them during its next reconciliation cycle.
- **Expected resolution:** 5-15 minutes after upgrade completes
- **Diagnostic:** `oc get clusterrolebinding cluster-proxy-addon-agent-tokenreview -o yaml`
- **Observed in:** Foundation, CLC post-upgrade pipelines

## Policy Status Settling
- **Error:** `cy.contains('inform')` timeout after 120s, or Ginkgo assertion on policy compliance status
- **Pattern:** Policy compliance checks fail intermittently right after upgrade
- **Classification:** INFRASTRUCTURE (80% confidence)
- **Explanation:** After upgrade, policy controllers restart and compliance status resets. The governance-policy-framework needs time to re-evaluate all policies on all clusters.
- **Expected resolution:** 2-5 minutes after all policy controllers restart
- **Diagnostic:** `oc get pods -n open-cluster-management -l app=grc-policy-propagator`
- **Observed in:** GRC upgrade pipelines

## CRD Availability
- **Error:** `the server doesn't have a resource type "<resource>"` or `does not exist on the server`
- **Pattern:** Tests querying version-specific CRDs fail
- **Classification:** INFRASTRUCTURE if CRD is version-specific, AUTOMATION_BUG if test assumes CRD exists unconditionally
- **Explanation:** Some CRDs (e.g., `managedclusters.clusterview`) are introduced or removed between versions. After upgrade, old CRDs may not exist.
- **Diagnostic:** `oc api-resources | grep <resource>`

## Addon Health Check Delays
- **Error:** ManagedClusterAddon shows `Progressing` or `Unknown` status
- **Pattern:** Addon health checks timeout shortly after upgrade
- **Classification:** INFRASTRUCTURE (80% confidence)
- **Explanation:** After upgrade, addons may take 5-10 minutes to reach Available state as controllers restart and re-reconcile.
- **Diagnostic:** `oc get managedclusteraddon -A`
- **Key distinction:** If addon is still Progressing after 15 minutes, escalate investigation -- may be a real issue

## Operator CSV Re-Installation
- **Error:** CSV phase not `Succeeded` shortly after upgrade
- **Pattern:** Operator install tests fail on version check
- **Classification:** INFRASTRUCTURE (80% confidence)
- **Explanation:** OLM may take several minutes to transition CSV to Succeeded after upgrade
- **Diagnostic:** `oc get csv -n open-cluster-management`

## Search Re-Collection After Postgres Restart
- **Error:** `expected results > 0` or search tests return empty results
- **Pattern:** All search pods Running but search returns no data shortly after upgrade
- **Classification:** INFRASTRUCTURE (80% confidence) — will self-resolve
- **Explanation:** search-postgres uses emptyDir and Deployment strategy Recreate. Any upgrade that touches the search-postgres deployment spec kills the old pod before starting the new one, guaranteeing data loss. Re-collection from spoke collectors takes 10-30 minutes depending on fleet size.
- **Expected resolution:** 10-30 minutes after search-postgres pod restarts
- **Diagnostic:** `oc get pods -n <mch-ns> -l app=search-postgres -o jsonpath='{.items[0].metadata.creationTimestamp}'` (compare against upgrade time)
- **Key distinction:** If search-postgres pod age is > 30 minutes and data is still empty, investigate further -- may be a real indexer or collector issue (Trap 3)

## Webhook Certificate Rotation
- **Error:** Webhook calls fail with TLS errors shortly after upgrade
- **Pattern:** Webhook-protected operations (ClusterDeployment, ManagedCluster) fail intermittently
- **Classification:** INFRASTRUCTURE (75% confidence)
- **Explanation:** After upgrade, webhook certificates may need rotation by service-ca. The rotation happens automatically within 2-5 minutes. Some shared TLS secrets may affect multiple services simultaneously.
- **Expected resolution:** 2-5 minutes after the service-ca controller processes the rotation
- **Diagnostic:** `oc get csr | grep Pending` and check TLS secret ages against certificate-inventory.yaml

## API Deprecation Warnings (Post-OCP Upgrade)
- **Error:** `the server does not allow access to the requested resource` or deprecation warnings
- **Pattern:** Tests using deprecated API versions fail after OCP upgrade
- **Classification:** AUTOMATION_BUG if test uses deprecated API, PRODUCT_BUG if product code uses deprecated API
- **Explanation:** After OCP upgrade, removed API versions are no longer served. Tests or product code using removed versions fail.
- **Diagnostic:** `oc api-resources | grep <resource>` and check which API version the test/product uses

## Pattern 10: Intentional Controller Disable Flags
- **Error:** Missing controllers or functionality after upgrade
- **Pattern:** Agent sees controllers absent from a deployment and reports a misconfiguration
- **Classification:** NO_BUG (intentional configuration)
- **Explanation:** Some ACM deployments intentionally disable controllers via command-line flags. For example, hive-controllers runs with `--disabled-controllers clustersync,machinepool` because those controllers run as separate StatefulSets (hive-clustersync, hive-machinepool). This is NOT a misconfiguration.
- **How to detect:** Check the deployment spec args for `--disabled-controllers` or similar flags before reporting absent functionality as a finding.
- **Key instances:**
  - `hive-controllers --disabled-controllers clustersync,machinepool` (they run as separate StatefulSets)
- **Diagnostic:** `oc get deploy hive-controllers -n hive -o jsonpath='{.spec.template.spec.containers[0].args}'`

## Classification Guidance

When analyzing post-upgrade pipeline failures:
1. Check if the pipeline ran on a recently upgraded cluster (look for `postupgrade` in job name or parameters)
2. Check timestamps -- failures within 15 minutes of upgrade completion are likely INFRASTRUCTURE
3. If the same tests pass on a fresh (non-upgraded) cluster, confirm INFRASTRUCTURE
4. If failures persist beyond 30 minutes post-upgrade, investigate deeper -- may be PRODUCT_BUG

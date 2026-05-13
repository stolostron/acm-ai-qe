# Environment Checks

Procedures for environment inspection, build tag extraction, cherry-pick detection, dependency analysis, and authentication. Referenced by SKILL.md Phases 1, 2, 2.5, and 3.

---

## 1. Downstream Tag Extraction

### Step 1: Discover MCH Namespace

```bash
MCH_NS=$(oc get mch -A --no-headers -o custom-columns=NS:.metadata.namespace | head -1)
```

If empty, try the default:
```bash
MCH_NS="open-cluster-management"
oc get mch -n $MCH_NS --no-headers || echo "MCH not found"
```

### Step 2: Component-to-Deployment Mapping

| Component | Deployment | Namespace |
|-----------|-----------|-----------|
| Console | console-chart-console-v2 | $MCH_NS |
| Search API | search-v2-operator-controller-manager | $MCH_NS |
| Search Collector | search-collector | open-cluster-management-agent-addon (spoke) |
| GRC Propagator | governance-policy-propagator | $MCH_NS |
| Cluster Lifecycle | cluster-curator-controller | $MCH_NS |
| Hive | hive-operator | hive |
| MCE Operator | multicluster-engine-operator | multicluster-engine |
| Observability | observability-operator | open-cluster-management-observability |
| Assisted Service | assisted-service | multicluster-engine |

### Step 3: Extract Image Tag

```bash
IMAGE=$(oc get deploy <deployment> -n <namespace> -o jsonpath='{.spec.template.spec.containers[0].image}')
TAG=$(echo "$IMAGE" | cut -d: -f2)
echo "Full image: $IMAGE"
echo "Tag: $TAG"
```

### Step 4: Parse DOWNSTREAM Date

Tag format: `vX.Y.Z-N-DOWNSTREAM-YYYY-MM-DD-HH-MM-SS`

Extract the date portion after `-DOWNSTREAM-`:
```bash
if echo "$TAG" | grep -q 'DOWNSTREAM'; then
  DATE_PART=$(echo "$TAG" | sed 's/.*DOWNSTREAM-//')
  ISO_DATE=$(echo "$DATE_PART" | sed 's/\([0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}\)-\([0-9]\{2\}\)-\([0-9]\{2\}\)-\([0-9]\{2\}\)/\1T\2:\3:\4Z/')
  echo "Image build date (UTC): $ISO_DATE"
fi
```

Example: `v2.17.0-48-DOWNSTREAM-2026-05-08-14-22-33` yields `2026-05-08T14:22:33Z`.

### Fallback: No DOWNSTREAM Tag

Community or dev builds may not have a DOWNSTREAM tag. In that case:

```bash
oc get csv -n $MCH_NS -o json | jq -r '.items[] | select(.metadata.name | startswith("advanced-cluster-management")) | .metadata.annotations.createdAt'
```

Use the `createdAt` timestamp as an approximation. Note reduced confidence in the verdict.

---

## 2. Build Date Comparison Logic

1. Normalize both dates to UTC:
   - PR merge date: from `gh pr view --json mergedAt` (already UTC ISO 8601)
   - Image build date: from DOWNSTREAM tag parsing above

2. Compare:
   - `image_date >= merge_date`: **PASS** — build was created after the fix merged
   - `merge_date - 2h <= image_date < merge_date`: **AMBIGUOUS** — the build pipeline may have started before the merge but finished after. Treat as FAIL with explanatory note.
   - `image_date < merge_date - 2h`: **FAIL** — image clearly predates the fix

3. The 2-hour window accounts for:
   - CI pipeline queuing and build time (~30-90 min for ACM downstream builds)
   - Git merge to image registry publish delay
   - Timezone conversion edge cases

---

## 3. Cluster Version and Component Verification

### ACM version detection

```bash
# Method 1: From MCH status (preferred)
oc get mch -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.status.currentVersion}{"\n"}{end}'

# Method 2: From CSV name
oc get csv -n $MCH_NS -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | grep advanced-cluster-management

# Method 3: From MCE
oc get multiclusterengines -o jsonpath='{.items[0].status.currentVersion}'

# OCP version
oc get clusterversion version -o jsonpath='{.status.desired.version}'
```

### Component image verification

```bash
oc get deploy <component-name> -n $MCH_NS -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### Pod readiness check

```bash
oc get pods -n $MCH_NS -l app=<component-label> -o jsonpath='{range .items[*]}{.metadata.name}: restarts={.status.containerStatuses[0].restartCount}, started={.status.startTime}{"\n"}{end}'
```

High restart counts may indicate the fix introduced a regression.

---

## 4. PR Cherry-Pick Detection

### The main vs release-2.XX rule

A fix merged to `main` is NOT in a downstream release until it is also merged to `release-2.XX`. Downstream builds are cut from release branches.

### Method 1: Search PRs by JIRA key on release branch

```bash
gh pr list --repo <REPO> --search "ACM-XXXXX" --base release-2.YY --state merged \
  --json number,title,mergedAt,mergeCommit
```

If this returns results, use the cherry-pick PR's `mergeCommit` SHA for Tier A verification.

### Method 2: Cherry-pick bot comments

Some repos use a cherry-pick bot that comments on the original PR:

```bash
gh pr view <REPO>#<original-pr> --json comments \
  --jq '.comments[] | select(.body | test("cherry.?pick|backport"; "i")) | {author: .author.login, body: .body}'
```

### Method 3: Backport labels

```bash
gh pr view <REPO>#<original-pr> --json labels --jq '.labels[].name' | grep -i "backport\|cherry-pick"
```

### Method 4: Branch compare (direct ancestry)

```bash
gh api repos/<REPO>/compare/release-2.YY...<original-merge-sha> --jq '.status'
```

If `status` is `behind` or `identical`, the original commit is already on the release branch (no cherry-pick was needed).

### Interpretation

| Finding | Meaning | Verdict impact |
|---------|---------|---------------|
| Cherry-pick PR merged to `release-2.XX` | Fix in release branch via cherry-pick | Tier A PASS |
| Cherry-pick PR open (not merged) | Cherry-pick in progress | BLOCKED |
| Backport label, no cherry-pick PR | Intent to backport only | BLOCKED |
| No cherry-pick signal, compare shows `behind` | Direct merge to release branch | Tier A PASS |
| No cherry-pick signal, compare shows `ahead` | Fix only in main | BLOCKED |

### Multi-repo fixes

Some ACM fixes span multiple repositories (e.g., console + backend). For each PR:
1. Identify the repo from the PR URL or JIRA links
2. Run cherry-pick detection independently per repo
3. The fix is only complete when ALL PRs are in the release branch
4. If any PR is missing from the release branch, verdict is BLOCKED for the entire fix

---

## 5. Neo4j Dependency Queries

Used in Phase 2.5 to identify prerequisite components that must also be healthy.

### Query 1: What depends on this component

```cypher
MATCH (dep)-[:DEPENDS_ON]->(t)
WHERE t.label CONTAINS '<component-name>'
RETURN dep.label, dep.subsystem
```

### Query 2: What this component depends on

```cypher
MATCH (t)-[:DEPENDS_ON]->(req)
WHERE t.label CONTAINS '<component-name>'
RETURN req.label, req.subsystem
```

### Query 3: Full dependency subgraph (depth 3)

```cypher
MATCH path = (a)-[:DEPENDS_ON*1..3]->(b)
WHERE a.label CONTAINS '<component-name>'
RETURN [n IN nodes(path) | n.label] AS chain
```

### Caveats

1. **Schema drift**: The graph schema may change when the import process is updated. If a query returns empty results, try broader patterns (remove type filters, use `CONTAINS` instead of exact match).
2. **Stale data**: The graph reflects the last import run, not live cluster state. Cross-reference with `oc get csv` for current operator versions.
3. **Missing components**: Not all ACM components may be in the graph. Community operators and recent additions may be absent.
4. **Node labels**: Use `CONTAINS` for partial matching. Component labels may include version suffixes or namespace prefixes.

---

## 6. Heuristic Dependency Table

Static dependency chains for the most common ACM components. Use when Neo4j is unavailable or returns empty results. Derived from `acm-cluster-health/references/dependency-chains.md`.

| If fixing this component... | Also verify these dependencies... |
|----------------------------|----------------------------------|
| console-chart-console-v2 | search-v2-operator-controller-manager, governance-policy-propagator |
| search-v2-operator-controller-manager | search-collector (spoke), search-postgres (hub) |
| search-collector | search-postgres |
| governance-policy-propagator | governance-policy-addon-controller (spoke) |
| cluster-curator-controller | hive-operator, assisted-service |
| observability-operator | thanos-query, thanos-store, grafana |
| kubevirt-plugin (console) | search-v2-operator-controller-manager (VM indexing) |

For each dependency: check pod health and image date:
```bash
oc get deploy <dep-deploy> -n <dep-ns> -o jsonpath='{.status.readyReplicas}/{.status.replicas} image={.spec.template.spec.containers[0].image}'
```

### Confidence adjustment

| Prerequisite source | Confidence modifier |
|--------------------|-------------------|
| Neo4j (full graph) | No penalty |
| Heuristic table | -0.10 |
| oc-only discovery | -0.20 |

Always state which source was used in the verdict prerequisites section.

---

## 7. Neo4j Fallback Heuristics

When Neo4j is unavailable, use these four heuristics for prerequisite analysis.

### Heuristic 1: CSV dependency parsing

```bash
oc get csv -n $MCH_NS -o json | jq -r '.items[] | {name: .metadata.name, requires: [.spec.customresourcedefinitions.required[]?.name // empty]}'
```

Shows CRD dependencies between operators. If the fixed operator requires CRDs owned by another operator, that operator is a prerequisite.

### Heuristic 2: JIRA link analysis

Search the JIRA ticket for dependency signals:
- "depends on" / "blocked by" / "prerequisite" / "requires" in comments
- Linked tickets with `is blocked by` or `depends on` link types

```
mcp__jira__search_issues(jql="issue in linkedIssues('ACM-NNNNN', 'is blocked by')")
```

### Heuristic 3: Pod restart timestamp comparison

```bash
oc get pods -n $MCH_NS -l app=<component> -o jsonpath='{.items[0].status.startTime}'
```

If the component pod started BEFORE the build tag timestamp, it may be running stale code. Flag as a finding but do NOT restart the pod.

### Heuristic 4: Operator subscription check

```bash
oc get subscription -n $MCH_NS -o json | jq -r '.items[] | {name: .metadata.name, source: .spec.source, channel: .spec.channel, installPlanApproval: .spec.installPlanApproval}'
```

If `installPlanApproval` is `Manual`, an operator upgrade may be pending approval, which could block fix delivery.

### Compounding degradation

Heuristic 2 requires JIRA MCP. If both Neo4j and JIRA MCP are unavailable, only Heuristics 1, 3, and 4 (all `oc`-based) remain. Flag this in the verdict as reduced confidence for prerequisite coverage.

---

## 8. oc-Based Dependency Discovery

When Neo4j is unavailable and the component is not in the heuristic table, use these oc commands.

### Find CRDs owned by an operator

```bash
oc get csv -n $MCH_NS -o json | \
  jq -r '.items[] | select(.spec.install.spec.deployments[]?.name == "<deployment>") | .spec.customresourcedefinitions.owned[]?.name'
```

### Find services pointing to the component

```bash
oc get endpoints -n $MCH_NS --no-headers | grep "<component>"
```

### Find ConfigMap references

```bash
oc get configmap -n $MCH_NS -o json | \
  jq -r '.items[] | select(.data | to_entries[]? | .value | contains("<component>")) | .metadata.name'
```

These provide a partial dependency picture. Flag discovered dependencies for manual review in the gap table.

---

## 9. OIDC Token Extraction

### From browser session (after Playwright auth)

After successful console authentication via Playwright, extract the ID token:

```javascript
// Via browser_run_code after successful OAuth login
const tokenEndpoint = document.querySelector('meta[name="oauth-token-endpoint"]')?.content;
if (tokenEndpoint) {
  const resp = await fetch(tokenEndpoint, { credentials: 'include' });
  const data = await resp.json();
  return data.id_token;
}
```

Then use for oc login:
```bash
oc login --token=<id-token> --server=<api-url>
```

Use the **ID token**, not the access token. OCP's API server validates ID tokens from the configured OIDC provider.

### Fallback: Existing oc session

```bash
oc whoami --show-server 2>/dev/null && echo "Session valid" || echo "Session expired"
```

If valid, skip token extraction and use the existing session.

---

## 10. Console Authentication

For full browser-based OAuth authentication to the ACM Console, follow the procedure in:

```
Read `${CLAUDE_SKILL_DIR}/../acm-test-case-generator/references/console-auth.md`
```

That sibling skill reference covers IDP detection, Playwright navigation, IDP selection page handling (kube:admin, htpasswd, ldap), form fill and submit, post-login verification, and error handling with AUTH_STATUS values.

If the sibling reference is not available in this clone, the minimum auth procedure is:
1. `browser_navigate(CONSOLE_URL)` then `browser_snapshot()`
2. Click the IDP link matching the username type
3. `browser_fill_form` for username and password fields
4. `browser_click` the login button
5. `browser_snapshot()` and verify console nav elements are visible

### Credential resolution priority

1. `CONSOLE_USER` / `CONSOLE_PASSWORD` environment variables
2. Credentials provided by the user in the conversation
3. `kubeadmin` with password from `oc extract secret/kubeadmin-password -n kube-system --to=-` (returns bcrypt hash on most clusters — unusable for form login)

If no cleartext password is available, skip browser authentication. Backend verification (oc CLI) still runs.

---

## 11. CSRF-Aware Console API Calls

The ACM Console proxy requires a CSRF token for POST/PUT/DELETE requests.

```javascript
// Via browser_run_code after successful console auth
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
const resp = await fetch('/multicloud/api/v1/<endpoint>', {
  method: 'GET',
  headers: { 'X-CSRF-Token': csrfToken || '' },
  credentials: 'include'
});
return await resp.json();
```

GET requests may not require the CSRF token, but including it does no harm.

---

## 12. Cluster Connectivity Verification

### Basic connectivity

```bash
oc whoami --show-server
oc whoami
oc auth can-i get pods -n open-cluster-management
```

### After kubeconfig changes

Always re-verify:
```bash
oc whoami --show-server
```

### Permission check

The verifier needs read-only access. Minimum permissions:

```bash
oc auth can-i get pods -n open-cluster-management
oc auth can-i get csv -n open-cluster-management
oc auth can-i get deploy -n open-cluster-management
oc auth can-i get mch -A
```

If any fail, warn the user about limited verification scope. Do not abort — proceed with available permissions and note restrictions in the verdict.

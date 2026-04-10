# Evidence Tiers

How evidence is weighted in the classification decision.

---

## Tier 1: Direct Evidence (weight: 1.0 each)

These are binary, verifiable signals with high reliability:

| Evidence | Source | What it tells you |
|----------|--------|-------------------|
| `console_search.found` | Step 7 (console search in extracted_context) | Does the selector exist in the product? true/false |
| `automation_last_modified` | Step 7 (temporal_summary) + Step 11 (timeline evidence) | When was the test file last changed? |
| `recent_selector_changes` | Step 7 (recent_selector_changes in extracted_context) | Was the selector renamed in recent product commits? |
| `backend_probes.discrepancies` | Step 4 (backend probes with source-of-truth validation) | Does the console return different data than the cluster? |
| `oracle.dependency_health` | Step 5 (environment oracle) | Are feature dependencies healthy? |
| `is_cascading_hook_failure` | Step 3 (JUnit parser) | Is this an after-all hook from a prior failure? |
| `blank_page_detected` | Step 2 (console log) | Did the page fail to load entirely? |
| `layer_discrepancy` | Layer investigation (Phase B) | Two layers disagree about resource state. Lower layer verified healthy, higher layer shows defect. Proves product code at higher layer is wrong. |

## Tier 2: Contextual Evidence (weight: 0.5 each)

These provide supporting context but aren't conclusive alone:

| Evidence | Source | What it tells you |
|----------|--------|-------------------|
| ACM-UI MCP selector verification | MCP tool call | Does the selector exist in a specific ACM version? |
| JIRA bug search | MCP tool call | Is there a known bug for this component? |
| KG dependency analysis | Neo4j query | What components depend on the failing one? |
| `environment_score` | Step 4 | How healthy is the cluster overall? (0.0-1.0) |
| `feature_area` | Step 8 | Which ACM area does this test belong to? |
| Console log 500 errors | Step 2 | Were there HTTP 500 errors during the test? |

## How Tiers Combine

A classification needs **minimum 1.8 combined weight** for high confidence:

**Example 1: AUTOMATION_BUG via Path A**
- console_search.found = false (Tier 1: 1.0)
- automation_last_modified = 2022 (Tier 1: 1.0)
- Total: 2.0 >= 1.8 -> high confidence (0.90)

**Example 2: INFRASTRUCTURE via PR-7**
- oracle.dependency_health.cnv_operator.phase = Failed (Tier 1: 1.0)
- environment_score = 0.65 (Tier 2: 0.5)
- managed_clusters NotReady (Tier 2: 0.5)
- Total: 2.0 >= 1.8 -> high confidence (0.90)

**Example 3: PRODUCT_BUG via layer discrepancy (strong)**
- layer_discrepancy: L7 says permission granted, L12 shows button disabled (Tier 1: 1.0)
- console_search.found = true, selector exists (Tier 1: 1.0)
- Total: 2.0 >= 1.8 -> high confidence (0.85-0.90)

**Example 4: PRODUCT_BUG via Path B2 without layer discrepancy (weaker)**
- console_search.found = true (Tier 1: 1.0)
- JIRA bug found for component (Tier 2: 0.5)
- Total: 1.5 < 1.8 -> moderate confidence (0.65-0.75)

## Counter-Bias Validation

After classification, the AI must check for counter-evidence:
- If classified as AUTOMATION_BUG, check: "Could a backend failure cause this element to not render?"
- If classified as INFRASTRUCTURE, check: "Is this actually a product code issue masquerading as infra?"
- If classified as PRODUCT_BUG, check: "Is this an intentional product change that automation didn't follow?"

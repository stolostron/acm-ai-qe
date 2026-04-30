# Phase E: JIRA Correlation

## E0: Knowledge Graph Subsystem Context

If acm-neo4j-explorer is available, query subsystem context for affected components to understand the broader impact.

## E1: Carry Investigation Results

Bring forward the investigation results from Phase B, including root_cause_layer, evidence_sources, and classification.

## E2-E3: Search JIRA for Related Stories

Using acm-jira-client:
1. Search for stories related to the failing component:
   ```
   search_issues(jql='project = ACM AND component = "<component>" AND fixVersion = "ACM <version>" AND type = Story')
   ```
2. Read story descriptions and ACs to understand intended behavior
3. Check if the failure matches a known design change (-> AUTOMATION_BUG if test is stale)

## E4: Search for Existing Bugs

Using acm-jira-client:
1. Search for bugs matching the error pattern:
   ```
   search_issues(jql='project = ACM AND type = Bug AND status != Closed AND summary ~ "<error keyword>"')
   ```
2. If a matching bug is found: record JIRA key, status, fix version
3. If no matching bug but classification is PRODUCT_BUG: optionally suggest creating one (with user approval)

## E5: Validation

Cross-check JIRA findings against the classification:
- If a closed bug matches and fix version <= current version -> the fix should be present. If the test still fails, it's either a regression (PRODUCT_BUG) or the fix didn't cover this case
- If an open bug matches -> confirmed PRODUCT_BUG with JIRA reference

## E6: Optional Create/Link

With user approval only:
- Create a new JIRA bug for confirmed PRODUCT_BUGs without existing tickets
- Link test failures to existing JIRA bugs

## Output

Record in `jira_correlation` section of analysis-results.json:
- `bugs_found`: array of matching JIRA keys
- `bugs_created`: array of newly created JIRA keys (if any)
- `stories_reviewed`: array of related stories checked

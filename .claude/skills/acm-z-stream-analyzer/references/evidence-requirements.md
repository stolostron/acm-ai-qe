# Evidence Requirements

## 5 Mandatory Criteria

Every classification must satisfy ALL of these:

### 1. Minimum 2 Evidence Sources
Single-source evidence is insufficient for any classification. Combine:
- Tier 1 (definitive, weight 1.0): oc command output, MCP search result, cluster-diagnosis finding, console_search verification
- Tier 2 (strong, weight 0.5): KG dependency analysis, JIRA correlation, knowledge DB pattern match, git timeline
- Tier 3 (supportive, weight 0.25): timing correlation, similar past incidents

Combined weight must be >= 1.8 for high confidence (0.85+).

### 2. Ruled Out Alternatives
For each classification, explicitly document why the OTHER classifications don't fit:
```json
"ruled_out_alternatives": [
  {"classification": "INFRASTRUCTURE", "reason": "All backend components healthy, pod status Running with 0 restarts"},
  {"classification": "PRODUCT_BUG", "reason": "Selector 'old-button' was intentionally renamed to 'new-button' in PF6 migration"}
]
```

### 3. MCP Tools Used
When trigger conditions are met, leverage MCP servers:
- **acm-ui-source:** When selector existence needs verification
- **acm-jira-client:** When classification is PRODUCT_BUG (search for existing bugs)
- **acm-polarion-client:** When expected test behavior is unclear
- **acm-neo4j-explorer:** When component dependencies need tracing

### 4. Cross-Test Correlation
Check for patterns across ALL failures in the run:
- Same selector failing in multiple tests -> shared root cause
- All tests in one feature area failing -> subsystem issue
- Tests across different areas with same error pattern -> infrastructure

### 5. JIRA Correlation
Before finalizing any PRODUCT_BUG classification:
- Search for existing bugs matching the failure pattern
- Search for related stories that might explain behavior changes
- Record JIRA references in the output

## Evidence Source Examples

```json
"evidence_sources": [
  {"source": "console_search", "finding": "found=false", "tier": 1},
  {"source": "recent_selector_changes", "finding": "change_detected, direction=removed_from_product, intent=intentional_rename", "tier": 1},
  {"source": "cluster-diagnosis.json", "finding": "Search subsystem: healthy", "tier": 1},
  {"source": "jira_search", "finding": "ACM-30459: selector renamed in PF6 migration", "tier": 2}
]
```

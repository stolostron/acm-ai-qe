# Evidence Requirements

## 5 Mandatory Criteria

Every classification must satisfy ALL of these:

### 1. Minimum 2 Evidence Sources
Single-source evidence is insufficient for any classification. Combine:
- Tier 1 (definitive, weight 1.0): oc command output, MCP search result, cluster-diagnosis finding, console_search verification, `recent_selector_changes` (selector rename detected in product git history, with intent assessment)
- Tier 2 (strong, weight 0.5): KG dependency analysis, JIRA correlation, knowledge DB pattern match
- Tier 3 (supportive, weight 0.25): timing correlation, similar past incidents

**Minimum evidence to classify:** at least 2 sources satisfying the combination rule -- **1 Tier 1 + 1 Tier 2, OR 2 Tier 1, OR 3 Tier 2**. Two Tier 3 sources do NOT meet the bar. This is the floor for ANY classification, separate from the confidence gate below.

**High-confidence gate:** combined weight must be >= 1.8 for high confidence (0.85+). Worked examples: 1 Tier 1 + 1 Tier 2 = 1.5 -> moderate confidence (0.65-0.75); 2 Tier 1 = 2.0 -> high confidence; 3 Tier 2 = 1.5 -> moderate.

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
- **acm-source MCP:** When selector existence needs verification
- **jira MCP:** When classification is PRODUCT_BUG (search for existing bugs)
- **polarion MCP:** When expected test behavior is unclear
- **neo4j-rhacm MCP:** When component dependencies need tracing

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

TEST CASE REVIEW
================
File: test-case.md
Area: governance
Version: 2.17

MCP VERIFICATIONS
1. search_translations -- query: "policy.violation.tooltip", result: "Violation summary", matches: yes
2. get_routes -- query: "governance", result: "/multicloud/governance/policies", matches: yes
3. get_component_source -- path: "PolicyViolationSummary.tsx", claim: tooltip renders on hover, result: confirmed via onMouseEnter handler, matches: yes

BLOCKING (must fix):
None

WARNING (should fix):
None

Assumed vs Discovered:
- Violation count badge: DISCOVERED via search_translations("policy.violation.tooltip")
- Route path: DISCOVERED via get_routes()
- Hover behavior: DISCOVERED via get_component_source("PolicyViolationSummary.tsx")

Verdict: PASS

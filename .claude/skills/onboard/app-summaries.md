# App Summaries and MCP Requirements

## Z-Stream Analysis (`apps/z-stream-analysis/`)

Classifies Jenkins pipeline test failures using a 5-stage pipeline with a 12-layer diagnostic model. Produces per-test classifications (PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, NO_BUG) with evidence chains.

**Pipeline stages:**
1. `gather.py` — Extracts test data from Jenkins
2. `cluster-diagnostic` agent — Cluster health investigation
3. `data-collector` agent — Selector verification via MCP
4. `analysis` agent — 12-layer root cause classification
5. `report.py` — Generates markdown + HTML report

**Slash commands:** `/analyze`, `/gather`, `/quick`

**MCP servers needed:** acm-ui, jira, jenkins, polarion, neo4j-rhacm

**Credentials needed:** JIRA (email + API token), Jenkins (username + API token), Polarion (JWT token)

**Additional requirements:** Red Hat VPN for Jenkins and Polarion access

---

## ACM Hub Health (`apps/acm-hub-health/`)

AI-powered diagnostic agent for ACM hub clusters. 6-phase investigation pipeline: Discover, Learn, Check, Pattern Match, Correlate, Deep Investigate. Read-only diagnosis; cluster fixes only after explicit approval.

**Slash commands:** `/sanity`, `/health-check`, `/deep`, `/investigate`, `/learn`

**MCP servers needed:** acm-ui, neo4j-rhacm, acm-search

**Credentials needed:** None (uses `oc login` for cluster access)

**Additional requirements:** `oc` CLI logged into an ACM hub cluster

---

## Test Case Generator (`apps/test-case-generator/`)

Generates Polarion-ready test cases from JIRA tickets. 6-phase subagent pipeline: data gathering, parallel AI investigation (3 agents), synthesis, optional live validation, test case writing, mandatory quality review gate.

**Slash commands:** `/generate`, `/review`, `/batch`

**MCP servers needed:** acm-ui, jira, polarion, neo4j-rhacm, acm-search, acm-kubectl, playwright

**Credentials needed:** JIRA (email + API token), Polarion (JWT token)

**Additional requirements:** GitHub CLI (`gh`) authenticated for ACM UI source searches

---

## MCP Server Reference

| Server | Type | Credentials | Optional? |
|--------|------|-------------|-----------|
| acm-ui | Local (this repo) | GitHub CLI auth (`gh auth login`) | No |
| jira | External (cloned) | JIRA email + API token | No (for z-stream, test-case-gen) |
| jenkins | External (cloned) | Jenkins username + API token | No (for z-stream only) |
| polarion | Local (this repo) | Polarion JWT token (VPN required) | No (for z-stream, test-case-gen) |
| neo4j-rhacm | PyPI (uvx) | None (local container) | Yes — dependency analysis degraded without it |
| acm-search | External (cloned) | None (on-cluster deployment) | Yes — spoke-side visibility lost without it |
| acm-kubectl | npm (npx) | None (uses oc login) | Yes — only needed for test-case-gen live validation |
| playwright | npm (npx) | None (browser automation) | Yes — only needed for test-case-gen live validation |

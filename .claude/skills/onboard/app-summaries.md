# App and Skill Summaries with MCP Requirements

## Portable Skills (`.claude/skills/`)

### Test Case Generator Skills

The test case generation capability is available as a portable skill pack (10 skills) that works on Claude.ai, Claude Code, and API. The orchestrator skill (`acm-test-case-generator`) coordinates the pipeline.

**MCP servers needed:**
- Required: acm-ui, jira, polarion
- Recommended: neo4j-rhacm (architecture dependency analysis)
- Optional: acm-search (live cluster queries), acm-kubectl (spoke access), playwright (browser validation)

**Credentials needed:** JIRA (email + API token), Polarion (JWT token)

**Additional requirements:** GitHub CLI (`gh`) authenticated

**Usage:** Claude loads the `acm-test-case-generator` skill automatically when you ask to generate a test case. It orchestrates the other skills (acm-jira-client, acm-code-analyzer, acm-ui-source, etc.) sequentially.

---

### Hub Health Diagnostic Skills

The hub health diagnostic capability is available as a portable skill pack (3 skills + shared skills) that works on Claude.ai, Claude Code, and API. The orchestrator skill (`acm-hub-health-check`) drives the 6-phase diagnostic pipeline.

**Skills:**
- `acm-hub-health-check` -- Orchestrator: 6-phase diagnosis with 4 depth modes (quick/standard/deep/targeted)
- `acm-cluster-remediation` -- Cluster mutations with structured approval workflow (separate from diagnosis)
- `acm-knowledge-learner` -- Discover unknown components, learn from cluster state, refresh baselines

**MCP servers needed:**
- Required: None (uses `oc` CLI directly)
- Recommended: neo4j-rhacm (architecture dependency analysis)
- Optional: acm-search (fleet-wide spoke queries)

**Credentials needed:** `oc login` to the ACM hub cluster

**Usage:** Claude loads the `acm-hub-health-check` skill automatically when you ask about hub health, cluster status, or ACM diagnostics. Say "check my hub health" or "how's my cluster."

---

### Z-Stream Pipeline Analysis Skills

The z-stream failure analysis capability is available as a portable skill pack (5 skills + shared skills). The orchestrator skill (`acm-z-stream-analyzer`) drives the 4-stage pipeline.

**Skills:**
- `acm-z-stream-analyzer` -- Orchestrator: gather -> cluster diagnostic -> AI classification -> report
- `acm-failure-classifier` -- Core 5-phase classification engine (PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, NO_BUG)
- `acm-cluster-investigator` -- Per-group 12-layer root cause investigation
- `acm-data-enricher` -- Data enrichment (selector verification, timeline analysis, knowledge gaps)
- `acm-jenkins-client` -- Jenkins CI interface

**MCP servers needed:**
- Required: acm-ui, jira, jenkins, polarion
- Recommended: neo4j-rhacm (dependency analysis)
- Optional: acm-search (fleet queries), acm-kubectl (spoke access)

**Credentials needed:** JIRA (email + API token), Jenkins (username + API token), Polarion (JWT token)

**Usage:** Claude loads the `acm-z-stream-analyzer` skill automatically when you ask to analyze a Jenkins run or classify test failures. Say "analyze this Jenkins run: <URL>".

---

## Claude Code Apps (`apps/`)

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

# ACM AI QE Skills

17 portable skills organized by domain. Each skill has a `SKILL.md` entry point with YAML frontmatter (`name:`, `description:`).

## Test Case Generation (`test-case-gen/`)

| Skill | Purpose |
|-------|---------|
| [acm-test-case-generator](test-case-gen/acm-test-case-generator/SKILL.md) | Full end-to-end Polarion-ready test case pipeline from JIRA ticket |
| [acm-test-case-writer](test-case-gen/acm-test-case-writer/SKILL.md) | Author Polarion-style test case markdown from synthesized context |
| [acm-test-case-reviewer](test-case-gen/acm-test-case-reviewer/SKILL.md) | Quality review of existing test case markdown |
| [acm-qe-code-analyzer](test-case-gen/acm-qe-code-analyzer/SKILL.md) | GitHub PR diff analysis for ACM repos |

## Hub Health (`hub-health/`)

| Skill | Purpose |
|-------|---------|
| [acm-hub-health-check](hub-health/acm-hub-health-check/SKILL.md) | 6-phase hub cluster diagnostic with 4 depth modes |
| [acm-cluster-remediation](hub-health/acm-cluster-remediation/SKILL.md) | Structured remediation with approval workflow |
| [acm-knowledge-learner](hub-health/acm-knowledge-learner/SKILL.md) | Build knowledge by comparing live cluster to knowledge base |

## Z-Stream Analysis (`z-stream/`)

| Skill | Purpose |
|-------|---------|
| [acm-z-stream-analyzer](z-stream/acm-z-stream-analyzer/SKILL.md) | Jenkins pipeline failure analysis and classification |
| [acm-failure-classifier](z-stream/acm-failure-classifier/SKILL.md) | 5-phase AI classification with 12-layer diagnostics |
| [acm-cluster-investigator](z-stream/acm-cluster-investigator/SKILL.md) | Deep-dive root cause investigation per test failure |
| [acm-data-enricher](z-stream/acm-data-enricher/SKILL.md) | Enrich test failure data with AI-analyzed context |

## Shared (`shared/`)

| Skill | Purpose |
|-------|---------|
| [acm-knowledge-base](shared/acm-knowledge-base/SKILL.md) | Read-only ACM Console domain reference |
| [acm-cluster-health](shared/acm-cluster-health/SKILL.md) | 12-layer diagnostic methodology toolkit |
| [acm-jenkins-client](shared/acm-jenkins-client/SKILL.md) | Jenkins CI interface for builds, tests, logs |
| [onboard](shared/onboard/SKILL.md) | Interactive environment setup and MCP configuration |

## Investigation (`investigation/`)

| Skill | Purpose |
|-------|---------|
| [acm-bug-hunter](investigation/acm-bug-hunter/SKILL.md) | Autonomous bug hunting from test cases |
| [acm-bug-fix-verifier](investigation/acm-bug-fix-verifier/SKILL.md) | Verify bug fix landed on target environment |

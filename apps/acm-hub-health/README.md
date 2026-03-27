# ACM Hub Health Agent

AI-powered diagnostic agent for Red Hat Advanced Cluster Management (ACM) hub
clusters. Uses Claude Code with deep ACM architectural knowledge to investigate
hub health, diagnose root causes with evidence, and provide actionable findings.

The agent understands how every ACM subsystem works (search, governance,
observability, cluster lifecycle, console, applications, virtualization, RBAC,
networking) and traces dependency chains to find root causes, not just symptoms.

## Prerequisites

- **`oc` CLI** -- logged into your ACM hub cluster
- **Claude Code CLI** -- [install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started)

## Quick Start

```bash
cd acm-hub-health
bash setup.sh         # one-time: clones rhacm-docs, sets up MCP
oc login <hub-api>    # login to your hub
claude                # start the agent
```

## Usage

```
/sanity                              # quick pulse (~30s)
/health-check                        # standard check (~2-3 min)
Do a thorough deep dive              # full audit (~5-10 min)
Investigate observability             # targeted deep dive
Why are managed clusters Unknown?     # symptom investigation
/learn                                # refresh knowledge from cluster
```

## How It Works

### 6-Phase Diagnostic Pipeline

1. **Discover** -- inventory what's deployed (MCH, MCE, components, nodes, fleet)
2. **Learn** -- consult architecture knowledge + previous discoveries
3. **Check** -- verify health per component (pods, logs, events, CRD status)
4. **Pattern Match** -- match symptoms against documented known issues with JIRA references
5. **Correlate** -- trace 6 dependency chains to find root cause
6. **Deep Investigate** -- logs, events, storage, networking for critical findings

### Self-Healing Knowledge

When the agent encounters something not in its knowledge base, it investigates
using ACM documentation and source code (via MCP), records findings in
`knowledge/learned/`, and future runs benefit from the discovery.

### Evidence-Based Diagnosis

Every conclusion requires 2+ evidence sources with explicit confidence levels.
The agent traces upstream through dependency chains rather than reporting
leaf symptoms independently.

## Knowledge Base

44 knowledge files covering 11 ACM subsystems -- architecture docs, structured
operational data, and diagnostic methodology.

```
knowledge/
  component-registry.md                 # Master inventory of ACM components
  failure-patterns.md                   # Failure signatures mapped to root causes
  healthy-baseline.yaml                 # Expected pod counts, deployment states
  dependency-chains.yaml                # 6 cascade paths (structured YAML)
  webhook-registry.yaml                 # Validating/mutating webhooks
  certificate-inventory.yaml            # TLS secrets, rotation, impact
  addon-catalog.yaml                    # Addon health checks and dependencies
  refresh.py                            # Update YAML from live cluster
  architecture/                         # How ACM works (per-component)
    kubernetes-fundamentals.md          # K8s primitives ACM uses
    acm-platform.md                     # MCH/MCE, operator hierarchy, addon framework
    search/                             # architecture.md, data-flow.md, known-issues.md
    governance/                         # "
    observability/                      # "
    cluster-lifecycle/                  # "
    console/                            # "
    application-lifecycle/              # "
    virtualization/                     # "
    rbac/                               # "
    addon-framework/                    # architecture.md
    networking/                         # architecture.md, known-issues.md
    infrastructure/                     # architecture.md, known-issues.md
  diagnostics/                          # Health check methodology
    dependency-chains.md                # 6 cascade paths (narrative)
    evidence-tiers.md                   # Evidence weighting rules
    diagnostic-playbooks.md             # Investigation procedures
  learned/                              # Agent-discovered knowledge (grows over time)
```

Refresh structured data from a live cluster:
```bash
python -m knowledge.refresh             # Refresh all YAML files
python -m knowledge.refresh --baseline  # Update healthy-baseline.yaml
python -m knowledge.refresh --webhooks  # Update webhook-registry.yaml
python -m knowledge.refresh --certs     # Update certificate-inventory.yaml
python -m knowledge.refresh --addons    # Update addon-catalog.yaml
python -m knowledge.refresh --promote   # Review learned/ entries for promotion
python -m knowledge.refresh --dry-run   # Preview changes without writing
```

Smart merge: curated content (impact descriptions, dependencies) is preserved.
New items get placeholder descriptions. Items no longer on the cluster are
flagged but kept. Version drift between YAML and cluster is detected.

## All Operations Are Read-Only

The agent never modifies your cluster. It uses only `oc get`, `oc describe`,
`oc logs`, and similar read-only commands. When a fix is needed, the agent
tells you exactly what to do.

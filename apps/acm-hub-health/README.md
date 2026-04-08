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
- **Podman** -- for Neo4j knowledge graph container (optional but recommended)

## Quick Start

```bash
cd acm-hub-health
bash setup.sh         # one-time: clones rhacm-docs, sets up MCPs (acm-ui, neo4j-rhacm)
oc login <hub-api>    # login to your hub
claude                # start the agent
```

Once Claude Code launches, it picks up the agent configuration (CLAUDE.md,
knowledge base, slash commands, permissions) automatically. You're ready
to go.

## Usage

Use slash commands or natural language inside the Claude Code session:

```
/sanity                              # quick pulse (~30s)
/health-check                        # standard check (~2-3 min)
/deep                                # full audit (~5-10 min)
/investigate observability            # targeted deep dive
Why are managed clusters Unknown?     # symptom investigation
/learn                                # refresh knowledge from cluster
```

## How It Works

### 6-Phase Diagnostic Pipeline

1. **Discover** -- inventory what's deployed (MCH, MCE, components, nodes, fleet)
2. **Learn** -- consult architecture knowledge + previous discoveries
3. **Check** -- layer-organized health checks (foundational layers first, then components)
4. **Pattern Match** -- match symptoms against documented known issues with JIRA references
5. **Correlate** -- trace horizontal (8 dependency chains) + vertical (12 infrastructure layers)
6. **Deep Investigate** -- logs, events, storage, networking + layer-based fallback

### Self-Healing Knowledge

When the agent encounters something not in its knowledge base, it
reverse-engineers dependencies from live cluster metadata (owner refs,
OLM labels, CSV metadata, env vars, webhooks), cross-references with
the knowledge graph (neo4j-rhacm MCP), then uses ACM source code
(acm-ui MCP) to understand how those dependencies work. Findings are
recorded in `knowledge/learned/` so future runs benefit.

### Evidence-Based Diagnosis

Every conclusion requires 2+ evidence sources with explicit confidence levels.
The agent traces upstream through dependency chains rather than reporting
leaf symptoms independently.

## Diagnose First, Fix With Approval

Diagnosis is always read-only (`oc get`, `oc describe`, `oc logs`). When
cluster-fixable issues are found, the agent presents all root causes and
exact fix commands in a structured remediation plan, then asks for your
explicit approval before making any changes. You review the full plan and
decide -- the agent never modifies the cluster without your consent.

## Session Tracing

Every diagnostic session is automatically traced to structured JSONL files
via Claude Code hooks. No setup required -- tracing is active from the
first session.

```
.claude/traces/
├── <session-id>.jsonl     # Detailed per-session trace
└── sessions.jsonl         # One-line summary per session (aggregate stats)
```

Each trace entry captures: tool calls (with `oc` verb/resource/namespace
parsing), MCP interactions (server, tool, input/output), knowledge file
reads (with diagnostic phase inference), mutation detection (remediation
commands), prompts (with diagnostic type detection), subagent operations,
and errors. The session index tracks aggregate stats: duration, tool call
count, MCP calls, oc commands, mutations, knowledge reads/writes, errors.

Trace files are gitignored. See the "Session Tracing" section in
[CLAUDE.md](CLAUDE.md) for the full field reference.

## Knowledge Base

54 knowledge files covering 12 ACM subsystems -- architecture docs, structured
operational data, 12-layer diagnostic model, and diagnostic methodology.

See [docs/06-SLASH-COMMANDS.md](docs/06-SLASH-COMMANDS.md) for full command reference.

```
knowledge/
  component-registry.md                 # Master inventory of ACM components
  failure-patterns.md                   # Failure signatures mapped to root causes
  healthy-baseline.yaml                 # Expected pod counts, deployment states
  dependency-chains.yaml                # 8 cascade paths (structured YAML)
  webhook-registry.yaml                 # Validating/mutating webhooks
  certificate-inventory.yaml            # TLS secrets, rotation, impact
  addon-catalog.yaml                    # Addon health checks and dependencies
  version-constraints.yaml              # Known version incompatibilities
  refresh.py                            # Update YAML from live cluster
  architecture/                         # How ACM works (per-component)
    kubernetes-fundamentals.md          # K8s primitives ACM uses
    acm-platform.md                     # MCH/MCE, operator hierarchy, addon framework
    search/                             # architecture.md, data-flow.md, known-issues.md
    governance/                         # "
    observability/                      # "
    cluster-lifecycle/                  # " + health-patterns.md
    console/                            # "
    application-lifecycle/              # "
    virtualization/                     # "
    rbac/                               # "
    automation/                         # " (ClusterCurator, AAP hooks)
    addon-framework/                    # " (addon manager, ManifestWork delivery)
    networking/                         # " (Submariner, tunnels, service discovery)
    infrastructure/                     # " + post-upgrade-patterns.md
  diagnostics/                          # Health check methodology
    diagnostic-layers.md                # 12-layer investigation framework
    dependency-chains.md                # 8 cascade paths (narrative)
    common-diagnostic-traps.md          # 13 patterns where obvious diagnosis is wrong
    evidence-tiers.md                   # Evidence weighting rules
    diagnostic-playbooks.md             # 14 per-subsystem investigation procedures
  learned/                              # Agent-discovered knowledge (grows over time)
```

Refresh structured data from a live cluster with `python -m knowledge.refresh`
(requires Python 3 + PyYAML). See [knowledge/README.md](knowledge/README.md)
for all flags and smart merge behavior.

---

## Optional: CLI Mode (Run From Any Terminal)

You can also run diagnostics directly from any terminal without launching an
interactive Claude Code session first. This is optional -- the default usage
above works without any additional setup.

### What It Does

The `acm-hub` script is a CLI wrapper that invokes Claude Code with the
correct project directory and prompt. It works from any terminal as long as
you're logged into a cluster with `oc`. You don't need to `cd` into the app
directory.

By default it runs in **print mode** -- streams the diagnosis to your terminal
and exits. Add `-i` for an **interactive session** where the agent can present
a remediation plan and execute fixes with your approval.

### Setup

**1. Make sure the prerequisites are met** (same as above -- `oc` + `claude`).

**2. Create a symlink** so `acm-hub` is available on your PATH:

```bash
# Option A: symlink to ~/.local/bin (most common)
mkdir -p ~/.local/bin
ln -s "$(pwd)/acm-hub" ~/.local/bin/acm-hub

# Option B: symlink to /usr/local/bin (system-wide)
sudo ln -s "$(pwd)/acm-hub" /usr/local/bin/acm-hub
```

Make sure the target directory is on your PATH. For `~/.local/bin`, add
this to your `~/.zshrc` or `~/.bashrc` if it's not already there:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

**3. Verify it works:**

```bash
acm-hub --help
```

That's it. The script resolves the app directory from its own location
(works through symlinks), so you can run it from anywhere.

### Commands

```bash
acm-hub sanity                        # quick pulse (~30s)
acm-hub check                         # standard health check (~2-3 min)
acm-hub health-check                  # same as check (matches /health-check slash command)
acm-hub deep                          # full deep audit (~5-10 min)
acm-hub investigate observability     # targeted investigation
acm-hub investigate "why clusters Unknown"
acm-hub learn                         # full knowledge refresh
acm-hub learn search                  # knowledge refresh for search only
```

### Print Mode vs Interactive Mode

```bash
acm-hub check                         # print mode (default)
acm-hub check -i                      # interactive mode
```

| | Print Mode (default) | Interactive Mode (`-i`) |
|---|---|---|
| **Output** | Streams diagnosis to terminal, exits | Full Claude Code session |
| **Remediation** | Presents plan but cannot execute | Can ask approval and execute fixes |
| **Use case** | Quick checks, scripting, CI | Full diagnostic + fix workflow |

### Examples

```bash
# Morning pulse check from any terminal
oc login https://my-hub:6443
acm-hub sanity

# Something looks wrong -- run a full check
acm-hub check

# Dig into a specific area
acm-hub investigate observability

# Found issues, want to fix them -- use interactive mode
acm-hub check -i
```

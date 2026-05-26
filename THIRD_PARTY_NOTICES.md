# Third-Party Notices

This project uses, adapts, or integrates code and data from the following
external sources. All usage complies with the respective licenses.

---

## MCP Servers (Forked / Adapted)

These servers are cloned into `mcp/.external/` (gitignored) by `mcp/setup.sh`.
We maintain forks with pending upstream PRs for our changes.

| Component | Upstream Repository | License | Maintainers | Our Fork | Our Changes |
|-----------|-------------------|---------|-------------|----------|-------------|
| JIRA MCP | [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server) | Apache 2.0 | jnpacker (Jeff Packer), stolostron contributors | [atifshafi/jira-mcp-server@feat/redhat-fields](https://github.com/atifshafi/jira-mcp-server/tree/feat/redhat-fields) | Red Hat custom fields, Jira Cloud migration, attachment/inline image support ([PR #24](https://github.com/stolostron/jira-mcp-server/pull/24)) |
| Jenkins MCP | [redhat-community-ai-tools/jenkins-mcp](https://github.com/redhat-community-ai-tools/jenkins-mcp) | Apache 2.0 | Red Hat Community AI Tools | [atifshafi/jenkins-mcp@fix/auth-logs-paths](https://github.com/atifshafi/jenkins-mcp/tree/fix/auth-logs-paths) | Auth fix, log path resolution, error handling ([PR #13](https://github.com/redhat-community-ai-tools/jenkins-mcp/pull/13)) |
| Knowledge Graph (data) | [stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph) | Apache 2.0 | bjoydeep (Joy Deep Bhattacharjee), stolostron contributors | [atifshafi/knowledge-graph@atif-depth-improvements](https://github.com/atifshafi/knowledge-graph/tree/atif-depth-improvements) | Depth query improvements, additional Cypher patterns ([PR #19](https://github.com/stolostron/knowledge-graph/pull/19)) |

---

## MCP Servers (Upstream, Unmodified)

These are used as-is without modification.

| Component | Source | License | How Used |
|-----------|--------|---------|----------|
| ACM Search / ACM Kubectl | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | MIT | Cloned to `mcp/.external/acm-mcp-server/`; also run via `npx` |
| Playwright MCP | [@playwright/mcp](https://www.npmjs.com/package/@playwright/mcp) (Microsoft) | Apache 2.0 | Run via `npx @playwright/mcp@latest` |
| Neo4j Cypher MCP | [mcp-neo4j-cypher](https://pypi.org/project/mcp-neo4j-cypher/) (Neo4j Labs) | MIT | Run via `uvx` for graph queries |

---

## PyPI / npm Runtime Dependencies

Key external packages consumed at runtime (not vendored):

| Package | License | Used By | Source |
|---------|---------|---------|--------|
| [polarion-mcp](https://pypi.org/project/polarion-mcp/) | MIT | Polarion wrapper (`mcp/polarion/`) | PyPI |
| [fastmcp](https://pypi.org/project/fastmcp/) | MIT | acm-source-mcp-server, JIRA MCP | PyPI |
| [pydantic](https://pypi.org/project/pydantic/) | MIT | test-case-generator, acm-source-mcp-server | PyPI |
| [mcp-remote](https://www.npmjs.com/package/mcp-remote) | MIT | ACM Search SSE bridge | npm |
| [requests](https://pypi.org/project/requests/) | Apache 2.0 | z-stream-analysis (Polarion HTTP) | PyPI |
| [PyYAML](https://pypi.org/project/PyYAML/) | MIT | z-stream-analysis, acm-hub-health (knowledge refresh) | PyPI |
| [python-jira](https://pypi.org/project/jira/) | BSD-2-Clause | JIRA MCP server | PyPI |

---

## Wrapper Inspirations

Code we wrote that was inspired by or adapts patterns from other projects:

| Our Code | Inspired By | Original Author(s) | What We Adapted |
|----------|-------------|--------------------|--------------------|
| `mcp/polarion/polarion-mcp-wrapper.py` (test run tools) | [stolostron/acm-workflows — Claude/plugins/polarion-tools](https://github.com/stolostron/acm-workflows/tree/main/Claude/plugins/polarion-tools) | hchenxa (ACM QE Team) | Test run creation, plan association, result upload patterns |
| `mcp/jenkins-acm-tools.py` | [redhat-community-ai-tools/jenkins-mcp](https://github.com/redhat-community-ai-tools/jenkins-mcp) | Red Hat Community AI Tools | Extended with 4 ACM-specific analysis tools |

---

## Design / Methodology Inspirations

Concepts and patterns referenced in our design (no code copied):

| Concept | Source | Used In | Reference |
|---------|--------|---------|-----------|
| Confidence-aware "Confession" pattern | [mikeyobrien/ralph-orchestrator](https://github.com/mikeyobrien/ralph-orchestrator/issues/74) | acm-bug-hunter skill | `.claude/skills/acm-bug-hunter/references/confidence-mechanism.md` |
| AI confessions research | [OpenAI alignment research](https://alignment.openai.com/confessions/) | acm-bug-hunter skill | Same reference file |
| Portable skill architecture | Anthropic: "The Complete Guide to Building Skills for Claude" (2026) | All 19 skills | `docs/skill-authoring-guide.md` |
| Portable skill architecture | Anthropic: "Why We Stopped Building Agents and Started Building Skills Instead" (Barry Zhang & Mahesh Murag, 2026) | All 19 skills | `docs/skill-authoring-guide.md` |

---

## Documentation Sources (Runtime Clones)

These are cloned at setup time for AI agent reference (not bundled in releases):

| Source | License | How Used |
|--------|---------|----------|
| [stolostron/rhacm-docs](https://github.com/stolostron/rhacm-docs) | Apache 2.0 | Cloned by `apps/acm-hub-health/setup.sh` for ACM documentation reference |

---

## CDN Assets (in HTML documentation)

Architecture diagram HTML files (`docs/architecture-diagrams.html` in each app) load:

| Asset | License | Source |
|-------|---------|--------|
| Mermaid.js | MIT | `cdn.jsdelivr.net/npm/mermaid@11` |
| Inter (font) | SIL Open Font License 1.1 | `fonts.googleapis.com` |
| JetBrains Mono (font) | SIL Open Font License 1.1 | `fonts.googleapis.com` |

---

## What Is Original

The following components are original work by the ACM AI QE team (Red Hat):

- `mcp/acm-source-mcp-server/` — ACM Console and Fleet Virtualization source search (18 tools)
- `mcp/polarion/polarion-mcp-wrapper.py` — SSL patching + 11 enhanced Polarion tools
- `mcp/jenkins-acm-tools.py` — 4 ACM pipeline analysis tools
- `mcp/acm-search-proxy.py` — Resilient proxy for ACM Search MCP
- `apps/` — All three applications (z-stream-analysis, acm-hub-health, test-case-generator)
- `.claude/skills/` — All 19 portable skills
- `.claude/knowledge/` — ACM domain knowledge database

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the full text.

SPDX-License-Identifier: Apache-2.0
Copyright Red Hat, Inc.

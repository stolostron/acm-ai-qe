# MCP Setup Guide

How to configure MCP servers for the ACM skill pack.

## Quick Setup

Run `/onboard` in Claude Code to configure everything interactively.

## MCP Server Reference

| Server | Type | Required By | Credentials |
|--------|------|-------------|-------------|
| acm-ui | Local Python server | acm-ui-source, acm-code-analyzer, acm-test-case-writer, acm-test-case-reviewer | GitHub CLI auth (`gh auth login`) |
| jira | Local Python server | acm-jira-client | JIRA email + API token |
| polarion | uvx + wrapper | acm-polarion-client | Polarion JWT token (VPN required) |
| neo4j-rhacm | uvx + Podman container | acm-neo4j-explorer | None (local container, password: rhacmgraph) |
| acm-search | Remote SSE (on-cluster) | acm-cluster-health (optional) | On-cluster service account token |
| acm-kubectl | npm package | acm-cluster-health (optional) | Uses oc login |
| playwright | npm package | acm-test-case-generator (optional) | None |
| jenkins | Local Python server | Z-stream only | Jenkins username + API token |

## Which MCPs Do I Need?

### For Test Case Generation
- **Required:** acm-ui, jira, polarion
- **Recommended:** neo4j-rhacm (richer architecture analysis)
- **Optional:** acm-search, acm-kubectl, playwright (live cluster validation)

### For Hub Health Diagnostics
- **Required:** None (uses `oc` CLI directly)
- **Recommended:** neo4j-rhacm (dependency analysis)
- **Optional:** acm-search (fleet-wide spoke queries)

### For Z-Stream Analysis
- **Required:** acm-ui, jira, jenkins, polarion
- **Recommended:** neo4j-rhacm
- **Optional:** acm-search, acm-kubectl

## Configuration Location

For portable skills, MCPs must be configured at the repo root level (`.mcp.json` in `ai_systems_v2/`). The `/onboard` skill handles this automatically.

For Claude Code apps (under `apps/`), each app has its own `.mcp.json`.

## Manual Configuration

If not using `/onboard`, create `.mcp.json` at the repo root. See `apps/test-case-generator/.mcp.json` or `apps/acm-hub-health/.mcp.json` for the format.

## Credential Sources

| Credential | Where to Get It |
|------------|----------------|
| JIRA API token | https://id.atlassian.com/manage-profile/security/api-tokens |
| Polarion JWT token | https://polarion.engineering.redhat.com/polarion/ > My Account > Personal Access Tokens (VPN required) |
| Jenkins API token | Jenkins > your username > Configure > API Token |
| GitHub CLI auth | Run `gh auth login` and follow prompts |

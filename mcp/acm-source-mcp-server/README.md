# ACM Source MCP Server

MCP server for ACM Console and Fleet Virtualization source code discovery.

## Overview

Provides 18 tools for searching, reading, and analyzing source code from
[stolostron/console](https://github.com/stolostron/console) and
[kubevirt-ui/kubevirt-plugin](https://github.com/kubevirt-ui/kubevirt-plugin)
via the GitHub API (`gh` CLI).

## Origin

This is **original work** by the ACM AI QE team (Red Hat), created as part of
the [stolostron/acm-ai-qe](https://github.com/stolostron/acm-ai-qe) project.

## License

Apache License 2.0 (inherited from the parent repository).

SPDX-License-Identifier: Apache-2.0
Copyright Red Hat, Inc.

## Dependencies

- `fastmcp` (MIT) -- MCP server framework
- `pydantic` / `pydantic-settings` (MIT) -- Configuration and validation
- `python-dotenv` (BSD-3-Clause) -- Environment variable loading
- `mcp` (MIT) -- Model Context Protocol SDK
- `gh` CLI (required at runtime) -- GitHub API access

## Usage

```bash
pip install -e .
acm-source-mcp-server
```

Or configure in `.mcp.json`:

```json
{
  "acm-source": {
    "command": "/path/to/venv/bin/acm-source-mcp-server",
    "timeout": 30
  }
}
```

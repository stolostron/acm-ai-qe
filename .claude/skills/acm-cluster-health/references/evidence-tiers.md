# Evidence Tier Framework

## Tiers

| Tier | Weight | Description | Examples |
|------|--------|-------------|----------|
| Tier 1 | 1.0 | Direct observation -- definitive evidence from commands or tools | `oc get` output, pod status, MCP search result, database query, log error line |
| Tier 2 | 0.5 | Strong indirect evidence -- correlated but not direct | Knowledge graph dependency, JIRA bug correlation, knowledge DB pattern match, commit history |
| Tier 3 | 0.25 | Contextual/suggestive -- supports but doesn't prove | Similar past incidents, version-known issues, heuristic pattern match |

## Requirements

- **Minimum 2 evidence sources** per conclusion
- **Combined weight >= 1.8** for high confidence (0.85+)
- **Single-source evidence is insufficient** for any conclusion
- If only 1 source available, confidence MUST be < 0.80

## Evidence Quality Rules

- `oc` command output is Tier 1 (you directly observed it)
- MCP query results are Tier 1 (tool returned verified data)
- Knowledge file pattern match is Tier 2 (curated but not live)
- JIRA bug match is Tier 2 (known issue but may not apply to this case)
- "Similar to past incident" is Tier 3 (pattern recognition, not proof)

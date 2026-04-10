# /generate -- Generate a test case from a JIRA ticket

Usage: `/generate <JIRA_ID> [--version <VERSION>] [--pr <PR_NUMBER>] [--area <AREA>] [--skip-live] [--repo <REPO>]`

## Arguments

- `JIRA_ID` (required): The JIRA ticket ID (e.g., ACM-30459)
- `--version`: ACM version override (default: detected from JIRA fix_versions)
- `--pr`: PR number override (default: auto-detected from JIRA or search)
- `--area`: Area override (default: auto-detected from PR file paths)
- `--skip-live`: Skip live cluster validation
- `--repo`: Repository override (default: stolostron/console)

## Pipeline

Execute the 3-stage pipeline with visible status updates:

### Stage 1: Gather

Run the gather script:
```bash
python -m src.scripts.gather $JIRA_ID [options from above]
```

Read the output to find the run directory path. Show a summary of what was gathered.

### Stage 2: Generate

Read `gather-output.json` from the run directory. Then perform the test-case-generator agent workflow:

1. Investigate the feature via MCP servers (JIRA, Polarion, ACM UI, Neo4j)
2. Synthesize a test plan from all sources
3. Optionally validate on a live cluster (unless --skip-live)
4. Generate the test case markdown following conventions
5. Self-review the output

Write `test-case.md` and `analysis-results.json` to the run directory.

### Stage 3: Report

Run the report script:
```bash
python -m src.scripts.report <run-directory>
```

Show the summary including:
- Structural validation result (PASS/FAIL)
- Polarion HTML generation status
- Pipeline timing
- Output file paths

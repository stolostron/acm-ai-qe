# /batch -- Generate test cases for multiple JIRA tickets

Usage: `/batch <JIRA_IDS> [--version <VERSION>] [--skip-live]`

## Arguments

- `JIRA_IDS` (required): Comma-separated JIRA ticket IDs (e.g., ACM-30459,ACM-30460,ACM-30461)
- `--version`: ACM version override (applied to all tickets)
- `--skip-live`: Skip live cluster validation for all tickets

## Process

For each JIRA ID in the comma-separated list:

1. Run `/generate <JIRA_ID> [options]`
2. Show the result (PASS/FAIL)
3. Continue to the next ticket regardless of result

After all tickets are processed, show a summary table:

```
Batch Results
=============
| JIRA ID    | Status | Steps | Complexity | Output |
|------------|--------|-------|------------|--------|
| ACM-30459  | PASS   | 8     | medium     | runs/ACM-30459/... |
| ACM-30460  | PASS   | 5     | simple     | runs/ACM-30460/... |
| ACM-30461  | FAIL   | -     | -          | (validation failed) |
```

# /analyze -- Analyze a Jenkins pipeline run

Usage: `/analyze <JENKINS_URL> [--skip-repo]`

## Arguments

- `JENKINS_URL` (required): Full URL to the Jenkins build (e.g., `https://jenkins.example.com/job/.../123/`)
- `--skip-repo`: Skip repository cloning (use cached repos if available)

## Stage 1: Gather

```
Stage 1: Gathering pipeline data from Jenkins...
```

Run the gather script:
```bash
python -m src.scripts.gather $ARGUMENTS
```

Read the output to find the run directory path. Summarize what was collected:
```
Stage 1 complete. Extracted N failed tests across M feature areas, K managed clusters.
Run directory: runs/<dir>
```

## Stage 1.5: Cluster Diagnostic

If `--skip-env` was NOT passed and cluster access is available:

```
Stage 1.5: Running comprehensive cluster diagnostic...
```

Spawn the `cluster-diagnostic` agent with the run directory path.
- Agent file: `.claude/agents/cluster-diagnostic.md`
- Input: run directory path (contains `core-data.json` and `cluster.kubeconfig`)
- Output: `cluster-diagnosis.json` with structured health data

After it completes, show the verdict and key findings:
```
Cluster diagnostic complete. Verdict: <HEALTHY|DEGRADED|CRITICAL> — <summary of findings>
```

Then spawn the `data-collector` agent with the run directory path.
- Agent file: `.claude/agents/data-collector.md`
- Input: run directory path
- Output: enriched `core-data.json` (page objects, selector verification, timeline analysis)

No stage banner for data-collector -- it runs quietly before Stage 2.

If cluster access is unavailable (gather.py reported cluster login failure), skip Stage 1.5:
```
Stage 1.5: Skipping cluster diagnostic (cluster access unavailable).
```

**STOP checkpoint:**
```
Data collection complete. <N> failed tests ready for analysis.
```

## Stage 2: AI Analysis

```
Stage 2: Analyzing <N> failed tests (12-layer diagnostic investigation)...
```

Spawn the `analysis` agent with the run directory path.
- Agent file: `.claude/agents/analysis.md`
- Input: run directory path (contains `core-data.json`, `cluster-diagnosis.json` if available)
- Output: `analysis-results.json` with per-test classifications

After it completes, show the classification breakdown:
```
Stage 2 complete. Classifications: X AUTOMATION_BUG, Y INFRASTRUCTURE, Z NO_BUG, W PRODUCT_BUG.
```

## Stage 3: Report

```
Stage 3: Generating report...
```

Run the report script:
```bash
python -m src.scripts.report runs/<run-dir>
```

Show the output files:
```
Pipeline complete.
  Report:     runs/<dir>/Detailed-Analysis.md
  HTML:       runs/<dir>/analysis-report.html
  Breakdown:  runs/<dir>/per-test-breakdown.json
  Summary:    runs/<dir>/SUMMARY.txt
```

If additional context is provided: $ARGUMENTS

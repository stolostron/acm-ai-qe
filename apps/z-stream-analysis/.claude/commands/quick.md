# /quick -- Fast triage without cluster diagnostic

Usage: `/quick <JENKINS_URL> [--skip-repo]`

Runs the pipeline without Stage 1.5 (cluster diagnostic and data enrichment).
Use this for fast triaging when cluster access is unavailable or when you
want a quick classification pass without waiting for the full diagnostic.

## Stage 1: Gather (with --skip-env)

```
Stage 1: Gathering pipeline data from Jenkins (quick mode, skipping cluster validation)...
```

Run the gather script with --skip-env:
```bash
python -m src.scripts.gather $ARGUMENTS --skip-env
```

Read the output to find the run directory. Summarize what was collected.

## Stage 1.5: Skipped

```
Stage 1.5: Skipped (quick mode).
```

Do NOT spawn the cluster-diagnostic or data-collector agents.
The analysis agent will work with the extracted context from gather.py
without cluster-level diagnostic data or enriched selector verification.

## Stage 2: AI Analysis

```
Stage 2: Analyzing <N> failed tests (12-layer diagnostic investigation)...
```

Spawn the `analysis` agent with the run directory path.
- Agent file: `.claude/agents/analysis.md`
- Output: `analysis-results.json`

Show the classification breakdown after completion.

## Stage 3: Report

```
Stage 3: Generating report...
```

```bash
python -m src.scripts.report runs/<run-dir>
```

Show the output files.

```
Pipeline complete (quick mode — no cluster diagnostic).
  Report:     runs/<dir>/Detailed-Analysis.md
  HTML:       runs/<dir>/analysis-report.html
  Summary:    runs/<dir>/SUMMARY.txt
```

If additional context is provided: $ARGUMENTS

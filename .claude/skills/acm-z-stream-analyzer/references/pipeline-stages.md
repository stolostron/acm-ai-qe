# Pipeline Stages Reference

## Stage Flow

```
Stage 1: gather.py           -> core-data.json + cluster.kubeconfig + repos/
  Steps 1-3: Jenkins build info, console log, test report
  Steps 4a-b: Cluster login + kubeconfig persist, landscape collection
  Step 5: Feature context oracle (Polarion, KG, dependency verification)
  Steps 6-9: Repo cloning, context extraction, feature grounding, knowledge

Stage 1.5: Cluster diagnostic  -> cluster-diagnosis.json
  6-phase investigation using acm-cluster-health methodology
  Produces structured health data with classification guidance

Data enrichment: acm-data-enricher -> enriches core-data.json
  Task 1: Resolve page objects
  Task 2: Verify selector existence (MCP)
  Task 3: Selector timeline analysis (git)
  Task 4: Feature knowledge gap filling (conditional)

Stage 2: AI Analysis           -> analysis-results.json
  Phase A: Ground and group
  Phase B: 12-layer investigation (via acm-cluster-investigator)
  Phase C: Multi-evidence correlation
  Phase D: Validation and routing
  Phase E: JIRA correlation

Stage 3: report.py            -> Detailed-Analysis.md + HTML + per-test JSON
```

## gather.py Options

```bash
python -m src.scripts.gather "<JENKINS_URL>"                  # Full pipeline
python -m src.scripts.gather "<JENKINS_URL>" --skip-env       # Skip cluster login
python -m src.scripts.gather "<JENKINS_URL>" --skip-repo      # Skip repo cloning
```

## report.py Options

```bash
python -m src.scripts.report <run-directory>                  # Generate reports
python -m src.scripts.report <run-directory> --keep-repos     # Don't cleanup repos/
```

## feedback.py (post-analysis)

```bash
python -m src.scripts.feedback <run-directory> --test "name" --correct
python -m src.scripts.feedback <run-directory> --test "name" --incorrect --should-be PRODUCT_BUG
python -m src.scripts.feedback --stats
```

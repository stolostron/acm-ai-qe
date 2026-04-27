# /gather -- Gather pipeline data from Jenkins (Stage 1 only)

Usage: `/gather <JENKINS_URL> [--skip-env] [--skip-repo]`

## Arguments

- `JENKINS_URL` (required): Full URL to the Jenkins build
- `--skip-env`: Skip cluster environment validation
- `--skip-repo`: Skip repository cloning

## Process

```
Stage 1: Gathering pipeline data from Jenkins...
```

Run the gather script:
```bash
python -m src.scripts.gather $ARGUMENTS
```

After it completes, read `core-data.json` from the run directory and summarize:
- Number of failed tests
- Feature areas detected
- Managed clusters found
- Whether cluster login succeeded
- Whether repos were cloned

```
Stage 1 complete.
  Run directory: runs/<dir>
  Failed tests:  N
  Feature areas: [list]
  Cluster:       <connected | unavailable>
  Repos:         <cloned | skipped>
```

This command runs Stage 1 only. To continue with the full pipeline, use `/analyze`.
To continue an existing run, pass the run directory to the analysis agent directly.

If additional context is provided: $ARGUMENTS

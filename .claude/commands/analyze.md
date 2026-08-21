# /analyze -- Analyze a Jenkins pipeline run

Usage: `/analyze <JENKINS_URL> [--skip-repo]`

## Arguments

- `JENKINS_URL` (required): Full URL to the Jenkins build (e.g., `https://jenkins.example.com/job/.../123/`)
- `--skip-repo`: Skip repository cloning (use cached repos if available)

## Execution

This command invokes the full z-stream analysis pipeline. Follow the `acm-z-stream-analyzer` skill at `.claude/skills/acm-z-stream-analyzer/SKILL.md` with the provided Jenkins URL.

The skill orchestrates all 5 stages:
1. **Stage 1 (Gather):** `cd lib/z-stream-analysis && python -m src.scripts.gather $ARGUMENTS`
2. **Stage 1.5 (Cluster Diagnostic):** Spawns `acm-hub-health-check` skill
3. **Stage 2 (AI Analysis):** Spawns `acm-failure-classifier` skill
4. **Stage 3 (Report):** `cd lib/z-stream-analysis && python -m src.scripts.report runs/<run-dir>`

If additional context is provided: $ARGUMENTS

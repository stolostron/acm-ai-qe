# /quick -- Fast triage without cluster diagnostic

Usage: `/quick <JENKINS_URL> [--skip-repo]`

Runs the pipeline without Stage 1.5 (cluster diagnostic and data enrichment).
Use this for fast triaging when cluster access is unavailable or when you
want a quick classification pass without waiting for the full diagnostic.

## Execution

This command invokes the z-stream analysis pipeline in quick mode. Follow the `acm-z-stream-analyzer` skill at `.claude/skills/acm-z-stream-analyzer/SKILL.md` with `--skip-env` flag.

The skill orchestrates stages 1, 2, and 3 (skipping Stage 1.5):
1. **Stage 1 (Gather):** `cd lib/z-stream-analysis && python -m src.scripts.gather $ARGUMENTS --skip-env`
2. **Stage 1.5:** Skipped (quick mode)
3. **Stage 2 (AI Analysis):** Spawns `acm-failure-classifier` skill
4. **Stage 3 (Report):** `cd lib/z-stream-analysis && python -m src.scripts.report runs/<run-dir>`

```
Pipeline complete (quick mode — no cluster diagnostic).
```

If additional context is provided: $ARGUMENTS

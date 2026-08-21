# Z-Stream Analysis Library

Deterministic Python code for the `acm-z-stream-analyzer` skill's data gathering and report generation stages.

## Usage

This library is invoked by the skill (`.claude/skills/acm-z-stream-analyzer/SKILL.md`), not run directly:

```bash
cd lib/z-stream-analysis && python -m src.scripts.gather "<JENKINS_URL>"
cd lib/z-stream-analysis && python -m src.scripts.report <run-directory>
```

## Setup

```bash
pip install -r requirements.txt
```

## Tests

```bash
pip install -r dev-requirements.txt
python -m pytest tests/unit/ tests/regression/ -q
```

## Structure

- `src/scripts/` -- Entry points (gather.py, report.py, feedback.py)
- `src/services/` -- 22 service modules (Jenkins client, stack parser, knowledge graph, etc.)
- `src/schemas/` -- JSON validation schemas
- `src/data/` -- Feature playbooks (YAML)
- `src/reports/` -- HTML report generator
- `tests/` -- Unit, regression, and integration tests

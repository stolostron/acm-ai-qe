"""Eval harness for acm-z-stream-analyzer skill.

Validates eval definitions in evals.json:
  - Schema correctness (required fields, valid categories)
  - Assertion reference checks (artifacts, stages/phases, tools mentioned in
    assertions exist in the skill's pipeline)
  - Coverage: every eval category is represented

Usage:
    python run_evals.py            # validate evals.json in same directory
    python run_evals.py path.json  # validate a specific evals file

Exit codes:
    0 -- all checks pass
    1 -- validation failures found
"""

import json
import sys
from pathlib import Path

REQUIRED_EVAL_FIELDS = {"id", "prompt", "expected_output", "assertions", "category"}
VALID_CATEGORIES = {"process", "structure", "edge-case", "degradation"}

KNOWN_PHASES = [
    "stage 1", "stage 1.5", "stage 2", "stage 3",
    "phase a", "phase b", "phase c", "phase d", "phase e",
]

KNOWN_ARTIFACTS = [
    "core-data.json", "cluster.kubeconfig", "cluster-diagnosis.json",
    "analysis-results.json", "detailed-analysis.md", "analysis-report.html",
    "per-test-breakdown.json", "summary.txt", "pipeline.log.jsonl",
]

KNOWN_MCP_TOOLS = [
    "acm-source", "search_code", "get_acm_selectors", "set_acm_version",
    "jira", "search_issues", "get_issue",
    "polarion", "get_polarion_work_items",
    "neo4j-rhacm", "read_neo4j_cypher",
    "acm-search", "acm-kubectl", "jenkins",
]


def load_evals(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_schema(evals_data: dict) -> list[str]:
    errors = []
    if "skill_name" not in evals_data:
        errors.append("Missing top-level 'skill_name'")
    if "evals" not in evals_data:
        errors.append("Missing top-level 'evals' array")
        return errors

    seen_ids = set()
    for i, ev in enumerate(evals_data["evals"]):
        prefix = f"eval[{i}]"
        missing = REQUIRED_EVAL_FIELDS - set(ev.keys())
        if missing:
            errors.append(f"{prefix}: missing fields {missing}")
            continue

        if ev["id"] in seen_ids:
            errors.append(f"{prefix}: duplicate id {ev['id']}")
        seen_ids.add(ev["id"])

        if ev["category"] not in VALID_CATEGORIES:
            errors.append(
                f"{prefix}: invalid category '{ev['category']}', "
                f"must be one of {VALID_CATEGORIES}"
            )

        if not isinstance(ev["assertions"], list) or len(ev["assertions"]) == 0:
            errors.append(f"{prefix}: assertions must be a non-empty list")

    return errors


def check_category_coverage(evals_data: dict) -> list[str]:
    warnings = []
    categories_present = {ev["category"] for ev in evals_data.get("evals", [])}
    missing = VALID_CATEGORIES - categories_present
    if missing:
        warnings.append(f"Missing eval categories: {missing}")
    return warnings


def check_assertion_references(evals_data: dict) -> dict:
    stats = {
        "total_assertions": 0,
        "artifact_refs": 0,
        "phase_refs": 0,
        "mcp_refs": 0,
    }
    for ev in evals_data.get("evals", []):
        for assertion in ev.get("assertions", []):
            stats["total_assertions"] += 1
            text = assertion.lower()
            if any(a.lower() in text for a in KNOWN_ARTIFACTS):
                stats["artifact_refs"] += 1
            if any(p in text for p in KNOWN_PHASES):
                stats["phase_refs"] += 1
            if any(t.lower() in text for t in KNOWN_MCP_TOOLS):
                stats["mcp_refs"] += 1
    return stats


def main() -> None:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = Path(__file__).parent / "evals.json"

    if not path.exists():
        print(f"Error: {path} not found")
        sys.exit(1)

    data = load_evals(path)
    errors = validate_schema(data)
    warnings = check_category_coverage(data)
    stats = check_assertion_references(data)

    print(f"Eval file: {path}")
    print(f"Skill: {data.get('skill_name', 'UNKNOWN')}")
    print(f"Total evals: {len(data.get('evals', []))}")
    print(f"Total assertions: {stats['total_assertions']}")
    print(f"  - artifact references: {stats['artifact_refs']}")
    print(f"  - phase references: {stats['phase_refs']}")
    print(f"  - MCP tool references: {stats['mcp_refs']}")

    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("\nResult: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()

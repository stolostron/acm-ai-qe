"""Deterministic schema validation for pipeline artifacts.

Validates JSON and markdown artifacts against their documented schemas
at each pipeline handoff point. Catches missing keys, wrong types,
empty required collections, and missing markdown sections.

Usage:
    python validate_artifact.py <artifact-path> <schema-name>
    python validate_artifact.py --pre-synthesis <run-dir>

Schema names:
    gather-output, phase1-jira, phase2-code, phase3-ui,
    synthesized-context, analysis-results

Pre-synthesis mode:
    Checks minimum viable data across phase1-jira.json, phase2-code.json,
    and phase3-ui.json before synthesis can proceed.

Exit codes:
    0 -- PASS (artifact conforms to schema)
    1 -- FAIL (schema violations found)
"""

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Schema definitions
#
# Each JSON schema maps required key names to a spec dict:
#   type        -- expected Python type name: str, int, float, bool, list, dict
#   non_empty   -- (list/dict only) must have len > 0
#   nested      -- (dict only) required sub-keys, same spec format
#   pattern     -- (str only) regex the value must match
#   min_value   -- (int/float only) inclusive minimum
#
# Markdown schemas use "sections" -- a list of required heading/text
# fragments checked case-insensitively.
# ---------------------------------------------------------------------------

SCHEMAS = {
    "phase1-jira": {
        "format": "json",
        "required": {
            "story": {
                "type": "dict",
                "non_empty": True,
                "nested": {
                    "key": {"type": "str"},
                    "summary": {"type": "str"},
                },
            },
            "acceptance_criteria": {
                "type": "list",
                "non_empty": True,
            },
            "linked_tickets": {
                "type": "dict",
            },
            "pr_references": {
                "type": "list",
            },
            "test_scenarios": {
                "type": "list",
                "non_empty": True,
            },
            "anomalies": {
                "type": "list",
            },
        },
    },
    "phase2-code": {
        "format": "json",
        "required": {
            "pr": {
                "type": "dict",
                "non_empty": True,
                "nested": {
                    "number": {"type": "int"},
                    "repo": {"type": "str"},
                    "title": {"type": "str"},
                },
            },
            "primary_files": {
                "type": "list",
                "non_empty": True,
            },
            "translations": {
                "type": "dict",
            },
            "test_scenarios": {
                "type": "list",
                "non_empty": True,
            },
            "anomalies": {
                "type": "list",
            },
        },
    },
    "phase3-ui": {
        "format": "json",
        "required": {
            "acm_version": {
                "type": "str",
            },
            "routes": {
                "type": "dict",
                "non_empty": True,
            },
            "entry_point": {
                "type": "str",
            },
            "translations_verified": {
                "type": "dict",
            },
            "anomalies": {
                "type": "list",
            },
        },
    },
    "analysis-results": {
        "format": "json",
        "required": {
            "jira_id": {
                "type": "str",
                "pattern": r"^ACM-",
            },
            "acm_version": {
                "type": "str",
            },
            "area": {
                "type": "str",
            },
            "steps_count": {
                "type": "int",
                "min_value": 1,
            },
            "test_case_file": {
                "type": "str",
            },
        },
    },
    "gather-output": {
        "format": "json",
        "required": {
            "jira_id": {
                "type": "str",
            },
            "run_dir": {
                "type": "str",
            },
            "timestamp": {
                "type": "str",
            },
            "options": {
                "type": "dict",
            },
        },
    },
    "synthesized-context": {
        "format": "markdown",
        "sections": [
            "JIRA INVESTIGATION",
            "CODE CHANGE ANALYSIS",
            "UI DISCOVERY",
            "TEST PLAN",
        ],
    },
}

TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}


def validate_json(data: dict, schema: dict) -> list[str]:
    """Validate a parsed JSON dict against a schema. Returns error strings."""
    errors = []
    required = schema.get("required", {})

    for key, spec in required.items():
        if key not in data:
            errors.append(f"[MISSING] {key}: required key not found")
            continue

        value = data[key]
        expected_type_name = spec.get("type", "str")
        expected_type = TYPE_MAP.get(expected_type_name)

        if value is None:
            errors.append(
                f"[TYPE] {key}: expected {expected_type_name}, got null"
            )
            continue

        if expected_type and not isinstance(value, expected_type):
            errors.append(
                f"[TYPE] {key}: expected {expected_type_name}, "
                f"got {type(value).__name__}"
            )
            continue

        if spec.get("non_empty") and hasattr(value, "__len__") and len(value) == 0:
            errors.append(
                f"[EMPTY] {key}: required non-empty "
                f"{expected_type_name} is empty"
            )

        if "pattern" in spec and isinstance(value, str):
            if not re.match(spec["pattern"], value):
                errors.append(
                    f'[PATTERN] {key}: expected pattern '
                    f'"{spec["pattern"]}", got "{value}"'
                )

        if "min_value" in spec and isinstance(value, (int, float)):
            if value < spec["min_value"]:
                errors.append(
                    f"[VALUE] {key}: expected >= {spec['min_value']}, "
                    f"got {value}"
                )

        if "nested" in spec and isinstance(value, dict):
            for sub_key, sub_spec in spec["nested"].items():
                if sub_key not in value:
                    errors.append(
                        f"[NESTED] {key}: missing required "
                        f'nested key "{sub_key}"'
                    )
                    continue

                sub_value = value[sub_key]
                sub_type_name = sub_spec.get("type", "str")
                sub_type = TYPE_MAP.get(sub_type_name)

                if sub_value is None:
                    errors.append(
                        f"[TYPE] {key}.{sub_key}: expected "
                        f"{sub_type_name}, got null"
                    )
                elif sub_type and not isinstance(sub_value, sub_type):
                    errors.append(
                        f"[TYPE] {key}.{sub_key}: expected "
                        f"{sub_type_name}, got {type(sub_value).__name__}"
                    )

    return errors


def validate_markdown(content: str, schema: dict) -> list[str]:
    """Validate markdown content for required sections."""
    errors = []
    for section in schema.get("sections", []):
        if not re.search(re.escape(section), content, re.IGNORECASE):
            errors.append(
                f'[SECTION] Missing required section: "{section}"'
            )
    return errors


def validate_artifact(artifact_path: Path, schema_name: str) -> tuple[bool, list[str]]:
    """Validate an artifact against its schema.

    Returns (passed, errors).
    """
    if schema_name not in SCHEMAS:
        return False, [f"Unknown schema: {schema_name}"]

    schema = SCHEMAS[schema_name]

    if not artifact_path.exists():
        return False, [f"Artifact not found: {artifact_path}"]

    try:
        content = artifact_path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, [f"Cannot read artifact: {exc}"]

    if not content.strip():
        return False, ["[PARSE] Artifact file is empty"]

    fmt = schema.get("format", "json")

    if fmt == "json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            return False, [f"[PARSE] Invalid JSON: {exc}"]

        if not isinstance(data, dict):
            return False, [
                f"[TYPE] Root must be a JSON object, "
                f"got {type(data).__name__}"
            ]

        errors = validate_json(data, schema)

    elif fmt == "markdown":
        errors = validate_markdown(content, schema)

    else:
        return False, [f"Unknown format: {fmt}"]

    return len(errors) == 0, errors


PRE_SYNTHESIS_CHECKS = {
    "phase1-jira.json": [
        {
            "path": ["story", "key"],
            "label": "story.key",
            "description": "JIRA story key (test case identity)",
        },
        {
            "path": ["story", "summary"],
            "label": "story.summary",
            "description": "JIRA story summary (test case title)",
        },
        {
            "path": ["acceptance_criteria"],
            "label": "acceptance_criteria",
            "description": "acceptance criteria (scope gate + test plan anchors)",
            "non_empty": True,
        },
    ],
    "phase2-code.json": [
        {
            "path": ["pr", "number"],
            "label": "pr.number",
            "description": "PR number (code context identity)",
        },
        {
            "path": ["pr", "repo"],
            "label": "pr.repo",
            "description": "PR repository (code context identity)",
        },
        {
            "path": ["primary_files"],
            "label": "primary_files",
            "description": "changed files (AC cross-reference requires knowing what changed)",
            "non_empty": True,
        },
    ],
    "phase3-ui.json": [
        {
            "path": ["entry_point"],
            "label": "entry_point",
            "description": "UI entry point (test case navigation start)",
        },
        {
            "path": ["routes"],
            "label": "routes",
            "description": "discovered routes (entry point verification)",
            "non_empty": True,
        },
    ],
}


def check_pre_synthesis(run_dir: Path) -> tuple[bool, list[str]]:
    """Check minimum viable data across investigation artifacts.

    Returns (passed, errors).
    """
    errors = []

    for filename, checks in PRE_SYNTHESIS_CHECKS.items():
        filepath = run_dir / filename
        if not filepath.exists():
            errors.append(
                f"[FILE] {filename}: artifact not found in {run_dir}"
            )
            continue

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            errors.append(
                f"[FILE] {filename}: cannot read or parse"
            )
            continue

        for check in checks:
            value = data
            for segment in check["path"]:
                if isinstance(value, dict) and segment in value:
                    value = value[segment]
                else:
                    value = None
                    break

            label = check["label"]
            desc = check["description"]

            if value is None:
                errors.append(
                    f"[MINIMUM] {filename} -> {label}: missing — {desc}"
                )
            elif check.get("non_empty") and hasattr(value, "__len__") and len(value) == 0:
                errors.append(
                    f"[MINIMUM] {filename} -> {label}: empty — {desc}"
                )

    return len(errors) == 0, errors


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--pre-synthesis":
        run_dir = Path(sys.argv[2])
        passed, errors = check_pre_synthesis(run_dir)

        if passed:
            print("VALIDATION: PASS")
            print("Check: pre-synthesis readiness")
            sys.exit(0)
        else:
            print("VALIDATION: FAIL")
            print("Check: pre-synthesis readiness")
            print("Errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)

    if len(sys.argv) < 3:
        print("Usage: python validate_artifact.py <artifact-path> <schema-name>")
        print(f"       python validate_artifact.py --pre-synthesis <run-dir>")
        print(f"Schemas: {', '.join(sorted(SCHEMAS.keys()))}")
        sys.exit(1)

    artifact_path = Path(sys.argv[1])
    schema_name = sys.argv[2]

    passed, errors = validate_artifact(artifact_path, schema_name)

    if passed:
        print("VALIDATION: PASS")
        print(f"Schema: {schema_name}")
        sys.exit(0)
    else:
        print("VALIDATION: FAIL")
        print(f"Schema: {schema_name}")
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

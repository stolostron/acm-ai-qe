#!/usr/bin/env python3
"""Stage 3: Generate reports, validate, and produce Polarion HTML (standalone).

Zero external dependencies -- uses only Python stdlib.
Validates test case markdown, generates Polarion HTML, writes summary.

Usage:
    python report.py <run-directory>
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Telemetry (inlined from src/services/telemetry.py)
# ---------------------------------------------------------------------------

class PipelineTelemetry:
    def __init__(self, run_dir: str, jira_id: str):
        self.run_dir = Path(run_dir)
        self.jira_id = jira_id
        self.log_path = self.run_dir / "pipeline.log.jsonl"
        self._stage_start = None
        self._pipeline_start = time.monotonic()
        self._log_event("pipeline_start", {"jira_id": jira_id})

    def _log_event(self, event_type: str, data: dict = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "jira_id": self.jira_id,
        }
        if data:
            entry.update(data)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def start_stage(self, stage_name: str):
        self._stage_start = time.monotonic()
        self._log_event("stage_start", {"stage": stage_name})

    def end_stage(self, stage_name: str, metadata: dict = None):
        elapsed = 0.0
        if self._stage_start is not None:
            elapsed = time.monotonic() - self._stage_start
        data = {"stage": stage_name, "elapsed_seconds": round(elapsed, 2)}
        if metadata:
            data.update(metadata)
        self._log_event("stage_end", data)
        self._stage_start = None

    def end_pipeline(self, verdict: str = "complete"):
        total_elapsed = time.monotonic() - self._pipeline_start
        self._log_event("pipeline_end", {
            "total_elapsed_seconds": round(total_elapsed, 2),
            "verdict": verdict,
        })

    def log_error(self, stage: str, error: str):
        self._log_event("error", {"stage": stage, "error": error})


# ---------------------------------------------------------------------------
# Convention validator (inlined from src/services/convention_validator.py)
# ---------------------------------------------------------------------------

REQUIRED_POLARION_FIELDS = [
    "Type", "Level", "Component", "Subcomponent", "Test Type",
    "Pos/Neg", "Importance", "Automation", "Tags", "Release",
]

AREA_TAG_PATTERNS = {
    "governance": r"\[GRC-\d+\.\d+\]",
    "rbac": r"\[FG-RBAC-\d+\.\d+\]",
    "fleet-virt": r"\[FG-RBAC-\d+\.\d+\].*Fleet Virtualization",
    "clusters": r"\[Clusters-\d+\.\d+\]",
    "search": r"\[FG-RBAC-\d+\.\d+\].*Search",
    "applications": r"\[Apps-\d+\.\d+\]",
    "credentials": r"\[Credentials-\d+\.\d+\]",
    "cclm": r"\[FG-RBAC-\d+\.\d+\].*CCLM",
    "mtv": r"\[MTV-\d+\.\d+\]",
}

AREA_TAG_EXAMPLES = {
    "governance": "[GRC-2.17]",
    "rbac": "[FG-RBAC-2.17]",
    "fleet-virt": "[FG-RBAC-2.17] Fleet Virtualization UI",
    "clusters": "[Clusters-2.17]",
    "search": "[FG-RBAC-2.17] Search",
    "applications": "[Apps-2.17]",
    "credentials": "[Credentials-2.17]",
    "cclm": "[FG-RBAC-2.17] CCLM",
    "mtv": "[MTV-2.17]",
}


EXPECTED_ARTIFACTS = [
    "gather-output.json",
    "pr-diff.txt",
    "phase1-feature-investigation.md",
    "phase1-code-change-analysis.md",
    "phase1-ui-discovery.md",
    "phase2-synthesized-context.md",
    "phase3-live-validation.md",
    "test-case.md",
    "phase4.5-quality-review.md",
]


def check_artifact_completeness(run_dir):
    """Check which pipeline artifacts were saved."""
    present = []
    missing = []
    for artifact in EXPECTED_ARTIFACTS:
        if (run_dir / artifact).exists():
            present.append(artifact)
        else:
            missing.append(artifact)
    return {
        "artifacts_present": len(present),
        "artifacts_expected": len(EXPECTED_ARTIFACTS),
        "artifacts_missing": missing,
        "pipeline_complete": len(missing) == 0,
    }


def _extract_step_sections(content: str) -> list:
    step_pattern = re.compile(r"^### Step \d+:", re.MULTILINE)
    step_starts = [m.start() for m in step_pattern.finditer(content)]
    if not step_starts:
        return []
    sections = []
    for i, start in enumerate(step_starts):
        end = step_starts[i + 1] if i + 1 < len(step_starts) else len(content)
        for boundary in ["## Teardown", "## Notes", "## Known Issues"]:
            match = re.search(rf"^{re.escape(boundary)}", content[start:end], re.MULTILINE)
            if match:
                end = start + match.start()
        sections.append(content[start:end])
    return sections


def validate_test_case(file_path: str, area: str = None) -> dict:
    path = Path(file_path)
    if not path.exists():
        return {
            "test_case_file": file_path,
            "verdict": "FAIL",
            "issues": [{"severity": "blocking", "category": "file", "message": f"File not found: {file_path}", "line": None}],
            "metadata_complete": False, "section_order_valid": False,
            "title_pattern_valid": False, "entry_point_present": False,
            "jira_coverage_present": False, "step_format_valid": False,
            "teardown_present": False, "total_steps": 0,
        }

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    issues = []

    # --- Title validation ---
    title_valid = False
    if lines and lines[0].startswith("# RHACM4K-"):
        title_valid = True
        title_line = lines[0]
        if not re.search(r"# RHACM4K-\w+ - \[", title_line):
            issues.append({"severity": "blocking", "category": "title",
                           "message": "Title does not match pattern: # RHACM4K-XXXXX - [Tag-Version] Area - Test Name", "line": 1})
            title_valid = False
        if area and title_valid and area in AREA_TAG_PATTERNS:
            tag_pattern = AREA_TAG_PATTERNS[area]
            if not re.search(tag_pattern, title_line):
                issues.append({"severity": "warning", "category": "title",
                               "message": f"Title tag does not match expected pattern for area '{area}' (e.g., {AREA_TAG_EXAMPLES.get(area, tag_pattern)})", "line": 1})
    else:
        issues.append({"severity": "blocking", "category": "title",
                       "message": "First line must start with '# RHACM4K-'", "line": 1})

    # --- Metadata validation ---
    metadata_complete = True
    for field in ["Polarion ID:", "Status:", "Created:", "Updated:"]:
        if f"**{field}**" not in content and f"**{field}" not in content:
            issues.append({"severity": "blocking", "category": "metadata",
                           "message": f"Missing metadata field: {field}", "line": None})
            metadata_complete = False

    for field in REQUIRED_POLARION_FIELDS:
        pattern = f"## {field}:"
        if pattern not in content:
            issues.append({"severity": "blocking", "category": "metadata",
                           "message": f"Missing Polarion field: ## {field}:", "line": None})
            metadata_complete = False

    type_line = next((l for l in lines if l.startswith("## Type:")), None)
    if type_line:
        type_value = type_line.split(":", 1)[1].strip().lower().replace(" ", "")
        if type_value not in ("testcase",):
            issues.append({"severity": "warning", "category": "metadata",
                           "message": f"Type field should be 'Test Case', found: '{type_line.split(':', 1)[1].strip()}'", "line": None})

    # --- Test Steps section header ---
    if "## Test Steps" not in content:
        step_pattern_found = re.search(r"^### Step \d+:", content, re.MULTILINE)
        if step_pattern_found:
            issues.append({"severity": "warning", "category": "structure",
                           "message": "Missing '## Test Steps' section header before step definitions", "line": None})

    # --- Section order validation ---
    section_order_valid = True
    expected_sections = ["Description", "Setup", "Test Steps", "Teardown"]
    section_positions = {}
    for section in expected_sections:
        pattern = f"## {section}"
        pos = content.find(pattern)
        if pos >= 0:
            section_positions[section] = pos

    prev_pos = -1
    for section in expected_sections:
        if section in section_positions:
            if section_positions[section] < prev_pos:
                issues.append({"severity": "warning", "category": "structure",
                               "message": f"Section '{section}' appears out of order", "line": None})
                section_order_valid = False
            prev_pos = section_positions[section]

    if "Description" not in section_positions and "## Description" not in content:
        issues.append({"severity": "blocking", "category": "description",
                       "message": "Missing ## Description section", "line": None})
        section_order_valid = False

    # --- Entry Point ---
    entry_point_present = "Entry Point" in content or "entry point" in content.lower()
    if not entry_point_present:
        issues.append({"severity": "warning", "category": "description",
                       "message": "No Entry Point found in description", "line": None})

    # --- JIRA Coverage ---
    jira_coverage_present = "Dev JIRA Coverage" in content or "JIRA Coverage" in content
    if not jira_coverage_present:
        issues.append({"severity": "warning", "category": "description",
                       "message": "No Dev JIRA Coverage found in description", "line": None})

    # --- Test Steps ---
    step_pattern = re.compile(r"^### Step \d+:", re.MULTILINE)
    steps = step_pattern.findall(content)
    total_steps = len(steps)

    step_format_valid = True
    if total_steps == 0:
        issues.append({"severity": "blocking", "category": "steps",
                       "message": "No test steps found (expected ### Step N: format)", "line": None})
        step_format_valid = False

    step_sections = _extract_step_sections(content)
    for i, step_content in enumerate(step_sections, 1):
        if "Expected Result" not in step_content and "expected result" not in step_content.lower():
            issues.append({"severity": "blocking", "category": "steps",
                           "message": f"Step {i} missing 'Expected Result' section", "line": None})
            step_format_valid = False

        if not re.search(r"^\d+\.", step_content, re.MULTILINE):
            issues.append({"severity": "warning", "category": "steps",
                           "message": f"Step {i} has no numbered actions (expected 1., 2., etc.)", "line": None})

        cli_pattern_re = re.compile(r"^\s*(?:oc|kubectl)\s+(?!#)", re.MULTILINE)
        if cli_pattern_re.search(step_content):
            expected_pos = step_content.lower().find("expected result")
            cli_match = cli_pattern_re.search(step_content)
            if cli_match and (expected_pos == -1 or cli_match.start() < expected_pos):
                bash_block = step_content.find("```bash")
                if bash_block == -1 or cli_match.start() < bash_block:
                    issues.append({"severity": "warning", "category": "steps",
                                   "message": f"Step {i}: CLI command detected in test step actions -- verify this is backend validation, not a UI substitute", "line": None})

    if len(step_sections) > 1:
        for i in range(len(step_sections) - 1):
            section_end = step_sections[i].rstrip()
            if not section_end.endswith("---"):
                issues.append({"severity": "warning", "category": "steps",
                               "message": f"Missing '---' separator after Step {i + 1}", "line": None})

    # --- Teardown ---
    teardown_present = "## Teardown" in content
    if not teardown_present:
        issues.append({"severity": "warning", "category": "teardown",
                       "message": "Missing ## Teardown section", "line": None})
    else:
        teardown_start = content.find("## Teardown")
        teardown_section = content[teardown_start:]
        delete_pattern = re.compile(r"oc delete|kubectl delete", re.MULTILINE)
        if delete_pattern.search(teardown_section):
            if "--ignore-not-found" not in teardown_section:
                issues.append({"severity": "warning", "category": "teardown",
                               "message": "Teardown has delete commands without --ignore-not-found", "line": None})

    # --- Setup commands ---
    if "## Setup" in content:
        setup_section = content[content.find("## Setup"):]
        if "## Test Steps" in setup_section:
            setup_section = setup_section[:setup_section.find("## Test Steps")]
        if "```bash" not in setup_section and "```" not in setup_section:
            issues.append({"severity": "warning", "category": "setup",
                           "message": "Setup section has no bash code blocks", "line": None})
        elif "```bash" in setup_section or "```" in setup_section:
            if "# Expected:" not in setup_section and "# Expected " not in setup_section:
                issues.append({"severity": "warning", "category": "setup",
                               "message": "Setup commands missing '# Expected:' comments", "line": None})

    # --- Verdict ---
    blocking = [i for i in issues if i["severity"] == "blocking"]
    verdict = "FAIL" if blocking else "PASS"

    return {
        "test_case_file": file_path,
        "verdict": verdict,
        "issues": issues,
        "metadata_complete": metadata_complete,
        "section_order_valid": section_order_valid,
        "title_pattern_valid": title_valid,
        "entry_point_present": entry_point_present,
        "jira_coverage_present": jira_coverage_present,
        "step_format_valid": step_format_valid,
        "teardown_present": teardown_present,
        "total_steps": total_steps,
    }


# ---------------------------------------------------------------------------
# HTML generator (inlined from src/services/html_generator.py)
# ---------------------------------------------------------------------------

BASE_STYLE = 'font-size:11pt;font-family:Arial,Helvetica,sans-serif;color:#000000;line-height:1.5'
BOLD_STYLE = f'{BASE_STYLE};font-weight:bold'
CODE_STYLE = 'font-family:Consolas,Monaco,monospace;font-size:10pt;background-color:#f5f5f5;padding:10px;border:1px solid #ccc;overflow-x:auto'


def _escape_html(text: str) -> str:
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def _extract_section(content: str, section_name: str, next_sections: list) -> str:
    pattern = f"## {section_name}"
    start = content.find(pattern)
    if start < 0:
        return None
    start = content.find("\n", start) + 1
    end = len(content)
    for next_sec in next_sections:
        next_pattern = f"## {next_sec}"
        pos = content.find(next_pattern, start)
        if 0 < pos < end:
            end = pos
    return content[start:end].strip()


def generate_setup_html(content: str) -> str:
    setup_text = _extract_section(content, "Setup", ["Test Steps", "Step 1"])
    if not setup_text:
        return ""
    html_parts = [f'<span style="{BASE_STYLE}">']
    lines = setup_text.split("\n")
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code_block:
                html_parts.append("</pre>")
                in_code_block = False
            else:
                html_parts.append(f'<pre style="{CODE_STYLE}">')
                in_code_block = True
            continue
        if in_code_block:
            html_parts.append(_escape_html(line))
            continue
        if stripped.startswith("**") and stripped.endswith("**"):
            label = stripped.strip("*").strip(":")
            html_parts.append(f'<span style="{BOLD_STYLE}">{_escape_html(label)}:</span><br>')
        elif stripped.startswith("- "):
            bullet_text = stripped[2:]
            html_parts.append(f"&bull; {_escape_html(bullet_text)}<br>")
        elif stripped:
            html_parts.append(f"{_escape_html(stripped)}<br>")
    if in_code_block:
        html_parts.append("</pre>")
    html_parts.append("</span>")
    return "\n".join(html_parts)


def generate_steps_html(content: str) -> str:
    step_pattern = re.compile(r"^### Step (\d+):\s*(.+)$", re.MULTILINE)
    matches = list(step_pattern.finditer(content))
    if not matches:
        return ""

    TH_STYLE = 'white-space:nowrap;height:12px;text-align:left;vertical-align:top;font-weight:bold;background-color:#F0F0F0;border:1px solid #CCCCCC;padding:5px;width:50%'
    TD_STYLE = 'height:12px;text-align:left;vertical-align:top;line-height:18px;border:1px solid #CCCCCC;padding:5px'
    MONO_STYLE = 'font-family:Consolas,Monaco,monospace;font-size:10pt'

    rows = [
        '<table style="border-collapse:collapse;width:100%;">',
        "<tbody>",
        f'<tr><th contenteditable="false" id="testStepKey:step" style="{TH_STYLE};">Step</th>'
        f'<th contenteditable="false" id="testStepKey:expectedResult" style="{TH_STYLE};">Expected Result</th></tr>',
    ]

    for i, match in enumerate(matches):
        step_num = match.group(1)
        step_title = match.group(2).strip()
        start = match.end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            next_section = content.find("\n## ", start)
            end = next_section if next_section > 0 else len(content)
        step_content = content[start:end].strip()

        actions_text = ""
        expected_text = ""
        er_marker = "**Expected Result:**"
        er_pos = step_content.find(er_marker)
        if er_pos < 0:
            er_marker = "**Expected Result**"
            er_pos = step_content.find(er_marker)
        if er_pos >= 0:
            actions_text = step_content[:er_pos].strip()
            expected_text = step_content[er_pos + len(er_marker):].strip()
        else:
            actions_text = step_content

        action_lines = [f'<span style="font-weight:bold;">Step {step_num}: {_escape_html(step_title)}</span><br><br>']
        in_code = False
        for line in actions_text.split("\n"):
            stripped = line.strip()
            if stripped == "---":
                continue
            if stripped.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                action_lines.append(f'<span style="{MONO_STYLE}">{_escape_html(stripped)}</span><br>')
                continue
            if stripped and not stripped.startswith("**Actions"):
                action_lines.append(f"{_escape_html(stripped)}<br>")
        actions_html = "\n".join(action_lines)

        expected_lines = []
        for line in expected_text.split("\n"):
            stripped = line.strip()
            if stripped == "---":
                continue
            if stripped.startswith("```"):
                continue
            if stripped.startswith("- "):
                expected_lines.append(f"&bull; {_escape_html(stripped[2:])}<br>")
            elif stripped:
                expected_lines.append(f"{_escape_html(stripped)}<br>")
        expected_html = "\n".join(expected_lines)

        rows.append(
            f'<tr><td style="{TD_STYLE}"><span style="{BASE_STYLE};">{actions_html}</span></td>'
            f'<td style="{TD_STYLE}"><span style="{BASE_STYLE};">{expected_html}</span></td></tr>'
        )

    rows.append("</tbody>")
    rows.append("</table>")
    return "\n".join(rows)


def generate_html(test_case_path: str, output_dir: str):
    path = Path(test_case_path)
    if not path.exists():
        return None, None
    content = path.read_text(encoding="utf-8")
    out = Path(output_dir)

    setup_html = generate_setup_html(content)
    steps_html = generate_steps_html(content)

    setup_path = None
    steps_path = None

    if setup_html:
        p = out / "test-case-setup.html"
        p.write_text(setup_html, encoding="utf-8")
        setup_path = str(p)
    if steps_html:
        p = out / "test-case-steps.html"
        p.write_text(steps_html, encoding="utf-8")
        steps_path = str(p)

    return setup_path, steps_path


# ---------------------------------------------------------------------------
# Main (inlined from src/scripts/report.py)
# ---------------------------------------------------------------------------

def find_test_case(run_dir: Path):
    test_case = run_dir / "test-case.md"
    if test_case.exists():
        return test_case
    for md in run_dir.glob("*.md"):
        if md.name.startswith("RHACM4K-"):
            return md
    return None


def write_summary(run_dir, test_case_path, review_result, setup_path, steps_path, jira_id, artifact_check=None):
    blocking = [i for i in review_result["issues"] if i["severity"] == "blocking"]
    warnings = [i for i in review_result["issues"] if i["severity"] == "warning"]

    summary_lines = [
        "Test Case Generation Summary",
        "============================",
        "",
        f"JIRA: {jira_id}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Primary deliverable: {test_case_path.name}",
        f"Steps: {review_result['total_steps']}",
        "",
        f"Structural Validation: {review_result['verdict']}",
        f"  Metadata complete: {'Yes' if review_result['metadata_complete'] else 'No'}",
        f"  Title pattern valid: {'Yes' if review_result['title_pattern_valid'] else 'No'}",
        f"  Section order valid: {'Yes' if review_result['section_order_valid'] else 'No'}",
        f"  Entry point present: {'Yes' if review_result['entry_point_present'] else 'No'}",
        f"  JIRA coverage present: {'Yes' if review_result['jira_coverage_present'] else 'No'}",
        f"  Step format valid: {'Yes' if review_result['step_format_valid'] else 'No'}",
        f"  Teardown present: {'Yes' if review_result['teardown_present'] else 'No'}",
    ]

    if blocking:
        summary_lines.extend(["", f"Blocking Issues ({len(blocking)}):"])
        for issue in blocking:
            summary_lines.append(f"  - [{issue['category']}] {issue['message']}")

    if warnings:
        summary_lines.extend(["", f"Warnings ({len(warnings)}):"])
        for issue in warnings:
            summary_lines.append(f"  - [{issue['category']}] {issue['message']}")

    if artifact_check:
        count = artifact_check["artifacts_present"]
        total = artifact_check["artifacts_expected"]
        if artifact_check["pipeline_complete"]:
            summary_lines.extend(["", f"Pipeline Artifacts: {count}/{total} complete"])
        else:
            summary_lines.extend(["", f"Pipeline Artifacts: {count}/{total} (INCOMPLETE)"])
            for name in artifact_check["artifacts_missing"]:
                summary_lines.append(f"  Missing: {name}")

    summary_lines.extend([
        "",
        "Polarion HTML:",
        f"  Setup: {'Generated' if setup_path else 'Not generated'}",
        f"  Steps: {'Generated' if steps_path else 'Not generated'}",
        "",
        "Output Files:",
    ])
    for f in sorted(run_dir.iterdir()):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            summary_lines.append(f"  {f.name} ({size_kb:.1f} KB)")

    summary_path = run_dir / "SUMMARY.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    return summary_path


def parse_args():
    parser = argparse.ArgumentParser(description="Stage 3: Generate reports and validate test case")
    parser.add_argument("run_dir", help="Path to the run directory")
    return parser.parse_args()


def main():
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()

    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}")
        sys.exit(1)

    jira_id = "UNKNOWN"
    area = None
    gather_path = run_dir / "gather-output.json"
    if gather_path.exists():
        gather_data = json.loads(gather_path.read_text(encoding="utf-8"))
        jira_id = gather_data.get("jira_id", "UNKNOWN")
        area = gather_data.get("area")
    else:
        if run_dir.parent.name.startswith("ACM-"):
            jira_id = run_dir.parent.name

    print("Stage 3: Generating reports...")

    telemetry = PipelineTelemetry(str(run_dir), jira_id)
    telemetry.start_stage("report")

    test_case_path = find_test_case(run_dir)
    if not test_case_path:
        print("  Error: No test case markdown found in run directory")
        print("  Expected: test-case.md or RHACM4K-*.md")
        telemetry.log_error("report", "No test case file found")
        telemetry.end_stage("report", {"verdict": "FAIL"})
        sys.exit(1)

    print(f"  Found: {test_case_path.name}")

    print("  Running structural validation...")
    review_result = validate_test_case(str(test_case_path), area=area)

    artifact_check = check_artifact_completeness(run_dir)

    review_result["artifacts"] = artifact_check
    review_path = run_dir / "review-results.json"
    review_path.write_text(
        json.dumps(review_result, indent=2, default=str),
        encoding="utf-8",
    )

    blocking = [i for i in review_result["issues"] if i["severity"] == "blocking"]
    warnings = [i for i in review_result["issues"] if i["severity"] == "warning"]

    if review_result["verdict"] == "PASS":
        print(f"  Structural validation: PASS ({review_result['total_steps']} steps)")
    else:
        print("  Structural validation: FAIL")
        for issue in blocking:
            print(f"    - [{issue['category']}] {issue['message']}")

    if warnings:
        for warning in warnings:
            print(f"    Warning: [{warning['category']}] {warning['message']}")

    if artifact_check["pipeline_complete"]:
        print(f"  Pipeline artifacts: {artifact_check['artifacts_present']}/{artifact_check['artifacts_expected']} complete")
    else:
        print(f"  Pipeline artifacts: {artifact_check['artifacts_present']}/{artifact_check['artifacts_expected']} (INCOMPLETE)")
        for name in artifact_check["artifacts_missing"]:
            print(f"    Missing: {name}")

    print("  Generating Polarion HTML...")
    setup_path, steps_path = generate_html(str(test_case_path), str(run_dir))

    if setup_path:
        print(f"  Setup HTML: {Path(setup_path).name}")
    if steps_path:
        print(f"  Steps HTML: {Path(steps_path).name}")
    if not setup_path and not steps_path:
        print("  Warning: No HTML generated (could not parse test case sections)")

    summary_path = write_summary(run_dir, test_case_path, review_result, setup_path, steps_path, jira_id, artifact_check)
    print(f"  Summary: {summary_path.name}")

    telemetry.end_stage("report", {
        "verdict": review_result["verdict"],
        "total_steps": review_result["total_steps"],
        "blocking_issues": len(blocking),
        "warnings": len(warnings),
        "html_generated": bool(setup_path or steps_path),
    })
    telemetry.end_pipeline(review_result["verdict"])

    print()
    print("  Stage 3 complete.")
    print(f"  Run directory: {run_dir}")
    print()
    print("  Output files:")
    for f in sorted(run_dir.iterdir()):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            print(f"    {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()

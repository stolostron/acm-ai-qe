"""Structural validation of test case markdown against conventions."""

import re
from pathlib import Path

from ..models.review_result import ReviewResult, ValidationIssue, Verdict


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


def _extract_step_sections(content: str) -> list[str]:
    """Extract the text content of each step section."""
    step_pattern = re.compile(r"^### Step \d+:", re.MULTILINE)
    step_starts = [m.start() for m in step_pattern.finditer(content)]
    if not step_starts:
        return []

    sections = []
    for i, start in enumerate(step_starts):
        end = step_starts[i + 1] if i + 1 < len(step_starts) else len(content)
        # Stop at ## Teardown or ## Notes if they come before next step
        for boundary in ["## Teardown", "## Notes", "## Known Issues"]:
            match = re.search(rf"^{re.escape(boundary)}", content[start:end], re.MULTILINE)
            if match:
                end = start + match.start()
        sections.append(content[start:end])
    return sections


def validate_test_case(file_path: str, area: str | None = None) -> ReviewResult:
    """Validate a test case markdown file against conventions."""
    path = Path(file_path)
    if not path.exists():
        return ReviewResult(
            test_case_file=file_path,
            verdict=Verdict.FAIL,
            issues=[ValidationIssue(
                severity="blocking",
                category="file",
                message=f"File not found: {file_path}",
            )],
        )

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    issues: list[ValidationIssue] = []

    # --- Title validation ---
    title_valid = False
    if lines and lines[0].startswith("# RHACM4K-"):
        title_valid = True
        title_line = lines[0]
        if not re.search(r"# RHACM4K-\w+ - \[", title_line):
            issues.append(ValidationIssue(
                severity="blocking",
                category="title",
                message="Title does not match pattern: # RHACM4K-XXXXX - [Tag-Version] Area - Test Name",
                line=1,
            ))
            title_valid = False

        # Validate area tag if area is provided
        if area and title_valid and area in AREA_TAG_PATTERNS:
            tag_pattern = AREA_TAG_PATTERNS[area]
            if not re.search(tag_pattern, title_line):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="title",
                    message=f"Title tag does not match expected pattern for area '{area}' (e.g., {AREA_TAG_EXAMPLES.get(area, tag_pattern)})",
                    line=1,
                ))
    else:
        issues.append(ValidationIssue(
            severity="blocking",
            category="title",
            message="First line must start with '# RHACM4K-'",
            line=1,
        ))

    # --- Metadata validation ---
    metadata_complete = True
    for field in ["Polarion ID:", "Status:", "Created:", "Updated:"]:
        if f"**{field}**" not in content and f"**{field}" not in content:
            issues.append(ValidationIssue(
                severity="blocking",
                category="metadata",
                message=f"Missing metadata field: {field}",
            ))
            metadata_complete = False

    # --- Polarion fields validation ---
    for field in REQUIRED_POLARION_FIELDS:
        pattern = f"## {field}:"
        if pattern not in content:
            issues.append(ValidationIssue(
                severity="blocking",
                category="metadata",
                message=f"Missing Polarion field: ## {field}:",
            ))
            metadata_complete = False

    # --- Type field value validation ---
    type_line = next((l for l in lines if l.startswith("## Type:")), None)
    if type_line:
        type_value = type_line.split(":", 1)[1].strip().lower().replace(" ", "")
        if type_value not in ("testcase",):
            issues.append(ValidationIssue(
                severity="warning",
                category="metadata",
                message=f"Type field should be 'Test Case', found: '{type_line.split(':', 1)[1].strip()}'",
            ))

    # --- Test Steps section header ---
    if "## Test Steps" not in content:
        step_pattern_found = re.search(r"^### Step \d+:", content, re.MULTILINE)
        if step_pattern_found:
            issues.append(ValidationIssue(
                severity="warning",
                category="structure",
                message="Missing '## Test Steps' section header before step definitions",
            ))

    # --- Section order validation ---
    section_order_valid = True
    expected_sections = ["Description", "Setup", "Test Steps", "Teardown"]
    section_positions = {}
    for section in expected_sections:
        pattern = f"## {section}"
        pos = content.find(pattern)
        if pos >= 0:
            section_positions[section] = pos

    # Check order (each section should come after the previous)
    prev_pos = -1
    for section in expected_sections:
        if section in section_positions:
            if section_positions[section] < prev_pos:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="structure",
                    message=f"Section '{section}' appears out of order",
                ))
                section_order_valid = False
            prev_pos = section_positions[section]

    # Description is mandatory
    if "Description" not in section_positions and "## Description" not in content:
        issues.append(ValidationIssue(
            severity="blocking",
            category="description",
            message="Missing ## Description section",
        ))
        section_order_valid = False

    # --- Entry Point ---
    entry_point_present = "Entry Point" in content or "entry point" in content.lower()
    if not entry_point_present:
        issues.append(ValidationIssue(
            severity="warning",
            category="description",
            message="No Entry Point found in description",
        ))

    # --- JIRA Coverage ---
    jira_coverage_present = "Dev JIRA Coverage" in content or "JIRA Coverage" in content
    if not jira_coverage_present:
        issues.append(ValidationIssue(
            severity="warning",
            category="description",
            message="No Dev JIRA Coverage found in description",
        ))

    # --- Test Steps ---
    step_pattern = re.compile(r"^### Step \d+:", re.MULTILINE)
    steps = step_pattern.findall(content)
    total_steps = len(steps)

    step_format_valid = True
    if total_steps == 0:
        issues.append(ValidationIssue(
            severity="blocking",
            category="steps",
            message="No test steps found (expected ### Step N: format)",
        ))
        step_format_valid = False

    # Per-step validation
    step_sections = _extract_step_sections(content)
    for i, step_content in enumerate(step_sections, 1):
        # Check for expected result in each step
        if "Expected Result" not in step_content and "expected result" not in step_content.lower():
            issues.append(ValidationIssue(
                severity="blocking",
                category="steps",
                message=f"Step {i} missing 'Expected Result' section",
            ))
            step_format_valid = False

        # Check for numbered actions (at least one line starting with "1.")
        if not re.search(r"^\d+\.", step_content, re.MULTILINE):
            issues.append(ValidationIssue(
                severity="warning",
                category="steps",
                message=f"Step {i} has no numbered actions (expected 1., 2., etc.)",
            ))

        # Check for CLI commands in test steps (heuristic)
        cli_pattern = re.compile(r"^\s*(?:oc|kubectl)\s+(?!#)", re.MULTILINE)
        if cli_pattern.search(step_content):
            # Only flag if it's not inside a ```bash block or after "Expected Result"
            expected_pos = step_content.lower().find("expected result")
            cli_match = cli_pattern.search(step_content)
            if cli_match and (expected_pos == -1 or cli_match.start() < expected_pos):
                # CLI in action area (before expected result) — might be testing backend
                bash_block = step_content.find("```bash")
                if bash_block == -1 or cli_match.start() < bash_block:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="steps",
                        message=f"Step {i}: CLI command detected in test step actions — verify this is backend validation, not a UI substitute",
                    ))

    # Check step separators (--- between consecutive steps)
    if len(step_sections) > 1:
        for i in range(len(step_sections) - 1):
            section_end = step_sections[i].rstrip()
            if not section_end.endswith("---"):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="steps",
                    message=f"Missing '---' separator after Step {i + 1}",
                ))

    # --- Teardown ---
    teardown_present = "## Teardown" in content
    if not teardown_present:
        issues.append(ValidationIssue(
            severity="warning",
            category="teardown",
            message="Missing ## Teardown section",
        ))
    else:
        teardown_start = content.find("## Teardown")
        teardown_section = content[teardown_start:]
        # Check for --ignore-not-found on delete commands
        delete_pattern = re.compile(r"oc delete|kubectl delete", re.MULTILINE)
        if delete_pattern.search(teardown_section):
            if "--ignore-not-found" not in teardown_section:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="teardown",
                    message="Teardown has delete commands without --ignore-not-found",
                ))

    # --- Setup commands ---
    if "## Setup" in content:
        setup_section = content[content.find("## Setup"):]
        if "## Test Steps" in setup_section:
            setup_section = setup_section[:setup_section.find("## Test Steps")]
        if "```bash" not in setup_section and "```" not in setup_section:
            issues.append(ValidationIssue(
                severity="warning",
                category="setup",
                message="Setup section has no bash code blocks",
            ))
        elif "```bash" in setup_section or "```" in setup_section:
            # Check for # Expected: comments in setup commands
            if "# Expected:" not in setup_section and "# Expected " not in setup_section:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="setup",
                    message="Setup commands missing '# Expected:' comments",
                ))

    # --- Determine verdict ---
    blocking = [i for i in issues if i.severity == "blocking"]
    verdict = Verdict.FAIL if blocking else Verdict.PASS

    return ReviewResult(
        test_case_file=file_path,
        verdict=verdict,
        issues=issues,
        metadata_complete=metadata_complete,
        section_order_valid=section_order_valid,
        title_pattern_valid=title_valid,
        entry_point_present=entry_point_present,
        jira_coverage_present=jira_coverage_present,
        step_format_valid=step_format_valid,
        teardown_present=teardown_present,
        total_steps=total_steps,
    )

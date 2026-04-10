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


def validate_test_case(file_path: str) -> ReviewResult:
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

    # Check for Expected Result in steps
    if total_steps > 0 and "Expected Result" not in content and "expected result" not in content.lower():
        issues.append(ValidationIssue(
            severity="blocking",
            category="steps",
            message="No 'Expected Result' sections found in test steps",
        ))
        step_format_valid = False

    # --- Teardown ---
    teardown_present = "## Teardown" in content
    if not teardown_present:
        issues.append(ValidationIssue(
            severity="warning",
            category="teardown",
            message="Missing ## Teardown section",
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

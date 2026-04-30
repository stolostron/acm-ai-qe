"""Programmatic enforcement of quality reviewer output.

Validates that the quality reviewer's output contains the required
minimum MCP verifications, structural checks, and translation
verification. Also warns (non-blocking) if a conditional feature
lacks a negative scenario step. This script cannot be bypassed by
the AI agent -- it's deterministic.

Usage:
    python review_enforcement.py <review-output-file>

Exit codes:
    0 -- PASS (all enforcement checks passed)
    1 -- FAIL (enforcement checks failed, verdict overridden to NEEDS_FIXES)
"""

import re
import sys
from pathlib import Path


MIN_MCP_VERIFICATIONS = 3


def count_mcp_verifications(review_text: str) -> int:
    """Count MCP verification entries in the review output."""
    section_match = re.search(
        r"MCP VERIFICATIONS.*?(?=\n(?:BLOCKING|WARNING|Verdict|$))",
        review_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not section_match:
        return 0

    section = section_match.group(0)
    entries = re.findall(
        r"\d+\.\s+(?:search_translations|get_routes|get_component_source|"
        r"search_code|get_wizard_steps|find_test_ids|get_acm_selectors|"
        r"get_polarion_work_items|get_polarion_test_case_summary)",
        section,
        re.IGNORECASE,
    )
    return len(entries)


def extract_verdict(review_text: str) -> str:
    """Extract the verdict from the review output."""
    match = re.search(r"Verdict:\s*(PASS|NEEDS_FIXES)", review_text, re.IGNORECASE)
    return match.group(1).upper() if match else "UNKNOWN"


def check_source_verification(review_text: str) -> bool:
    """Check if get_component_source was used for factual verification."""
    return bool(
        re.search(r"get_component_source", review_text, re.IGNORECASE)
    )


def check_translation_verification(review_text: str) -> bool:
    """Check if search_translations was used at least once in the review."""
    return bool(
        re.search(r"search_translations", review_text, re.IGNORECASE)
    )


def extract_section(text: str, heading: str) -> str:
    """Extract content under a markdown heading (## or ###).

    Returns the text from the heading to the next heading of same
    or higher level, or end of text.
    """
    pattern = rf"(?:#{{2,3}})\s+{re.escape(heading)}.*?\n(.*?)(?=\n#{{2,3}}\s|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def check_negative_scenario(review_path: Path) -> list[str]:
    """Check if a negative scenario exists when feature is conditionally rendered.

    Derives the test-case path from the review output path (same directory,
    file named test-case.md). Returns a list of warning strings (empty if OK
    or not applicable).
    """
    warnings: list[str] = []
    test_case_path = review_path.parent / "test-case.md"
    if not test_case_path.exists():
        return warnings

    tc_text = test_case_path.read_text(encoding="utf-8")

    description = extract_section(tc_text, "Description")
    conditional_keywords = [
        "conditional", "conditionally rendered", "feature gate",
        "feature flag", "permission", "role-based",
        "hidden when", "visible only", "not shown",
    ]
    has_conditional = any(
        kw.lower() in description.lower() for kw in conditional_keywords
    )

    if not has_conditional:
        return warnings

    negative_indicators = [
        "not visible", "not displayed", "should not appear",
        "not available", "not shown", "not rendered",
        "hidden", "absent", "does not appear", "is not present",
        "cannot access", "no longer visible", "removed from",
    ]
    step_matches = re.findall(
        r"###\s+Step\s+\d+.*?\n(.*?)(?=###\s+Step\s+\d+|\Z)",
        tc_text,
        re.DOTALL | re.IGNORECASE,
    )
    steps_text = " ".join(step_matches)

    has_negative = any(
        ind.lower() in steps_text.lower() for ind in negative_indicators
    )

    if not has_negative:
        warnings.append(
            "WARNING: Description mentions conditional rendering but no "
            "negative scenario step found. Consider adding a step that "
            "verifies the feature is NOT visible when the condition is not met."
        )

    return warnings


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python review_enforcement.py <review-output-file>")
        sys.exit(1)

    review_path = Path(sys.argv[1])
    if not review_path.exists():
        print(f"Error: Review output file not found: {review_path}")
        sys.exit(1)

    review_text = review_path.read_text(encoding="utf-8")
    issues = []

    mcp_count = count_mcp_verifications(review_text)
    if mcp_count < MIN_MCP_VERIFICATIONS:
        issues.append(
            f"Insufficient MCP verifications: found {mcp_count}, "
            f"minimum required is {MIN_MCP_VERIFICATIONS}"
        )

    if not check_source_verification(review_text):
        issues.append(
            "No get_component_source verification found. "
            "The reviewer must read at least one component source "
            "to verify a factual claim."
        )

    if not check_translation_verification(review_text):
        issues.append(
            "No search_translations verification found. "
            "The reviewer must verify at least one UI label or "
            "metric name against current source via search_translations."
        )

    neg_warnings = check_negative_scenario(review_path)

    agent_verdict = extract_verdict(review_text)

    if issues:
        print("ENFORCEMENT: FAIL")
        print(f"Agent verdict was: {agent_verdict}")
        print(f"Overriding to: NEEDS_FIXES")
        print(f"Reasons:")
        for issue in issues:
            print(f"  - {issue}")
        for warn in neg_warnings:
            print(f"  - {warn}")
        sys.exit(1)
    else:
        print("ENFORCEMENT: PASS")
        print(f"Agent verdict: {agent_verdict}")
        print(f"MCP verifications found: {mcp_count}")
        print(f"Source verification: present")
        print(f"Translation verification: present")
        for warn in neg_warnings:
            print(f"  - {warn}")
        sys.exit(0)


if __name__ == "__main__":
    main()

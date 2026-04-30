"""Programmatic enforcement of quality reviewer output.

Validates that the quality reviewer's output contains the required
minimum MCP verifications and structural checks. This script cannot
be bypassed by the AI agent -- it's deterministic.

Usage:
    python review_enforcement.py <review-output-file>

Exit codes:
    0 -- PASS (all enforcement checks passed)
    1 -- FAIL (enforcement checks failed, verdict overridden to NEEDS_FIXES)
"""

import json
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

    agent_verdict = extract_verdict(review_text)

    if issues:
        print("ENFORCEMENT: FAIL")
        print(f"Agent verdict was: {agent_verdict}")
        print(f"Overriding to: NEEDS_FIXES")
        print(f"Reasons:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("ENFORCEMENT: PASS")
        print(f"Agent verdict: {agent_verdict}")
        print(f"MCP verifications found: {mcp_count}")
        print(f"Source verification: present")
        sys.exit(0)


if __name__ == "__main__":
    main()

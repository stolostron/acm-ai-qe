"""Stage 3: Generate reports, validate, and produce Polarion HTML.

Deterministic Python script that validates the test case markdown,
generates Polarion HTML, writes a summary, and logs telemetry.

Usage:
    python -m src.scripts.report <run-directory>
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.review_result import ReviewResult
from src.services.convention_validator import validate_test_case
from src.services.html_generator import generate_html
from src.services.telemetry import PipelineTelemetry

EXPECTED_ARTIFACTS = [
    ("gather-output.json",),
    ("pr-diff.txt",),
    ("phase1-feature-investigation.md", "phase2-jira.json"),
    ("phase1-code-change-analysis.md", "phase3-code.json"),
    ("phase1-ui-discovery.md", "phase4-ui.json"),
    ("phase2-synthesized-context.md", "synthesized-context.md"),
    ("phase3-live-validation.md", "phase6-live-validation.md"),
    ("test-case.md",),
    ("phase4.5-quality-review.md", "phase8-review.md"),
]


def check_artifact_completeness(run_dir: Path) -> dict:
    """Check which pipeline artifacts were saved."""
    present = []
    missing = []
    for alternates in EXPECTED_ARTIFACTS:
        found = None
        for name in alternates:
            if (run_dir / name).exists():
                found = name
                break
        if found:
            present.append(found)
        else:
            missing.append(alternates[0])
    return {
        "artifacts_present": len(present),
        "artifacts_expected": len(EXPECTED_ARTIFACTS),
        "artifacts_missing": missing,
        "pipeline_complete": len(missing) == 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 3: Generate reports and validate test case",
    )
    parser.add_argument("run_dir", help="Path to the run directory")
    return parser.parse_args()


def find_test_case(run_dir: Path) -> Path | None:
    """Find the test case markdown file in the run directory."""
    test_case = run_dir / "test-case.md"
    if test_case.exists():
        return test_case

    for md in run_dir.glob("*.md"):
        if md.name.startswith("RHACM4K-"):
            return md

    return None


def write_summary(
    run_dir: Path,
    test_case_path: Path,
    review_result: ReviewResult,
    setup_path: str | None,
    steps_path: str | None,
    jira_id: str,
    artifact_check: dict | None = None,
) -> Path:
    """Write a human-readable SUMMARY.txt."""
    summary_lines = [
        f"Test Case Generation Summary",
        f"============================",
        f"",
        f"JIRA: {jira_id}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"Primary deliverable: {test_case_path.name}",
        f"Steps: {review_result.total_steps}",
        f"",
        f"Structural Validation: {review_result.verdict.value}",
        f"  Metadata complete: {'Yes' if review_result.metadata_complete else 'No'}",
        f"  Title pattern valid: {'Yes' if review_result.title_pattern_valid else 'No'}",
        f"  Section order valid: {'Yes' if review_result.section_order_valid else 'No'}",
        f"  Entry point present: {'Yes' if review_result.entry_point_present else 'No'}",
        f"  JIRA coverage present: {'Yes' if review_result.jira_coverage_present else 'No'}",
        f"  Step format valid: {'Yes' if review_result.step_format_valid else 'No'}",
        f"  Teardown present: {'Yes' if review_result.teardown_present else 'No'}",
    ]

    if review_result.blocking_issues:
        summary_lines.append(f"")
        summary_lines.append(f"Blocking Issues ({len(review_result.blocking_issues)}):")
        for issue in review_result.blocking_issues:
            summary_lines.append(f"  - [{issue.category}] {issue.message}")

    if review_result.warnings:
        summary_lines.append(f"")
        summary_lines.append(f"Warnings ({len(review_result.warnings)}):")
        for issue in review_result.warnings:
            summary_lines.append(f"  - [{issue.category}] {issue.message}")

    if artifact_check:
        count = artifact_check["artifacts_present"]
        total = artifact_check["artifacts_expected"]
        if artifact_check["pipeline_complete"]:
            summary_lines.append(f"")
            summary_lines.append(f"Pipeline Artifacts: {count}/{total} complete")
        else:
            summary_lines.append(f"")
            summary_lines.append(f"Pipeline Artifacts: {count}/{total} (INCOMPLETE)")
            for name in artifact_check["artifacts_missing"]:
                summary_lines.append(f"  Missing: {name}")

    summary_lines.append(f"")
    summary_lines.append(f"Polarion HTML:")
    summary_lines.append(f"  Setup: {'Generated' if setup_path else 'Not generated'}")
    summary_lines.append(f"  Steps: {'Generated' if steps_path else 'Not generated'}")

    summary_lines.append(f"")
    summary_lines.append(f"Output Files:")
    for f in sorted(run_dir.iterdir()):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            summary_lines.append(f"  {f.name} ({size_kb:.1f} KB)")

    summary_path = run_dir / "SUMMARY.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    return summary_path


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()

    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}")
        sys.exit(1)

    # Extract JIRA ID and area from gather-output.json (authoritative source)
    jira_id = "UNKNOWN"
    area = None
    gather_path = run_dir / "gather-output.json"
    if gather_path.exists():
        gather_data = json.loads(gather_path.read_text(encoding="utf-8"))
        jira_id = gather_data.get("jira_id", "UNKNOWN")
        area = gather_data.get("area")
    else:
        # Fallback: extract from directory name
        if run_dir.parent.name.startswith("ACM-"):
            jira_id = run_dir.parent.name

    print(f"Stage 3: Generating reports...")

    telemetry = PipelineTelemetry(str(run_dir), jira_id)
    telemetry.start_stage("report")

    # --- Find test case ---
    test_case_path = find_test_case(run_dir)
    if not test_case_path:
        print("  Error: No test case markdown found in run directory")
        print("  Expected: test-case.md or RHACM4K-*.md")
        telemetry.log_error("report", "No test case file found")
        telemetry.end_stage("report", {"verdict": "FAIL"})
        sys.exit(1)

    print(f"  Found: {test_case_path.name}")

    # --- Structural validation ---
    print("  Running structural validation...")
    review_result = validate_test_case(str(test_case_path), area=area)

    # --- Artifact completeness ---
    artifact_check = check_artifact_completeness(run_dir)

    review_data = review_result.model_dump()
    review_data["artifacts"] = artifact_check
    review_path = run_dir / "review-results.json"
    review_path.write_text(
        json.dumps(review_data, indent=2, default=str),
        encoding="utf-8",
    )

    if review_result.verdict.value == "PASS":
        print(f"  Structural validation: PASS ({review_result.total_steps} steps)")
    else:
        print(f"  Structural validation: FAIL")
        for issue in review_result.blocking_issues:
            print(f"    - [{issue.category}] {issue.message}")

    if review_result.warnings:
        for warning in review_result.warnings:
            print(f"    Warning: [{warning.category}] {warning.message}")

    if artifact_check["pipeline_complete"]:
        print(f"  Pipeline artifacts: {artifact_check['artifacts_present']}/{artifact_check['artifacts_expected']} complete")
    else:
        print(f"  Pipeline artifacts: {artifact_check['artifacts_present']}/{artifact_check['artifacts_expected']} (INCOMPLETE)")
        for name in artifact_check["artifacts_missing"]:
            print(f"    Missing: {name}")

    # --- Generate Polarion HTML ---
    print("  Generating Polarion HTML...")
    setup_path, steps_path = generate_html(str(test_case_path), str(run_dir))

    if setup_path:
        print(f"  Setup HTML: {Path(setup_path).name}")
    if steps_path:
        print(f"  Steps HTML: {Path(steps_path).name}")
    if not setup_path and not steps_path:
        print("  Warning: No HTML generated (could not parse test case sections)")

    # --- Write summary ---
    summary_path = write_summary(run_dir, test_case_path, review_result, setup_path, steps_path, jira_id, artifact_check)
    print(f"  Summary: {summary_path.name}")

    # --- Telemetry ---
    telemetry.end_stage("report", {
        "verdict": review_result.verdict.value,
        "total_steps": review_result.total_steps,
        "blocking_issues": len(review_result.blocking_issues),
        "warnings": len(review_result.warnings),
        "html_generated": bool(setup_path or steps_path),
    })
    telemetry.end_pipeline(review_result.verdict.value)

    # --- Final output ---
    print()
    print(f"  Stage 3 complete.")
    print(f"  Run directory: {run_dir}")
    print()
    print("  Output files:")
    for f in sorted(run_dir.iterdir()):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            print(f"    {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()

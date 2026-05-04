"""Stage 1: Gather data for test case generation.

Deterministic Python script that collects PR data, existing test cases,
conventions, and area knowledge. No LLM or MCP calls.

Usage:
    python -m src.scripts.gather ACM-30459 [--version 2.17] [--pr 5790] [--area governance] [--skip-live] [--repo stolostron/console]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.gather_output import GatherOptions, GatherOutput
from src.services.file_service import (
    find_existing_test_cases,
    read_area_knowledge,
    read_conventions,
    read_html_templates,
)
from src.services.github_service import (
    detect_area_from_files,
    get_pr_diff,
    get_pr_metadata,
    search_pr_for_jira,
)
from src.services.telemetry import PipelineTelemetry


def create_run_directory(jira_id: str) -> Path:
    """Create a timestamped run directory."""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    run_dir = PROJECT_ROOT / "runs" / "test-case-generator" / jira_id / f"{jira_id}-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 1: Gather data for test case generation",
    )
    parser.add_argument("jira_id", help="JIRA ticket ID (e.g., ACM-30459)")
    parser.add_argument("--version", help="ACM version (e.g., 2.17)")
    parser.add_argument("--pr", type=int, help="PR number (auto-detected if omitted)")
    parser.add_argument("--area", help="Console area (auto-detected from PR paths)")
    parser.add_argument("--skip-live", action="store_true", help="Skip live cluster validation")
    parser.add_argument("--cluster-url", help="Console URL for live validation (e.g., https://console-openshift-console.apps.hub.example.com)")
    parser.add_argument("--repo", default="stolostron/console", help="GitHub repo (default: stolostron/console)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    jira_id = args.jira_id.upper()

    print(f"Stage 1: Gathering data for {jira_id}...")

    run_dir = create_run_directory(jira_id)
    telemetry = PipelineTelemetry(str(run_dir), jira_id)
    telemetry.start_stage("gather")

    pr_number = args.pr
    pr_data = None
    area = args.area
    diff_file = None

    # --- PR Discovery ---
    if not pr_number:
        print(f"  Searching for PR associated with {jira_id}...")
        pr_number = search_pr_for_jira(jira_id, args.repo)
        if pr_number:
            print(f"  Found PR #{pr_number}")
        else:
            print(f"  No PR found for {jira_id} in {args.repo}")

    # --- PR Metadata ---
    if pr_number:
        print(f"  Fetching PR #{pr_number} metadata...")
        pr_data = get_pr_metadata(pr_number, args.repo)
        if pr_data:
            print(f"  PR: {pr_data.title}")
            print(f"  Files: {len(pr_data.files)} changed ({pr_data.additions}+ / {pr_data.deletions}-)")

            # Auto-detect area from file paths
            if not area:
                area = detect_area_from_files(pr_data.files)
                if area:
                    print(f"  Area detected: {area}")

            # Fetch full diff
            print(f"  Fetching PR diff...")
            diff_path = run_dir / "pr-diff.txt"
            diff_result = get_pr_diff(pr_number, args.repo, diff_path)
            if diff_result:
                pr_data.diff_file = str(diff_path)
                print(f"  Diff saved: {diff_path.name}")
        else:
            print(f"  Failed to fetch PR #{pr_number} metadata")

    # --- Version ---
    acm_version = args.version
    if not acm_version:
        print("  ACM version not specified (will be detected from JIRA in Stage 2)")

    # --- Existing Test Cases ---
    version_for_search = acm_version or "latest"
    existing = find_existing_test_cases(version_for_search, area=area)
    if existing:
        print(f"  Found {len(existing)} peer test case(s) for reference")
    else:
        print(f"  No existing test cases found for version {version_for_search}")

    # --- Conventions ---
    print("  Loading conventions...")
    conventions = read_conventions()
    html_templates = read_html_templates()
    if conventions:
        print(f"  Loaded test-case-format.md ({len(conventions)} chars)")
    else:
        print("  WARNING: test-case-format.md not found in knowledge/conventions/")

    # --- Area Knowledge ---
    area_knowledge = None
    if area:
        area_knowledge = read_area_knowledge(area)
        if area_knowledge:
            print(f"  Loaded {area} architecture knowledge ({len(area_knowledge)} chars)")
        else:
            print(f"  No architecture knowledge found for area: {area}")

    # --- Classify PR files as test vs production ---
    test_files: list[str] = []
    production_files: list[str] = []
    if pr_data and pr_data.files:
        for f in pr_data.files:
            if ".test." in f or ".spec." in f or "/tests/" in f or "/__tests__/" in f:
                test_files.append(f)
            else:
                production_files.append(f)

    # --- Build Output ---
    output = GatherOutput(
        jira_id=jira_id,
        acm_version=acm_version,
        area=area,
        pr_data=pr_data,
        existing_test_cases=existing,
        conventions=conventions,
        area_knowledge=area_knowledge,
        html_templates=html_templates,
        run_dir=str(run_dir),
        options=GatherOptions(
            skip_live=args.skip_live,
            cluster_url=args.cluster_url,
            repo=args.repo,
        ),
        test_files=test_files,
        production_files=production_files,
    )

    # --- Write Output ---
    output_path = run_dir / "gather-output.json"
    output_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8",
    )

    telemetry.end_stage("gather", {
        "pr_found": pr_data is not None,
        "pr_number": pr_number,
        "area": area,
        "existing_test_cases_count": len(existing),
        "conventions_loaded": bool(conventions),
    })

    # --- Summary ---
    print()
    print(f"  Stage 1 complete. Output: {output_path}")
    print(f"  Run directory: {run_dir}")
    print()

    # Print the run directory path for Stage 2 to pick up
    print(str(run_dir))


if __name__ == "__main__":
    main()

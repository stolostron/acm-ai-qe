#!/usr/bin/env python3
"""
Z-Stream Analysis - Main Entry Point (v2.0)

CLI tool for gathering pipeline failure data for AI analysis.

Architecture (v2.0):
- Phase 1: Data Gathering (this script + gather.py)
- Phase 2: AI Analysis (Claude Code agent reads repos and classifies)
- Phase 3: Report Generation (report.py)

Usage:
    python main.py <jenkins_url>
    python main.py --url <jenkins_url> [--output-dir <path>] [--verbose]

Examples:
    python main.py https://jenkins.example.com/job/pipeline/123/
    python main.py --url https://jenkins.example.com/job/pipeline/123/ --output-dir ./results
"""

import argparse
import sys
from pathlib import Path

# Add source directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from scripts.gather import DataGatherer


def validate_jenkins_url(url: str) -> bool:
    """Validate that the provided URL looks like a Jenkins build URL."""
    if not url:
        return False

    if not url.startswith(('http://', 'https://')):
        return False

    if '/job/' not in url:
        return False

    return True


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Z-Stream Analysis - Jenkins Pipeline Failure Analyzer (v2.0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Architecture (v2.0):
  Phase 1: Data Gathering - Collects factual data, clones repos
  Phase 2: AI Analysis   - Agent reads repos, investigates, classifies
  Phase 3: Report Gen    - Formats AI output into reports

This script runs Phase 1 (data gathering).
AI analysis happens via the z-stream-analysis agent.
Report generation: python -m src.scripts.report <run_dir>

Examples:
  %(prog)s https://jenkins.example.com/job/pipeline/123/
  %(prog)s --url https://jenkins.example.com/job/pipeline/123/ --verbose
  %(prog)s --url https://jenkins.example.com/job/pipeline/123/ --output-dir ./my-results
        """
    )

    parser.add_argument(
        'url',
        nargs='?',
        help='Jenkins build URL to analyze'
    )

    parser.add_argument(
        '--url', '-u',
        dest='url_flag',
        help='Jenkins build URL to analyze (alternative to positional argument)'
    )

    parser.add_argument(
        '--output-dir', '-o',
        default='./runs',
        help='Directory to save analysis results (default: ./runs)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--skip-env',
        action='store_true',
        help='Skip environment validation'
    )

    parser.add_argument(
        '--skip-repo',
        action='store_true',
        help='Skip repository cloning'
    )

    args = parser.parse_args()

    # Get the Jenkins URL from either positional or flag argument
    jenkins_url = args.url or args.url_flag

    if not jenkins_url:
        parser.print_help()
        print("\nError: Jenkins URL is required", file=sys.stderr)
        sys.exit(1)

    # Validate URL
    if not validate_jenkins_url(jenkins_url):
        print(f"Error: Invalid Jenkins URL: {jenkins_url}", file=sys.stderr)
        print("URL should be in format: https://jenkins.example.com/job/<job-name>/<build-number>/", file=sys.stderr)
        sys.exit(1)

    try:
        # Run data gathering (Phase 1)
        gatherer = DataGatherer(output_dir=args.output_dir, verbose=args.verbose)
        run_dir, data = gatherer.gather_all(
            jenkins_url,
            skip_environment=args.skip_env,
            skip_repository=args.skip_repo
        )

        # Print summary
        print("\n" + "=" * 60)
        print("PHASE 1 COMPLETE: Data Gathering")
        print("=" * 60)
        print(f"\nRun directory: {run_dir}")

        test_report = data.get('test_report', {})
        summary = test_report.get('summary', {})

        if summary.get('total_tests', 0) > 0:
            print(f"\nTest Summary:")
            print(f"  Total: {summary.get('total_tests', 0)}")
            print(f"  Failed: {summary.get('failed_count', 0)}")
            print(f"  Pass Rate: {summary.get('pass_rate', 0):.1f}%")

        failed_tests = test_report.get('failed_tests', [])
        if failed_tests:
            print(f"\nFailed Tests ({len(failed_tests)}):")
            for test in failed_tests[:5]:
                print(f"  - {test.get('test_name', 'Unknown')}")
            if len(failed_tests) > 5:
                print(f"  ... and {len(failed_tests) - 5} more")

        repos = data.get('repositories', {})
        print(f"\nRepositories:")
        print(f"  Automation: {'Cloned' if repos.get('automation', {}).get('cloned') else 'Not cloned'}")
        print(f"  Console: {'Cloned' if repos.get('console', {}).get('cloned') else 'Not cloned'}")

        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print(f"\n1. AI Analysis (via z-stream-analysis agent):")
        print(f"   - Agent reads: {run_dir}/core-data.json")
        print(f"   - Agent investigates: {run_dir}/repos/")
        print(f"   - Agent creates: {run_dir}/analysis-results.json")
        print(f"\n2. Report Generation:")
        print(f"   python -m src.scripts.report {run_dir}")
        print("\n" + "=" * 60 + "\n")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\nAnalysis cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

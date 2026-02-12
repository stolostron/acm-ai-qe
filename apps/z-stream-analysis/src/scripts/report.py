#!/usr/bin/env python3
"""
Report Generation Script
Formats AI analysis results into various report formats.

This script handles MECHANICAL formatting only.
Takes analysis-results.json (from AI) and generates readable reports.

Usage:
    python -m src.scripts.report <run_dir>
    python -m src.scripts.report --run-dir ./runs/job_20260113_153000

Input:
    - core-data.json (primary gathered data) OR legacy raw-data.json
    - analysis-results.json (AI analysis output)

Output:
    - Detailed-Analysis.md (comprehensive markdown report)
    - per-test-breakdown.json (structured JSON for tooling)
    - SUMMARY.txt (brief text summary)

Note:
    Auto-detects multi-file structure (core-data.json) vs legacy (raw-data.json)
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class ReportFormatter:
    """
    Report Formatter - Generates reports from AI analysis results.
    
    This class performs MECHANICAL formatting only.
    The analysis and reasoning come from AI (analysis-results.json).
    """
    
    CLASSIFICATION_EMOJI = {
        'PRODUCT_BUG': '🔴',
        'AUTOMATION_BUG': '🟡',
        'INFRASTRUCTURE': '🔵',
        'UNKNOWN': '⚪',
        'REQUIRES_INVESTIGATION': '⚪',
        'NO_BUG': '🟢',
        'FLAKY': '🟢'
    }
    
    PRIORITY_EMOJI = {
        'CRITICAL': '🔴',
        'HIGH': '🟠',
        'MEDIUM': '🟡',
        'LOW': '🟢'
    }
    
    def __init__(self, run_dir: Path, validate_schema: bool = True):
        """
        Initialize report formatter.

        Args:
            run_dir: Path to the run directory containing gathered data and analysis
            validate_schema: If True, validate analysis-results.json before processing
        """
        self.run_dir = Path(run_dir)
        self.logger = logging.getLogger(__name__)

        # Auto-detect and load data (multi-file or legacy)
        self.raw_data = self._load_core_data()
        self.analysis_results = self._load_json('analysis-results.json')

        if not self.raw_data:
            raise FileNotFoundError(f"No data files found in {run_dir}")

        # Validate schema if analysis-results.json file exists — fail hard on errors.
        # Use 'is not None' (not truthiness) because {} is falsy but means the file
        # exists with an empty object, which is still a schema error.
        if validate_schema and self.analysis_results is not None:
            self._validate_analysis_results(strict=True)

    def _load_core_data(self) -> Optional[Dict[str, Any]]:
        """
        Load core data from multi-file structure or legacy raw-data.json.

        Detection logic:
        1. If manifest.json exists → multi-file mode, load core-data.json
        2. If raw-data.json exists with _migration_version → multi-file mode
        3. If raw-data.json exists without _migration_version → legacy mode

        Returns:
            Loaded data dictionary or None if not found
        """
        # Check for multi-file structure
        manifest = self._load_json('manifest.json')
        if manifest:
            self.logger.debug("Detected multi-file structure (manifest.json present)")
            core_data = self._load_json('core-data.json')
            if core_data:
                return core_data
            else:
                self.logger.warning("manifest.json found but core-data.json missing")

        # Check raw-data.json
        raw_data = self._load_json('raw-data.json')
        if raw_data:
            # Check if it's a migration stub
            if raw_data.get('_migration_version'):
                self.logger.debug("Detected multi-file stub, loading core-data.json")
                core_data = self._load_json('core-data.json')
                if core_data:
                    return core_data
                else:
                    self.logger.warning("Migration stub found but core-data.json missing")
                    return None
            else:
                # Legacy format - return as-is
                self.logger.debug("Detected legacy raw-data.json format")
                return raw_data

        # Try core-data.json directly
        core_data = self._load_json('core-data.json')
        if core_data:
            self.logger.debug("Loading core-data.json directly")
            return core_data

        return None

    def _validate_analysis_results(self, strict: bool = True):
        """
        Validate analysis-results.json against schema.

        Args:
            strict: If True, raise on validation errors instead of logging warnings.
                    This prevents silent generation of empty reports when field names
                    don't match what the report formatter expects.
        """
        try:
            from src.services.schema_validation_service import SchemaValidationService

            validator = SchemaValidationService()
            result = validator.validate(self.analysis_results)

            if not result.is_valid:
                message = (
                    f"analysis-results.json has schema errors:\n"
                    f"{validator.format_issues(result)}\n\n"
                    f"See schema: src/schemas/analysis_results_schema.json\n"
                    f"See output example: .claude/agents/z-stream-analysis.md (lines 970-1079)\n\n"
                    f"Fix analysis-results.json and re-run: python -m src.scripts.report {self.run_dir}"
                )
                if strict:
                    raise ValueError(message)
                else:
                    self.logger.warning(message)
            elif result.warnings_count > 0:
                self.logger.info(
                    f"Schema validation passed with {result.warnings_count} warnings"
                )
            else:
                self.logger.debug("Schema validation passed")

        except ImportError:
            self.logger.debug("Schema validation service not available, skipping validation")
        except ValueError:
            raise  # Re-raise validation errors
        except Exception as e:
            self.logger.warning(f"Schema validation error: {e}")
        
    def _load_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load a JSON file from the run directory."""
        filepath = self.run_dir / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    
    def format_all(self) -> Dict[str, str]:
        """
        Generate all report formats.
        
        Returns:
            Dictionary of report type to file path
        """
        reports = {}
        
        # Generate Markdown report
        md_path = self.format_markdown()
        reports['markdown'] = str(md_path)
        
        # Generate JSON breakdown
        json_path = self.format_json()
        reports['json'] = str(json_path)
        
        # Generate text summary
        summary_path = self.format_summary()
        reports['summary'] = str(summary_path)
        
        return reports
    
    def format_markdown(self) -> Path:
        """Generate detailed Markdown report."""
        lines = []
        
        # Header
        jenkins_url = self.raw_data.get('metadata', {}).get('jenkins_url', 'Unknown')
        gathered_at = self.raw_data.get('metadata', {}).get('gathered_at', '')
        
        lines.extend([
            "# Pipeline Failure Analysis Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Jenkins URL:** {jenkins_url}",
            "",
            "---",
            "",
        ])
        
        # Executive Summary
        overall = self.analysis_results.get('summary', {}) if self.analysis_results else {}
        overall_classification = overall.get('overall_classification', 'REQUIRES_INVESTIGATION')
        overall_confidence = overall.get('overall_confidence', 0.0)
        
        emoji = self.CLASSIFICATION_EMOJI.get(overall_classification, '⚪')
        
        lines.extend([
            "## Executive Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| **Overall Classification** | {emoji} {overall_classification.replace('_', ' ')} |",
            f"| **Confidence** | {overall_confidence:.0%} |",
        ])
        
        # Test summary from raw data
        test_report = self.raw_data.get('test_report', {})
        summary = test_report.get('summary', {})
        
        if summary.get('total_tests', 0) > 0:
            lines.extend([
                f"| **Total Tests** | {summary.get('total_tests', 0)} |",
                f"| **Passed** | {summary.get('passed_count', 0)} |",
                f"| **Failed** | {summary.get('failed_count', 0)} |",
                f"| **Pass Rate** | {summary.get('pass_rate', 0):.1f}% |",
            ])
        
        lines.extend(["", ""])
        
        # Classification Breakdown
        if self.analysis_results:
            by_classification = overall.get('by_classification', {})
            if by_classification:
                lines.extend([
                    "### Classification Breakdown",
                    "",
                ])
                
                for cl, count in sorted(by_classification.items(), key=lambda x: x[1], reverse=True):
                    emoji = self.CLASSIFICATION_EMOJI.get(cl, '⚪')
                    cl_display = cl.replace('_', ' ')
                    lines.append(f"- {emoji} **{cl_display}**: {count} test(s)")
                
                lines.extend(["", ""])
        
        # Build Information
        jenkins = self.raw_data.get('jenkins', {})
        if jenkins and not jenkins.get('error'):
            lines.extend([
                "---",
                "",
                "## Build Information",
                "",
                f"- **Job Name:** {jenkins.get('job_name', 'N/A')}",
                f"- **Build Number:** {jenkins.get('build_number', 'N/A')}",
                f"- **Build Result:** {jenkins.get('build_result', 'N/A')}",
            ])
            
            if jenkins.get('branch'):
                lines.append(f"- **Branch:** {jenkins.get('branch')}")
            if jenkins.get('commit_sha'):
                lines.append(f"- **Commit:** `{jenkins.get('commit_sha', '')[:8]}`")
            
            lines.extend(["", ""])
        
        # Per-Test Analysis (from AI)
        if self.analysis_results is not None:
            per_test = self.analysis_results.get('per_test_analysis', [])
            if per_test:
                lines.extend(self._format_per_test_section(per_test))
            else:
                # analysis-results.json exists but per_test_analysis is missing/empty.
                # This means field names don't match — fail instead of silently dropping all analysis.
                raise ValueError(
                    "analysis-results.json exists but 'per_test_analysis' is missing or empty.\n"
                    "The report would be generated without any test classifications.\n\n"
                    "Common mistake: using 'failed_tests' instead of 'per_test_analysis'.\n"
                    "See schema: src/schemas/analysis_results_schema.json\n"
                    f"Fix analysis-results.json and re-run: python -m src.scripts.report {self.run_dir}"
                )
        else:
            # No analysis-results.json file — show raw data as placeholder
            failed_tests = test_report.get('failed_tests', [])
            if failed_tests:
                lines.extend(self._format_per_test_from_raw(failed_tests))
        
        # Common Patterns
        if self.analysis_results:
            patterns = self.analysis_results.get('common_patterns', [])
            if patterns:
                lines.extend([
                    "---",
                    "",
                    "## Common Patterns Identified",
                    "",
                ])
                for pattern in patterns:
                    lines.append(f"- {pattern}")
                lines.extend(["", ""])
        
        # Priority Actions
        if self.analysis_results:
            priority_order = overall.get('priority_order', [])
            if priority_order:
                lines.extend([
                    "---",
                    "",
                    "## Recommended Actions (by Priority)",
                    "",
                ])
                
                for i, item in enumerate(priority_order, 1):
                    test_name = item.get('test', 'Unknown')
                    priority = item.get('priority', 'MEDIUM')
                    reason = item.get('reason', '')
                    classification = item.get('classification', 'UNKNOWN')
                    
                    emoji = self.PRIORITY_EMOJI.get(priority, '⚪')
                    lines.extend([
                        f"### {i}. {test_name}",
                        "",
                        f"**Priority:** {emoji} {priority}",
                        f"**Classification:** {classification.replace('_', ' ')}",
                        f"**Reason:** {reason}",
                        "",
                    ])
                
                lines.append("")
        
        # Environment Assessment
        env = self.raw_data.get('environment', {})
        if env and not env.get('error'):
            lines.extend([
                "---",
                "",
                "## Environment Status",
                "",
                f"- **Cluster Connected:** {'✅ Yes' if env.get('cluster_connectivity') else '❌ No'}",
                f"- **API Accessible:** {'✅ Yes' if env.get('api_accessibility') else '❌ No'}",
                f"- **Environment Score:** {env.get('environment_score', 0):.0%}",
                "",
            ])
            
            cluster_info = env.get('cluster_info', {})
            if cluster_info:
                lines.append(f"- **Cluster:** {cluster_info.get('name', 'N/A')}")
                lines.append(f"- **Platform:** {cluster_info.get('platform', 'N/A')}")
                lines.append("")
        
        # Footer
        lines.extend([
            "---",
            "",
            "*Report generated by Z-Stream Analysis Framework*",
            f"*Data gathered: {gathered_at}*",
        ])
        
        # Write report
        report_path = self.run_dir / 'Detailed-Analysis.md'
        report_path.write_text('\n'.join(lines))
        
        return report_path
    
    def _format_per_test_section(self, per_test: List[Dict[str, Any]]) -> List[str]:
        """Format the per-test analysis section from AI results."""
        lines = [
            "---",
            "",
            "## Individual Test Failures",
            "",
        ]
        
        for i, test in enumerate(per_test, 1):
            test_name = test.get('test_name', 'Unknown')
            test_file = test.get('test_file', test.get('class_name', ''))
            classification = test.get('classification', 'UNKNOWN')
            confidence = test.get('confidence', 0)
            reasoning = test.get('reasoning', {})
            error = test.get('error', {})
            recommended_fix = test.get('recommended_fix', {})
            
            emoji = self.CLASSIFICATION_EMOJI.get(classification, '⚪')
            
            lines.extend([
                f"### {i}. {test_name}",
                "",
                f"**File:** `{test_file}`",
                "",
                "| Property | Value |",
                "|----------|-------|",
                f"| **Classification** | {emoji} {classification.replace('_', ' ')} |",
                f"| **Confidence** | {confidence:.0%} |",
                "",
            ])
            
            # Error message
            error_msg = error.get('message', '')
            if error_msg:
                error_display = error_msg[:200].replace('\n', ' ').replace('|', '\\|')
                if len(error_msg) > 200:
                    error_display += "..."
                lines.extend([
                    "**Error:**",
                    "```",
                    error_display,
                    "```",
                    "",
                ])
            
            # Reasoning
            if isinstance(reasoning, dict):
                summary = reasoning.get('summary', '')
                evidence = reasoning.get('evidence', [])
                conclusion = reasoning.get('conclusion', '')
                
                if summary:
                    lines.append(f"**Analysis:** {summary}")
                    lines.append("")
                
                if evidence:
                    lines.append("**Evidence:**")
                    for ev in evidence[:5]:  # Limit to 5
                        lines.append(f"- {ev}")
                    lines.append("")
                
                if conclusion:
                    lines.append(f"**Conclusion:** {conclusion}")
                    lines.append("")
            elif isinstance(reasoning, str):
                lines.append(f"**Analysis:** {reasoning}")
                lines.append("")
            
            # Recommended fix
            if isinstance(recommended_fix, dict):
                action = recommended_fix.get('action', '')
                steps = recommended_fix.get('steps', [])
                owner = recommended_fix.get('owner', '')
                
                if action:
                    lines.append(f"**Recommended Fix:** {action}")
                    
                    if steps:
                        lines.append("")
                        for step in steps:
                            lines.append(f"  - {step}")
                    
                    if owner:
                        lines.append(f"  - **Owner:** {owner}")
                    
                    lines.append("")
            elif isinstance(recommended_fix, str) and recommended_fix:
                lines.append(f"**Recommended Fix:** {recommended_fix}")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return lines
    
    def _format_per_test_from_raw(self, failed_tests: List[Dict[str, Any]]) -> List[str]:
        """Format per-test section from raw data (when AI analysis not available)."""
        lines = [
            "---",
            "",
            "## Individual Test Failures",
            "",
            "> **Note:** AI analysis not yet performed. Showing preliminary classifications.",
            "",
        ]
        
        for i, test in enumerate(failed_tests, 1):
            test_name = test.get('test_name', 'Unknown')
            class_name = test.get('class_name', '')
            classification = test.get('preliminary_classification', 'UNKNOWN')
            confidence = test.get('preliminary_confidence', 0)
            reasoning = test.get('preliminary_reasoning', '')
            fix = test.get('preliminary_fix', '')
            error_msg = test.get('error_message', '')
            failure_type = test.get('failure_type', 'unknown')
            
            emoji = self.CLASSIFICATION_EMOJI.get(classification, '⚪')
            
            lines.extend([
                f"### {i}. {test_name}",
                "",
                f"**Class:** `{class_name}`",
                "",
                "| Property | Value |",
                "|----------|-------|",
                f"| **Classification** | {emoji} {classification.replace('_', ' ')} (preliminary) |",
                f"| **Failure Type** | `{failure_type}` |",
                f"| **Confidence** | {confidence:.0%} |",
                "",
            ])
            
            if error_msg:
                error_display = error_msg[:200].replace('\n', ' ')
                if len(error_msg) > 200:
                    error_display += "..."
                lines.extend([
                    "**Error:**",
                    "```",
                    error_display,
                    "```",
                    "",
                ])
            
            if reasoning:
                lines.append(f"**Preliminary Analysis:** {reasoning}")
                lines.append("")
            
            if fix:
                lines.append(f"**Suggested Fix:** {fix}")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return lines
    
    def format_json(self) -> Path:
        """Generate structured JSON breakdown for tooling."""
        
        # Build structured output
        output = {
            'metadata': {
                'jenkins_url': self.raw_data.get('metadata', {}).get('jenkins_url'),
                'generated_at': datetime.now().isoformat(),
                'data_source': 'analysis-results.json' if self.analysis_results else 'core-data.json'
            },
            'summary': {},
            'per_test_breakdown': [],
            'raw_test_data': []
        }
        
        # Add summary
        if self.analysis_results:
            output['summary'] = self.analysis_results.get('summary', {})
            output['per_test_breakdown'] = self.analysis_results.get('per_test_analysis', [])
        
        # Add raw test data
        test_report = self.raw_data.get('test_report', {})
        output['raw_test_data'] = test_report.get('failed_tests', [])
        
        # Summary from raw data
        output['test_summary'] = test_report.get('summary', {})
        
        # Save
        output_path = self.run_dir / 'per-test-breakdown.json'
        output_path.write_text(json.dumps(output, indent=2, default=str))
        
        return output_path
    
    def format_summary(self) -> Path:
        """Generate brief text summary."""
        lines = [
            "=" * 60,
            "PIPELINE FAILURE ANALYSIS SUMMARY",
            "=" * 60,
            "",
        ]
        
        # Jenkins info
        jenkins_url = self.raw_data.get('metadata', {}).get('jenkins_url', 'Unknown')
        lines.append(f"Jenkins URL: {jenkins_url}")
        
        # Build info
        jenkins = self.raw_data.get('jenkins', {})
        lines.append(f"Build: {jenkins.get('job_name', 'N/A')} #{jenkins.get('build_number', 'N/A')}")
        lines.append(f"Result: {jenkins.get('build_result', 'N/A')}")
        lines.append("")
        
        # Test summary
        test_report = self.raw_data.get('test_report', {})
        summary = test_report.get('summary', {})
        
        if summary.get('total_tests', 0) > 0:
            lines.extend([
                "TEST SUMMARY:",
                f"  Total: {summary.get('total_tests', 0)}",
                f"  Passed: {summary.get('passed_count', 0)}",
                f"  Failed: {summary.get('failed_count', 0)}",
                f"  Pass Rate: {summary.get('pass_rate', 0):.1f}%",
                "",
            ])
        
        # Classification breakdown
        if self.analysis_results:
            overall = self.analysis_results.get('summary', {})
            by_classification = overall.get('by_classification', {})
            
            if by_classification:
                lines.append("FAILURE BREAKDOWN:")
                for cl, count in sorted(by_classification.items(), key=lambda x: x[1], reverse=True):
                    cl_display = cl.replace('_', ' ')
                    lines.append(f"  [{cl_display}]: {count} test(s)")
                lines.append("")
            
            # Overall classification
            overall_cl = overall.get('overall_classification', 'UNKNOWN')
            overall_conf = overall.get('overall_confidence', 0)
            lines.extend([
                f"OVERALL: {overall_cl.replace('_', ' ')} ({overall_conf:.0%} confidence)",
                "",
            ])
        else:
            # From raw data
            failed_tests = test_report.get('failed_tests', [])
            if failed_tests:
                lines.append("FAILED TESTS:")
                for test in failed_tests[:10]:
                    name = test.get('test_name', 'Unknown')
                    cl = test.get('preliminary_classification', 'UNKNOWN')
                    lines.append(f"  - {name[:40]}... [{cl}]")
                
                if len(failed_tests) > 10:
                    lines.append(f"  ... and {len(failed_tests) - 10} more")
                lines.append("")
        
        # Actions
        if self.analysis_results:
            priority_order = self.analysis_results.get('summary', {}).get('priority_order', [])
            if priority_order:
                lines.extend([
                    "PRIORITY ACTIONS:",
                ])
                for i, item in enumerate(priority_order[:5], 1):
                    test = item.get('test', 'Unknown')
                    priority = item.get('priority', 'MEDIUM')
                    lines.append(f"  {i}. [{priority}] {test[:40]}...")
                lines.append("")
        
        lines.extend([
            "=" * 60,
            "See Detailed-Analysis.md for full report",
            "=" * 60,
        ])
        
        # Save
        summary_path = self.run_dir / 'SUMMARY.txt'
        summary_path.write_text('\n'.join(lines))
        
        return summary_path


def format_reports(run_dir: str, cleanup_repos: bool = False) -> Dict[str, str]:
    """
    Convenience function to format all reports.

    Args:
        run_dir: Path to run directory
        cleanup_repos: If True, delete repos/ directory after report generation

    Returns:
        Dictionary of report type to file path
    """
    formatter = ReportFormatter(Path(run_dir))
    reports = formatter.format_all()

    # Optional cleanup of repos to save disk space
    if cleanup_repos:
        repos_path = Path(run_dir) / 'repos'
        if repos_path.exists():
            shutil.rmtree(repos_path)
            print(f"Cleaned up repos directory to save disk space: {repos_path}")

    return reports


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Z-Stream Analysis - Report Generation Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script formats analysis results into readable reports.

Input Files (in run directory):
  core-data.json           Primary gathered data (or legacy raw-data.json)
  analysis-results.json    AI analysis output (optional)

Note: Auto-detects multi-file structure vs legacy format.

Output Files:
  Detailed-Analysis.md     Comprehensive markdown report
  per-test-breakdown.json  Structured data for tooling
  SUMMARY.txt              Brief text summary

Examples:
  python -m src.scripts.report ./runs/job_20260113_153000
  python -m src.scripts.report --run-dir ./runs/job_20260113_153000
  python -m src.scripts.report ./runs/job_20260113_153000 --keep-repos
        """
    )

    parser.add_argument('run_dir', nargs='?', help='Path to run directory')
    parser.add_argument('--run-dir', '-r', dest='run_dir_flag', help='Path to run directory (alternative)')
    parser.add_argument('--keep-repos', '-k', action='store_true',
                        help='Keep repos/ directory after report generation (default: cleanup to save disk space)')

    args = parser.parse_args()

    run_dir = args.run_dir or args.run_dir_flag

    if not run_dir:
        parser.print_help()
        print("\nError: Run directory is required", file=sys.stderr)
        sys.exit(1)

    run_path = Path(run_dir)
    if not run_path.exists():
        print(f"Error: Directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        print("\n" + "=" * 60)
        print("STAGE 3: REPORT GENERATION")
        print("=" * 60)

        print("\n[1/3] Loading analysis results...", flush=True)
        formatter = ReportFormatter(run_path)

        print("[2/3] Generating reports...", flush=True)
        reports = formatter.format_all()

        print("[3/3] Finalizing...", flush=True)

        print("\n" + "=" * 60)
        print("REPORTS GENERATED")
        print("=" * 60)

        for report_type, path in reports.items():
            print(f"  {report_type}: {path}")

        # Cleanup repos by default to save disk space (skip if --keep-repos)
        repos_path = run_path / 'repos'
        if repos_path.exists():
            if args.keep_repos:
                print(f"\nRepos preserved at: {repos_path}")
            else:
                shutil.rmtree(repos_path)
                print(f"\nCleaned up repos/ to save disk space (use --keep-repos to preserve)")

        print("\n" + "=" * 60 + "\n")

        sys.exit(0)

    except FileNotFoundError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

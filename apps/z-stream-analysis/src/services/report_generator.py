#!/usr/bin/env python3
"""
Report Generator Service
Generates comprehensive analysis reports in multiple formats (Markdown, JSON, HTML)
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class ReportGenerator:
    """
    Report Generator Service
    Generates detailed analysis reports from pipeline failure analysis results.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize Report Generator.
        
        Args:
            output_dir: Base output directory for reports
        """
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir) if output_dir else Path('./runs')
        
    def generate_all_reports(self, result: Dict[str, Any], jenkins_url: str, 
                            run_dir: Optional[Path] = None) -> Dict[str, str]:
        """
        Generate all report types and return paths to generated files.
        
        Args:
            result: Complete analysis result dictionary
            jenkins_url: Jenkins build URL that was analyzed
            run_dir: Directory to save reports (optional)
            
        Returns:
            Dictionary of report type to file path
        """
        if run_dir is None:
            run_dir = self._create_run_directory(jenkins_url)
        
        reports = {}
        
        # Generate Markdown report
        md_path = self.generate_markdown_report(result, jenkins_url, run_dir)
        reports['markdown'] = str(md_path)
        
        # Generate JSON reports
        json_paths = self.generate_json_reports(result, jenkins_url, run_dir)
        reports.update(json_paths)
        
        # Generate summary report
        summary_path = self.generate_summary_report(result, jenkins_url, run_dir)
        reports['summary'] = str(summary_path)
        
        self.logger.info(f"Generated {len(reports)} reports in {run_dir}")
        
        return reports
    
    def _create_run_directory(self, jenkins_url: str) -> Path:
        """Create a timestamped directory for this analysis run."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        job_name = "analysis"
        if '/job/' in jenkins_url:
            parts = jenkins_url.split('/job/')
            if len(parts) > 1:
                job_name = parts[-1].split('/')[0]
        
        run_dir = self.output_dir / f"{job_name}_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        
        return run_dir
    
    def generate_markdown_report(self, result: Dict[str, Any], jenkins_url: str,
                                 run_dir: Path) -> Path:
        """Generate the detailed Markdown analysis report."""
        
        classification = result.get('overall_classification', 'UNKNOWN')
        confidence = result.get('overall_confidence', 0.0)
        investigation = result.get('investigation_result', {})
        solution = result.get('solution_result', {})
        
        lines = [
            "# Pipeline Failure Analysis Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Jenkins URL:** {jenkins_url}",
            f"**Investigation ID:** {result.get('investigation_id', 'N/A')}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| **Classification** | {classification} |",
            f"| **Confidence** | {confidence:.1%} |",
            f"| **Analysis Time** | {result.get('total_analysis_time', 0):.2f}s |",
            "",
        ]
        
        # Add classification banner
        lines.extend([
            "### Classification",
            "",
        ])
        
        if 'PRODUCT' in classification:
            lines.append("🔴 **PRODUCT BUG** - Issue in the product under test")
        elif 'AUTOMATION' in classification:
            lines.append("🟡 **AUTOMATION BUG** - Issue in the test automation code")
        elif 'INFRASTRUCTURE' in classification:
            lines.append("🔵 **INFRASTRUCTURE** - Environment or infrastructure issue")
        elif 'NO_BUG' in classification or 'FLAKY' in classification:
            lines.append("🟢 **NO BUG / FLAKY** - Transient issue, no action needed")
        else:
            lines.append("⚪ **REQUIRES INVESTIGATION** - Manual analysis recommended")
        
        lines.append("")
        
        # Add classification reasoning
        bug_classification = solution.get('bug_classification', {})
        if bug_classification.get('reasoning'):
            lines.extend([
                "### Reasoning",
                "",
            ])
            for reason in bug_classification.get('reasoning', []):
                lines.append(f"- {reason}")
            lines.append("")
        
        # Add failure analysis section
        lines.extend([
            "---",
            "",
            "## Failure Analysis",
            "",
        ])
        
        jenkins_intel = investigation.get('jenkins_analysis', investigation.get('jenkins_intelligence', {}))
        
        if jenkins_intel:
            lines.extend([
                "### Jenkins Build Information",
                "",
            ])
            
            metadata = jenkins_intel.get('metadata', jenkins_intel)
            lines.append(f"- **Job Name:** {metadata.get('job_name', 'N/A')}")
            lines.append(f"- **Build Number:** {metadata.get('build_number', 'N/A')}")
            lines.append(f"- **Build Result:** {metadata.get('build_result', 'N/A')}")
            
            if metadata.get('branch'):
                lines.append(f"- **Branch:** {metadata.get('branch')}")
            if metadata.get('commit_sha'):
                lines.append(f"- **Commit:** `{metadata.get('commit_sha')[:8]}`")
            
            lines.append("")
            
            # Failure patterns
            failure_analysis = jenkins_intel.get('failure_analysis', {})
            patterns = failure_analysis.get('patterns', {})
            
            has_patterns = any(patterns.values())
            if has_patterns:
                lines.extend([
                    "### Detected Failure Patterns",
                    "",
                ])
                
                for pattern_type, matches in patterns.items():
                    if matches:
                        display_name = pattern_type.replace('_', ' ').title()
                        lines.append(f"- **{display_name}:** {len(matches)} occurrence(s)")
                
                lines.append("")
        
        # Environment assessment
        env_assessment = investigation.get('environment_assessment', investigation.get('environment_validation', {}))
        if env_assessment:
            lines.extend([
                "### Environment Assessment",
                "",
            ])
            
            cluster_info = env_assessment.get('cluster_info', {})
            if cluster_info:
                lines.append(f"- **Cluster:** {cluster_info.get('name', 'N/A')}")
                lines.append(f"- **Connected:** {'✅ Yes' if cluster_info.get('connected') else '❌ No'}")
                lines.append(f"- **Platform:** {cluster_info.get('platform', 'N/A')}")
            else:
                lines.append(f"- **Cluster Connectivity:** {'✅ Yes' if env_assessment.get('cluster_connectivity') else '❌ No'}")
            
            lines.append(f"- **API Accessible:** {'✅ Yes' if env_assessment.get('api_accessibility') else '❌ No'}")
            lines.append(f"- **Environment Score:** {env_assessment.get('environment_score', 0):.1%}")
            lines.append("")
        
        # Repository analysis
        repo_intel = investigation.get('repository_intelligence', investigation.get('repository_analysis', {}))
        if repo_intel and repo_intel.get('repository_cloned'):
            lines.extend([
                "### Repository Analysis",
                "",
            ])
            
            lines.append(f"- **Repository:** {repo_intel.get('repository_url', 'N/A')}")
            lines.append(f"- **Branch:** {repo_intel.get('branch', repo_intel.get('branch_analyzed', 'N/A'))}")
            
            test_files = repo_intel.get('test_files', repo_intel.get('test_files_found', []))
            if test_files:
                lines.append(f"- **Test Files Found:** {len(test_files)}")
            
            deps = repo_intel.get('dependency_analysis', {})
            if deps.get('framework'):
                lines.append(f"- **Test Framework:** {deps.get('framework')} {deps.get('version', '')}")
            
            lines.append("")
        
        # NEW: Per-Test Failure Breakdown
        test_report = jenkins_intel.get('test_report', {})
        if test_report and test_report.get('failed_tests'):
            lines.extend(self._generate_per_test_section(test_report))
        
        # Fix recommendations
        fix_recommendations = solution.get('fix_recommendations', [])
        if fix_recommendations:
            lines.extend([
                "---",
                "",
                "## Recommended Fixes",
                "",
            ])
            
            for i, fix in enumerate(fix_recommendations, 1):
                priority = fix.get('priority', 'MEDIUM')
                priority_emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(priority, '⚪')
                
                lines.append(f"### {i}. {fix.get('title', 'Untitled')} {priority_emoji}")
                lines.append("")
                lines.append(f"**Priority:** {priority}")
                lines.append(f"**Type:** {fix.get('type', 'N/A')}")
                lines.append(f"**Confidence:** {fix.get('confidence', 0):.0%}")
                lines.append("")
                lines.append(f"**Description:** {fix.get('description', 'No description')}")
                lines.append("")
                
                implementation = fix.get('implementation', {})
                if implementation:
                    if implementation.get('files'):
                        lines.append("**Files to modify:**")
                        lines.append("")
                        for file in implementation.get('files', []):
                            lines.append(f"- `{file}`")
                        lines.append("")
                    
                    if implementation.get('actions'):
                        lines.append("**Actions:**")
                        lines.append("")
                        for j, action in enumerate(implementation.get('actions', []), 1):
                            lines.append(f"{j}. {action}")
                        lines.append("")
        
        # Implementation guidance
        impl_guidance = solution.get('implementation_guidance', {})
        if impl_guidance:
            lines.extend([
                "---",
                "",
                "## Implementation Guidance",
                "",
            ])
            
            if impl_guidance.get('summary'):
                lines.append(f"**Summary:** {impl_guidance.get('summary')}")
                lines.append("")
            
            if impl_guidance.get('prerequisites'):
                lines.append("### Prerequisites")
                lines.append("")
                for prereq in impl_guidance.get('prerequisites', []):
                    lines.append(f"- {prereq}")
                lines.append("")
            
            if impl_guidance.get('validation_steps'):
                lines.append("### Validation Steps")
                lines.append("")
                for j, step in enumerate(impl_guidance.get('validation_steps', []), 1):
                    lines.append(f"{j}. {step}")
                lines.append("")
            
            if impl_guidance.get('rollback_plan'):
                lines.append("### Rollback Plan")
                lines.append("")
                for step in impl_guidance.get('rollback_plan', []):
                    lines.append(f"- {step}")
                lines.append("")
        
        # Evidence sources
        evidence_sources = result.get('evidence_sources', [])
        if evidence_sources:
            lines.extend([
                "---",
                "",
                "## Evidence Sources",
                "",
            ])
            for source in evidence_sources:
                lines.append(f"- {source}")
            lines.append("")
        
        # Claim validation
        claim_validation = solution.get('claim_validation', result.get('evidence_validation', {}))
        if claim_validation:
            lines.extend([
                "---",
                "",
                "## Evidence Validation",
                "",
            ])
            
            summary = claim_validation.get('summary', {})
            if summary:
                lines.append(f"- **Total Claims:** {summary.get('total_claims', 0)}")
                lines.append(f"- **Verified:** {summary.get('verified', 0)}")
                lines.append(f"- **Unverified:** {summary.get('unverified', 0)}")
                lines.append(f"- **Confidence:** {claim_validation.get('validation_confidence', 0):.1%}")
            lines.append("")
        
        # Footer
        lines.extend([
            "---",
            "",
            "*Report generated by Z-Stream Analysis Framework*",
            f"*Analysis ID: {result.get('investigation_id', 'N/A')}*",
        ])
        
        # Write the report
        report_path = run_dir / 'Detailed-Analysis.md'
        with open(report_path, 'w') as f:
            f.write('\n'.join(lines))
        
        self.logger.info(f"Generated Markdown report: {report_path}")
        return report_path
    
    def generate_json_reports(self, result: Dict[str, Any], jenkins_url: str,
                             run_dir: Path) -> Dict[str, str]:
        """Generate JSON reports for machine consumption."""
        reports = {}
        
        # Jenkins metadata
        jenkins_metadata = {
            'jenkins_url': jenkins_url,
            'analysis_timestamp': datetime.now().isoformat(),
            'build_info': result.get('investigation_result', {}).get('jenkins_analysis', 
                          result.get('investigation_result', {}).get('jenkins_intelligence', {}))
        }
        
        metadata_path = run_dir / 'jenkins-metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(jenkins_metadata, f, indent=2, default=str)
        reports['jenkins_metadata'] = str(metadata_path)
        
        # Analysis metadata
        analysis_metadata = {
            'investigation_id': result.get('investigation_id'),
            'overall_classification': result.get('overall_classification', 'UNKNOWN'),
            'overall_confidence': result.get('overall_confidence', 0.0),
            'total_analysis_time': result.get('total_analysis_time', 0.0),
            'investigation_confidence': result.get('investigation_result', {}).get('confidence_score', 0.0),
            'solution_confidence': result.get('solution_result', {}).get('confidence_score', 0.0),
            'evidence_sources': result.get('evidence_sources', []),
            'timestamp': datetime.now().isoformat()
        }
        
        analysis_path = run_dir / 'analysis-metadata.json'
        with open(analysis_path, 'w') as f:
            json.dump(analysis_metadata, f, indent=2, default=str)
        reports['analysis_metadata'] = str(analysis_path)
        
        # Full results
        full_results_path = run_dir / 'full-analysis-results.json'
        with open(full_results_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        reports['full_results'] = str(full_results_path)
        
        self.logger.info(f"Generated {len(reports)} JSON reports")
        return reports
    
    def generate_summary_report(self, result: Dict[str, Any], jenkins_url: str,
                               run_dir: Path) -> Path:
        """Generate a brief summary report."""
        
        classification = result.get('overall_classification', 'UNKNOWN')
        confidence = result.get('overall_confidence', 0.0)
        
        lines = [
            "=" * 60,
            "PIPELINE FAILURE ANALYSIS SUMMARY",
            "=" * 60,
            "",
            f"Jenkins URL: {jenkins_url}",
            f"Classification: {classification}",
            f"Confidence: {confidence:.1%}",
            f"Analysis Time: {result.get('total_analysis_time', 0):.2f}s",
            "",
        ]
        
        # Per-test failure summary
        investigation = result.get('investigation_result', {})
        jenkins_intel = investigation.get('jenkins_analysis', investigation.get('jenkins_intelligence', {}))
        test_report = jenkins_intel.get('test_report', {})
        
        if test_report and test_report.get('failed_tests'):
            failed_tests = test_report.get('failed_tests', [])
            total_tests = test_report.get('total_tests', 0)
            pass_rate = test_report.get('pass_rate', 0)
            
            lines.extend([
                "TEST SUMMARY:",
                f"  Total Tests: {total_tests}",
                f"  Failed: {len(failed_tests)}",
                f"  Pass Rate: {pass_rate:.1f}%",
                "",
                "FAILURE BREAKDOWN:",
            ])
            
            # Count by classification
            by_cl = {}
            for test in failed_tests:
                cl = test.get('classification', 'UNKNOWN')
                by_cl[cl] = by_cl.get(cl, 0) + 1
            
            for cl, count in sorted(by_cl.items(), key=lambda x: x[1], reverse=True):
                cl_display = cl.replace('_', ' ')
                lines.append(f"  [{cl_display}] {count} test(s)")
            
            lines.append("")
            
            # List first 5 failed tests
            lines.append("FAILED TESTS (first 5):")
            for test in failed_tests[:5]:
                test_name = test.get('test_name', 'Unknown')
                cl = test.get('classification', 'UNKNOWN')
                lines.append(f"  - {test_name[:50]}... [{cl}]")
            
            if len(failed_tests) > 5:
                lines.append(f"  ... and {len(failed_tests) - 5} more")
            
            lines.append("")
        
        # Top recommendation
        recommendations = result.get('solution_result', {}).get('fix_recommendations', [])
        if recommendations:
            top_rec = recommendations[0]
            lines.extend([
                "PRIMARY RECOMMENDATION:",
                f"  {top_rec.get('title', 'N/A')}",
                f"  Priority: {top_rec.get('priority', 'N/A')}",
                "",
            ])
        
        # Errors if any
        inv_errors = result.get('investigation_result', {}).get('errors', [])
        sol_errors = result.get('solution_result', {}).get('errors', [])
        all_errors = inv_errors + sol_errors
        
        if all_errors:
            lines.extend([
                "WARNINGS:",
            ])
            for error in all_errors[:3]:
                lines.append(f"  - {error}")
            lines.append("")
        
        lines.extend([
            "=" * 60,
            "See Detailed-Analysis.md for full report",
            "=" * 60,
        ])
        
        summary_path = run_dir / 'SUMMARY.txt'
        with open(summary_path, 'w') as f:
            f.write('\n'.join(lines))
        
        self.logger.info(f"Generated summary report: {summary_path}")
        return summary_path
    
    def _generate_per_test_section(self, test_report: Dict[str, Any]) -> List[str]:
        """Generate the per-test failure breakdown section."""
        lines = [
            "---",
            "",
            "## Individual Test Failures",
            "",
        ]
        
        # Summary table
        total = test_report.get('total_tests', 0)
        passed = test_report.get('passed_count', 0)
        failed = test_report.get('failed_count', 0)
        skipped = test_report.get('skipped_count', 0)
        pass_rate = test_report.get('pass_rate', 0)
        
        lines.extend([
            "### Test Suite Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| **Total Tests** | {total} |",
            f"| **Passed** | {passed} ✅ |",
            f"| **Failed** | {failed} ❌ |",
            f"| **Skipped** | {skipped} ⏭️ |",
            f"| **Pass Rate** | {pass_rate:.1f}% |",
            "",
        ])
        
        failed_tests = test_report.get('failed_tests', [])
        if not failed_tests:
            return lines
        
        # Group by classification
        by_classification = {}
        for test in failed_tests:
            cl = test.get('classification', 'UNKNOWN')
            if cl not in by_classification:
                by_classification[cl] = []
            by_classification[cl].append(test)
        
        # Classification summary
        lines.extend([
            "### Classification Breakdown",
            "",
        ])
        
        classification_emoji = {
            'PRODUCT_BUG': '🔴',
            'AUTOMATION_BUG': '🟡',
            'INFRASTRUCTURE': '🔵',
            'UNKNOWN': '⚪'
        }
        
        for cl, tests in sorted(by_classification.items(), key=lambda x: len(x[1]), reverse=True):
            emoji = classification_emoji.get(cl, '⚪')
            display_name = cl.replace('_', ' ')
            lines.append(f"- {emoji} **{display_name}**: {len(tests)} test(s)")
        
        lines.append("")
        
        # Detailed per-test breakdown
        lines.extend([
            "### Per-Test Analysis",
            "",
        ])
        
        for i, test in enumerate(failed_tests, 1):
            test_name = test.get('test_name', 'Unknown')
            classification = test.get('classification', 'UNKNOWN')
            failure_type = test.get('failure_type', 'unknown')
            confidence = test.get('classification_confidence', 0)
            reasoning = test.get('classification_reasoning', '')
            recommended_fix = test.get('recommended_fix', '')
            error_message = test.get('error_message', '')
            
            emoji = classification_emoji.get(classification, '⚪')
            
            lines.extend([
                f"#### {i}. {test_name}",
                "",
                f"| Property | Value |",
                f"|----------|-------|",
                f"| **Classification** | {emoji} {classification.replace('_', ' ')} |",
                f"| **Failure Type** | `{failure_type}` |",
                f"| **Confidence** | {confidence:.0%} |",
                "",
            ])
            
            if reasoning:
                lines.append(f"**Analysis:** {reasoning}")
                lines.append("")
            
            if error_message:
                # Truncate and escape for markdown
                error_display = error_message[:200].replace('\n', ' ').replace('|', '\\|')
                if len(error_message) > 200:
                    error_display += "..."
                lines.extend([
                    "**Error:**",
                    "```",
                    error_display,
                    "```",
                    "",
                ])
            
            if recommended_fix:
                lines.extend([
                    f"**Recommended Fix:** {recommended_fix}",
                    "",
                ])
            
            lines.append("---")
            lines.append("")
        
        return lines
    
    def print_console_summary(self, result: Dict[str, Any]):
        """Print a summary to the console."""
        classification = result.get('overall_classification', 'UNKNOWN')
        confidence = result.get('overall_confidence', 0.0)
        
        # Classification banner
        banner_width = 60
        
        if 'PRODUCT' in classification:
            color = '\033[91m'  # Red
            symbol = '🔴'
        elif 'AUTOMATION' in classification:
            color = '\033[93m'  # Yellow
            symbol = '🟡'
        elif 'INFRASTRUCTURE' in classification:
            color = '\033[94m'  # Blue
            symbol = '🔵'
        elif 'NO_BUG' in classification or 'FLAKY' in classification:
            color = '\033[92m'  # Green
            symbol = '🟢'
        else:
            color = '\033[0m'
            symbol = '⚪'
        
        reset = '\033[0m'
        
        print("\n" + "=" * banner_width)
        print(f"{color}{'ANALYSIS RESULT'.center(banner_width)}{reset}")
        print("=" * banner_width)
        print(f"\n{symbol} Classification: {color}{classification}{reset}")
        print(f"   Confidence: {confidence:.1%}")
        print(f"   Time: {result.get('total_analysis_time', 0):.2f}s")
        
        # NEW: Per-test summary if available
        investigation = result.get('investigation_result', {})
        jenkins_intel = investigation.get('jenkins_analysis', investigation.get('jenkins_intelligence', {}))
        test_report = jenkins_intel.get('test_report', {})
        
        if test_report and test_report.get('failed_tests'):
            failed_tests = test_report.get('failed_tests', [])
            print(f"\n   Test Failures: {len(failed_tests)}")
            
            # Count by classification
            by_cl = {}
            for test in failed_tests:
                cl = test.get('classification', 'UNKNOWN')
                by_cl[cl] = by_cl.get(cl, 0) + 1
            
            for cl, count in sorted(by_cl.items(), key=lambda x: x[1], reverse=True):
                cl_display = cl.replace('_', ' ')
                print(f"     - {cl_display}: {count}")
        
        print("\n" + "=" * banner_width + "\n")

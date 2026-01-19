#!/usr/bin/env python3
"""
Z-Stream Analysis - Main Entry Point
CLI tool for analyzing Jenkins pipeline failures using the 2-Agent Intelligence Framework.

Usage:
    python main.py <jenkins_url>
    python main.py --url <jenkins_url> [--output-dir <path>] [--verbose]
    
Examples:
    python main.py https://jenkins.example.com/job/pipeline/123/
    python main.py --url https://jenkins.example.com/job/pipeline/123/ --output-dir ./results
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.two_agent_intelligence_framework import TwoAgentIntelligenceFramework
from services.evidence_validation_engine import EvidenceValidationEngine
from services.report_generator import ReportGenerator


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)


def validate_jenkins_url(url: str) -> bool:
    """Validate that the provided URL looks like a Jenkins build URL."""
    if not url:
        return False
    
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        return False
    
    # Should contain 'job' in the path for Jenkins
    if '/job/' not in url:
        return False
    
    return True


def create_output_directory(output_dir: str, jenkins_url: str) -> Path:
    """Create timestamped output directory for analysis results."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Extract job name from URL for directory naming
    job_name = "analysis"
    if '/job/' in jenkins_url:
        parts = jenkins_url.split('/job/')
        if len(parts) > 1:
            job_name = parts[-1].split('/')[0]
    
    run_dir = Path(output_dir) / f"{job_name}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    return run_dir


def print_classification_banner(classification: str, confidence: float):
    """Print a clear classification banner to the terminal."""
    banner_width = 60
    
    # Determine banner style based on classification
    if 'PRODUCT' in classification.upper():
        color = '\033[91m'  # Red
        symbol = '🔴'
    elif 'AUTOMATION' in classification.upper():
        color = '\033[93m'  # Yellow
        symbol = '🟡'
    elif 'NO BUGS' in classification.upper():
        color = '\033[92m'  # Green
        symbol = '🟢'
    else:
        color = '\033[94m'  # Blue
        symbol = '🔵'
    
    reset = '\033[0m'
    
    print("\n" + "=" * banner_width)
    print(f"{color}{'ANALYSIS RESULT'.center(banner_width)}{reset}")
    print("=" * banner_width)
    print(f"\n{symbol} Classification: {color}{classification}{reset}")
    print(f"   Confidence: {confidence:.1%}")
    print("\n" + "=" * banner_width + "\n")


def run_analysis(jenkins_url: str, output_dir: str, logger: logging.Logger) -> dict:
    """
    Run the complete 2-agent analysis pipeline.

    Args:
        jenkins_url: Jenkins build URL to analyze
        output_dir: Directory to save results
        logger: Logger instance

    Returns:
        dict: Complete analysis results
    """
    logger.info(f"Starting analysis for: {jenkins_url}")

    # Create output directory
    run_dir = create_output_directory(output_dir, jenkins_url)
    logger.info(f"Results will be saved to: {run_dir}")

    # Initialize the framework
    framework = TwoAgentIntelligenceFramework()

    # Run the 2-agent analysis
    logger.info("Phase 1: Investigation Intelligence - Gathering evidence...")
    logger.info("Phase 2: Solution Intelligence - Analyzing and generating solutions...")

    analysis_result = framework.analyze_pipeline_failure(jenkins_url)

    # Convert to dictionary for output
    result_dict = framework.to_dict(analysis_result)

    # Run evidence validation on key claims
    logger.info("Running evidence validation...")
    validation_engine = EvidenceValidationEngine()

    # Extract claims from the solution result for validation
    claims = []
    bug_classification = result_dict.get('solution_result', {}).get('bug_classification', {})
    for reason in bug_classification.get('reasoning', []):
        claims.append(reason)

    if claims:
        validation_result = validation_engine.validate_technical_claims(
            claims,
            result_dict.get('investigation_result', {})
        )
        result_dict['evidence_validation'] = validation_engine.to_dict(validation_result)
    
    # Save results to files
    save_results(run_dir, result_dict, jenkins_url, logger)
    
    return result_dict


def save_results(run_dir: Path, result_dict: dict, jenkins_url: str, logger: logging.Logger):
    """Save analysis results to output files using the ReportGenerator."""
    
    # Use the report generator
    report_generator = ReportGenerator()
    reports = report_generator.generate_all_reports(result_dict, jenkins_url, run_dir)
    
    for report_type, path in reports.items():
        logger.info(f"Saved {report_type}: {path}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Z-Stream Analysis - Jenkins Pipeline Failure Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
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
        '--json',
        action='store_true',
        help='Output results as JSON to stdout'
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
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    try:
        # Run the analysis
        result = run_analysis(jenkins_url, args.output_dir, logger)
        
        # Print classification banner
        classification = result.get('overall_classification', 'UNKNOWN')
        confidence = result.get('overall_confidence', 0.0)
        print_classification_banner(classification, confidence)
        
        # Output JSON if requested
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        
        # Print summary
        print(f"Analysis complete. Results saved to: {args.output_dir}")
        print(f"\nKey files generated:")
        print(f"  - Detailed-Analysis.md (Human-readable report)")
        print(f"  - jenkins-metadata.json (Build information)")
        print(f"  - analysis-metadata.json (Analysis metrics)")
        print(f"  - full-analysis-results.json (Complete data)")
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\nAnalysis cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=args.verbose)
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

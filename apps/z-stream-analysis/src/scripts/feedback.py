#!/usr/bin/env python3
"""
Feedback CLI

Command-line interface for rating z-stream analysis classifications.
Testers use this to mark classifications as correct or incorrect,
building a dataset for accuracy tracking over time.

Usage:
    # Mark a test classification as correct
    python -m src.scripts.feedback runs/<dir> --test "test_name" --correct

    # Mark as incorrect with correction
    python -m src.scripts.feedback runs/<dir> --test "test_name" --incorrect \
        --should-be PRODUCT_BUG --note "search-api was down"

    # Set overall run accuracy
    python -m src.scripts.feedback runs/<dir> --overall-accuracy 0.85

    # Show accuracy stats across all runs
    python -m src.scripts.feedback --stats

    # Show misclassification patterns
    python -m src.scripts.feedback --patterns
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directories to path for imports
script_dir = Path(__file__).parent
src_dir = script_dir.parent
app_dir = src_dir.parent
sys.path.insert(0, str(app_dir))

from src.services.feedback_service import FeedbackService


VALID_CLASSIFICATIONS = [
    'PRODUCT_BUG', 'AUTOMATION_BUG', 'INFRASTRUCTURE',
    'MIXED', 'UNKNOWN', 'NO_BUG', 'FLAKY',
]


def main():
    parser = argparse.ArgumentParser(
        description='Z-Stream Analysis - Classification Feedback',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mark test as correctly classified
  python -m src.scripts.feedback runs/job_20260113_153000 --test "test_policy_create" --correct

  # Mark test as incorrectly classified
  python -m src.scripts.feedback runs/job_20260113_153000 --test "test_search" --incorrect \\
      --should-be PRODUCT_BUG --note "search-api pod was crashing"

  # Set overall accuracy for a run
  python -m src.scripts.feedback runs/job_20260113_153000 --overall-accuracy 0.85

  # View accuracy stats across all runs
  python -m src.scripts.feedback --stats

  # View misclassification patterns
  python -m src.scripts.feedback --patterns
        """
    )

    parser.add_argument('run_dir', nargs='?', help='Path to run directory')
    parser.add_argument('--test', '-t', help='Test name to rate')
    parser.add_argument('--correct', action='store_true',
                        help='Mark classification as correct')
    parser.add_argument('--incorrect', action='store_true',
                        help='Mark classification as incorrect')
    parser.add_argument('--should-be', '-s', choices=VALID_CLASSIFICATIONS,
                        help='What the classification should have been')
    parser.add_argument('--note', '-n', help='Feedback note')
    parser.add_argument('--by', help='Submitter name')
    parser.add_argument('--overall-accuracy', type=float,
                        help='Set overall accuracy for the run (0.0-1.0)')
    parser.add_argument('--stats', action='store_true',
                        help='Show accuracy stats across all runs')
    parser.add_argument('--patterns', action='store_true',
                        help='Show misclassification patterns')
    parser.add_argument('--runs-dir', default='./runs',
                        help='Base runs directory (default: ./runs)')

    args = parser.parse_args()

    service = FeedbackService(runs_dir=args.runs_dir)

    # Stats mode
    if args.stats:
        stats = service.get_accuracy_stats()
        print("\n" + "=" * 50)
        print("CLASSIFICATION ACCURACY STATS")
        print("=" * 50)
        print(f"Total runs rated:  {stats['total_runs']}")
        print(f"Total tests rated: {stats['total_tests_rated']}")
        if stats['overall_accuracy'] is not None:
            print(f"Overall accuracy:  {stats['overall_accuracy']:.1%}")
            print(f"  Correct:   {stats['total_correct']}")
            print(f"  Incorrect: {stats['total_incorrect']}")
        else:
            print("Overall accuracy:  No data")

        if stats.get('per_run_accuracies'):
            print("\nPer-run breakdown:")
            for run_id, accuracy in stats['per_run_accuracies'].items():
                acc_str = f"{accuracy:.1%}" if accuracy is not None else "N/A"
                print(f"  {run_id}: {acc_str}")
        print("=" * 50 + "\n")
        return

    # Patterns mode
    if args.patterns:
        patterns = service.get_misclassification_patterns()
        print("\n" + "=" * 50)
        print("MISCLASSIFICATION PATTERNS")
        print("=" * 50)
        if patterns:
            for pattern, count in patterns.items():
                print(f"  {pattern}: {count} time(s)")
        else:
            print("  No misclassification data yet")
        print("=" * 50 + "\n")
        return

    # Feedback mode requires run_dir
    if not args.run_dir:
        parser.print_help()
        print("\nError: Run directory required for feedback submission",
              file=sys.stderr)
        sys.exit(1)

    run_dir = args.run_dir

    # Overall accuracy
    if args.overall_accuracy is not None:
        if not 0.0 <= args.overall_accuracy <= 1.0:
            print("Error: --overall-accuracy must be between 0.0 and 1.0",
                  file=sys.stderr)
            sys.exit(1)

        run_path = service._resolve_run_dir(run_dir)
        feedback = service._load_run_feedback(run_path)
        if feedback is None:
            from src.services.feedback_service import RunFeedback
            feedback = RunFeedback(run_id=run_dir)
        feedback.overall_accuracy = args.overall_accuracy
        service._save_run_feedback(run_path, feedback)
        service._update_index(run_dir, feedback)

        print(f"Overall accuracy set to {args.overall_accuracy:.1%} for {run_dir}")
        return

    # Single test feedback
    if not args.test:
        parser.print_help()
        print("\nError: --test required for feedback submission",
              file=sys.stderr)
        sys.exit(1)

    if not args.correct and not args.incorrect:
        parser.print_help()
        print("\nError: Must specify --correct or --incorrect",
              file=sys.stderr)
        sys.exit(1)

    if args.incorrect and not args.should_be:
        print("Error: --should-be required when marking as --incorrect",
              file=sys.stderr)
        sys.exit(1)

    is_correct = args.correct
    result = service.submit_feedback(
        run_id=run_dir,
        test_name=args.test,
        is_correct=is_correct,
        correct_classification=args.should_be if args.incorrect else None,
        note=args.note,
        submitted_by=args.by,
    )

    if is_correct:
        print(f"Marked '{args.test}' as CORRECT ({result.original_classification})")
    else:
        print(f"Marked '{args.test}' as INCORRECT: "
              f"{result.original_classification} -> {args.should_be}")
    if args.note:
        print(f"  Note: {args.note}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Feedback Service

Collects tester feedback on classification accuracy.
Stores per-run feedback and maintains a global index for accuracy tracking.

Storage:
- Per-run: <run_dir>/feedback.json
- Global index: runs/feedback-index.json
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class ClassificationFeedback:
    """Feedback on a single test classification."""
    test_name: str
    run_id: str
    original_classification: str
    correct_classification: Optional[str] = None
    is_correct: bool = True
    feedback_note: Optional[str] = None
    submitted_by: Optional[str] = None
    submitted_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RunFeedback:
    """Aggregate feedback for an entire run."""
    run_id: str
    test_feedbacks: List[ClassificationFeedback] = field(default_factory=list)
    overall_accuracy: Optional[float] = None
    general_notes: Optional[str] = None
    submitted_at: str = field(default_factory=lambda: datetime.now().isoformat())


class FeedbackService:
    """
    Manages classification feedback collection and accuracy tracking.

    Usage:
        service = FeedbackService(runs_dir='./runs')
        service.submit_feedback('run_123', 'test_name', is_correct=False,
                                correct_classification='PRODUCT_BUG',
                                note='search-api was down')
        stats = service.get_accuracy_stats()
    """

    def __init__(self, runs_dir: str = './runs'):
        self.runs_dir = Path(runs_dir)
        self.logger = logging.getLogger(__name__)
        self.index_path = self.runs_dir / 'feedback-index.json'

    def _load_run_feedback(self, run_dir: Path) -> Optional[RunFeedback]:
        """Load existing feedback for a run."""
        feedback_path = run_dir / 'feedback.json'
        if not feedback_path.exists():
            return None

        try:
            data = json.loads(feedback_path.read_text())
            feedbacks = []
            for tf in data.get('test_feedbacks', []):
                feedbacks.append(ClassificationFeedback(**tf))
            return RunFeedback(
                run_id=data.get('run_id', ''),
                test_feedbacks=feedbacks,
                overall_accuracy=data.get('overall_accuracy'),
                general_notes=data.get('general_notes'),
                submitted_at=data.get('submitted_at', ''),
            )
        except Exception as e:
            self.logger.warning(f"Failed to load feedback from {feedback_path}: {e}")
            return None

    def _save_run_feedback(self, run_dir: Path, feedback: RunFeedback):
        """Save feedback to the run directory."""
        feedback_path = run_dir / 'feedback.json'
        feedback_path.write_text(
            json.dumps(asdict(feedback), indent=2, default=str)
        )

    def _load_index(self) -> Dict[str, Any]:
        """Load the global feedback index."""
        if not self.index_path.exists():
            return {'runs': {}, 'updated_at': None}
        try:
            return json.loads(self.index_path.read_text())
        except Exception:
            return {'runs': {}, 'updated_at': None}

    def _save_index(self, index: Dict[str, Any]):
        """Save the global feedback index."""
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        index['updated_at'] = datetime.now().isoformat()
        self.index_path.write_text(
            json.dumps(index, indent=2, default=str)
        )

    def _resolve_run_dir(self, run_id: str) -> Path:
        """Resolve run_id to a directory path."""
        run_path = Path(run_id)
        if run_path.is_absolute() and run_path.exists():
            return run_path
        # Try under runs_dir
        candidate = self.runs_dir / run_id
        if candidate.exists():
            return candidate
        # Try as-is (relative path)
        if run_path.exists():
            return run_path
        return candidate  # Return even if doesn't exist

    def _get_original_classification(
        self, run_dir: Path, test_name: str
    ) -> str:
        """Get original classification from analysis-results.json."""
        results_path = run_dir / 'analysis-results.json'
        if not results_path.exists():
            return 'UNKNOWN'
        try:
            data = json.loads(results_path.read_text())
            for test in data.get('per_test_analysis', []):
                if test.get('test_name') == test_name:
                    return test.get('classification', 'UNKNOWN')
        except Exception:
            pass
        return 'UNKNOWN'

    def submit_feedback(
        self,
        run_id: str,
        test_name: str,
        is_correct: bool,
        correct_classification: Optional[str] = None,
        note: Optional[str] = None,
        submitted_by: Optional[str] = None,
    ) -> ClassificationFeedback:
        """
        Submit feedback for a single test classification.

        Args:
            run_id: Run directory name or path
            test_name: Name of the test
            is_correct: Whether the classification was correct
            correct_classification: What it should have been (if incorrect)
            note: Optional feedback note
            submitted_by: Optional submitter identifier

        Returns:
            The created ClassificationFeedback
        """
        run_dir = self._resolve_run_dir(run_id)
        original = self._get_original_classification(run_dir, test_name)

        feedback_item = ClassificationFeedback(
            test_name=test_name,
            run_id=run_id,
            original_classification=original,
            correct_classification=correct_classification,
            is_correct=is_correct,
            feedback_note=note,
            submitted_by=submitted_by,
        )

        # Load or create run feedback
        run_feedback = self._load_run_feedback(run_dir)
        if run_feedback is None:
            run_feedback = RunFeedback(run_id=run_id)

        # Update existing or append
        updated = False
        for i, existing in enumerate(run_feedback.test_feedbacks):
            if existing.test_name == test_name:
                run_feedback.test_feedbacks[i] = feedback_item
                updated = True
                break
        if not updated:
            run_feedback.test_feedbacks.append(feedback_item)

        # Save
        self._save_run_feedback(run_dir, run_feedback)
        self._update_index(run_id, run_feedback)

        self.logger.info(
            f"Feedback submitted for '{test_name}' in {run_id}: "
            f"{'correct' if is_correct else f'incorrect -> {correct_classification}'}"
        )

        return feedback_item

    def submit_run_feedback(
        self,
        run_id: str,
        feedbacks: List[Dict[str, Any]],
        overall_accuracy: Optional[float] = None,
        general_notes: Optional[str] = None,
    ) -> RunFeedback:
        """
        Submit batch feedback for a run.

        Args:
            run_id: Run directory name or path
            feedbacks: List of dicts with test_name, is_correct, etc.
            overall_accuracy: Optional overall accuracy score
            general_notes: Optional general notes
        """
        run_dir = self._resolve_run_dir(run_id)

        items = []
        for fb in feedbacks:
            test_name = fb['test_name']
            original = self._get_original_classification(run_dir, test_name)
            items.append(ClassificationFeedback(
                test_name=test_name,
                run_id=run_id,
                original_classification=original,
                correct_classification=fb.get('correct_classification'),
                is_correct=fb.get('is_correct', True),
                feedback_note=fb.get('note'),
                submitted_by=fb.get('submitted_by'),
            ))

        run_feedback = RunFeedback(
            run_id=run_id,
            test_feedbacks=items,
            overall_accuracy=overall_accuracy,
            general_notes=general_notes,
        )

        self._save_run_feedback(run_dir, run_feedback)
        self._update_index(run_id, run_feedback)

        return run_feedback

    def _update_index(self, run_id: str, run_feedback: RunFeedback):
        """Update the global feedback index."""
        index = self._load_index()

        total = len(run_feedback.test_feedbacks)
        correct = sum(1 for f in run_feedback.test_feedbacks if f.is_correct)
        accuracy = correct / total if total > 0 else None

        index['runs'][run_id] = {
            'total_feedbacks': total,
            'correct_count': correct,
            'incorrect_count': total - correct,
            'accuracy': accuracy,
            'overall_accuracy': run_feedback.overall_accuracy,
            'submitted_at': run_feedback.submitted_at,
        }

        self._save_index(index)

    def get_accuracy_stats(self) -> Dict[str, Any]:
        """
        Get aggregate accuracy statistics across all runs.

        Returns:
            Dict with total_runs, total_tests, overall_accuracy,
            per_run_accuracies, and most common misclassifications.
        """
        index = self._load_index()
        runs = index.get('runs', {})

        if not runs:
            return {
                'total_runs': 0,
                'total_tests_rated': 0,
                'overall_accuracy': None,
                'per_run_accuracies': {},
            }

        total_correct = 0
        total_tests = 0

        for run_id, stats in runs.items():
            total_correct += stats.get('correct_count', 0)
            total_tests += stats.get('total_feedbacks', 0)

        overall_accuracy = total_correct / total_tests if total_tests > 0 else None

        return {
            'total_runs': len(runs),
            'total_tests_rated': total_tests,
            'total_correct': total_correct,
            'total_incorrect': total_tests - total_correct,
            'overall_accuracy': overall_accuracy,
            'per_run_accuracies': {
                run_id: stats.get('accuracy')
                for run_id, stats in runs.items()
            },
        }

    def get_misclassification_patterns(self) -> Dict[str, int]:
        """
        Get common from->to misclassification patterns.

        Returns:
            Dict mapping "FROM -> TO" to count.
        """
        patterns: Dict[str, int] = {}

        # Scan all run directories for feedback
        if not self.runs_dir.exists():
            return patterns

        for run_dir in self.runs_dir.iterdir():
            if not run_dir.is_dir():
                continue
            feedback = self._load_run_feedback(run_dir)
            if feedback is None:
                continue

            for tf in feedback.test_feedbacks:
                if not tf.is_correct and tf.correct_classification:
                    key = f"{tf.original_classification} -> {tf.correct_classification}"
                    patterns[key] = patterns.get(key, 0) + 1

        # Sort by frequency
        return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True))

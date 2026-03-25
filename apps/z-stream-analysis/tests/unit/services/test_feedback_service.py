"""
Unit tests for FeedbackService.

Tests feedback submission, index management, accuracy stats,
and misclassification pattern detection.
"""

import json
import pytest
from pathlib import Path

from src.services.feedback_service import (
    FeedbackService,
    ClassificationFeedback,
    RunFeedback,
)


@pytest.fixture
def tmp_runs(tmp_path):
    """Create a temporary runs directory with a sample run."""
    runs_dir = tmp_path / 'runs'
    runs_dir.mkdir()

    # Create a sample run with analysis results
    run_dir = runs_dir / 'job_20260113_153000'
    run_dir.mkdir()

    analysis_results = {
        'per_test_analysis': [
            {
                'test_name': 'test_policy_create',
                'classification': 'AUTOMATION_BUG',
                'confidence': 0.85,
                'evidence_sources': [
                    {'source': 'console_search', 'finding': 'not found'},
                    {'source': 'timeline', 'finding': 'removed'},
                ],
            },
            {
                'test_name': 'test_search_query',
                'classification': 'AUTOMATION_BUG',
                'confidence': 0.80,
                'evidence_sources': [
                    {'source': 'console_search', 'finding': 'not found'},
                    {'source': 'error', 'finding': 'element not found'},
                ],
            },
            {
                'test_name': 'test_cluster_create',
                'classification': 'INFRASTRUCTURE',
                'confidence': 0.90,
                'evidence_sources': [
                    {'source': 'env', 'finding': 'timeout'},
                    {'source': 'console', 'finding': 'timeout'},
                ],
            },
        ],
        'summary': {
            'by_classification': {
                'AUTOMATION_BUG': 2,
                'INFRASTRUCTURE': 1,
            }
        },
        'investigation_phases_completed': ['A', 'B', 'C', 'D', 'E'],
    }

    (run_dir / 'analysis-results.json').write_text(
        json.dumps(analysis_results, indent=2)
    )

    return runs_dir


class TestSubmitFeedback:
    """Test single test feedback submission."""

    def test_submit_correct_feedback(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        result = service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_cluster_create',
            is_correct=True,
        )

        assert result.test_name == 'test_cluster_create'
        assert result.is_correct is True
        assert result.original_classification == 'INFRASTRUCTURE'

        # Check file was created
        feedback_path = tmp_runs / 'job_20260113_153000' / 'feedback.json'
        assert feedback_path.exists()

    def test_submit_incorrect_feedback(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        result = service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_search_query',
            is_correct=False,
            correct_classification='PRODUCT_BUG',
            note='search-api was down',
        )

        assert result.is_correct is False
        assert result.original_classification == 'AUTOMATION_BUG'
        assert result.correct_classification == 'PRODUCT_BUG'
        assert result.feedback_note == 'search-api was down'

    def test_submit_updates_existing(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        # Submit first
        service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_search_query',
            is_correct=True,
        )

        # Update
        service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_search_query',
            is_correct=False,
            correct_classification='PRODUCT_BUG',
        )

        # Load and verify only one entry
        feedback_path = tmp_runs / 'job_20260113_153000' / 'feedback.json'
        data = json.loads(feedback_path.read_text())
        search_feedbacks = [
            f for f in data['test_feedbacks']
            if f['test_name'] == 'test_search_query'
        ]
        assert len(search_feedbacks) == 1
        assert search_feedbacks[0]['is_correct'] is False

    def test_submit_with_submitter(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        result = service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_cluster_create',
            is_correct=True,
            submitted_by='vincent',
        )

        assert result.submitted_by == 'vincent'


class TestSubmitRunFeedback:
    """Test batch feedback submission."""

    def test_submit_batch(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        feedbacks = [
            {'test_name': 'test_policy_create', 'is_correct': True},
            {
                'test_name': 'test_search_query',
                'is_correct': False,
                'correct_classification': 'PRODUCT_BUG',
                'note': 'backend crash',
            },
            {'test_name': 'test_cluster_create', 'is_correct': True},
        ]

        result = service.submit_run_feedback(
            run_id='job_20260113_153000',
            feedbacks=feedbacks,
            overall_accuracy=0.67,
        )

        assert len(result.test_feedbacks) == 3
        assert result.overall_accuracy == 0.67

    def test_batch_with_general_notes(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        result = service.submit_run_feedback(
            run_id='job_20260113_153000',
            feedbacks=[
                {'test_name': 'test_policy_create', 'is_correct': True},
            ],
            general_notes='Overall analysis was good but missed backend issues',
        )

        assert result.general_notes is not None


class TestAccuracyStats:
    """Test accuracy statistics."""

    def test_empty_stats(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))
        stats = service.get_accuracy_stats()

        assert stats['total_runs'] == 0
        assert stats['total_tests_rated'] == 0
        assert stats['overall_accuracy'] is None

    def test_stats_after_feedback(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        # Submit mixed feedback
        service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_policy_create',
            is_correct=True,
        )
        service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_search_query',
            is_correct=False,
            correct_classification='PRODUCT_BUG',
        )

        stats = service.get_accuracy_stats()

        assert stats['total_runs'] == 1
        assert stats['total_tests_rated'] == 2
        assert stats['total_correct'] == 1
        assert stats['total_incorrect'] == 1
        assert stats['overall_accuracy'] == 0.5

    def test_stats_across_runs(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        # Create second run
        run2 = tmp_runs / 'job_20260114_120000'
        run2.mkdir()
        analysis = {
            'per_test_analysis': [
                {
                    'test_name': 'test_a',
                    'classification': 'PRODUCT_BUG',
                    'confidence': 0.9,
                    'evidence_sources': [
                        {'source': 'a', 'finding': 'b'},
                        {'source': 'c', 'finding': 'd'},
                    ],
                },
            ],
            'summary': {'by_classification': {'PRODUCT_BUG': 1}},
            'investigation_phases_completed': ['A', 'B', 'C', 'D', 'E'],
        }
        (run2 / 'analysis-results.json').write_text(json.dumps(analysis))

        # Feedback for run 1
        service.submit_feedback('job_20260113_153000', 'test_policy_create', True)

        # Feedback for run 2
        service.submit_feedback('job_20260114_120000', 'test_a', True)

        stats = service.get_accuracy_stats()

        assert stats['total_runs'] == 2
        assert stats['total_tests_rated'] == 2
        assert stats['overall_accuracy'] == 1.0


class TestMisclassificationPatterns:
    """Test misclassification pattern detection."""

    def test_no_patterns(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))
        patterns = service.get_misclassification_patterns()
        assert len(patterns) == 0

    def test_detect_patterns(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        # Submit incorrect feedback
        service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_search_query',
            is_correct=False,
            correct_classification='PRODUCT_BUG',
        )
        service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_policy_create',
            is_correct=False,
            correct_classification='PRODUCT_BUG',
        )

        patterns = service.get_misclassification_patterns()

        assert 'AUTOMATION_BUG -> PRODUCT_BUG' in patterns
        assert patterns['AUTOMATION_BUG -> PRODUCT_BUG'] == 2


class TestIndexManagement:
    """Test the global feedback index."""

    def test_index_created_on_first_feedback(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        service.submit_feedback(
            run_id='job_20260113_153000',
            test_name='test_policy_create',
            is_correct=True,
        )

        index_path = tmp_runs / 'feedback-index.json'
        assert index_path.exists()

        index = json.loads(index_path.read_text())
        assert 'job_20260113_153000' in index['runs']
        assert index['updated_at'] is not None

    def test_index_accuracy_calculation(self, tmp_runs):
        service = FeedbackService(runs_dir=str(tmp_runs))

        service.submit_feedback('job_20260113_153000', 'test_policy_create', True)
        service.submit_feedback('job_20260113_153000', 'test_search_query', False,
                                correct_classification='PRODUCT_BUG')
        service.submit_feedback('job_20260113_153000', 'test_cluster_create', True)

        index = json.loads((tmp_runs / 'feedback-index.json').read_text())
        run_stats = index['runs']['job_20260113_153000']

        assert run_stats['total_feedbacks'] == 3
        assert run_stats['correct_count'] == 2
        assert run_stats['incorrect_count'] == 1
        assert abs(run_stats['accuracy'] - 0.6667) < 0.01

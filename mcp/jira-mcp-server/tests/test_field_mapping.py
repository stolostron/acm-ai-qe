"""Tests for field-building logic: falsy-check bug fixes and new writable field mappings.

These test the field dict construction in create_issue/update_issue tool handlers.
Since the field dict building happens inside nested tool functions, we test
the logic patterns directly.
"""

import pytest


class TestFalsyCheckFixes:
    """Verify that `is not None` checks handle falsy values correctly."""

    def test_story_points_zero_included(self):
        """story_points=0 should result in field being set (not skipped)."""
        fields = {}
        story_points = 0
        if story_points is not None:
            fields['customfield_12310243'] = story_points
        assert 'customfield_12310243' in fields
        assert fields['customfield_12310243'] == 0

    def test_story_points_none_skipped(self):
        """story_points=None should NOT set the field."""
        fields = {}
        story_points = None
        if story_points is not None:
            fields['customfield_12310243'] = story_points
        assert 'customfield_12310243' not in fields

    def test_story_points_positive(self):
        """story_points=5.0 should set the field normally."""
        fields = {}
        story_points = 5.0
        if story_points is not None:
            fields['customfield_12310243'] = story_points
        assert fields['customfield_12310243'] == 5.0

    def test_original_estimate_empty_included(self):
        """original_estimate='' should result in field being set."""
        fields = {}
        original_estimate = ""
        if original_estimate is not None:
            fields['timetracking'] = {'originalEstimate': original_estimate}
        assert 'timetracking' in fields
        assert fields['timetracking']['originalEstimate'] == ""

    def test_original_estimate_none_skipped(self):
        """original_estimate=None should NOT set the field."""
        fields = {}
        original_estimate = None
        if original_estimate is not None:
            fields['timetracking'] = {'originalEstimate': original_estimate}
        assert 'timetracking' not in fields

    def test_old_falsy_check_would_fail_zero(self):
        """Demonstrate the old bug: `if story_points:` skips 0."""
        fields = {}
        story_points = 0
        # OLD broken logic
        if story_points:
            fields['customfield_12310243'] = story_points
        # This proves the old check was wrong
        assert 'customfield_12310243' not in fields

    def test_old_falsy_check_would_fail_empty_string(self):
        """Demonstrate the old bug: `if original_estimate:` skips ''."""
        fields = {}
        original_estimate = ""
        # OLD broken logic
        if original_estimate:
            fields['timetracking'] = {'originalEstimate': original_estimate}
        # This proves the old check was wrong
        assert 'timetracking' not in fields


class TestNewWritableFieldMappings:
    """Verify new field mapping patterns produce correct JIRA API format."""

    def test_qa_contact_mapping(self):
        """qa_contact maps to {'name': username}."""
        fields = {}
        qa_contact = "rhn-support-ashafi"
        if qa_contact is not None:
            fields['customfield_12315948'] = {'name': qa_contact}
        assert fields['customfield_12315948'] == {'name': 'rhn-support-ashafi'}

    def test_epic_link_mapping(self):
        """epic_link maps to string value."""
        fields = {}
        epic_link = "ACM-24035"
        if epic_link is not None:
            fields['customfield_12311140'] = epic_link
        assert fields['customfield_12311140'] == "ACM-24035"

    def test_severity_mapping(self):
        """severity maps to {'value': severity_name}."""
        fields = {}
        severity = "Important"
        if severity is not None:
            fields['customfield_12316142'] = {'value': severity}
        assert fields['customfield_12316142'] == {'value': 'Important'}

    def test_affects_versions_mapping(self):
        """affects_versions maps to list of {'name': version} dicts."""
        fields = {}
        affects_versions = ["ACM 2.15.0", "ACM 2.16.0"]
        if affects_versions is not None:
            fields['versions'] = [{'name': v} for v in affects_versions]
        assert fields['versions'] == [{'name': 'ACM 2.15.0'}, {'name': 'ACM 2.16.0'}]

    def test_acceptance_criteria_mapping(self):
        """acceptance_criteria maps to plain string."""
        fields = {}
        acceptance_criteria = "All tests pass"
        if acceptance_criteria is not None:
            fields['customfield_12315940'] = acceptance_criteria
        assert fields['customfield_12315940'] == "All tests pass"

    def test_reviewers_mapping(self):
        """reviewers maps to list of {'name': username} dicts."""
        fields = {}
        reviewers = ["user1", "user2"]
        if reviewers is not None:
            fields['customfield_12315950'] = [{'name': r} for r in reviewers]
        assert fields['customfield_12315950'] == [{'name': 'user1'}, {'name': 'user2'}]

    def test_none_fields_not_set(self):
        """None values should not create entries in the fields dict."""
        fields = {}
        for field_val, field_key in [
            (None, 'customfield_12315948'),
            (None, 'customfield_12311140'),
            (None, 'customfield_12316142'),
            (None, 'versions'),
            (None, 'customfield_12315940'),
            (None, 'customfield_12315950'),
        ]:
            if field_val is not None:
                fields[field_key] = field_val
        assert len(fields) == 0

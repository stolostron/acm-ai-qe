# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file was developed with AI assistance.

"""Mock-based tests for _issue_to_dict with all new fields."""

import pytest

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig
from tests.conftest import make_mock_issue


@pytest.fixture
def client():
    """Create a JiraClient instance for testing _issue_to_dict."""
    config = JiraConfig(server_url="https://test.atlassian.net", access_token="test-token")
    return JiraClient(config)


class TestStoryWithAllFields:
    def test_all_new_fields_present(self, client):
        """Story issue with all new fields returns complete dict."""
        issue = make_mock_issue(
            key="ACM-26041",
            issue_type="Story",
            sprint_data=["ACM Console 2.17 - 1"],
            qa_contact="rhn-support-dhuynh",
            epic_link="ACM-24035",
            severity="Important",
            versions=["ACM 2.15.0"],
            acceptance_criteria="All tests pass and coverage above 80%",
            contributors=["Alice Smith", "Bob Jones"],
            issuelinks=[
                {'type': 'Blocks', 'direction': 'outward', 'key': 'ACM-100', 'summary': 'Blocked task'},
                {'type': 'Relates', 'direction': 'inward', 'key': 'ACM-200', 'summary': 'Related work'},
            ],
            attachments=["screenshot.png", "log.txt"],
        )

        result = client._issue_to_dict(issue)

        assert result['sprint'] == "ACM Console 2.17 - 1"
        assert result['qa_contact'] == "rhn-support-dhuynh"
        assert result['epic_link'] == "ACM-24035"
        assert result['severity'] == "Important"
        assert result['affects_versions'] == ["ACM 2.15.0"]
        assert result['acceptance_criteria'] == "All tests pass and coverage above 80%"
        assert result['contributors'] == ["Alice Smith", "Bob Jones"]
        assert len(result['issue_links']) == 2
        assert result['issue_links'][0]['direction'] == 'outward'
        assert result['issue_links'][1]['direction'] == 'inward'
        assert result['attachments'] == ["screenshot.png", "log.txt"]


class TestSubtaskHasEpicLink:
    def test_epic_link_returned_for_subtask(self, client):
        """Sub-task issue returns epic_link (bug fix: was only for Stories)."""
        issue = make_mock_issue(
            key="ACM-30198",
            issue_type="Sub-task",
            epic_link="ACM-24035",
            parent={'key': 'ACM-26041', 'summary': 'Parent story', 'issue_type': 'Story'},
        )

        result = client._issue_to_dict(issue)
        assert result['epic_link'] == "ACM-24035"
        assert result['parent'] is not None


class TestTaskInSprint:
    def test_sprint_name_parsed(self, client):
        """Task with sprint field has sprint name parsed correctly."""
        issue = make_mock_issue(
            key="ACM-30114",
            issue_type="Task",
            sprint_data=["ACM Console 2.17 - 1"],
        )

        result = client._issue_to_dict(issue)
        assert result['sprint'] == "ACM Console 2.17 - 1"


class TestIssueWithLinks:
    def test_issue_links_parsed(self, client):
        """Issue with inward + outward links returns correct issue_links."""
        issue = make_mock_issue(
            key="ACM-500",
            issuelinks=[
                {'type': 'Blocks', 'direction': 'outward', 'key': 'ACM-501', 'summary': 'Downstream'},
                {'type': 'Cloners', 'direction': 'inward', 'key': 'ACM-499', 'summary': 'Clone source'},
            ],
        )

        result = client._issue_to_dict(issue)
        assert len(result['issue_links']) == 2
        assert result['issue_links'][0] == {
            'type': 'Blocks', 'direction': 'outward', 'key': 'ACM-501', 'summary': 'Downstream'
        }
        assert result['issue_links'][1] == {
            'type': 'Cloners', 'direction': 'inward', 'key': 'ACM-499', 'summary': 'Clone source'
        }


class TestIssueWithAttachments:
    def test_attachment_filenames(self, client):
        """Issue with attachments returns list of filenames."""
        issue = make_mock_issue(
            key="ACM-600",
            attachments=["report.pdf", "data.csv", "diagram.png"],
        )

        result = client._issue_to_dict(issue)
        assert result['attachments'] == ["report.pdf", "data.csv", "diagram.png"]


class TestIssueWithAffectsVersions:
    def test_affects_versions_list(self, client):
        """Issue with affects versions returns list of version names."""
        issue = make_mock_issue(
            key="ACM-800",
            versions=["ACM 2.15.0", "ACM 2.16.0"],
        )

        result = client._issue_to_dict(issue)
        assert result['affects_versions'] == ["ACM 2.15.0", "ACM 2.16.0"]


class TestMinimalFields:
    def test_no_crashes_with_none_or_empty(self, client):
        """Issue with None/empty for all optional new fields does not crash."""
        issue = make_mock_issue(
            key="ACM-999",
            sprint_data=None,
            qa_contact=None,
            epic_link=None,
            severity=None,
            versions=None,
            acceptance_criteria=None,
            issuelinks=None,
            attachments=None,
        )

        result = client._issue_to_dict(issue)
        assert result['sprint'] is None
        assert result['qa_contact'] is None
        assert result['epic_link'] is None
        assert result['severity'] is None
        assert result['affects_versions'] == []
        assert result['acceptance_criteria'] is None
        assert result['contributors'] == []
        assert result['issue_links'] == []
        assert result['attachments'] == []
        assert result['key'] == "ACM-999"
        assert result['status'] == "New"

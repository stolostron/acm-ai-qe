"""Tests for client helper methods: _parse_sprint_field and _parse_issue_links."""

from unittest.mock import MagicMock

import pytest

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig


@pytest.fixture
def client():
    """Create a JiraClient instance (not connected) for testing helper methods."""
    config = JiraConfig(server_url="https://test.example.com", access_token="test")
    return JiraClient(config)


# --- _parse_sprint_field tests ---

class TestParseSprintField:
    def test_active_sprint(self, client):
        """Active sprint string returns correct name."""
        sprint_data = [
            "com.atlassian.greenhopper.service.sprint.Sprint@7e3f1[id=82854,rapidViewId=16103,"
            "state=ACTIVE,name=ACM Console Train 37 - 1,startDate=2026-02-12T00:00:00.000Z,"
            "endDate=2026-02-25T00:00:00.000Z,completeDate=<null>,activatedDate=2026-02-12T00:00:00.000Z,"
            "sequence=82854,goal=,autoStartStop=false]"
        ]
        result = client._parse_sprint_field(sprint_data)
        assert result == "ACM Console Train 37 - 1"

    def test_multiple_sprints_returns_last(self, client):
        """With multiple sprints (closed + active), returns the last one (most recent)."""
        sprint_data = [
            "com.atlassian.greenhopper.service.sprint.Sprint@aaa[id=82000,state=CLOSED,"
            "name=ACM Console Train 36 - 2,startDate=2026-01-15T00:00:00.000Z]",
            "com.atlassian.greenhopper.service.sprint.Sprint@bbb[id=82854,state=ACTIVE,"
            "name=ACM Console Train 37 - 1,startDate=2026-02-12T00:00:00.000Z]"
        ]
        result = client._parse_sprint_field(sprint_data)
        assert result == "ACM Console Train 37 - 1"

    def test_none_returns_none(self, client):
        """None input returns None."""
        assert client._parse_sprint_field(None) is None

    def test_empty_list_returns_none(self, client):
        """Empty list returns None."""
        assert client._parse_sprint_field([]) is None

    def test_malformed_string_returns_none(self, client):
        """String without 'name=' returns None."""
        sprint_data = ["some random string without the expected format"]
        assert client._parse_sprint_field(sprint_data) is None


# --- _parse_issue_links tests ---

class TestParseIssueLinks:
    def test_outward_link(self, client):
        """Outward issue link is parsed correctly."""
        link = MagicMock()
        link_type = MagicMock()
        link_type.name = "Blocks"
        link.type = link_type
        outward = MagicMock()
        outward.key = "ACM-100"
        outward.fields.summary = "Blocked issue"
        link.outwardIssue = outward
        # Ensure inwardIssue is absent
        del link.inwardIssue

        result = client._parse_issue_links([link])
        assert len(result) == 1
        assert result[0] == {
            'type': 'Blocks',
            'direction': 'outward',
            'key': 'ACM-100',
            'summary': 'Blocked issue'
        }

    def test_inward_link(self, client):
        """Inward issue link is parsed correctly."""
        link = MagicMock()
        link_type = MagicMock()
        link_type.name = "Relates"
        link.type = link_type
        inward = MagicMock()
        inward.key = "ACM-200"
        inward.fields.summary = "Related issue"
        link.inwardIssue = inward
        del link.outwardIssue

        result = client._parse_issue_links([link])
        assert len(result) == 1
        assert result[0] == {
            'type': 'Relates',
            'direction': 'inward',
            'key': 'ACM-200',
            'summary': 'Related issue'
        }

    def test_mixed_links(self, client):
        """Both inward and outward links are parsed correctly."""
        link_out = MagicMock()
        lt_out = MagicMock()
        lt_out.name = "Blocks"
        link_out.type = lt_out
        out_issue = MagicMock()
        out_issue.key = "ACM-100"
        out_issue.fields.summary = "Blocked"
        link_out.outwardIssue = out_issue
        del link_out.inwardIssue

        link_in = MagicMock()
        lt_in = MagicMock()
        lt_in.name = "Cloners"
        link_in.type = lt_in
        in_issue = MagicMock()
        in_issue.key = "ACM-300"
        in_issue.fields.summary = "Cloned from"
        link_in.inwardIssue = in_issue
        del link_in.outwardIssue

        result = client._parse_issue_links([link_out, link_in])
        assert len(result) == 2
        assert result[0]['direction'] == 'outward'
        assert result[1]['direction'] == 'inward'

    def test_empty_list(self, client):
        """Empty links list returns empty list."""
        assert client._parse_issue_links([]) == []

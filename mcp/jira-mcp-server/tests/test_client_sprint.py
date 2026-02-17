"""Mock-based tests for sprint-related client methods."""

from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

import pytest

from jira_mcp_server.client import JiraClient
from jira_mcp_server.config import JiraConfig


@pytest.fixture
def client():
    """Create a JiraClient with a mocked JIRA connection."""
    config = JiraConfig(server_url="https://test.example.com", access_token="test")
    c = JiraClient(config)
    c._jira = MagicMock()
    return c


class TestListBoards:
    def test_returns_dicts(self, client):
        """list_boards returns list of board dicts."""
        board1 = MagicMock()
        board1.id = 16103
        board1.name = "ACM Console"
        board1.type = "scrum"

        board2 = MagicMock()
        board2.id = 200
        board2.name = "Other Board"
        board2.type = "kanban"

        client._jira.boards.return_value = [board1, board2]

        result = asyncio.get_event_loop().run_until_complete(client.list_boards())
        assert len(result) == 2
        assert result[0] == {'id': 16103, 'name': 'ACM Console', 'type': 'scrum'}
        assert result[1] == {'id': 200, 'name': 'Other Board', 'type': 'kanban'}

    def test_with_name_filter(self, client):
        """list_boards passes name filter to JIRA API."""
        client._jira.boards.return_value = []
        asyncio.get_event_loop().run_until_complete(client.list_boards(name="ACM"))
        client._jira.boards.assert_called_once_with(name="ACM")


class TestListSprints:
    def test_returns_dicts(self, client):
        """list_sprints returns list of sprint dicts."""
        sprint = MagicMock()
        sprint.id = 82854
        sprint.name = "ACM Console Train 37 - 1"
        sprint.state = "active"
        sprint.startDate = "2026-02-12T00:00:00.000Z"
        sprint.endDate = "2026-02-25T00:00:00.000Z"

        client._jira.sprints.return_value = [sprint]

        result = asyncio.get_event_loop().run_until_complete(
            client.list_sprints(16103)
        )
        assert len(result) == 1
        assert result[0]['id'] == 82854
        assert result[0]['name'] == "ACM Console Train 37 - 1"
        assert result[0]['state'] == "active"

    def test_with_state_filter(self, client):
        """list_sprints passes state filter to JIRA API."""
        client._jira.sprints.return_value = []
        asyncio.get_event_loop().run_until_complete(
            client.list_sprints(16103, state="active")
        )
        client._jira.sprints.assert_called_once_with(16103, state="active")


class TestAddToSprint:
    def test_calls_api(self, client):
        """add_to_sprint calls JIRA API with correct arguments."""
        client._jira.add_issues_to_sprint.return_value = None
        asyncio.get_event_loop().run_until_complete(
            client.add_to_sprint(82854, ["ACM-26041", "ACM-30198"])
        )
        client._jira.add_issues_to_sprint.assert_called_once_with(
            82854, ["ACM-26041", "ACM-30198"]
        )

    def test_error_handling(self, client):
        """add_to_sprint propagates JIRAError."""
        from jira.exceptions import JIRAError
        client._jira.add_issues_to_sprint.side_effect = JIRAError("Sprint error")
        with pytest.raises(ValueError, match="Failed to add issues to sprint"):
            asyncio.get_event_loop().run_until_complete(
                client.add_to_sprint(99999, ["BAD-1"])
            )

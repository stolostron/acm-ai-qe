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

"""Tests for automatic update check functionality."""

import os
import subprocess
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from jira_mcp_server.server import JiraMCPServer


@pytest.fixture
def server():
    """Create a JiraMCPServer instance with mocked dependencies."""
    with patch.dict(os.environ, {
        'JIRA_SERVER_URL': 'https://test.atlassian.net',
        'JIRA_ACCESS_TOKEN': 'test-token',
    }):
        srv = JiraMCPServer()
        return srv


@pytest.mark.asyncio
async def test_update_check_sets_warning_when_behind(server):
    """When origin/main is ahead, _update_warning should be set."""
    fetch_result = MagicMock(returncode=0)
    count_result = MagicMock(returncode=0, stdout="3\n")

    with patch("jira_mcp_server.server.os.path.isdir", return_value=True), \
         patch("jira_mcp_server.server.subprocess.run", side_effect=[fetch_result, count_result]):
        await server._check_for_updates()

    assert server._update_warning is not None
    assert "3 commit(s) ahead" in server._update_warning


@pytest.mark.asyncio
async def test_update_check_no_warning_when_up_to_date(server):
    """When local is up to date, no warning should be set."""
    fetch_result = MagicMock(returncode=0)
    count_result = MagicMock(returncode=0, stdout="0\n")

    with patch("jira_mcp_server.server.os.path.isdir", return_value=True), \
         patch("jira_mcp_server.server.subprocess.run", side_effect=[fetch_result, count_result]):
        await server._check_for_updates()

    assert server._update_warning is None


@pytest.mark.asyncio
async def test_update_check_no_git_dir(server):
    """When .git directory does not exist, skip silently."""
    with patch("jira_mcp_server.server.os.path.isdir", return_value=False), \
         patch("jira_mcp_server.server.subprocess.run") as mock_run:
        await server._check_for_updates()

    mock_run.assert_not_called()
    assert server._update_warning is None


@pytest.mark.asyncio
async def test_update_check_handles_fetch_failure(server):
    """If git fetch fails, no warning and no crash."""
    with patch("jira_mcp_server.server.os.path.isdir", return_value=True), \
         patch("jira_mcp_server.server.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
        await server._check_for_updates()

    assert server._update_warning is None


@pytest.mark.asyncio
async def test_update_check_handles_rev_list_failure(server):
    """If rev-list returns non-zero, no warning."""
    fetch_result = MagicMock(returncode=0)
    count_result = MagicMock(returncode=128, stdout="")

    with patch("jira_mcp_server.server.os.path.isdir", return_value=True), \
         patch("jira_mcp_server.server.subprocess.run", side_effect=[fetch_result, count_result]):
        await server._check_for_updates()

    assert server._update_warning is None


@pytest.mark.asyncio
async def test_emit_warning_once(server):
    """Warning should be emitted via ctx.warning only once."""
    server._update_warning = "update available"

    ctx = AsyncMock()

    await server._emit_update_warning(ctx)
    ctx.warning.assert_called_once_with("update available")
    assert server._update_warning_emitted is True

    # Second call should not emit again
    ctx.reset_mock()
    await server._emit_update_warning(ctx)
    ctx.warning.assert_not_called()


@pytest.mark.asyncio
async def test_emit_warning_skipped_when_no_warning(server):
    """No ctx.warning call when there is no update warning."""
    ctx = AsyncMock()

    await server._emit_update_warning(ctx)
    ctx.warning.assert_not_called()


@pytest.mark.asyncio
async def test_emit_warning_skipped_when_no_ctx(server):
    """No crash when ctx is None."""
    server._update_warning = "update available"

    await server._emit_update_warning(None)
    assert server._update_warning_emitted is False

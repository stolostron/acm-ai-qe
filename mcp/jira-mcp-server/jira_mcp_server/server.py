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

"""Main MCP server implementation for Jira."""

import asyncio
import logging
import os
import re
import subprocess
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP, Context
from pydantic import BaseModel

from .config import JiraConfig
from .client import JiraClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Statuses that do NOT require fix_version to be set
# Any status not in this set will require fix_version before transitioning
EARLY_STATUSES = {'new', 'backlog', 'in progress'}


def _user_ref(identifier: str) -> Dict[str, str]:
    """Build a user reference dict for Jira Cloud.

    Only accountId is valid on Jira Cloud (name was deprecated for privacy).
    Use search_users to resolve a display name or email to an accountId first.
    """
    if ':' in identifier or (identifier.startswith('7') and len(identifier) > 30):
        return {'accountId': identifier}
    raise ValueError(
        f"'{identifier}' does not look like a Jira Cloud accountId. "
        f"Use search_users to find the accountId for this user first."
    )


def _validate_git_commit_sha(sha: str) -> None:
    """Validate that a git commit SHA is either 40 characters (SHA-1) or 64 characters (SHA-256).

    Args:
        sha: The git commit SHA to validate

    Raises:
        ValueError: If the SHA is not a valid length or contains invalid characters
    """
    if not sha:
        return

    # Check if it's all hexadecimal characters
    if not all(c in '0123456789abcdefABCDEF' for c in sha):
        raise ValueError(f"Git commit SHA must contain only hexadecimal characters: {sha}")

    # Check length - must be either 40 (SHA-1) or 64 (SHA-256) characters
    if len(sha) not in [40, 64]:
        raise ValueError(f"Git commit SHA must be either 40 characters (SHA-1) or 64 characters (SHA-256), got {len(sha)} characters: {sha}")


# Pydantic models for structured responses
class SubtaskResponse(BaseModel):
    key: str
    summary: str
    status: str
    issue_type: str

class ParentResponse(BaseModel):
    key: str
    summary: str
    issue_type: str

class IssueLinkResponse(BaseModel):
    type: str
    direction: str
    key: str
    summary: str

class IssueResponse(BaseModel):
    key: str
    summary: str
    description: str
    status: str
    priority: str
    issue_type: str
    project: str
    assignee: Optional[str]
    reporter: Optional[str]
    created: str
    updated: str
    resolution: Optional[str]
    labels: List[str]
    components: List[str]
    comments: List["CommentResponse"]
    url: str
    fix_versions: List[str]
    target_version: List[str]
    work_type: Optional[str]
    security_level: Optional[str]
    due_date: Optional[str]
    target_start: Optional[str]
    target_end: Optional[str]
    original_estimate: Optional[str]
    story_points: Optional[float]
    git_commit: Optional[str]
    git_pull_requests: Optional[str]
    subtasks: List[SubtaskResponse]
    parent: Optional[ParentResponse]
    parent_link: Optional[str] = None
    epic_link: Optional[str] = None
    sprint: Optional[str] = None
    qa_contact: Optional[str] = None
    severity: Optional[str] = None
    affects_versions: List[str] = []
    acceptance_criteria: Optional[str] = None
    contributors: List[str] = []
    issue_links: List[IssueLinkResponse] = []
    attachments: List[str] = []

class ProjectResponse(BaseModel):
    key: str
    name: str
    description: str
    lead: str

class ComponentResponse(BaseModel):
    id: str
    name: str
    description: str
    lead: str
    assignee_type: str
    is_assignee_type_valid: bool

class CommentResponse(BaseModel):
    id: str
    body: str
    author: str
    created: str
    updated: str

class WorkLogResponse(BaseModel):
    id: str
    time_spent: str
    comment: str
    author: str
    created: str
    started: str

class LinkResponse(BaseModel):
    link_type: str
    inward_issue: str
    outward_issue: str
    inward_description: Optional[str]
    outward_description: Optional[str]
    comment: Optional[str]
    created: bool

class LinkTypeResponse(BaseModel):
    id: str
    name: str
    inward: str
    outward: str

class UserResponse(BaseModel):
    account_id: Optional[str]
    name: Optional[str]
    display_name: str
    email_address: Optional[str]
    active: bool

class WatcherResponse(BaseModel):
    username: str
    display_name: str
    email: Optional[str]
    active: bool

class TeamAssignmentResponse(BaseModel):
    issue_key: str
    team_name: str
    successes: List[str]
    failures: List[Dict[str, str]]
    total_added: int
    total_failed: int

class TeamInfoResponse(BaseModel):
    teams: Dict[str, List[str]]

class ComponentAliasResponse(BaseModel):
    aliases: Dict[str, str]
class JiraMCPServer:
    """MCP Server for Jira integration."""
    
    def __init__(self):
        """Initialize the Jira MCP server."""
        self.mcp = FastMCP("Jira MCP Server")
        self.config = JiraConfig.from_env()
        self.client = JiraClient(self.config)
        self._update_warning: Optional[str] = None
        self._update_warning_emitted = False
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self) -> None:
        """Set up MCP tools for Jira operations."""
        
        @self.mcp.tool()
        async def search_issues(
            jql: str,
            max_results: int = 100,
            ctx: Optional[Context] = None
        ) -> List[IssueResponse]:
            """Search for Jira issues using JQL (Jira Query Language).

            Args:
                jql: JQL query string (e.g., 'project = PROJ AND status = Open')
                max_results: Maximum number of results to return (default: 100)
                ctx: MCP context for progress reporting
            """
            await self._emit_update_warning(ctx)
            if ctx:
                await ctx.info(f"Searching issues with JQL: {jql}")
            
            try:
                issues = await self.client.search_issues(jql, max_results)
                if ctx:
                    await ctx.info(f"Found {len(issues)} issues")
                return [IssueResponse(**issue) for issue in issues]
            except Exception as e:
                if ctx:
                    await ctx.error(f"Search failed: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def search_issues_by_team(
            team_name: str,
            project_key: Optional[str] = None,
            status: Optional[str] = None,
            max_results: int = 100,
            ctx: Optional[Context] = None
        ) -> List[IssueResponse]:
            """Search for issues assigned to any member of a team.
            
            This tool finds all issues where the assignee is one of the team members.
            It automatically constructs the appropriate JQL query based on the team configuration.

            Args:
                team_name: Name of the team to search for
                project_key: Optional project key to filter results (e.g., 'PROJ')
                status: Optional status to filter results (e.g., 'Open', 'In Progress')
                max_results: Maximum number of results to return (default: 100)
                ctx: MCP context for progress reporting
            """
            await self._emit_update_warning(ctx)
            if ctx:
                await ctx.info(f"Searching issues assigned to team '{team_name}'")
            
            try:
                # Get team members
                team_members = self.config.get_team_members(team_name)
                
                if not team_members:
                    raise ValueError(f"Team '{team_name}' has no members")
                
                # Build JQL query for assignee in team members
                assignee_clause = " OR ".join([f'assignee = "{member}"' for member in team_members])
                jql_parts = [f"({assignee_clause})"]
                
                # Add optional filters
                if project_key:
                    jql_parts.insert(0, f"project = {project_key}")
                
                if status:
                    jql_parts.append(f'status = "{status}"')
                
                jql = " AND ".join(jql_parts)
                
                if ctx:
                    await ctx.info(f"Generated JQL: {jql}")
                    await ctx.info(f"Searching for issues assigned to: {', '.join(team_members)}")
                
                # Execute search
                issues = await self.client.search_issues(jql, max_results)
                
                if ctx:
                    await ctx.info(f"Found {len(issues)} issues assigned to team '{team_name}'")
                
                return [IssueResponse(**issue) for issue in issues]
                
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to search issues for team '{team_name}': {str(e)}")
                raise
        
        @self.mcp.tool()
        async def get_issue(
            issue_key: str,
            ctx: Optional[Context] = None
        ) -> IssueResponse:
            """Get detailed information about a specific Jira issue.
            
            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                ctx: MCP context for progress reporting
            """
            await self._emit_update_warning(ctx)
            if ctx:
                await ctx.info(f"Fetching issue: {issue_key}")
            
            try:
                issue = await self.client.get_issue(issue_key)
                return IssueResponse(**issue)
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to get issue {issue_key}: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def create_issue(
            project_key: str,
            summary: str,
            description: str,
            priority: str = "Normal",
            work_type: Optional[str] = None,
            components: Optional[List[str]] = None,
            target_version: Optional[List[str]] = None,
            issue_type: str = "Task",
            due_date: Optional[str] = None,
            assignee: Optional[str] = None,
            team: Optional[str] = None,
            labels: Optional[List[str]] = None,
            fix_versions: Optional[List[str]] = None,
            security_level: Optional[str] = "Red Hat Employee",
            target_start: Optional[str] = None,
            target_end: Optional[str] = None,
            original_estimate: Optional[str] = None,
            story_points: Optional[float] = None,
            git_commit: Optional[str] = None,
            git_pull_requests: Optional[str] = None,
            parent: Optional[str] = None,
            epic_name: Optional[str] = None,
            parent_link: Optional[str] = None,
            epic_link: Optional[str] = None,
            qa_contact: Optional[str] = None,
            severity: Optional[str] = None,
            affects_versions: Optional[List[str]] = None,
            acceptance_criteria: Optional[str] = None,
            contributors: Optional[List[str]] = None,
            ctx: Optional[Context] = None
        ) -> IssueResponse:
            """Create a new Jira issue.

            ⚠️ WARNING: Issues created in Jira CANNOT BE UNDONE. Issues are permanent records and cannot be deleted.
            Only create issues when explicitly requested by the user. Never use for testing or if uncertain about parameters.

            Args:
                project_key: Project key (e.g., 'PROJ')
                summary: Issue summary/title
                description: Issue description
                issue_type: Issue type (e.g., 'Bug', 'Task', 'Story', 'Sub-task')
                priority: Issue priority (defaults to 'Normal')
                assignee: Username of assignee
                team: Team name to add as watchers (all team members will be added as watchers)
                labels: List of labels to add
                fix_versions: List of fix version names (set when issue is closed)
                target_version: List of target version names (set when issue is created)
                work_type: Work type for the issue (STRONGLY RECOMMENDED). Available options:
                    - **None** = -1
                    - **Associate Wellness & Development** = 10604
                    - **BU Features** = 10605
                    - **Future Sustainability** = 10606
                    - **Incidents & Support** = 10607
                    - **Quality / Stability / Reliability** = 10608
                    - **Security & Compliance** = 10609
                    - **Product / Portfolio Work** = 10610
                security_level: Security level name
                due_date: Due date in YYYY-MM-DD format
                target_start: Target start date in YYYY-MM-DD format
                target_end: Target end date in YYYY-MM-DD format
                components: List of component names (STRONGLY RECOMMENDED)
                original_estimate: Original time estimate (e.g., '1h 30m'). RECOMMENDED for better estimation tracking.
                story_points: Story points value. RECOMMENDED for better sprint planning.
                git_commit: Git commit hash or reference
                git_pull_requests: Git pull requests, comma separated list of pull requests URLs
                parent: Parent issue key for sub-tasks (e.g., 'PROJ-123')
                epic_name: Epic Name (required for Epic issue type)
                parent_link: Parent link issue key for hierarchy (e.g., linking an Epic
                    to its parent Feature). Use instead of 'parent' for non-sub-task
                    relationships (e.g., 'PROJ-100').
                epic_link: Epic link issue key for linking a Story to its parent Epic
                    (e.g., 'PROJ-200').
                qa_contact: QA Contact username
                severity: Severity value (e.g., 'Important', 'Critical', 'Major', 'Moderate', 'Low')
                affects_versions: List of affected version names (e.g., ['ACM 2.16.0'])
                acceptance_criteria: Acceptance criteria text
                contributors: List of contributor usernames to add to the issue
                ctx: MCP context for progress reporting
            """
            # Validate required fields
            if not summary or not summary.strip():
                raise ValueError("Summary cannot be empty")
            if not description or not description.strip():
                raise ValueError("Description cannot be empty")

            # Validate optional fields if provided
            if assignee is not None and (not assignee or not assignee.strip()):
                raise ValueError("Assignee cannot be empty")
            if fix_versions is not None and (not fix_versions or len(fix_versions) == 0):
                raise ValueError("Fix versions cannot be empty")

            await self._emit_update_warning(ctx)
            if ctx:
                await ctx.info(f"Creating issue in project {project_key}")

            fields = {}
            if priority:
                fields['priority'] = {'name': priority}
            if assignee:
                fields['assignee'] = {'name': assignee}
            if labels:
                # Labels are passed as array of strings directly to Jira API
                fields['labels'] = labels
            if fix_versions:
                # Fix versions need to be converted to objects with 'name' property
                fields['fixVersions'] = [{'name': version} for version in fix_versions]
            if target_version:
                # Target versions need to be converted to objects with 'name' property
                fields['customfield_10855'] = [{'name': version} for version in target_version]
            if work_type:
                fields['customfield_10464'] = {'id': str(work_type)}  # Activity Type (formerly Work Type)
            if security_level:
                fields['security'] = {'name': security_level}
            if due_date:
                fields['duedate'] = due_date
            if target_start:
                fields['customfield_10022'] = target_start  # Target Start custom field
            if target_end:
                fields['customfield_10023'] = target_end  # Target End custom field
            if components:
                # Resolve component aliases to actual component names
                resolved_components = self.config.resolve_component_names(components)
                # Components need to be converted to objects with 'name' property
                fields['components'] = [{'name': component} for component in resolved_components]
            if original_estimate:
                fields['timetracking'] = {'originalEstimate': original_estimate}
            if story_points is not None:
                fields['customfield_10028'] = story_points  # Story points custom field
            if git_commit:
                _validate_git_commit_sha(git_commit)
                fields['customfield_10583'] = git_commit  # Git Commit custom field
            if git_pull_requests:
                fields['customfield_10875'] = git_pull_requests  # Git Pull Requests custom field
            if parent:
                fields['parent'] = {'key': parent}  # Parent issue for sub-tasks
            if epic_name:
                fields['customfield_10011'] = epic_name  # Epic Name custom field
            if parent_link:
                fields['customfield_10014'] = parent_link  # Parent Link custom field
            if epic_link:
                fields['customfield_10014'] = epic_link  # Epic Link custom field
            if qa_contact is not None:
                qa_val = qa_contact.strip() if isinstance(qa_contact, str) else ""
                if qa_val:
                    fields['customfield_10470'] = _user_ref(qa_val)  # QA Contact
            if severity is not None:
                fields['customfield_10840'] = {'value': severity}  # Severity
            if affects_versions is not None:
                fields['versions'] = [{'name': v} for v in affects_versions]
            if acceptance_criteria is not None:
                fields['customfield_10718'] = acceptance_criteria  # Acceptance Criteria
            if contributors is not None:
                valid = [c.strip() for c in contributors if isinstance(c, str) and c.strip()]
                if valid:
                    fields['customfield_10466'] = [_user_ref(c) for c in valid]  # Contributors

            try:
                issue = await self.client.create_issue(
                    project_key, summary, description, issue_type, **fields
                )
                if ctx:
                    await ctx.info(f"Created issue: {issue['key']}")
                
                # If a team is specified, add team members as watchers
                if team:
                    try:
                        team_members = self.config.get_team_members(team)
                        if ctx:
                            await ctx.info(f"Adding {len(team_members)} team members as watchers")
                        await self.client.add_team_as_watchers(issue['key'], team_members)
                    except Exception as team_error:
                        if ctx:
                            await ctx.warning(f"Failed to add team watchers: {str(team_error)}")
                
                return IssueResponse(**issue)
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to create issue: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def update_issue(
            issue_key: str,
            priority: Optional[str] = None,
            work_type: Optional[str] = None,
            components: Optional[List[str]] = None,
            due_date: Optional[str] = None,
            summary: Optional[str] = None,
            description: Optional[str] = None,
            assignee: Optional[str] = None,
            labels: Optional[List[str]] = None,
            fix_versions: Optional[List[str]] = None,
            target_version: Optional[List[str]] = None,
            security_level: Optional[str] = None,
            target_start: Optional[str] = None,
            target_end: Optional[str] = None,
            original_estimate: Optional[str] = None,
            story_points: Optional[float] = None,
            git_commit: Optional[str] = None,
            git_pull_requests: Optional[str] = None,
            parent_link: Optional[str] = None,
            epic_link: Optional[str] = None,
            qa_contact: Optional[str] = None,
            severity: Optional[str] = None,
            affects_versions: Optional[List[str]] = None,
            acceptance_criteria: Optional[str] = None,
            contributors: Optional[List[str]] = None,
            ctx: Optional[Context] = None
        ) -> IssueResponse:
            """Update an existing Jira issue.

            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                summary: New summary/title
                description: New description
                priority: New priority
                assignee: New assignee username
                labels: New labels list
                fix_versions: List of fix version names (set when issue is closed)
                target_version: List of target version names (set when issue is created)
                work_type: Work type for the issue (STRONGLY RECOMMENDED). Available options:
                    - **None** = -1
                    - **Associate Wellness & Development** = 10604
                    - **BU Features** = 10605
                    - **Future Sustainability** = 10606
                    - **Incidents & Support** = 10607
                    - **Quality / Stability / Reliability** = 10608
                    - **Security & Compliance** = 10609
                    - **Product / Portfolio Work** = 10610
                security_level: Security level name
                due_date: Due date in YYYY-MM-DD format
                target_start: Target start date in YYYY-MM-DD format
                target_end: Target end date in YYYY-MM-DD format
                components: List of component names (STRONGLY RECOMMENDED)
                original_estimate: Original time estimate (e.g., '1h 30m')
                story_points: Story points value
                git_commit: Git commit hash or reference
                git_pull_requests: Git pull requests, comma separated list of pull requests URLs
                parent_link: Parent link issue key for hierarchy (e.g., linking an Epic
                    to its parent Feature). Use instead of 'parent' for non-sub-task
                    relationships (e.g., 'PROJ-100').
                epic_link: Epic link issue key for linking a Story to its parent Epic
                    (e.g., 'PROJ-200').
                qa_contact: QA Contact username
                severity: Severity value (e.g., 'Important', 'Critical', 'Major', 'Moderate', 'Low')
                affects_versions: List of affected version names (e.g., ['ACM 2.16.0'])
                acceptance_criteria: Acceptance criteria text
                contributors: List of contributor usernames to add to the issue
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Updating issue: {issue_key}")

            fields = {}
            if summary:
                fields['summary'] = summary
            if description:
                fields['description'] = description
            if priority:
                fields['priority'] = {'name': priority}
            if assignee:
                fields['assignee'] = {'name': assignee}
            if labels:
                # Labels are passed as array of strings directly to Jira API
                fields['labels'] = labels
            if fix_versions:
                # Fix versions need to be converted to objects with 'name' property
                fields['fixVersions'] = [{'name': version} for version in fix_versions]
            if target_version:
                # Target versions need to be converted to objects with 'name' property
                fields['customfield_10855'] = [{'name': version} for version in target_version]
            if work_type:
                fields['customfield_10464'] = {'id': str(work_type)}  # Activity Type (formerly Work Type)
            if security_level:
                fields['security'] = {'name': security_level}
            if due_date:
                fields['duedate'] = due_date
            if target_start:
                fields['customfield_10022'] = target_start  # Target Start custom field
            if target_end:
                fields['customfield_10023'] = target_end  # Target End custom field
            if components:
                # Resolve component aliases to actual component names
                resolved_components = self.config.resolve_component_names(components)
                # Components need to be converted to objects with 'name' property
                fields['components'] = [{'name': component} for component in resolved_components]
            if original_estimate:
                fields['timetracking'] = {'originalEstimate': original_estimate}
            if story_points is not None:
                fields['customfield_10028'] = story_points  # Story points custom field
            if git_commit:
                _validate_git_commit_sha(git_commit)
                fields['customfield_10583'] = git_commit  # Git Commit custom field
            if git_pull_requests:
                fields['customfield_10875'] = git_pull_requests  # Git Pull Requests custom field
            if parent_link:
                fields['customfield_10014'] = parent_link  # Parent Link custom field
            if epic_link:
                fields['customfield_10014'] = epic_link  # Epic Link custom field
            if qa_contact is not None:
                qa_val = qa_contact.strip() if isinstance(qa_contact, str) else ""
                if qa_val:
                    fields['customfield_10470'] = _user_ref(qa_val)  # QA Contact
            if severity is not None:
                fields['customfield_10840'] = {'value': severity}  # Severity
            if affects_versions is not None:
                fields['versions'] = [{'name': v} for v in affects_versions]
            if acceptance_criteria is not None:
                fields['customfield_10718'] = acceptance_criteria  # Acceptance Criteria
            if contributors is not None:
                valid = [c.strip() for c in contributors if isinstance(c, str) and c.strip()]
                if valid:
                    fields['customfield_10466'] = [_user_ref(c) for c in valid]  # Contributors

            if not fields:
                raise ValueError("At least one field must be provided to update an issue")

            try:
                issue = await self.client.update_issue(issue_key, **fields)
                if ctx:
                    await ctx.info(f"Updated issue: {issue_key}")
                return IssueResponse(**issue)
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to update issue {issue_key}: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def clear_field(
            issue_key: str,
            field_name: str,
            ctx: Optional[Context] = None
        ) -> IssueResponse:
            """Clear (unset) a field on a Jira issue.

            Dynamically determines the correct empty value by inspecting the
            field's schema from the Jira edit metadata.

            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                field_name: The Jira field ID to clear (e.g., 'fixVersions',
                    'customfield_10855', 'duedate', 'labels', 'components',
                    'assignee', 'priority', 'security', 'timetracking').
                    Use the debug_issue_fields tool to discover available field IDs.
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Fetching edit metadata for {issue_key}")

            editmeta = await self.client.get_editmeta(issue_key)

            if field_name not in editmeta:
                available = ', '.join(sorted(editmeta.keys()))
                raise ValueError(
                    f"Field '{field_name}' is not editable on {issue_key}. "
                    f"Editable fields: {available}"
                )

            schema = editmeta[field_name].get('schema', {})
            field_type = schema.get('type', '')

            # Determine the correct clear value based on schema type
            if field_type == 'array':
                clear_value = []
            elif field_type in ('string', 'date', 'datetime'):
                clear_value = None
            elif field_type == 'number':
                clear_value = None
            elif field_type == 'timetracking':
                clear_value = {'originalEstimate': '0m'}
            else:
                # option, user, security, priority, issuelink, etc.
                clear_value = None

            if ctx:
                await ctx.info(
                    f"Clearing '{field_name}' (type={field_type}) on {issue_key}"
                )

            try:
                issue = await self.client.update_issue(
                    issue_key, **{field_name: clear_value}
                )
                if ctx:
                    await ctx.info(f"Cleared '{field_name}' on {issue_key}")
                return IssueResponse(**issue)
            except Exception as e:
                if ctx:
                    await ctx.error(
                        f"Failed to clear '{field_name}' on {issue_key}: {str(e)}"
                    )
                raise

        @self.mcp.tool()
        async def transition_issue(
            issue_key: str,
            transition: str,
            ctx: Optional[Context] = None
        ) -> IssueResponse:
            """Transition a Jira issue to a new status.

            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                transition: Transition name (e.g., 'Done', 'In Progress')
                ctx: MCP context for progress reporting

            Note:
                It is highly recommended to set fix_version on the issue before
                transitioning to statuses beyond 'New', 'Backlog', and 'In Progress'.
            """
            if ctx:
                await ctx.info(f"Transitioning issue {issue_key} to {transition}")

            try:
                # Warn if fix_version is not set for statuses beyond early stages
                if transition.lower() not in EARLY_STATUSES:
                    current_issue = await self.client.get_issue(issue_key)
                    fix_versions = current_issue.get('fix_versions', [])
                    if not fix_versions:
                        warning_msg = (
                            f"Warning: {issue_key} is being transitioned to '{transition}' "
                            f"without a fix_version set. It is highly recommended to set "
                            f"fix_version before moving beyond 'In Progress'."
                        )
                        if ctx:
                            await ctx.warning(warning_msg)
                        logger.warning(warning_msg)

                issue = await self.client.transition_issue(issue_key, transition)
                if ctx:
                    await ctx.info(f"Transitioned issue {issue_key} to {transition}")
                return IssueResponse(**issue)
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to transition issue {issue_key}: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def add_comment(
            issue_key: str,
            comment: str,
            security_level: Optional[str] = "Red Hat Employee",
            ctx: Optional[Context] = None
        ) -> CommentResponse:
            """Add a comment to a Jira issue.

            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                comment: Comment text
                security_level: Security level name (default: "Red Hat Employee")
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Adding comment to issue: {issue_key}")
            
            try:
                comment_data = await self.client.add_comment(issue_key, comment, security_level)
                if ctx:
                    await ctx.info(f"Added comment to issue: {issue_key}")
                return CommentResponse(**comment_data)
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to add comment to {issue_key}: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def log_time(
            issue_key: str,
            time_spent: str,
            comment: str,
            started: Optional[str] = None,
            ctx: Optional[Context] = None
        ) -> WorkLogResponse:
            """Log time spent on a Jira issue with an optional comment.
            
            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                time_spent: Time spent in Jira format (e.g., '1h 30m', '2d 4h', '45m')
                comment: Comment describing the work done
                started: Start date/time in ISO format (optional, defaults to now)
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Logging {time_spent} on issue: {issue_key}")
            
            
            try:
                work_log = await self.client.log_work(issue_key, time_spent, comment, started)
                if ctx:
                    await ctx.info(f"Successfully logged time on issue: {issue_key}")
                return WorkLogResponse(**work_log)
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to log time on {issue_key}: {str(e)}")
                raise

        @self.mcp.tool()
        async def get_projects(
            ctx: Optional[Context] = None
        ) -> List[ProjectResponse]:
            """Get all Jira projects accessible to the user.

            Args:
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info("Fetching all projects")

            try:
                projects = await self.client.get_projects()
                if ctx:
                    await ctx.info(f"Found {len(projects)} projects")
                return [ProjectResponse(**project) for project in projects]
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to get projects: {str(e)}")
                raise

        @self.mcp.tool()
        async def get_project_components(
            project_key: str,
            ctx: Optional[Context] = None
        ) -> List[ComponentResponse]:
            """Get all components available in a specific Jira project.

            Args:
                project_key: Project key (e.g., 'ACM', 'PROJ')
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Fetching components for project: {project_key}")

            try:
                components = await self.client.get_project_components(project_key)
                if ctx:
                    await ctx.info(f"Found {len(components)} components in project {project_key}")
                return [ComponentResponse(**component) for component in components]
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to get components for project {project_key}: {str(e)}")
                raise

        @self.mcp.tool()
        async def link_issue(
            link_type: str,
            inward_issue: str,
            outward_issue: str,
            comment: Optional[str] = None,
            security_level: Optional[str] = None,
            ctx: Optional[Context] = None
        ) -> LinkResponse:
            """Create a link between two Jira issues.
            
            Args:
                link_type: The type of link to create (e.g., 'Blocks', 'Relates', 'Duplicates')
                inward_issue: The issue key to link from (e.g., 'PROJ-123')
                outward_issue: The issue key to link to (e.g., 'PROJ-456')
                comment: Optional comment to add when creating the link
                security_level: Optional security level for the comment (default: None)
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Creating link: {inward_issue} {link_type} {outward_issue}")
            
            try:
                link_data = await self.client.create_issue_link(
                    link_type, inward_issue, outward_issue, comment, security_level
                )
                if ctx:
                    await ctx.info(f"Successfully created link between {inward_issue} and {outward_issue}")
                return LinkResponse(**link_data)
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to create link: {str(e)}")
                raise

        @self.mcp.tool()
        async def get_link_types(
            ctx: Optional[Context] = None
        ) -> List[LinkTypeResponse]:
            """Get all available issue link types.
            
            Args:
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info("Fetching available link types")
            
            try:
                link_types = await self.client.get_issue_link_types()
                if ctx:
                    await ctx.info(f"Found {len(link_types)} link types")
                return [LinkTypeResponse(**link_type) for link_type in link_types]
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to get link types: {str(e)}")
                raise

        @self.mcp.tool()
        async def debug_issue_fields(
            issue_key: str,
            ctx: Optional[Context] = None
        ) -> Dict[str, Any]:
            """Debug function to show all raw Jira fields for an issue.

            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Debugging raw fields for issue: {issue_key}")

            try:
                raw_issue = await self.client.get_raw_issue_fields(issue_key)
                if ctx:
                    await ctx.info(f"Retrieved raw fields for issue: {issue_key}")
                return raw_issue
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to get raw fields for {issue_key}: {str(e)}")
                raise

        @self.mcp.tool()
        async def search_users(
            query: str,
            max_results: int = 50,
            ctx: Optional[Context] = None
        ) -> List[UserResponse]:
            """Search for Jira users by name, email, or username.

            This tool performs a fuzzy search across user names and email addresses,
            making it useful for finding a user's Jira ID when you only have partial
            information.

            Args:
                query: Search query - can be a partial name, email address, or username.
                       Examples: "john", "jsmith", "john.smith@company.com"
                max_results: Maximum number of results to return (default: 50)
                ctx: MCP context for progress reporting

            Returns:
                List of matching users with their account_id, name, display_name,
                email_address, and active status. Use the 'name' field for assignee
                operations in self-hosted Jira, or 'account_id' for Jira Cloud.
            """
            if ctx:
                await ctx.info(f"Searching for users matching: {query}")

            try:
                users = await self.client.search_users(query, max_results)
                if ctx:
                    await ctx.info(f"Found {len(users)} matching users")
                return [UserResponse(**user) for user in users]
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to search users: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def assign_team_to_issue(
            issue_key: str,
            team_name: str,
            ctx: Optional[Context] = None
        ) -> TeamAssignmentResponse:
            """Assign a team to an issue by adding all team members as watchers.
            
            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                team_name: Name of the team to assign
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Assigning team '{team_name}' to issue: {issue_key}")
            
            try:
                team_members = self.config.get_team_members(team_name)
                result = await self.client.add_team_as_watchers(issue_key, team_members)
                
                if ctx:
                    await ctx.info(f"Added {result['total_added']} watchers, {result['total_failed']} failed")
                
                return TeamAssignmentResponse(
                    issue_key=result['issue_key'],
                    team_name=team_name,
                    successes=result['successes'],
                    failures=result['failures'],
                    total_added=result['total_added'],
                    total_failed=result['total_failed']
                )
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to assign team to {issue_key}: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def add_watcher_to_issue(
            issue_key: str,
            username: str,
            ctx: Optional[Context] = None
        ) -> Dict[str, Any]:
            """Add a watcher to an issue.
            
            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                username: Username of the user to add as watcher
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Adding watcher {username} to issue: {issue_key}")
            
            try:
                result = await self.client.add_watcher(issue_key, username)
                if ctx:
                    await ctx.info(f"Successfully added watcher {username}")
                return result
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to add watcher: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def remove_watcher_from_issue(
            issue_key: str,
            username: str,
            ctx: Optional[Context] = None
        ) -> Dict[str, Any]:
            """Remove a watcher from an issue.
            
            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                username: Username of the user to remove as watcher
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Removing watcher {username} from issue: {issue_key}")
            
            try:
                result = await self.client.remove_watcher(issue_key, username)
                if ctx:
                    await ctx.info(f"Successfully removed watcher {username}")
                return result
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to remove watcher: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def get_issue_watchers(
            issue_key: str,
            ctx: Optional[Context] = None
        ) -> List[WatcherResponse]:
            """Get all watchers for an issue.
            
            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Getting watchers for issue: {issue_key}")
            
            try:
                watchers = await self.client.get_watchers(issue_key)
                if ctx:
                    await ctx.info(f"Found {len(watchers)} watchers")
                return [WatcherResponse(**watcher) for watcher in watchers]
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to get watchers: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def list_teams(
            ctx: Optional[Context] = None
        ) -> TeamInfoResponse:
            """List all configured teams and their members.
            
            Args:
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info("Listing all teams")
            
            try:
                teams = self.config.list_teams()
                if ctx:
                    await ctx.info(f"Found {len(teams)} teams")
                return TeamInfoResponse(teams=teams)
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to list teams: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def add_team(
            team_name: str,
            members: List[str],
            ctx: Optional[Context] = None
        ) -> TeamInfoResponse:
            """Add or update a team configuration.
            
            Args:
                team_name: Name of the team
                members: List of member usernames
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Adding/updating team '{team_name}' with {len(members)} members")
            
            try:
                self.config.add_team(team_name, members)
                if ctx:
                    await ctx.info(f"Successfully added/updated team '{team_name}'")
                return TeamInfoResponse(teams=self.config.list_teams())
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to add team: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def remove_team(
            team_name: str,
            ctx: Optional[Context] = None
        ) -> TeamInfoResponse:
            """Remove a team configuration.
            
            Args:
                team_name: Name of the team to remove
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Removing team '{team_name}'")
            
            try:
                self.config.remove_team(team_name)
                if ctx:
                    await ctx.info(f"Successfully removed team '{team_name}'")
                return TeamInfoResponse(teams=self.config.list_teams())
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to remove team: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def list_component_aliases(
            ctx: Optional[Context] = None
        ) -> ComponentAliasResponse:
            """List all configured component aliases.
            
            Args:
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info("Listing all component aliases")
            
            try:
                aliases = self.config.list_component_aliases()
                if ctx:
                    await ctx.info(f"Found {len(aliases)} component aliases")
                return ComponentAliasResponse(aliases=aliases)
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to list component aliases: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def add_component_alias(
            alias: str,
            component_name: str,
            ctx: Optional[Context] = None
        ) -> ComponentAliasResponse:
            """Add or update a component alias configuration.
            
            Args:
                alias: Short alias for the component (e.g., 'ui', 'be', 'infra')
                component_name: Actual component name in Jira (e.g., 'User Interface', 'Backend Services')
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Adding/updating component alias '{alias}' -> '{component_name}'")
            
            try:
                self.config.add_component_alias(alias, component_name)
                if ctx:
                    await ctx.info(f"Successfully added/updated component alias '{alias}'")
                return ComponentAliasResponse(aliases=self.config.list_component_aliases())
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to add component alias: {str(e)}")
                raise
        
        @self.mcp.tool()
        async def remove_component_alias(
            alias: str,
            ctx: Optional[Context] = None
        ) -> ComponentAliasResponse:
            """Remove a component alias configuration.
            
            Args:
                alias: Alias to remove
                ctx: MCP context for progress reporting
            """
            if ctx:
                await ctx.info(f"Removing component alias '{alias}'")
            
            try:
                self.config.remove_component_alias(alias)
                if ctx:
                    await ctx.info(f"Successfully removed component alias '{alias}'")
                return ComponentAliasResponse(aliases=self.config.list_component_aliases())
            except Exception as e:
                if ctx:
                    await ctx.error(f"Failed to remove component alias: {str(e)}")
                raise
    def _setup_resources(self) -> None:
        """Set up MCP resources for Jira data."""
        
        @self.mcp.resource("jira://issue/{issue_key}")
        async def get_issue_resource(issue_key: str) -> str:
            """Get issue details as a formatted resource.
            
            Args:
                issue_key: Jira issue key (e.g., 'PROJ-123')
            """
            try:
                issue = await self.client.get_issue(issue_key)
                return f"""# {issue['key']}: {issue['summary']}

**Status:** {issue['status']}
**Priority:** {issue['priority']}
**Type:** {issue['issue_type']}
**Project:** {issue['project']}
**Assignee:** {issue['assignee'] or 'Unassigned'}
**Reporter:** {issue['reporter']}

## Description
{issue['description']}

## Details
- **Created:** {issue['created']}
- **Updated:** {issue['updated']}
- **Resolution:** {issue['resolution'] or 'Unresolved'}
- **Labels:** {', '.join(issue['labels']) if issue['labels'] else 'None'}
- **Components:** {', '.join(issue['components']) if issue['components'] else 'None'}
- **Fix Versions:** {', '.join(issue['fix_versions']) if issue['fix_versions'] else 'None'}
- **Target Version:** {', '.join(issue['target_version']) if issue['target_version'] else 'None'}
- **Work Type:** {issue['work_type'] or 'None'}
- **Security Level:** {issue['security_level'] or 'None'}
- **Due Date:** {issue['due_date'] or 'None'}
- **Target Start:** {issue['target_start'] or 'None'}
- **Target End:** {issue['target_end'] or 'None'}
- **Original Estimate:** {issue['original_estimate'] or 'None'}
- **Story Points:** {issue['story_points'] or 'None'}
- **Git Commit:** {issue['git_commit'] or 'None'}
- **Git Pull Requests:** {issue['git_pull_requests'] or 'None'}

**URL:** {issue['url']}
"""
            except Exception as e:
                return f"Error fetching issue {issue_key}: {str(e)}"
        
        @self.mcp.resource("jira://projects")
        async def get_projects_resource() -> str:
            """Get all projects as a formatted resource."""
            try:
                projects = await self.client.get_projects()
                result = "# Jira Projects\n\n"
                for project in projects:
                    result += f"## {project['key']}: {project['name']}\n"
                    if project['description']:
                        result += f"{project['description']}\n"
                    result += f"**Lead:** {project['lead']}\n\n"
                return result
            except Exception as e:
                return f"Error fetching projects: {str(e)}"
    
    async def _check_for_updates(self) -> None:
        """Check if origin/main has commits not present locally."""
        try:
            # Find the repo root (server may be installed anywhere)
            repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            git_dir = os.path.join(repo_dir, ".git")
            if not os.path.isdir(git_dir):
                return

            # Fetch latest refs from origin (quiet, no output)
            subprocess.run(
                ["git", "fetch", "origin", "main", "--quiet"],
                cwd=repo_dir, capture_output=True, timeout=10
            )

            # Count commits on origin/main that are not in local HEAD
            result = subprocess.run(
                ["git", "rev-list", "HEAD..origin/main", "--count"],
                cwd=repo_dir, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                count = int(result.stdout.strip())
                if count > 0:
                    self._update_warning = (
                        f"jira-mcp-server update available: origin/main is {count} "
                        f"commit(s) ahead. Run 'git pull' in {repo_dir} to update."
                    )
                    logger.warning(self._update_warning)
        except Exception as e:
            logger.debug(f"Update check failed (non-fatal): {e}")

    async def _emit_update_warning(self, ctx: Optional[Context]) -> None:
        """Emit update warning once per session via MCP context."""
        if self._update_warning and not self._update_warning_emitted and ctx:
            await ctx.warning(self._update_warning)
            self._update_warning_emitted = True

    async def start(self) -> None:
        """Start the MCP server."""
        try:
            self.config.validate_required_fields()
            await self.client.connect()
            logger.info("Connected to Jira successfully")
            logger.info(f"Server URL: {self.config.server_url}")
            await self._check_for_updates()
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
    
    def create_sse_app(self, host: str = "127.0.0.1", port: int = 8000):
        """Create SSE HTTP app for the MCP server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            
        Returns:
            ASGI application configured for SSE transport
        """
        return self.mcp.http_app(transport="sse")
    
    def run_sse_server(self, host: str = "127.0.0.1", port: int = 8000):
        """Run the MCP server with SSE transport.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        import uvicorn
        app = self.create_sse_app(host, port)
        logger.info(f"Starting SSE server on {host}:{port}")
        logger.info(f"SSE endpoint: http://{host}:{port}/sse")
        logger.info(f"Message endpoint: http://{host}:{port}/messages/")
        uvicorn.run(app, host=host, port=port)
    

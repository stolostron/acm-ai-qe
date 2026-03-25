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

"""Jira client wrapper for MCP server."""

import asyncio
from typing import List, Dict, Any, Optional
from jira import JIRA
from jira.exceptions import JIRAError
from asyncio_throttle import Throttler

from .config import JiraConfig


class JiraClient:
    """Async wrapper for Jira client with rate limiting."""
    
    def __init__(self, config: JiraConfig):
        """Initialize Jira client with configuration."""
        self.config = config
        self._jira: Optional[JIRA] = None
        self.throttler = Throttler(rate_limit=10, period=1.0)  # 10 requests per second
    
    async def connect(self) -> None:
        """Connect to Jira server using appropriate authentication method.

        For Jira Cloud (atlassian.net): Uses basic auth with email and API token
        For self-hosted Jira: Uses personal access token authentication
        """
        try:
            options = {
                'verify': self.config.verify_ssl,
                'timeout': self.config.timeout
            }

            if self.config.is_cloud():
                # Jira Cloud requires basic auth with email and API token
                self._jira = JIRA(
                    server=self.config.server_url,
                    basic_auth=(self.config.email, self.config.access_token),
                    options=options
                )
            else:
                # Self-hosted Jira uses personal access token
                self._jira = JIRA(
                    server=self.config.server_url,
                    token_auth=self.config.access_token,
                    options=options
                )

            # Test connection
            await self._async_call(lambda: self._jira.myself())
        except JIRAError as e:
            raise ConnectionError(f"Failed to connect to Jira: {e}")
    
    async def _async_call(self, func):
        """Execute synchronous Jira calls asynchronously with throttling."""
        async with self.throttler:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, func)
    
    async def search_issues(self, jql: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for issues using JQL."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")

        if max_results is None:
            max_results = self.config.max_results
        
        try:
            issues = await self._async_call(
                lambda: self._jira.search_issues(
                    jql,
                    maxResults=max_results,
                    expand='changelog'
                )
            )
            
            return [self._issue_to_dict(issue) for issue in issues]
        except JIRAError as e:
            raise ValueError(f"JQL search failed: {e}")
    
    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific issue by key."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(
                lambda: self._jira.issue(
                    issue_key,
                    expand='changelog,transitions,comments'
                )
            )
            return self._issue_to_dict(issue)
        except JIRAError as e:
            raise ValueError(f"Failed to get issue {issue_key}: {e}")
    
    async def create_issue(self, project_key: str, summary: str, description: str, 
                          issue_type: str = "Task", **fields) -> Dict[str, Any]:
        """Create a new issue."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        # Convert timetracking.originalEstimate from time string to minutes for Jira API
        if 'timetracking' in fields and isinstance(fields['timetracking'], dict):
            if 'originalEstimate' in fields['timetracking'] and isinstance(fields['timetracking']['originalEstimate'], str):
                seconds = self._time_string_to_seconds(fields['timetracking']['originalEstimate'])
                fields['timetracking']['originalEstimate'] = str(seconds // 60)  # Jira expects minutes as string
        
        issue_dict = {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': issue_type},
            **fields
        }
        
        try:
            issue = await self._async_call(
                lambda: self._jira.create_issue(fields=issue_dict)
            )
            return self._issue_to_dict(issue)
        except JIRAError as e:
            raise ValueError(f"Failed to create issue: {e}")
    
    async def update_issue(self, issue_key: str, **fields) -> Dict[str, Any]:
        """Update an existing issue."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        # Convert timetracking.originalEstimate from time string to minutes for Jira API
        if 'timetracking' in fields and isinstance(fields['timetracking'], dict):
            if 'originalEstimate' in fields['timetracking'] and isinstance(fields['timetracking']['originalEstimate'], str):
                seconds = self._time_string_to_seconds(fields['timetracking']['originalEstimate'])
                fields['timetracking']['originalEstimate'] = str(seconds // 60)  # Jira expects minutes as string
        
        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))
            await self._async_call(lambda: issue.update(fields=fields))
            # Return updated issue
            return await self.get_issue(issue_key)
        except JIRAError as e:
            raise ValueError(f"Failed to update issue {issue_key}: {e}")
    
    async def transition_issue(self, issue_key: str, transition: str) -> Dict[str, Any]:
        """Transition an issue to a new status."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))
            transitions = await self._async_call(lambda: self._jira.transitions(issue))
            
            # Find transition by name
            transition_id = None
            for t in transitions:
                if t['name'].lower() == transition.lower():
                    transition_id = t['id']
                    break
            
            if not transition_id:
                available = [t['name'] for t in transitions]
                raise ValueError(f"Transition '{transition}' not available. Available: {available}")
            
            await self._async_call(
                lambda: self._jira.transition_issue(issue, transition_id)
            )
            
            return await self.get_issue(issue_key)
        except JIRAError as e:
            raise ValueError(f"Failed to transition issue {issue_key}: {e}")
    
    async def add_comment(self, issue_key: str, comment: str, security_level: Optional[str] = None) -> Dict[str, Any]:
        """Add a comment to an issue."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")

        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))

            # Build comment parameters
            comment_kwargs = {}
            if security_level:
                # Use 'group' type for security levels like "Red Hat Employee"
                comment_kwargs['visibility'] = {'type': 'group', 'value': security_level}

            comment_obj = await self._async_call(
                lambda: self._jira.add_comment(issue, comment, **comment_kwargs)
            )
            
            return {
                'id': comment_obj.id,
                'body': comment_obj.body,
                'author': comment_obj.author.displayName,
                'created': comment_obj.created,
                'updated': comment_obj.updated
            }
        except JIRAError as e:
            raise ValueError(f"Failed to add comment to {issue_key}: {e}")
    
    async def log_work(self, issue_key: str, time_spent: str, comment: str, started: Optional[str] = None) -> Dict[str, Any]:
        """Log work time on an issue with a comment."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))
            
            # Prepare work log parameters
            work_log_params = {
                'timeSpent': time_spent,
                'comment': comment
            }
            
            # Add started time if provided
            if started:
                work_log_params['started'] = started
            
            # Log the work using direct parameters instead of a dictionary
            work_log_obj = await self._async_call(
                lambda: self._jira.add_worklog(issue, **work_log_params)
            )
            
            return {
                'id': work_log_obj.id,
                'time_spent': work_log_obj.timeSpent,
                'comment': work_log_obj.comment,
                'author': work_log_obj.author.displayName,
                'created': work_log_obj.created,
                'started': work_log_obj.started
            }
        except JIRAError as e:
            raise ValueError(f"Failed to log work on {issue_key}: {e}")
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")

        try:
            projects = await self._async_call(lambda: self._jira.projects())
            return [
                {
                    'key': project.key,
                    'name': project.name,
                    'description': getattr(project, 'description', ''),
                    'lead': getattr(project.lead, 'displayName', '') if hasattr(project, 'lead') else ''
                }
                for project in projects
            ]
        except JIRAError as e:
            raise ValueError(f"Failed to get projects: {e}")

    async def get_project_components(self, project_key: str) -> List[Dict[str, Any]]:
        """Get all components for a specific project."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")

        try:
            components = await self._async_call(
                lambda: self._jira.project_components(project_key)
            )
            return [
                {
                    'id': component.id,
                    'name': component.name,
                    'description': getattr(component, 'description', '') or '',
                    'lead': getattr(component.lead, 'displayName', '') if getattr(component, 'lead', None) else '',
                    'assignee_type': getattr(component, 'assigneeType', ''),
                    'is_assignee_type_valid': getattr(component, 'isAssigneeTypeValid', False)
                }
                for component in components
            ]
        except JIRAError as e:
            raise ValueError(f"Failed to get components for project {project_key}: {e}")
    
    async def create_issue_link(
        self, 
        link_type: str, 
        inward_issue: str, 
        outward_issue: str, 
        comment: Optional[str] = None,
        security_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a link between two issues.
        
        Args:
            link_type: The type of link to create (e.g., 'Blocks', 'Relates', 'Duplicates')
            inward_issue: The issue key to link from (e.g., 'PROJ-123')
            outward_issue: The issue key to link to (e.g., 'PROJ-456')
            comment: Optional comment to add when creating the link
            security_level: Optional security level for the comment
            
        Returns:
            Dict containing link information
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            # Prepare comment data if provided
            comment_data = None
            if comment:
                comment_data = {'body': comment}
                if security_level:
                    comment_data['visibility'] = {'type': 'group', 'value': security_level}
            
            # Create the issue link
            response = await self._async_call(
                lambda: self._jira.create_issue_link(
                    type=link_type,
                    inwardIssue=inward_issue,
                    outwardIssue=outward_issue,
                    comment=comment_data
                )
            )
            
            # Get link types to find the proper names
            link_types = await self._async_call(lambda: self._jira.issue_link_types())
            link_type_info = None
            for lt in link_types:
                if lt.name.lower() == link_type.lower():
                    link_type_info = lt
                    break
            
            return {
                'link_type': link_type,
                'inward_issue': inward_issue,
                'outward_issue': outward_issue,
                'inward_description': link_type_info.inward if link_type_info else None,
                'outward_description': link_type_info.outward if link_type_info else None,
                'comment': comment,
                'created': True
            }
            
        except JIRAError as e:
            raise ValueError(f"Failed to create issue link: {e}")
    
    async def get_issue_link_types(self) -> List[Dict[str, Any]]:
        """Get available issue link types.
        
        Returns:
            List of available link types with their descriptions
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            link_types = await self._async_call(lambda: self._jira.issue_link_types())
            return [
                {
                    'id': lt.id,
                    'name': lt.name,
                    'inward': lt.inward,
                    'outward': lt.outward
                }
                for lt in link_types
            ]
        except JIRAError as e:
            raise ValueError(f"Failed to get issue link types: {e}")

    async def search_users(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for Jira users by name or email.

        Args:
            query: Search query (name, email, or display name)
            max_results: Maximum number of results to return (default: 50)

        Returns:
            List of user dictionaries with account_id, name, display_name, email_address, active
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")

        try:
            if self.config.is_cloud():
                url = f"{self._jira._options['server']}/rest/api/3/user/search"
                response = await self._async_call(
                    lambda: self._jira._session.get(
                        url, params={'query': query, 'maxResults': max_results}
                    )
                )
                if not response.ok:
                    raise ValueError(f"User search failed: HTTP {response.status_code}")
                users_data = response.json()
                return [
                    {
                        'account_id': u.get('accountId'),
                        'name': u.get('name'),
                        'display_name': u.get('displayName', ''),
                        'email_address': u.get('emailAddress'),
                        'active': u.get('active', True)
                    }
                    for u in users_data
                ]
            else:
                users = await self._async_call(
                    lambda: self._jira.search_users(query, maxResults=max_results)
                )
                return [
                    {
                        'account_id': getattr(user, 'accountId', None),
                        'name': getattr(user, 'name', None),
                        'display_name': getattr(user, 'displayName', ''),
                        'email_address': getattr(user, 'emailAddress', None),
                        'active': getattr(user, 'active', True)
                    }
                    for user in users
                ]
        except JIRAError as e:
            raise ValueError(f"Failed to search users: {e}")

    async def get_raw_issue_fields(self, issue_key: str) -> Dict[str, Any]:
        """Get all raw fields from a Jira issue for debugging purposes."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(
                lambda: self._jira.issue(
                    issue_key,
                    expand='changelog,transitions,comments'
                )
            )
            
            # Convert the raw issue fields to a dictionary
            raw_fields = {}
            
            # Get all field attributes
            for field_name in dir(issue.fields):
                if not field_name.startswith('_'):
                    try:
                        field_value = getattr(issue.fields, field_name)
                        if field_value is not None:
                            # Try to serialize the field value
                            if hasattr(field_value, '__dict__'):
                                # Complex object, get its attributes
                                if hasattr(field_value, 'name'):
                                    raw_fields[field_name] = field_value.name
                                elif hasattr(field_value, 'value'):
                                    raw_fields[field_name] = field_value.value
                                else:
                                    raw_fields[field_name] = str(field_value)
                            elif isinstance(field_value, list):
                                # Handle lists
                                raw_fields[field_name] = [
                                    item.name if hasattr(item, 'name') else str(item) 
                                    for item in field_value
                                ]
                            else:
                                # Simple value
                                raw_fields[field_name] = field_value
                    except Exception as e:
                        # If we can't access a field, note the error
                        raw_fields[field_name] = f"Error accessing field: {str(e)}"
            
            # Add some metadata
            result = {
                'issue_key': issue.key,
                'raw_fields': raw_fields,
                'field_count': len(raw_fields)
            }
            
            return result
            
        except JIRAError as e:
            raise ValueError(f"Failed to get raw fields for issue {issue_key}: {e}")
    
    async def get_editmeta(self, issue_key: str) -> Dict[str, Any]:
        """Get edit metadata for an issue, describing each editable field's schema.

        Returns a dict mapping field IDs to their schema info (name, type, items, etc.).
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")

        try:
            url = f"{self._jira._options['server']}/rest/api/2/issue/{issue_key}/editmeta"
            response = await self._async_call(
                lambda: self._jira._session.get(url)
            )
            if not response.ok:
                raise ValueError(f"Failed to get edit metadata for {issue_key}: HTTP {response.status_code}")
            data = response.json()
            return data.get('fields', {})
        except JIRAError as e:
            raise ValueError(f"Failed to get edit metadata for {issue_key}: {e}") from e

    async def add_watcher(self, issue_key: str, username: str) -> Dict[str, Any]:
        """Add a watcher to an issue.
        
        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123')
            username: Username of the user to add as watcher
            
        Returns:
            Dict containing watcher information
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))
            await self._async_call(lambda: self._jira.add_watcher(issue, username))
            
            return {
                'issue_key': issue_key,
                'watcher': username,
                'added': True
            }
        except JIRAError as e:
            raise ValueError(f"Failed to add watcher {username} to {issue_key}: {e}")
    
    async def remove_watcher(self, issue_key: str, username: str) -> Dict[str, Any]:
        """Remove a watcher from an issue.
        
        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123')
            username: Username of the user to remove as watcher
            
        Returns:
            Dict containing watcher information
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))
            await self._async_call(lambda: self._jira.remove_watcher(issue, username))
            
            return {
                'issue_key': issue_key,
                'watcher': username,
                'removed': True
            }
        except JIRAError as e:
            raise ValueError(f"Failed to remove watcher {username} from {issue_key}: {e}")
    
    async def get_watchers(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get all watchers for an issue.
        
        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123')
            
        Returns:
            List of watchers with their information
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            watchers_obj = await self._async_call(
                lambda: self._jira.watchers(issue_key)
            )
            
            return [
                {
                    'username': watcher.name,
                    'display_name': watcher.displayName,
                    'email': getattr(watcher, 'emailAddress', None),
                    'active': getattr(watcher, 'active', True)
                }
                for watcher in watchers_obj.watchers
            ]
        except JIRAError as e:
            raise ValueError(f"Failed to get watchers for {issue_key}: {e}")
    
    async def add_team_as_watchers(self, issue_key: str, team_members: List[str]) -> Dict[str, Any]:
        """Add multiple team members as watchers to an issue.
        
        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123')
            team_members: List of usernames to add as watchers
            
        Returns:
            Dict containing success and failure information
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        successes = []
        failures = []
        
        for username in team_members:
            try:
                await self.add_watcher(issue_key, username)
                successes.append(username)
            except Exception as e:
                failures.append({'username': username, 'error': str(e)})
        
        return {
            'issue_key': issue_key,
            'successes': successes,
            'failures': failures,
            'total_added': len(successes),
            'total_failed': len(failures)
        }
    
    def _extract_custom_field_value(self, field_value):
        """Extract string value from custom field that might be a CustomFieldOption object."""
        if field_value is None:
            return None
        
        # Debug: log the type for troubleshooting
        field_type = type(field_value).__name__
        
        # Handle CustomFieldOption objects from Jira library
        if hasattr(field_value, 'value'):
            return str(field_value.value)
        # Handle dict-like objects that might have a 'value' key
        if isinstance(field_value, dict) and 'value' in field_value:
            return str(field_value['value'])
        # Handle string values directly
        if isinstance(field_value, str):
            return field_value
        # Handle objects with name attribute (common in Jira)
        if hasattr(field_value, 'name'):
            return str(field_value.name)
        
        # For CustomFieldOption specifically, try to access its string representation or properties
        if 'CustomFieldOption' in field_type:
            # Try various common attributes
            for attr in ['value', 'name', 'displayName', 'id']:
                if hasattr(field_value, attr):
                    val = getattr(field_value, attr)
                    if val is not None:
                        return str(val)
        
        # Fallback to string conversion
        return str(field_value)
    
    def _extract_git_pull_requests(self, field_value):
        """Extract git pull requests from custom field that might be a list or string."""
        if field_value is None:
            return None
        
        # If it's already a string, return it
        if isinstance(field_value, str):
            return field_value
        
        # If it's a list, join the items with commas
        if isinstance(field_value, list):
            # Filter out None values and convert all items to strings
            valid_items = [str(item) for item in field_value if item is not None]
            return ', '.join(valid_items) if valid_items else None
        
        # Fallback to string conversion
        return str(field_value)
    
    def _time_string_to_seconds(self, time_string: str) -> int:
        """Convert Jira time format (e.g., '1h 30m', '2d', '45m') to seconds."""
        if not time_string:
            return None
        
        # Remove whitespace and convert to lowercase
        time_string = time_string.replace(' ', '').lower()
        
        total_seconds = 0
        current_number = ''
        
        for char in time_string:
            if char.isdigit() or char == '.':
                current_number += char
            elif char in ['d', 'h', 'm', 's']:
                if current_number:
                    value = float(current_number)
                    if char == 'd':  # days
                        total_seconds += value * 24 * 3600
                    elif char == 'h':  # hours
                        total_seconds += value * 3600
                    elif char == 'm':  # minutes
                        total_seconds += value * 60
                    elif char == 's':  # seconds
                        total_seconds += value
                    current_number = ''
        
        return int(total_seconds)
    
    def _seconds_to_time_string(self, seconds: int) -> str:
        """Convert seconds to Jira time format (e.g., '1h 30m')."""
        if seconds is None:
            return None
        
        # Convert to days, hours, minutes
        days = seconds // (24 * 3600)
        remaining_seconds = seconds % (24 * 3600)
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        if not parts:
            return "0m"
        
        return " ".join(parts)
    
    def _parse_issue_links(self, links) -> List[Dict[str, Any]]:
        """Parse issue links into structured format."""
        result = []
        for link in links or []:
            try:
                link_type = getattr(getattr(link, 'type', None), 'name', 'unknown')
                outward = getattr(link, 'outwardIssue', None)
                inward = getattr(link, 'inwardIssue', None)
                target = outward or inward
                if not target:
                    continue

                key = getattr(target, 'key', None)
                if not key:
                    continue

                summary = getattr(getattr(target, 'fields', None), 'summary', None)
                result.append({
                    'type': link_type,
                    'direction': 'outward' if outward else 'inward',
                    'key': key,
                    'summary': summary,
                })
            except Exception:
                continue
        return result

    def _issue_to_dict(self, issue) -> Dict[str, Any]:
        """Convert Jira issue object to dictionary."""
        result = {
            'key': issue.key,
            'summary': issue.fields.summary,
            'description': getattr(issue.fields, 'description', '') or '',
            'status': issue.fields.status.name,
            'priority': getattr(issue.fields.priority, 'name', '') if issue.fields.priority else '',
            'issue_type': issue.fields.issuetype.name,
            'project': issue.fields.project.key,
            'assignee': issue.fields.assignee.displayName if issue.fields.assignee else None,
            'reporter': issue.fields.reporter.displayName if issue.fields.reporter else None,
            'created': issue.fields.created,
            'updated': issue.fields.updated,
            'resolution': issue.fields.resolution.name if issue.fields.resolution else None,
            'labels': getattr(issue.fields, 'labels', []),
            'components': [comp.name for comp in getattr(issue.fields, 'components', [])],
            'comments': [
                {
                    'id': comment.id,
                    'body': comment.body,
                    'author': comment.author.displayName,
                    'created': comment.created,
                    'updated': comment.updated
                }
                for comment in getattr(getattr(issue.fields, 'comment', None), 'comments', []) or []
            ],
            'url': f"{self.config.server_url}/browse/{issue.key}",
            'fix_versions': [version.name for version in getattr(issue.fields, 'fixVersions', [])],
            'target_version': [v.name for v in getattr(issue.fields, 'customfield_10855', []) or []],  # Target Version custom field
            'work_type': self._extract_custom_field_value(getattr(issue.fields, 'customfield_10464', None)),  # Activity Type (formerly Work Type)
            'security_level': getattr(issue.fields.security, 'name', None) if getattr(issue.fields, 'security', None) else None,
            'due_date': getattr(issue.fields, 'duedate', None),
            'target_start': getattr(issue.fields, 'customfield_10022', None),  # Target Start custom field
            'target_end': getattr(issue.fields, 'customfield_10023', None),  # Target End custom field
            'original_estimate': self._seconds_to_time_string(getattr(issue.fields, 'timeoriginalestimate', None)),
            'story_points': getattr(issue.fields, 'customfield_10028', None),  # Story points custom field
            'git_commit': self._extract_custom_field_value(getattr(issue.fields, 'customfield_10583', None)),  # Git Commit custom field
            'git_pull_requests': self._extract_git_pull_requests(getattr(issue.fields, 'customfield_10875', None)),  # Git Pull Requests custom field
            'subtasks': [
                {
                    'key': subtask.key,
                    'summary': subtask.fields.summary,
                    'status': subtask.fields.status.name,
                    'issue_type': subtask.fields.issuetype.name
                }
                for subtask in getattr(issue.fields, 'subtasks', [])
            ],
            'parent': {
                'key': issue.fields.parent.key,
                'summary': issue.fields.parent.fields.summary,
                'issue_type': issue.fields.parent.fields.issuetype.name
            } if getattr(issue.fields, 'parent', None) else None,
            'parent_link': getattr(issue.fields, 'customfield_10014', None),  # Parent Link custom field
            'epic_link': getattr(issue.fields, 'customfield_10014', None),  # Epic Link custom field
            'sprint': self._extract_sprint(getattr(issue.fields, 'customfield_10020', None)),
            'qa_contact': self._extract_user_display_name(getattr(issue.fields, 'customfield_10470', None)),
            'severity': self._extract_custom_field_value(getattr(issue.fields, 'customfield_10840', None)),
            'affects_versions': [v.name for v in getattr(issue.fields, 'versions', []) or []],
            'acceptance_criteria': getattr(issue.fields, 'customfield_10718', None),
            'contributors': self._extract_user_list(getattr(issue.fields, 'customfield_10466', None)),
            'issue_links': self._parse_issue_links(getattr(issue.fields, 'issuelinks', []) or []),
            'attachments': [a.filename for a in getattr(issue.fields, 'attachment', []) or []],
        }

        return result

    @staticmethod
    def _extract_sprint(sprint_data) -> Optional[str]:
        """Extract sprint name from Jira Cloud sprint field.

        The field may be: a list of sprint objects (with .name), a list of
        strings, a single object, or None.  Returns the name of the last
        (most recent) sprint.
        """
        if not sprint_data:
            return None
        items = sprint_data if isinstance(sprint_data, list) else [sprint_data]
        if not items:
            return None
        last = items[-1]
        if hasattr(last, 'name'):
            return last.name
        return str(last) if last else None

    @staticmethod
    def _extract_user_display_name(field_value) -> Optional[str]:
        """Extract display name from a user-type field (may be object or string)."""
        if field_value is None:
            return None
        if hasattr(field_value, 'displayName'):
            return field_value.displayName
        return str(field_value) if field_value else None

    @staticmethod
    def _extract_user_list(field_value) -> List[str]:
        """Extract list of display names from a multi-user field (may be strings or objects)."""
        if not field_value:
            return []
        if isinstance(field_value, str):
            field_value = [field_value]
        elif not isinstance(field_value, (list, tuple)):
            field_value = [field_value]
        result = []
        for item in field_value:
            if hasattr(item, 'displayName'):
                result.append(item.displayName)
            elif isinstance(item, str):
                result.append(item)
            else:
                result.append(str(item))
        return result
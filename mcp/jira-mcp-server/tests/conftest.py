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

"""Shared test fixtures for JIRA MCP server tests."""

from unittest.mock import MagicMock


def make_mock_issue(
    key="TEST-1",
    summary="Test issue",
    description="Test description",
    status="New",
    priority="Major",
    issue_type="Task",
    project="TEST",
    assignee="testuser",
    reporter="reporter",
    created="2025-01-01T00:00:00.000+0000",
    updated="2025-01-02T00:00:00.000+0000",
    resolution=None,
    labels=None,
    components=None,
    comments=None,
    fix_versions=None,
    target_version=None,
    work_type=None,
    security=None,
    duedate=None,
    target_start=None,
    target_end=None,
    timeoriginalestimate=None,
    story_points=None,
    git_commit=None,
    git_pull_requests=None,
    subtasks=None,
    parent=None,
    sprint_data=None,
    qa_contact=None,
    epic_link=None,
    severity=None,
    versions=None,
    acceptance_criteria=None,
    contributors=None,
    issuelinks=None,
    attachments=None,
):
    """Create a mock JIRA issue object for testing _issue_to_dict."""
    issue = MagicMock()
    issue.key = key

    fields = MagicMock()
    fields.summary = summary
    fields.description = description

    # Status
    status_obj = MagicMock()
    status_obj.name = status
    fields.status = status_obj

    # Priority
    if priority:
        priority_obj = MagicMock()
        priority_obj.name = priority
        fields.priority = priority_obj
    else:
        fields.priority = None

    # Issue type
    issuetype_obj = MagicMock()
    issuetype_obj.name = issue_type
    fields.issuetype = issuetype_obj

    # Project
    project_obj = MagicMock()
    project_obj.key = project
    fields.project = project_obj

    # Assignee
    if assignee:
        assignee_obj = MagicMock()
        assignee_obj.displayName = assignee
        fields.assignee = assignee_obj
    else:
        fields.assignee = None

    # Reporter
    if reporter:
        reporter_obj = MagicMock()
        reporter_obj.displayName = reporter
        fields.reporter = reporter_obj
    else:
        fields.reporter = None

    fields.created = created
    fields.updated = updated

    # Resolution
    if resolution:
        resolution_obj = MagicMock()
        resolution_obj.name = resolution
        fields.resolution = resolution_obj
    else:
        fields.resolution = None

    fields.labels = labels or []

    # Components
    comp_objs = []
    for c in (components or []):
        comp_obj = MagicMock()
        comp_obj.name = c
        comp_objs.append(comp_obj)
    fields.components = comp_objs

    # Comments
    comment_container = MagicMock()
    comment_list = []
    for c in (comments or []):
        comment_obj = MagicMock()
        comment_obj.id = c.get('id', '1')
        comment_obj.body = c.get('body', '')
        author_obj = MagicMock()
        author_obj.displayName = c.get('author', 'author')
        comment_obj.author = author_obj
        comment_obj.created = c.get('created', created)
        comment_obj.updated = c.get('updated', updated)
        comment_list.append(comment_obj)
    comment_container.comments = comment_list
    fields.comment = comment_container

    # Fix versions
    fv_objs = []
    for v in (fix_versions or []):
        fv_obj = MagicMock()
        fv_obj.name = v
        fv_objs.append(fv_obj)
    fields.fixVersions = fv_objs

    # Target version (custom field)
    tv_objs = []
    for v in (target_version or []):
        tv_obj = MagicMock()
        tv_obj.name = v
        tv_objs.append(tv_obj)
    fields.customfield_10855 = tv_objs or None

    # Work type (Activity Type)
    if work_type:
        wt_obj = MagicMock()
        wt_obj.value = work_type
        fields.customfield_10464 = wt_obj
    else:
        fields.customfield_10464 = None

    # Security
    if security:
        sec_obj = MagicMock()
        sec_obj.name = security
        fields.security = sec_obj
    else:
        fields.security = None

    fields.duedate = duedate
    fields.customfield_10022 = target_start
    fields.customfield_10023 = target_end
    fields.timeoriginalestimate = timeoriginalestimate
    fields.customfield_10028 = story_points
    
    # Git commit
    if git_commit:
        gc_obj = MagicMock()
        gc_obj.value = git_commit
        fields.customfield_10583 = gc_obj
    else:
        fields.customfield_10583 = None

    fields.customfield_10875 = git_pull_requests

    # Subtasks
    st_objs = []
    for st in (subtasks or []):
        st_obj = MagicMock()
        st_obj.key = st['key']
        st_fields = MagicMock()
        st_fields.summary = st['summary']
        st_status = MagicMock()
        st_status.name = st['status']
        st_fields.status = st_status
        st_type = MagicMock()
        st_type.name = st.get('issue_type', 'Sub-task')
        st_fields.issuetype = st_type
        st_obj.fields = st_fields
        st_objs.append(st_obj)
    fields.subtasks = st_objs

    # Parent
    if parent:
        parent_obj = MagicMock()
        parent_obj.key = parent['key']
        parent_fields = MagicMock()
        parent_fields.summary = parent['summary']
        parent_type = MagicMock()
        parent_type.name = parent.get('issue_type', 'Story')
        parent_fields.issuetype = parent_type
        parent_obj.fields = parent_fields
        fields.parent = parent_obj
    else:
        fields.parent = None

    # Parent Link / Epic Link (cloud uses same field)
    fields.customfield_10014 = epic_link

    # Sprint (cloud: array of sprint name strings)
    fields.customfield_10020 = sprint_data

    # QA Contact
    fields.customfield_10470 = qa_contact

    # Severity
    if severity:
        sev_obj = MagicMock()
        sev_obj.value = severity
        fields.customfield_10840 = sev_obj
    else:
        fields.customfield_10840 = None

    # Affects Versions
    ver_objs = []
    for v in (versions or []):
        ver_obj = MagicMock()
        ver_obj.name = v
        ver_objs.append(ver_obj)
    fields.versions = ver_objs

    # Acceptance Criteria
    fields.customfield_10718 = acceptance_criteria

    # Contributors (multi-user picker)
    contributor_objs = []
    for c in (contributors or []):
        c_obj = MagicMock()
        c_obj.displayName = c
        contributor_objs.append(c_obj)
    fields.customfield_10466 = contributor_objs or None

    # Issue Links
    link_objs = []
    for lnk in (issuelinks or []):
        link_obj = MagicMock()
        link_type_obj = MagicMock()
        link_type_obj.name = lnk['type']
        link_obj.type = link_type_obj
        if lnk['direction'] == 'outward':
            outward = MagicMock()
            outward.key = lnk['key']
            outward_fields = MagicMock()
            outward_fields.summary = lnk['summary']
            outward.fields = outward_fields
            link_obj.outwardIssue = outward
            # Make sure inwardIssue is not present
            del link_obj.inwardIssue
        else:
            inward = MagicMock()
            inward.key = lnk['key']
            inward_fields = MagicMock()
            inward_fields.summary = lnk['summary']
            inward.fields = inward_fields
            link_obj.inwardIssue = inward
            # Make sure outwardIssue is not present
            del link_obj.outwardIssue
        link_objs.append(link_obj)
    fields.issuelinks = link_objs

    # Attachments
    att_objs = []
    for a in (attachments or []):
        att_obj = MagicMock()
        att_obj.filename = a
        att_objs.append(att_obj)
    fields.attachment = att_objs

    issue.fields = fields
    return issue

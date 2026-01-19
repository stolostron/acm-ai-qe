"""
Mock JIRA Data Fixtures
========================

Centralized mock JIRA ticket data for testing Agent A and related components.
Supports various ticket scenarios without external API dependencies.
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class MockJIRATicket:
    """Mock JIRA ticket structure matching real API responses."""
    key: str
    title: str
    description: str
    status: str
    priority: str
    component: str
    fix_version: str
    assignee: str
    labels: List[str]
    comments: List[Dict[str, str]]
    subtasks: List[Dict[str, Any]]
    linked_issues: List[Dict[str, Any]]


# Standard test tickets with various scenarios
MOCK_JIRA_TICKETS: Dict[str, MockJIRATicket] = {
    # Ticket with full PR references in description
    "PROJECT-12345": MockJIRATicket(
        key="PROJECT-12345",
        title="Implement feature X with configuration Y",
        description="""
        Full description with requirements...

        Implementation includes:
        - Feature A: Core functionality
        - Feature B: Configuration management
        - Feature C: Integration with external systems

        Related PRs:
        - PR #468: https://github.com/org/repo/pull/468
        - PR #469 for additional changes

        Acceptance Criteria:
        - [ ] Feature A works correctly
        - [ ] Feature B handles edge cases
        - [ ] Integration with systems verified
        """,
        status="In Progress",
        priority="High",
        component="ClusterCurator",
        fix_version="2.15.0",
        assignee="developer1",
        labels=["QE-Required", "E2E-Testing"],
        comments=[
            {"author": "dev1", "body": "PR #468 ready for review"},
            {"author": "qa1", "body": "Tested on staging environment"}
        ],
        subtasks=[],
        linked_issues=[]
    ),

    # Ticket with no PR references
    "PROJECT-54321": MockJIRATicket(
        key="PROJECT-54321",
        title="Add new configuration option for feature",
        description="""
        Add ability to configure feature behavior through new settings.

        Technical Details:
        - New configuration fields required
        - Backward compatibility must be maintained
        - Documentation updates needed
        """,
        status="Open",
        priority="Medium",
        component="Policy",
        fix_version="2.16.0",
        assignee="developer2",
        labels=["Configuration"],
        comments=[],
        subtasks=[],
        linked_issues=[]
    ),

    # Ticket with multiple components
    "PROJECT-99999": MockJIRATicket(
        key="PROJECT-99999",
        title="Cross-component integration for observability",
        description="""
        Integration between multiple components for enhanced observability.

        Components Involved:
        - Observability controller
        - Metrics collector
        - Alert manager

        Requirements:
        - All components must work together seamlessly
        - Performance requirements must be met
        """,
        status="In Development",
        priority="Critical",
        component="Observability,Metrics,Alerting",
        fix_version="2.15.0",
        assignee="developer3",
        labels=["Cross-Component", "Integration"],
        comments=[
            {"author": "architect", "body": "Design approved"},
            {"author": "dev3", "body": "Implementation in progress on PR #500"}
        ],
        subtasks=[
            {"key": "PROJECT-99999-1", "summary": "Implement metrics collector"},
            {"key": "PROJECT-99999-2", "summary": "Integrate alert manager"}
        ],
        linked_issues=[
            {"key": "PROJECT-88888", "type": "blocks"}
        ]
    ),

    # Ticket with missing fix_version
    "PROJECT-NOVERSION": MockJIRATicket(
        key="PROJECT-NOVERSION",
        title="Bug fix for edge case handling",
        description="Fix edge case in feature processing.",
        status="Open",
        priority="Low",
        component="Console",
        fix_version="",  # No version specified
        assignee="developer4",
        labels=["Bugfix"],
        comments=[],
        subtasks=[],
        linked_issues=[]
    ),

    # Ticket with empty description
    "PROJECT-EMPTYDESC": MockJIRATicket(
        key="PROJECT-EMPTYDESC",
        title="Short ticket with no description",
        description="",
        status="Open",
        priority="Medium",
        component="Application",
        fix_version="2.15.0",
        assignee="developer5",
        labels=[],
        comments=[],
        subtasks=[],
        linked_issues=[]
    ),

    # Ticket for ClusterCurator digest-based upgrades (ACM-22079 style)
    "ACM-22079": MockJIRATicket(
        key="ACM-22079",
        title="ClusterCurator digest-based upgrades support",
        description="""
        Implement digest-based upgrade mechanism for ClusterCurator.

        Feature Description:
        - Support digest-based image references for cluster upgrades
        - Enable disconnected environment support
        - Provide fallback mechanism for upgrade failures

        Technical Requirements:
        - ClusterCurator controller updates
        - CRD schema modifications
        - API version compatibility

        Related PR: https://github.com/stolostron/cluster-curator-controller/pull/468

        Acceptance Criteria:
        - Digest-based upgrades complete successfully
        - Fallback mechanism works as expected
        - Disconnected environments supported
        """,
        status="In Progress",
        priority="High",
        component="ClusterCurator",
        fix_version="2.15.0",
        assignee="developer1",
        labels=["QE-Required", "Upgrade", "Disconnected"],
        comments=[
            {"author": "dev1", "body": "PR #468 implements core functionality"},
            {"author": "qa1", "body": "Ready for QE validation"}
        ],
        subtasks=[],
        linked_issues=[]
    ),

    # Minimal viable ticket
    "PROJECT-MINIMAL": MockJIRATicket(
        key="PROJECT-MINIMAL",
        title="Minimal ticket for testing",
        description="Basic description.",
        status="Open",
        priority="Medium",
        component="Unknown",
        fix_version="1.0.0",
        assignee="",
        labels=[],
        comments=[],
        subtasks=[],
        linked_issues=[]
    )
}


def get_mock_jira_ticket(ticket_id: str) -> MockJIRATicket:
    """Get a mock JIRA ticket by ID."""
    return MOCK_JIRA_TICKETS.get(ticket_id, MOCK_JIRA_TICKETS["PROJECT-MINIMAL"])


def create_custom_jira_ticket(
    key: str,
    title: str = "Custom Test Ticket",
    description: str = "Custom description for testing",
    status: str = "Open",
    priority: str = "Medium",
    component: str = "TestComponent",
    fix_version: str = "1.0.0",
    **kwargs
) -> MockJIRATicket:
    """Create a custom mock JIRA ticket with specified parameters."""
    return MockJIRATicket(
        key=key,
        title=title,
        description=description,
        status=status,
        priority=priority,
        component=component,
        fix_version=fix_version,
        assignee=kwargs.get("assignee", "tester"),
        labels=kwargs.get("labels", []),
        comments=kwargs.get("comments", []),
        subtasks=kwargs.get("subtasks", []),
        linked_issues=kwargs.get("linked_issues", [])
    )


# Mock JIRA API client for testing
class MockJiraApiClient:
    """Mock JIRA API client for unit testing."""

    def __init__(self, tickets: Dict[str, MockJIRATicket] = None):
        self.tickets = tickets or MOCK_JIRA_TICKETS
        self.call_count = 0
        self.last_ticket_id = None
        self.should_fail = False
        self.failure_message = "Mock API failure"

    def set_failure_mode(self, should_fail: bool, message: str = "Mock API failure"):
        """Configure the mock to simulate API failures."""
        self.should_fail = should_fail
        self.failure_message = message

    async def get_ticket_information(self, ticket_id: str):
        """Mock implementation of JIRA ticket retrieval."""
        self.call_count += 1
        self.last_ticket_id = ticket_id

        if self.should_fail:
            raise Exception(self.failure_message)

        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise Exception(f"Ticket {ticket_id} not found")

        return ticket

    def get_call_count(self) -> int:
        """Get the number of API calls made."""
        return self.call_count

    def reset(self):
        """Reset the mock state."""
        self.call_count = 0
        self.last_ticket_id = None
        self.should_fail = False


# Expected outputs for JIRA analysis scenarios
EXPECTED_JIRA_ANALYSIS_OUTPUTS = {
    "PROJECT-12345": {
        "pr_references": ["468", "469"],
        "component_analysis": {
            "primary_component": "ClusterCurator",
            "component_count": 1
        },
        "has_acceptance_criteria": True,
        "sufficiency_score_min": 0.75
    },
    "PROJECT-54321": {
        "pr_references": [],
        "component_analysis": {
            "primary_component": "Policy",
            "component_count": 1
        },
        "has_acceptance_criteria": False,
        "sufficiency_score_min": 0.60
    },
    "PROJECT-99999": {
        "pr_references": ["500"],
        "component_analysis": {
            "primary_component": "Observability",
            "component_count": 3
        },
        "has_acceptance_criteria": True,
        "sufficiency_score_min": 0.80
    },
    "ACM-22079": {
        "pr_references": ["468"],
        "component_analysis": {
            "primary_component": "ClusterCurator",
            "component_count": 1
        },
        "has_acceptance_criteria": True,
        "sufficiency_score_min": 0.85
    }
}

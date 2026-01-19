"""
Mock GitHub Data Fixtures
==========================

Centralized mock GitHub PR and repository data for testing Agent C
and GitHub MCP integration.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class MockPRFile:
    """Mock PR file change structure."""
    filename: str
    additions: int
    deletions: int
    status: str = "modified"


@dataclass
class MockPullRequest:
    """Mock GitHub Pull Request structure."""
    number: int
    title: str
    body: str
    state: str
    files: List[MockPRFile]
    commits: List[Dict[str, Any]]
    reviews: List[Dict[str, Any]]
    author: str
    base_branch: str
    head_branch: str


# Standard mock PRs for testing
MOCK_PR_DATA: Dict[str, MockPullRequest] = {
    "468": MockPullRequest(
        number=468,
        title="Add digest-based upgrade support for ClusterCurator",
        body="""
        This PR implements digest-based upgrade support for ClusterCurator.

        ## Changes
        - Added digest resolution for cluster upgrades
        - Implemented fallback mechanism for upgrade failures
        - Updated CRD schema with new fields

        ## Testing
        - Unit tests added
        - Integration tests updated
        - Manual testing completed on staging

        Fixes: ACM-22079
        """,
        state="open",
        files=[
            MockPRFile(filename="pkg/controller/clustercurator_controller.go", additions=150, deletions=30),
            MockPRFile(filename="pkg/api/v1beta1/clustercurator_types.go", additions=45, deletions=5),
            MockPRFile(filename="config/crd/bases/cluster.open-cluster-management.io_clustercurators.yaml", additions=80, deletions=10),
            MockPRFile(filename="test/e2e/clustercurator_upgrade_test.go", additions=200, deletions=0, status="added"),
            MockPRFile(filename="docs/digest-based-upgrades.md", additions=100, deletions=0, status="added")
        ],
        commits=[
            {"sha": "abc123", "message": "Add digest resolution logic"},
            {"sha": "def456", "message": "Implement fallback mechanism"},
            {"sha": "ghi789", "message": "Update CRD schema"}
        ],
        reviews=[
            {"user": "reviewer1", "state": "APPROVED", "body": "LGTM"},
            {"user": "reviewer2", "state": "COMMENTED", "body": "Minor suggestions"}
        ],
        author="developer1",
        base_branch="main",
        head_branch="feature/digest-upgrades"
    ),

    "500": MockPullRequest(
        number=500,
        title="Cross-component observability integration",
        body="""
        Integration PR for observability components.

        ## Components Updated
        - Observability controller
        - Metrics collector
        - Alert manager
        """,
        state="open",
        files=[
            MockPRFile(filename="pkg/observability/controller.go", additions=100, deletions=20),
            MockPRFile(filename="pkg/metrics/collector.go", additions=80, deletions=15),
            MockPRFile(filename="pkg/alerts/manager.go", additions=60, deletions=10)
        ],
        commits=[
            {"sha": "obs123", "message": "Add observability integration"}
        ],
        reviews=[],
        author="developer3",
        base_branch="main",
        head_branch="feature/observability-integration"
    ),

    # Large PR with many files (100+ files)
    "999": MockPullRequest(
        number=999,
        title="Large refactoring PR",
        body="Major codebase refactoring across multiple packages.",
        state="open",
        files=[MockPRFile(filename=f"pkg/module{i}/file{j}.go", additions=10, deletions=5)
               for i in range(10) for j in range(12)],  # 120 files
        commits=[{"sha": f"commit{i}", "message": f"Refactor module {i}"} for i in range(15)],
        reviews=[],
        author="developer4",
        base_branch="main",
        head_branch="feature/major-refactor"
    ),

    # Security-sensitive PR
    "666": MockPullRequest(
        number=666,
        title="Security authentication improvements",
        body="Updates to authentication and authorization mechanisms.",
        state="open",
        files=[
            MockPRFile(filename="pkg/auth/authentication.go", additions=200, deletions=50),
            MockPRFile(filename="pkg/auth/authorization.go", additions=150, deletions=30),
            MockPRFile(filename="pkg/crypto/encryption.go", additions=100, deletions=20),
            MockPRFile(filename="config/rbac/role.yaml", additions=30, deletions=5)
        ],
        commits=[
            {"sha": "sec123", "message": "Improve authentication flow"},
            {"sha": "sec456", "message": "Update authorization logic"}
        ],
        reviews=[
            {"user": "security-reviewer", "state": "CHANGES_REQUESTED", "body": "Need security review"}
        ],
        author="security-dev",
        base_branch="main",
        head_branch="feature/security-improvements"
    )
}


def get_mock_pr(pr_number: str) -> Optional[MockPullRequest]:
    """Get a mock PR by number."""
    return MOCK_PR_DATA.get(pr_number)


def create_custom_pr(
    number: int,
    title: str = "Test PR",
    body: str = "Test PR description",
    files: List[Dict[str, Any]] = None,
    **kwargs
) -> MockPullRequest:
    """Create a custom mock PR with specified parameters."""
    if files is None:
        files = [MockPRFile(filename="test/file.go", additions=10, deletions=5)]
    else:
        files = [MockPRFile(**f) for f in files]

    return MockPullRequest(
        number=number,
        title=title,
        body=body,
        state=kwargs.get("state", "open"),
        files=files,
        commits=kwargs.get("commits", []),
        reviews=kwargs.get("reviews", []),
        author=kwargs.get("author", "test-author"),
        base_branch=kwargs.get("base_branch", "main"),
        head_branch=kwargs.get("head_branch", f"feature/test-{number}")
    )


# Mock GitHub MCP responses
class MockGitHubMCPClient:
    """Mock GitHub MCP client for testing."""

    def __init__(self, prs: Dict[str, MockPullRequest] = None):
        self.prs = prs or MOCK_PR_DATA
        self.call_count = 0
        self.should_fail = False
        self.failure_message = "Mock MCP failure"
        self.available = True

    def set_failure_mode(self, should_fail: bool, message: str = "Mock MCP failure"):
        """Configure the mock to simulate failures."""
        self.should_fail = should_fail
        self.failure_message = message

    def set_availability(self, available: bool):
        """Set whether the MCP is available."""
        self.available = available

    def get_pull_request(self, repo: str, pr_number: int) -> Dict[str, Any]:
        """Mock implementation of PR retrieval."""
        self.call_count += 1

        if not self.available:
            return {"status": "error", "error": "MCP not available"}

        if self.should_fail:
            return {"status": "error", "error": self.failure_message}

        pr = self.prs.get(str(pr_number))
        if not pr:
            return {"status": "error", "error": f"PR #{pr_number} not found"}

        return {
            "status": "success",
            "data": {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "files": [{"filename": f.filename, "additions": f.additions, "deletions": f.deletions}
                         for f in pr.files],
                "author": {"login": pr.author}
            }
        }

    def get_pull_request_files(self, repo: str, pr_number: int) -> Dict[str, Any]:
        """Mock implementation of PR files retrieval."""
        self.call_count += 1

        if not self.available:
            return {"status": "error", "error": "MCP not available"}

        if self.should_fail:
            return {"status": "error", "error": self.failure_message}

        pr = self.prs.get(str(pr_number))
        if not pr:
            return {"status": "error", "error": f"PR #{pr_number} not found"}

        return {
            "status": "success",
            "data": {
                "files": [{"filename": f.filename, "additions": f.additions,
                          "deletions": f.deletions, "status": f.status}
                         for f in pr.files]
            }
        }

    def search_repositories(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Mock implementation of repository search."""
        self.call_count += 1

        if not self.available:
            return {"status": "error", "error": "MCP not available"}

        if self.should_fail:
            return {"status": "error", "error": self.failure_message}

        # Return mock search results
        return {
            "status": "success",
            "data": {
                "items": [
                    {"fullName": "stolostron/cluster-curator-controller", "url": "https://github.com/stolostron/cluster-curator-controller"},
                    {"fullName": "stolostron/acm-e2e", "url": "https://github.com/stolostron/acm-e2e"}
                ]
            }
        }

    def reset(self):
        """Reset the mock state."""
        self.call_count = 0
        self.should_fail = False
        self.available = True


# Expected analysis outputs for PR scenarios
EXPECTED_PR_ANALYSIS_OUTPUTS = {
    "468": {
        "files_count": 5,
        "has_tests": True,
        "has_docs": True,
        "deployment_components": ["ClusterCurator", "Controller", "CustomResourceDefinition"],
        "is_security_sensitive": False,
        "change_impact": "medium"
    },
    "500": {
        "files_count": 3,
        "has_tests": False,
        "has_docs": False,
        "deployment_components": ["Observability", "Metrics", "Alerts"],
        "is_security_sensitive": False,
        "change_impact": "medium"
    },
    "999": {
        "files_count": 120,
        "has_tests": False,
        "has_docs": False,
        "deployment_components": [],
        "is_security_sensitive": False,
        "change_impact": "high"
    },
    "666": {
        "files_count": 4,
        "has_tests": False,
        "has_docs": False,
        "deployment_components": ["Auth", "Crypto"],
        "is_security_sensitive": True,
        "change_impact": "high"
    }
}


# Mock repository data for QE intelligence analysis
MOCK_REPOSITORY_DATA = {
    "stolostron/cluster-curator-controller": {
        "name": "cluster-curator-controller",
        "description": "Cluster lifecycle curator for ACM",
        "language": "Go",
        "test_framework": "Ginkgo",
        "test_file_count": 45,
        "stars": 25
    },
    "stolostron/acm-e2e": {
        "name": "acm-e2e",
        "description": "End-to-end tests for ACM",
        "language": "TypeScript",
        "test_framework": "Cypress",
        "test_file_count": 150,
        "stars": 15
    },
    "stolostron/clc-ui-e2e": {
        "name": "clc-ui-e2e",
        "description": "UI E2E tests for cluster lifecycle",
        "language": "JavaScript",
        "test_framework": "Cypress",
        "test_file_count": 78,
        "stars": 10
    }
}

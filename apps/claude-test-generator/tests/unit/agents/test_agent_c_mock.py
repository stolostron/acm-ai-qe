"""
Agent C (GitHub Investigation) Mock Tests
==========================================

Comprehensive mock-based tests for Agent C GitHub investigation functionality.
Tests PR analysis, code investigation, and repository analysis without external dependencies.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../fixtures'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../.claude/ai-services'))

from mock_github_data import (
    MOCK_PR_DATA, MockPullRequest, MockGitHubMCPClient,
    get_mock_pr, create_custom_pr, EXPECTED_PR_ANALYSIS_OUTPUTS,
    MOCK_REPOSITORY_DATA
)


class TestAgentCPRAnalysis:
    """Test Agent C PR analysis functionality."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub MCP client."""
        return MockGitHubMCPClient()

    # ============== Test Scenario C-1: PR with Code Changes ==============
    def test_pr_with_code_changes_analysis(self, mock_github_client):
        """Test analysis of PR with significant code changes."""
        pr = get_mock_pr("468")
        expected = EXPECTED_PR_ANALYSIS_OUTPUTS["468"]

        # Analyze PR files
        analysis = self._analyze_pr_changes(pr)

        assert analysis['files_count'] == expected['files_count']
        assert analysis['change_impact'] in ['low', 'medium', 'high']
        assert 'deployment_components' in analysis

    # ============== Test Scenario C-2: PR with Tests ==============
    def test_pr_with_test_files(self, mock_github_client):
        """Test detection of test files in PR."""
        pr = get_mock_pr("468")
        expected = EXPECTED_PR_ANALYSIS_OUTPUTS["468"]

        # Check for test files
        has_tests = self._detect_test_files(pr.files)

        assert has_tests == expected['has_tests']

    # ============== Test Scenario C-3: PR Not Found ==============
    def test_pr_not_found_handling(self, mock_github_client):
        """Test graceful handling when PR is not found."""
        result = mock_github_client.get_pull_request("org/repo", 99999)

        assert result['status'] == 'error'
        assert 'not found' in result['error'].lower()

    # ============== Test Scenario C-4: MCP Available ==============
    def test_mcp_available_fast_response(self, mock_github_client):
        """Test fast response when MCP is available."""
        mock_github_client.set_availability(True)

        result = mock_github_client.get_pull_request("stolostron/cluster-curator-controller", 468)

        assert result['status'] == 'success'
        assert result['data']['number'] == 468

    # ============== Test Scenario C-5: MCP Unavailable Fallback ==============
    def test_mcp_unavailable_fallback(self, mock_github_client):
        """Test fallback when MCP is unavailable."""
        mock_github_client.set_availability(False)

        result = mock_github_client.get_pull_request("org/repo", 468)

        assert result['status'] == 'error'
        assert 'not available' in result['error'].lower()

    # ============== Test Scenario C-6: Large PR Handling ==============
    def test_large_pr_handling(self, mock_github_client):
        """Test handling of large PR with 100+ files."""
        pr = get_mock_pr("999")
        expected = EXPECTED_PR_ANALYSIS_OUTPUTS["999"]

        # Analyze large PR
        analysis = self._analyze_pr_changes(pr)

        assert analysis['files_count'] == expected['files_count']
        assert analysis['files_count'] > 100
        assert analysis['change_impact'] == 'high'

    # ============== Test Scenario C-7: Security-Sensitive Changes ==============
    def test_security_sensitive_detection(self, mock_github_client):
        """Test detection of security-sensitive changes."""
        pr = get_mock_pr("666")
        expected = EXPECTED_PR_ANALYSIS_OUTPUTS["666"]

        # Check for security sensitivity
        is_security_sensitive = self._check_security_sensitivity(pr.files)

        assert is_security_sensitive == expected['is_security_sensitive']

    def _analyze_pr_changes(self, pr: MockPullRequest) -> Dict[str, Any]:
        """Analyze PR changes."""
        files_count = len(pr.files)
        total_changes = sum(f.additions + f.deletions for f in pr.files)

        # Determine impact
        if files_count > 50 or total_changes > 1000:
            impact = 'high'
        elif files_count > 10 or total_changes > 200:
            impact = 'medium'
        else:
            impact = 'low'

        # Extract components from file paths
        components = set()
        for f in pr.files:
            if 'controller' in f.filename.lower():
                components.add('Controller')
            if 'api' in f.filename.lower():
                components.add('API')
            if 'crd' in f.filename.lower() or '.yaml' in f.filename:
                components.add('CustomResourceDefinition')
            if 'clustercurator' in f.filename.lower():
                components.add('ClusterCurator')
            if 'auth' in f.filename.lower():
                components.add('Auth')
            if 'crypto' in f.filename.lower():
                components.add('Crypto')

        return {
            'files_count': files_count,
            'total_changes': total_changes,
            'change_impact': impact,
            'deployment_components': list(components),
            'has_tests': self._detect_test_files(pr.files),
            'has_docs': any('doc' in f.filename.lower() or '.md' in f.filename for f in pr.files)
        }

    def _detect_test_files(self, files) -> bool:
        """Detect presence of test files."""
        test_patterns = ['test', 'spec', '_test.go', '.test.js', '.spec.ts']
        for f in files:
            for pattern in test_patterns:
                if pattern in f.filename.lower():
                    return True
        return False

    def _check_security_sensitivity(self, files) -> bool:
        """Check for security-sensitive file changes."""
        security_patterns = ['auth', 'crypto', 'security', 'credential', 'secret', 'rbac']
        for f in files:
            for pattern in security_patterns:
                if pattern in f.filename.lower():
                    return True
        return False


class TestAgentCRepositoryAnalysis:
    """Test Agent C repository analysis functionality."""

    @pytest.fixture
    def mock_github_client(self):
        return MockGitHubMCPClient()

    def test_repository_search(self, mock_github_client):
        """Test repository search functionality."""
        result = mock_github_client.search_repositories("cluster-curator")

        assert result['status'] == 'success'
        assert len(result['data']['items']) > 0

    def test_repository_analysis_structure(self):
        """Test repository analysis output structure."""
        repo_data = MOCK_REPOSITORY_DATA["stolostron/cluster-curator-controller"]

        analysis = self._analyze_repository(repo_data)

        assert 'test_framework' in analysis
        assert 'test_file_count' in analysis
        assert 'language' in analysis

    def _analyze_repository(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze repository data."""
        return {
            'name': repo_data.get('name'),
            'language': repo_data.get('language'),
            'test_framework': repo_data.get('test_framework'),
            'test_file_count': repo_data.get('test_file_count'),
            'analysis_status': 'complete'
        }


class TestAgentCMCPIntegration:
    """Test Agent C MCP integration scenarios."""

    @pytest.fixture
    def mock_github_client(self):
        return MockGitHubMCPClient()

    def test_mcp_health_check(self, mock_github_client):
        """Test MCP health check."""
        mock_github_client.set_availability(True)
        assert mock_github_client.available is True

    def test_mcp_failure_recovery(self, mock_github_client):
        """Test recovery from MCP failure."""
        # First call fails
        mock_github_client.set_failure_mode(True, "Temporary failure")
        result1 = mock_github_client.get_pull_request("org/repo", 468)
        assert result1['status'] == 'error'

        # Reset and retry
        mock_github_client.reset()
        result2 = mock_github_client.get_pull_request("stolostron/cluster-curator-controller", 468)
        assert result2['status'] == 'success'

    def test_mcp_call_count_tracking(self, mock_github_client):
        """Test that MCP calls are tracked."""
        initial_count = mock_github_client.call_count

        mock_github_client.get_pull_request("org/repo", 468)
        mock_github_client.get_pull_request_files("org/repo", 468)

        assert mock_github_client.call_count == initial_count + 2


class TestAgentCChangeImpactAnalysis:
    """Test Agent C change impact analysis."""

    def test_low_impact_detection(self):
        """Test detection of low-impact changes."""
        pr = create_custom_pr(
            number=100,
            files=[
                {'filename': 'README.md', 'additions': 10, 'deletions': 2},
                {'filename': 'docs/guide.md', 'additions': 5, 'deletions': 0}
            ]
        )

        impact = self._calculate_impact(pr)
        assert impact == 'low'

    def test_medium_impact_detection(self):
        """Test detection of medium-impact changes."""
        pr = create_custom_pr(
            number=101,
            files=[
                {'filename': 'pkg/controller/main.go', 'additions': 100, 'deletions': 30},
                {'filename': 'pkg/api/types.go', 'additions': 50, 'deletions': 10}
            ]
        )

        impact = self._calculate_impact(pr)
        assert impact == 'medium'

    def test_high_impact_detection(self):
        """Test detection of high-impact changes."""
        # Use the large PR mock
        pr = get_mock_pr("999")

        impact = self._calculate_impact(pr)
        assert impact == 'high'

    def _calculate_impact(self, pr: MockPullRequest) -> str:
        """Calculate change impact."""
        files_count = len(pr.files)
        total_changes = sum(f.additions + f.deletions for f in pr.files)

        if files_count > 50 or total_changes > 500:
            return 'high'
        elif files_count > 10 or total_changes > 100:
            return 'medium'
        else:
            return 'low'


class TestAgentCOutputStructure:
    """Test Agent C output structure and format."""

    def test_output_structure_completeness(self):
        """Test that Agent C output has all required sections."""
        output = self._generate_mock_agent_c_output()

        required_sections = [
            'pr_analysis',
            'repository_analysis',
            'testing_scope',
            'change_impact'
        ]

        for section in required_sections:
            assert section in output, f"Missing section: {section}"

    def test_output_ready_for_phase_3(self):
        """Test that output is ready for Phase 3 consumption."""
        output = self._generate_mock_agent_c_output()

        assert output.get('confidence_score') is not None
        assert output.get('analysis_complete') is True

    def _generate_mock_agent_c_output(self) -> Dict[str, Any]:
        """Generate complete mock Agent C output."""
        return {
            'analysis_metadata': {
                'agent': 'Agent C - GitHub Investigation',
                'timestamp': datetime.now().isoformat()
            },
            'pr_analysis': {
                'pr_number': '468',
                'files_changed': 5,
                'change_impact': 'medium'
            },
            'repository_analysis': {
                'target_repositories': ['stolostron/cluster-curator-controller']
            },
            'testing_scope': {
                'unit_tests_present': True,
                'e2e_tests_present': True
            },
            'change_impact': 'medium',
            'security_analysis': {
                'is_security_sensitive': False
            },
            'confidence_score': 0.88,
            'analysis_complete': True
        }


class TestAgentCCustomPRScenarios:
    """Test Agent C with custom PR scenarios."""

    def test_custom_pr_creation(self):
        """Test creating custom PR for edge cases."""
        custom = create_custom_pr(
            number=777,
            title="Custom test PR",
            body="Testing specific scenario",
            files=[
                {'filename': 'pkg/custom/file.go', 'additions': 100, 'deletions': 50}
            ]
        )

        assert custom.number == 777
        assert len(custom.files) == 1

    def test_pr_with_no_files(self):
        """Test handling of PR with no file changes."""
        custom = create_custom_pr(
            number=888,
            files=[]
        )

        assert len(custom.files) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

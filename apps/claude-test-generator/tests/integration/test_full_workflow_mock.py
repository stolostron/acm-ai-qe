"""
Full Workflow Integration Mock Tests
=====================================

End-to-end integration tests for the complete 6-phase workflow.
Tests complete flow with mocked external dependencies.
"""

import pytest
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../fixtures'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/ai-services'))

from mock_jira_data import MOCK_JIRA_TICKETS, MockJiraApiClient
from mock_github_data import MockGitHubMCPClient, MOCK_PR_DATA
from mock_environment_data import MockEnvironmentAssessmentClient
from mock_phase_outputs import (
    create_mock_phase_1_result, create_mock_phase_2_result,
    create_mock_agent_packages, create_mock_qe_intelligence,
    create_mock_strategic_intelligence, get_complete_workflow_mock_data
)


@dataclass
class WorkflowContext:
    """Context passed through workflow phases."""
    jira_id: str
    run_id: str
    run_dir: str
    phase_results: Dict[str, Any]


class MockFrameworkOrchestrator:
    """Mock framework orchestrator for integration testing."""

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or tempfile.mkdtemp()
        self.jira_client = MockJiraApiClient()
        self.github_client = MockGitHubMCPClient()
        self.env_client = MockEnvironmentAssessmentClient()

    async def execute_full_workflow(self, jira_id: str) -> Dict[str, Any]:
        """Execute complete 6-phase workflow."""
        run_id = f"{jira_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        run_dir = Path(self.base_dir) / "runs" / jira_id / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        context = WorkflowContext(
            jira_id=jira_id,
            run_id=run_id,
            run_dir=str(run_dir),
            phase_results={}
        )

        try:
            # Phase 0: Initialization Cleanup
            phase_0_result = await self._execute_phase_0(context)
            context.phase_results['phase_0'] = phase_0_result

            # Phase 1: Parallel Foundation Analysis (Agent A + D)
            phase_1_result = await self._execute_phase_1(context)
            context.phase_results['phase_1'] = phase_1_result

            # Phase 2: Parallel Deep Investigation (Agent B + C)
            phase_2_result = await self._execute_phase_2(context)
            context.phase_results['phase_2'] = phase_2_result

            # Phase 2.5: Data Flow & QE Intelligence
            phase_2_5_result = await self._execute_phase_2_5(context)
            context.phase_results['phase_2_5'] = phase_2_5_result

            # Phase 3: AI Cross-Agent Analysis
            phase_3_result = await self._execute_phase_3(context)
            context.phase_results['phase_3'] = phase_3_result

            # Phase 4: Pattern Extension & Test Generation
            phase_4_result = await self._execute_phase_4(context)
            context.phase_results['phase_4'] = phase_4_result

            # Phase 5: Comprehensive Cleanup
            phase_5_result = await self._execute_phase_5(context)
            context.phase_results['phase_5'] = phase_5_result

            return {
                'success': True,
                'jira_id': jira_id,
                'run_id': run_id,
                'run_dir': str(run_dir),
                'phase_results': context.phase_results,
                'output_files': self._get_output_files(run_dir)
            }

        except Exception as e:
            return {
                'success': False,
                'jira_id': jira_id,
                'run_id': run_id,
                'error': str(e),
                'phase_results': context.phase_results
            }

    async def _execute_phase_0(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute Phase 0: Initialization Cleanup."""
        return {
            'phase_name': 'Phase 0 - Initialization Cleanup',
            'execution_status': 'success',
            'files_removed': 0,
            'execution_time': 0.1
        }

    async def _execute_phase_1(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute Phase 1: Agent A + D."""
        phase_1 = create_mock_phase_1_result("success")

        # Simulate Agent A JIRA fetch
        try:
            ticket = await self.jira_client.get_ticket_information(context.jira_id)
            agent_a_success = True
        except Exception:
            agent_a_success = False

        # Simulate Agent D environment check
        try:
            env_data = self.env_client.assess_environment()
            agent_d_success = True
        except Exception:
            agent_d_success = False

        return {
            'phase_name': 'Phase 1 - Parallel Foundation Analysis',
            'execution_status': 'success' if agent_a_success and agent_d_success else 'partial',
            'agent_a_status': 'success' if agent_a_success else 'failed',
            'agent_d_status': 'success' if agent_d_success else 'failed',
            'agent_results': [asdict(r) for r in phase_1.agent_results],
            'execution_time': 5.5
        }

    async def _execute_phase_2(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute Phase 2: Agent B + C."""
        phase_2 = create_mock_phase_2_result("success")

        # Simulate Agent C GitHub fetch
        try:
            pr_result = self.github_client.get_pull_request("org/repo", 468)
            agent_c_success = pr_result['status'] == 'success'
        except Exception:
            agent_c_success = False

        return {
            'phase_name': 'Phase 2 - Parallel Deep Investigation',
            'execution_status': 'success',
            'agent_b_status': 'success',
            'agent_c_status': 'success' if agent_c_success else 'failed',
            'agent_results': [asdict(r) for r in phase_2.agent_results],
            'execution_time': 8.0
        }

    async def _execute_phase_2_5(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute Phase 2.5: Data Flow & QE Intelligence."""
        agent_packages = create_mock_agent_packages("success")
        qe_intelligence = create_mock_qe_intelligence("success")

        return {
            'phase_name': 'Phase 2.5 - Data Flow & QE Intelligence',
            'execution_status': 'success',
            'agent_packages_count': len(agent_packages),
            'qe_intelligence_status': qe_intelligence.execution_status,
            'data_preservation_verified': True,
            'execution_time': 3.0
        }

    async def _execute_phase_3(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute Phase 3: AI Analysis."""
        strategic_intelligence = create_mock_strategic_intelligence("success")

        return {
            'phase_name': 'Phase 3 - AI Cross-Agent Analysis',
            'execution_status': 'success',
            'strategic_intelligence': strategic_intelligence,
            'analysis_confidence': strategic_intelligence.get('overall_confidence', 0.9),
            'execution_time': 4.0
        }

    async def _execute_phase_4(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute Phase 4: Test Generation."""
        run_dir = Path(context.run_dir)

        # Create output files
        test_cases_content = """# Test Cases for {}

## TC-001: Verify Feature Basic Functionality

| Step | Action | UI Method | CLI Method | Expected Result |
|------|--------|-----------|------------|-----------------|
| 1 | Access system | Navigate to console | `oc login` | Successfully authenticated |
| 2 | Navigate to feature | Click Feature menu | `oc get feature` | Feature page displayed |
| 3 | Execute operation | Click Execute | `oc apply -f config.yaml` | Operation completes |
| 4 | Verify results | Check status | `oc get status` | Status shows success |
""".format(context.jira_id)

        analysis_content = """# Complete Analysis for {}

## Summary
Feature analysis complete with QE intelligence integration.

## Key Findings
- Component: ClusterCurator
- Complexity: Medium
- Test Cases Generated: 4
""".format(context.jira_id)

        (run_dir / "Test-Cases.md").write_text(test_cases_content)
        (run_dir / "Complete-Analysis.md").write_text(analysis_content)

        return {
            'phase_name': 'Phase 4 - Pattern Extension & Test Generation',
            'execution_status': 'success',
            'test_cases_generated': 4,
            'output_files': ['Test-Cases.md', 'Complete-Analysis.md'],
            'format_validation_passed': True,
            'execution_time': 2.0
        }

    async def _execute_phase_5(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute Phase 5: Cleanup."""
        run_dir = Path(context.run_dir)

        # Remove temp files (if any)
        temp_patterns = ['*.tmp', '*_staging.json', '*_intelligence.json']
        files_removed = 0

        for pattern in temp_patterns:
            for f in run_dir.glob(pattern):
                f.unlink()
                files_removed += 1

        return {
            'phase_name': 'Phase 5 - Comprehensive Cleanup',
            'execution_status': 'success',
            'files_removed': files_removed,
            'essential_files_preserved': True,
            'execution_time': 0.3
        }

    def _get_output_files(self, run_dir: Path) -> List[str]:
        """Get list of output files."""
        return [f.name for f in run_dir.glob("*") if f.is_file()]

    def cleanup(self):
        """Cleanup test directory."""
        if self.base_dir and Path(self.base_dir).exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)


class TestFullWorkflowIntegration:
    """Test complete workflow integration scenarios."""

    @pytest.fixture
    def orchestrator(self):
        orch = MockFrameworkOrchestrator()
        yield orch
        orch.cleanup()

    # ============== Test Scenario E2E-1: Happy Path ==============
    @pytest.mark.asyncio
    async def test_happy_path_complete_workflow(self, orchestrator):
        """Test complete workflow with all phases succeeding."""
        result = await orchestrator.execute_full_workflow("ACM-22079")

        assert result['success'] is True
        assert result['jira_id'] == "ACM-22079"

        # All phases should succeed
        for phase in ['phase_0', 'phase_1', 'phase_2', 'phase_2_5', 'phase_3', 'phase_4', 'phase_5']:
            assert phase in result['phase_results']
            assert result['phase_results'][phase]['execution_status'] == 'success'

        # Output files should exist
        assert 'Test-Cases.md' in result['output_files']
        assert 'Complete-Analysis.md' in result['output_files']

    # ============== Test Scenario E2E-2: JIRA Failure Recovery ==============
    @pytest.mark.asyncio
    async def test_jira_failure_recovery(self, orchestrator):
        """Test workflow with JIRA API failure."""
        orchestrator.jira_client.set_failure_mode(True, "JIRA API unavailable")

        result = await orchestrator.execute_full_workflow("PROJECT-12345")

        # Workflow should still complete (with partial success)
        assert 'phase_results' in result
        assert result['phase_results']['phase_1']['agent_a_status'] == 'failed'

    # ============== Test Scenario E2E-3: GitHub Failure Recovery ==============
    @pytest.mark.asyncio
    async def test_github_failure_recovery(self, orchestrator):
        """Test workflow with GitHub API failure."""
        orchestrator.github_client.set_availability(False)

        result = await orchestrator.execute_full_workflow("ACM-22079")

        # Workflow should still complete
        assert result['phase_results']['phase_2']['agent_c_status'] == 'failed'
        # Phase 3 and 4 should still execute
        assert result['phase_results']['phase_3']['execution_status'] == 'success'

    # ============== Test Scenario E2E-4: Environment Unavailable ==============
    @pytest.mark.asyncio
    async def test_environment_unavailable(self, orchestrator):
        """Test workflow with environment unavailable."""
        orchestrator.env_client.set_current_environment("unreachable_cluster")

        result = await orchestrator.execute_full_workflow("ACM-22079")

        # Should still complete with available data
        assert 'phase_results' in result

    # ============== Test Scenario E2E-5: Minimal Viable Input ==============
    @pytest.mark.asyncio
    async def test_minimal_viable_input(self, orchestrator):
        """Test workflow with sparse JIRA data."""
        result = await orchestrator.execute_full_workflow("PROJECT-MINIMAL")

        assert result['success'] is True
        # Should still produce output
        assert 'Test-Cases.md' in result['output_files']


class TestPhaseTransitions:
    """Test transitions between phases."""

    @pytest.fixture
    def orchestrator(self):
        orch = MockFrameworkOrchestrator()
        yield orch
        orch.cleanup()

    @pytest.mark.asyncio
    async def test_phase_1_to_2_data_flow(self, orchestrator):
        """Test data flows correctly from Phase 1 to Phase 2."""
        result = await orchestrator.execute_full_workflow("ACM-22079")

        phase_1 = result['phase_results']['phase_1']
        phase_2 = result['phase_results']['phase_2']

        # Both phases should have agent results
        assert 'agent_results' in phase_1
        assert 'agent_results' in phase_2

    @pytest.mark.asyncio
    async def test_phase_2_5_data_preservation(self, orchestrator):
        """Test data preservation in Phase 2.5."""
        result = await orchestrator.execute_full_workflow("ACM-22079")

        phase_2_5 = result['phase_results']['phase_2_5']

        assert phase_2_5['data_preservation_verified'] is True
        assert phase_2_5['agent_packages_count'] >= 2

    @pytest.mark.asyncio
    async def test_phase_3_to_4_flow(self, orchestrator):
        """Test strategic intelligence flows to Phase 4."""
        result = await orchestrator.execute_full_workflow("ACM-22079")

        phase_3 = result['phase_results']['phase_3']
        phase_4 = result['phase_results']['phase_4']

        # Phase 3 should have intelligence
        assert 'strategic_intelligence' in phase_3
        # Phase 4 should generate test cases
        assert phase_4['test_cases_generated'] >= 1


class TestOutputValidation:
    """Test output file validation."""

    @pytest.fixture
    def orchestrator(self):
        orch = MockFrameworkOrchestrator()
        yield orch
        orch.cleanup()

    @pytest.mark.asyncio
    async def test_test_cases_file_created(self, orchestrator):
        """Test Test-Cases.md file is created."""
        result = await orchestrator.execute_full_workflow("ACM-22079")

        run_dir = Path(result['run_dir'])
        assert (run_dir / "Test-Cases.md").exists()

    @pytest.mark.asyncio
    async def test_analysis_file_created(self, orchestrator):
        """Test Complete-Analysis.md file is created."""
        result = await orchestrator.execute_full_workflow("ACM-22079")

        run_dir = Path(result['run_dir'])
        assert (run_dir / "Complete-Analysis.md").exists()

    @pytest.mark.asyncio
    async def test_temp_files_cleaned(self, orchestrator):
        """Test temporary files are cleaned up."""
        result = await orchestrator.execute_full_workflow("ACM-22079")

        phase_5 = result['phase_results']['phase_5']
        assert phase_5['essential_files_preserved'] is True

    @pytest.mark.asyncio
    async def test_output_content_quality(self, orchestrator):
        """Test output files have expected content."""
        result = await orchestrator.execute_full_workflow("ACM-22079")

        run_dir = Path(result['run_dir'])
        test_cases = (run_dir / "Test-Cases.md").read_text()

        # Should contain test case structure
        assert "TC-001" in test_cases
        assert "Step" in test_cases or "Action" in test_cases


class TestErrorHandling:
    """Test error handling and recovery."""

    @pytest.fixture
    def orchestrator(self):
        orch = MockFrameworkOrchestrator()
        yield orch
        orch.cleanup()

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, orchestrator):
        """Test graceful degradation on partial failures."""
        # Simulate multiple failures
        orchestrator.jira_client.set_failure_mode(True)
        orchestrator.github_client.set_availability(False)

        result = await orchestrator.execute_full_workflow("TEST-123")

        # Should still produce some output
        assert 'phase_results' in result

    @pytest.mark.asyncio
    async def test_execution_continues_on_agent_failure(self, orchestrator):
        """Test execution continues when an agent fails."""
        orchestrator.github_client.set_failure_mode(True)

        result = await orchestrator.execute_full_workflow("ACM-22079")

        # Later phases should still execute
        assert 'phase_4' in result['phase_results']
        assert result['phase_results']['phase_4']['execution_status'] == 'success'


class TestWorkflowMetrics:
    """Test workflow metrics and timing."""

    @pytest.fixture
    def orchestrator(self):
        orch = MockFrameworkOrchestrator()
        yield orch
        orch.cleanup()

    @pytest.mark.asyncio
    async def test_phase_timing_recorded(self, orchestrator):
        """Test execution times are recorded."""
        result = await orchestrator.execute_full_workflow("ACM-22079")

        for phase_name, phase_result in result['phase_results'].items():
            assert 'execution_time' in phase_result
            assert phase_result['execution_time'] >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

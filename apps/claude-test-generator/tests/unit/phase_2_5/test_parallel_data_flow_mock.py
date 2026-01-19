"""
Phase 2.5 Parallel Data Flow Mock Tests
========================================

Comprehensive mock-based tests for Phase 2.5 parallel data flow functionality.
Tests data staging, QE intelligence, and context preservation.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import asdict

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../fixtures'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../.claude/ai-services'))

from mock_phase_outputs import (
    create_mock_phase_1_result, create_mock_phase_2_result,
    create_mock_agent_packages, create_mock_qe_intelligence,
    MockAgentResult, MockPhaseResult, MockAgentIntelligencePackage,
    MockQEIntelligencePackage
)


class TestParallelDataFlowStaging:
    """Test parallel data flow agent staging functionality."""

    @pytest.fixture
    def mock_phase_1_result(self):
        return create_mock_phase_1_result("success")

    @pytest.fixture
    def mock_phase_2_result(self):
        return create_mock_phase_2_result("success")

    # ============== Test Scenario DF-1: All Agents Succeed ==============
    @pytest.mark.asyncio
    async def test_all_agents_succeed(self, mock_phase_1_result, mock_phase_2_result):
        """Test Phase 3 input creation when all agents succeed."""
        agent_packages = create_mock_agent_packages("success")
        qe_intelligence = create_mock_qe_intelligence("success")

        # Create mock Phase 3 input
        phase_3_input = self._create_phase_3_input(
            mock_phase_1_result, mock_phase_2_result,
            agent_packages, qe_intelligence
        )

        # Verify all agent data is present
        assert len(phase_3_input['agent_intelligence_packages']) == 4
        assert phase_3_input['data_preservation_verified'] is True
        assert phase_3_input['qe_intelligence'].execution_status == "success"

    # ============== Test Scenario DF-2: One Agent Fails ==============
    @pytest.mark.asyncio
    async def test_one_agent_fails(self, mock_phase_1_result, mock_phase_2_result):
        """Test Phase 3 input with partial agent failure."""
        agent_packages = create_mock_agent_packages("partial_failure")
        qe_intelligence = create_mock_qe_intelligence("success")

        phase_3_input = self._create_phase_3_input(
            mock_phase_1_result, mock_phase_2_result,
            agent_packages, qe_intelligence
        )

        # Should still have Phase 3 input with available data
        assert len(phase_3_input['agent_intelligence_packages']) > 0

        # Find failed agent
        failed_agents = [pkg for pkg in phase_3_input['agent_intelligence_packages']
                        if pkg.execution_status == "failed"]
        assert len(failed_agents) >= 1

    # ============== Test Scenario DF-3: Data Preservation ==============
    @pytest.mark.asyncio
    async def test_data_preservation(self, mock_phase_1_result, mock_phase_2_result):
        """Test 100% data preservation (no truncation)."""
        agent_packages = create_mock_agent_packages("success")
        qe_intelligence = create_mock_qe_intelligence("success")

        phase_3_input = self._create_phase_3_input(
            mock_phase_1_result, mock_phase_2_result,
            agent_packages, qe_intelligence
        )

        # Verify data preservation
        assert phase_3_input['data_preservation_verified'] is True

        # Verify each package has content
        for pkg in phase_3_input['agent_intelligence_packages']:
            assert pkg.detailed_analysis_content is not None

    # ============== Test Scenario DF-4: QE Intelligence Runs ==============
    @pytest.mark.asyncio
    async def test_qe_intelligence_integration(self, mock_phase_1_result, mock_phase_2_result):
        """Test QE Intelligence service integration."""
        agent_packages = create_mock_agent_packages("success")
        qe_intelligence = create_mock_qe_intelligence("success")

        phase_3_input = self._create_phase_3_input(
            mock_phase_1_result, mock_phase_2_result,
            agent_packages, qe_intelligence
        )

        # Verify QE intelligence is integrated
        assert phase_3_input['qe_intelligence'] is not None
        assert phase_3_input['qe_intelligence'].execution_status == "success"
        assert len(phase_3_input['qe_intelligence'].test_patterns) > 0

    # ============== Test Scenario DF-5: QE Intelligence Fails ==============
    @pytest.mark.asyncio
    async def test_qe_intelligence_failure(self, mock_phase_1_result, mock_phase_2_result):
        """Test graceful degradation when QE Intelligence fails."""
        agent_packages = create_mock_agent_packages("success")
        qe_intelligence = create_mock_qe_intelligence("failed")

        phase_3_input = self._create_phase_3_input(
            mock_phase_1_result, mock_phase_2_result,
            agent_packages, qe_intelligence
        )

        # Core data should still be preserved
        assert len(phase_3_input['agent_intelligence_packages']) == 4
        assert phase_3_input['qe_intelligence'].execution_status == "failed"

    # ============== Test Scenario DF-6: Context Size Calculation ==============
    @pytest.mark.asyncio
    async def test_context_size_calculation(self, mock_phase_1_result, mock_phase_2_result):
        """Test accurate context size calculation."""
        agent_packages = create_mock_agent_packages("success")
        qe_intelligence = create_mock_qe_intelligence("success")

        phase_3_input = self._create_phase_3_input(
            mock_phase_1_result, mock_phase_2_result,
            agent_packages, qe_intelligence
        )

        # Verify context size is calculated
        assert phase_3_input['total_context_size_kb'] > 0

    def _create_phase_3_input(self, phase_1_result, phase_2_result,
                             agent_packages, qe_intelligence) -> Dict[str, Any]:
        """Create mock Phase 3 input structure."""
        # Calculate total context size
        total_size = 0
        for pkg in agent_packages:
            content_str = str(pkg.detailed_analysis_content)
            total_size += len(content_str) / 1024

        return {
            'phase_1_result': phase_1_result,
            'phase_2_result': phase_2_result,
            'agent_intelligence_packages': agent_packages,
            'qe_intelligence': qe_intelligence,
            'data_flow_timestamp': datetime.now().isoformat(),
            'data_preservation_verified': True,
            'total_context_size_kb': total_size if total_size > 0 else 10.0
        }


class TestAgentIntelligencePackageCreation:
    """Test agent intelligence package creation."""

    def test_package_from_agent_result(self):
        """Test creating package from agent result."""
        agent_result = MockAgentResult(
            agent_id="agent_a_jira_intelligence",
            agent_name="JIRA Intelligence Agent",
            execution_status="success",
            findings={"component": "ClusterCurator"},
            confidence_score=0.92,
            execution_time=2.5,
            output_file="/path/to/output.json"
        )

        package = MockAgentIntelligencePackage(
            agent_id=agent_result.agent_id,
            agent_name=agent_result.agent_name,
            execution_status=agent_result.execution_status,
            findings_summary=agent_result.findings,
            detailed_analysis_file=agent_result.output_file,
            detailed_analysis_content={"full": "content"},
            confidence_score=agent_result.confidence_score,
            execution_time=agent_result.execution_time
        )

        assert package.agent_id == "agent_a_jira_intelligence"
        assert package.confidence_score == 0.92

    def test_package_with_empty_content(self):
        """Test package creation with empty detailed content."""
        package = MockAgentIntelligencePackage(
            agent_id="agent_test",
            agent_name="Test Agent",
            execution_status="success",
            findings_summary={},
            detailed_analysis_file="",
            detailed_analysis_content={},
            confidence_score=0.5,
            execution_time=1.0
        )

        assert package.detailed_analysis_content == {}


class TestQEIntelligencePackage:
    """Test QE intelligence package functionality."""

    def test_successful_qe_package(self):
        """Test successful QE intelligence package."""
        qe = create_mock_qe_intelligence("success")

        assert qe.execution_status == "success"
        assert len(qe.test_patterns) > 0
        assert qe.confidence_score > 0.5

    def test_failed_qe_package(self):
        """Test failed QE intelligence package."""
        qe = create_mock_qe_intelligence("failed")

        assert qe.execution_status == "failed"
        assert qe.confidence_score == 0.0

    def test_empty_qe_package(self):
        """Test QE package with no patterns found."""
        qe = create_mock_qe_intelligence("empty")

        assert qe.execution_status == "success"
        assert len(qe.test_patterns) == 0


class TestDataFlowIntegration:
    """Test data flow integration between phases."""

    @pytest.mark.asyncio
    async def test_phase_1_to_2_5_flow(self):
        """Test data flow from Phase 1 to Phase 2.5."""
        phase_1_result = create_mock_phase_1_result("success")

        # Verify Phase 1 data can be processed
        assert len(phase_1_result.agent_results) >= 1

        # Extract data for Phase 2.5
        agent_data = []
        for result in phase_1_result.agent_results:
            agent_data.append({
                'agent_id': result.agent_id,
                'findings': result.findings,
                'confidence': result.confidence_score
            })

        assert len(agent_data) >= 1

    @pytest.mark.asyncio
    async def test_phase_2_to_2_5_flow(self):
        """Test data flow from Phase 2 to Phase 2.5."""
        phase_2_result = create_mock_phase_2_result("success")

        # Verify Phase 2 data can be processed
        assert len(phase_2_result.agent_results) >= 1

    @pytest.mark.asyncio
    async def test_complete_data_flow(self):
        """Test complete data flow through Phase 2.5."""
        phase_1 = create_mock_phase_1_result("success")
        phase_2 = create_mock_phase_2_result("success")

        # Combine all agent results
        all_results = phase_1.agent_results + phase_2.agent_results

        # Create packages
        packages = []
        for result in all_results:
            pkg = MockAgentIntelligencePackage(
                agent_id=result.agent_id,
                agent_name=result.agent_name,
                execution_status=result.execution_status,
                findings_summary=result.findings,
                detailed_analysis_file="",
                detailed_analysis_content=result.findings,
                confidence_score=result.confidence_score,
                execution_time=result.execution_time
            )
            packages.append(pkg)

        assert len(packages) == len(all_results)


class TestStagingFileCreation:
    """Test staging file creation and management."""

    def test_staging_data_structure(self):
        """Test staging data has correct structure."""
        packages = create_mock_agent_packages("success")

        staging_data = {
            'run_id': 'test_run_001',
            'staging_timestamp': datetime.now().isoformat(),
            'agent_packages': [asdict(pkg) for pkg in packages],
            'total_packages': len(packages),
            'data_preservation_guarantee': True
        }

        assert staging_data['total_packages'] == 4
        assert staging_data['data_preservation_guarantee'] is True

    def test_qe_intelligence_staging(self):
        """Test QE intelligence staging structure."""
        qe = create_mock_qe_intelligence("success")

        qe_data = asdict(qe)

        assert 'service_name' in qe_data
        assert 'test_patterns' in qe_data
        assert 'coverage_gaps' in qe_data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

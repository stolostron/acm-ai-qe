"""
Mock Phase Output Fixtures
===========================

Centralized mock outputs for each framework phase to enable isolated testing
of individual phases and integration testing of the full workflow.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class MockAgentResult:
    """Mock agent result structure matching the framework's AgentResult."""
    agent_id: str
    agent_name: str
    execution_status: str
    findings: Dict[str, Any]
    confidence_score: float
    execution_time: float
    output_file: str = ""


@dataclass
class MockPhaseResult:
    """Mock phase result structure matching the framework's PhaseResult."""
    agent_results: List[MockAgentResult]
    phase_id: str = ""
    execution_status: str = "success"
    execution_time: float = 0.0


@dataclass
class MockAgentIntelligencePackage:
    """Mock agent intelligence package for Phase 3 input."""
    agent_id: str
    agent_name: str
    execution_status: str
    findings_summary: Dict[str, Any]
    detailed_analysis_file: str
    detailed_analysis_content: Dict[str, Any]
    confidence_score: float
    execution_time: float
    context_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MockQEIntelligencePackage:
    """Mock QE intelligence package from Phase 2.5."""
    service_name: str = "QEIntelligenceService"
    execution_status: str = "success"
    repository_analysis: Dict[str, Any] = field(default_factory=dict)
    test_patterns: List[Dict[str, Any]] = field(default_factory=list)
    coverage_gaps: Dict[str, Any] = field(default_factory=dict)
    automation_insights: Dict[str, Any] = field(default_factory=dict)
    testing_recommendations: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    confidence_score: float = 0.0


# Phase 0 cleanup mock outputs
MOCK_PHASE_0_OUTPUTS = {
    "clean_start": {
        "cleanup_successful": True,
        "cleanup_type": "initialization",
        "files_removed": 0,
        "directories_cleaned": 0,
        "total_size_freed_bytes": 0,
        "execution_time": 0.1
    },
    "stale_staging_files": {
        "cleanup_successful": True,
        "cleanup_type": "initialization",
        "files_removed": 5,
        "directories_cleaned": 1,
        "total_size_freed_bytes": 10240,
        "execution_time": 0.3
    },
    "stale_cache_files": {
        "cleanup_successful": True,
        "cleanup_type": "initialization",
        "files_removed": 10,
        "directories_cleaned": 2,
        "total_size_freed_bytes": 51200,
        "execution_time": 0.5
    },
    "permission_error": {
        "cleanup_successful": False,
        "cleanup_type": "initialization",
        "files_removed": 0,
        "directories_cleaned": 0,
        "error": "Permission denied",
        "execution_time": 0.1
    }
}


# Phase 1 mock outputs (Agents A + D)
def create_mock_phase_1_result(scenario: str = "success") -> MockPhaseResult:
    """Create mock Phase 1 result for testing."""
    scenarios = {
        "success": MockPhaseResult(
            phase_id="phase_1",
            execution_status="success",
            execution_time=5.5,
            agent_results=[
                MockAgentResult(
                    agent_id="agent_a_jira_intelligence",
                    agent_name="JIRA Intelligence Agent",
                    execution_status="success",
                    findings={
                        "jira_info": {
                            "jira_id": "ACM-22079",
                            "title": "ClusterCurator digest-based upgrades",
                            "component": "ClusterCurator",
                            "priority": "High",
                            "fix_version": "2.15.0"
                        },
                        "requirement_analysis": {
                            "primary_requirements": ["Digest-based upgrade support", "Disconnected environment support"],
                            "component_focus": "ClusterCurator",
                            "priority_level": "High"
                        },
                        "pr_discoveries": [{"pr_number": "468", "pr_title": "Add digest support"}]
                    },
                    confidence_score=0.92,
                    execution_time=2.5
                ),
                MockAgentResult(
                    agent_id="agent_d_environment_intelligence",
                    agent_name="Environment Intelligence Agent",
                    execution_status="success",
                    findings={
                        "environment_assessment": {
                            "health_status": "healthy",
                            "acm_version": "2.15.0",
                            "deployment_status": "deployed"
                        },
                        "tooling_analysis": {
                            "available_tools": {"oc": True, "kubectl": True, "gh": True}
                        }
                    },
                    confidence_score=0.88,
                    execution_time=3.0
                )
            ]
        ),
        "agent_a_failure": MockPhaseResult(
            phase_id="phase_1",
            execution_status="partial",
            execution_time=5.0,
            agent_results=[
                MockAgentResult(
                    agent_id="agent_a_jira_intelligence",
                    agent_name="JIRA Intelligence Agent",
                    execution_status="failed",
                    findings={"error": "JIRA API unavailable"},
                    confidence_score=0.0,
                    execution_time=2.0
                ),
                MockAgentResult(
                    agent_id="agent_d_environment_intelligence",
                    agent_name="Environment Intelligence Agent",
                    execution_status="success",
                    findings={"environment_assessment": {"health_status": "healthy"}},
                    confidence_score=0.85,
                    execution_time=3.0
                )
            ]
        ),
        "minimal": MockPhaseResult(
            phase_id="phase_1",
            execution_status="success",
            execution_time=2.0,
            agent_results=[
                MockAgentResult(
                    agent_id="agent_a_jira_intelligence",
                    agent_name="JIRA Intelligence Agent",
                    execution_status="success",
                    findings={"jira_info": {"jira_id": "TEST-123", "title": "Test"}},
                    confidence_score=0.65,
                    execution_time=1.0
                )
            ]
        )
    }
    return scenarios.get(scenario, scenarios["success"])


# Phase 2 mock outputs (Agents B + C)
def create_mock_phase_2_result(scenario: str = "success") -> MockPhaseResult:
    """Create mock Phase 2 result for testing."""
    scenarios = {
        "success": MockPhaseResult(
            phase_id="phase_2",
            execution_status="success",
            execution_time=8.0,
            agent_results=[
                MockAgentResult(
                    agent_id="agent_b_documentation_intelligence",
                    agent_name="Documentation Intelligence Agent",
                    execution_status="success",
                    findings={
                        "feature_operation_model": "Digest-based upgrade workflow",
                        "business_logic_map": {
                            "primary_flow": "Upgrade initiation -> Digest resolution -> Upgrade execution",
                            "fallback_flow": "Failure detection -> Rollback"
                        },
                        "user_workflows": ["Create ClusterCurator", "Monitor upgrade", "Verify completion"],
                        "integration_points": ["ClusterCurator API", "ManagedCluster API"]
                    },
                    confidence_score=0.90,
                    execution_time=4.0
                ),
                MockAgentResult(
                    agent_id="agent_c_github_investigation",
                    agent_name="GitHub Investigation Agent",
                    execution_status="success",
                    findings={
                        "pr_analysis": {
                            "pr_number": "468",
                            "files_changed": 5,
                            "change_impact": "medium"
                        },
                        "repository_analysis": {
                            "target_repositories": ["stolostron/cluster-curator-controller"]
                        },
                        "testing_scope": {
                            "unit_tests_present": True,
                            "e2e_tests_present": True
                        }
                    },
                    confidence_score=0.88,
                    execution_time=4.0
                )
            ]
        ),
        "agent_c_failure": MockPhaseResult(
            phase_id="phase_2",
            execution_status="partial",
            execution_time=6.0,
            agent_results=[
                MockAgentResult(
                    agent_id="agent_b_documentation_intelligence",
                    agent_name="Documentation Intelligence Agent",
                    execution_status="success",
                    findings={"feature_operation_model": "Basic feature workflow"},
                    confidence_score=0.85,
                    execution_time=3.0
                ),
                MockAgentResult(
                    agent_id="agent_c_github_investigation",
                    agent_name="GitHub Investigation Agent",
                    execution_status="failed",
                    findings={"error": "GitHub API rate limited"},
                    confidence_score=0.0,
                    execution_time=3.0
                )
            ]
        )
    }
    return scenarios.get(scenario, scenarios["success"])


# Phase 2.5 mock outputs
def create_mock_agent_packages(scenario: str = "success") -> List[MockAgentIntelligencePackage]:
    """Create mock agent intelligence packages for Phase 2.5/3 input."""
    if scenario == "success":
        return [
            MockAgentIntelligencePackage(
                agent_id="agent_a_jira_intelligence",
                agent_name="JIRA Intelligence Agent",
                execution_status="success",
                findings_summary={"jira_info": {"component": "ClusterCurator"}},
                detailed_analysis_file="",
                detailed_analysis_content={
                    "requirement_analysis": {
                        "component_focus": "ClusterCurator",
                        "primary_requirements": ["Feature A", "Feature B"],
                        "priority_level": "High"
                    },
                    "jira_info": {"jira_id": "ACM-22079", "title": "Digest upgrades"}
                },
                confidence_score=0.92,
                execution_time=2.5
            ),
            MockAgentIntelligencePackage(
                agent_id="agent_d_environment_intelligence",
                agent_name="Environment Intelligence Agent",
                execution_status="success",
                findings_summary={"environment": "healthy"},
                detailed_analysis_file="",
                detailed_analysis_content={
                    "environment_assessment": {"health_status": "healthy"},
                    "tooling_analysis": {"available_tools": {"oc": True}}
                },
                confidence_score=0.88,
                execution_time=3.0
            ),
            MockAgentIntelligencePackage(
                agent_id="agent_b_documentation_intelligence",
                agent_name="Documentation Intelligence Agent",
                execution_status="success",
                findings_summary={"documentation": "comprehensive"},
                detailed_analysis_file="",
                detailed_analysis_content={
                    "discovered_documentation": ["doc1", "doc2", "doc3"]
                },
                confidence_score=0.90,
                execution_time=4.0
            ),
            MockAgentIntelligencePackage(
                agent_id="agent_c_github_investigation",
                agent_name="GitHub Investigation Agent",
                execution_status="success",
                findings_summary={"pr_analysis": "complete"},
                detailed_analysis_file="",
                detailed_analysis_content={
                    "repository_analysis": {"target_repositories": ["repo1", "repo2"]}
                },
                confidence_score=0.88,
                execution_time=4.0
            )
        ]
    elif scenario == "partial_failure":
        return [
            MockAgentIntelligencePackage(
                agent_id="agent_a_jira_intelligence",
                agent_name="JIRA Intelligence Agent",
                execution_status="success",
                findings_summary={"jira_info": {"component": "TestComponent"}},
                detailed_analysis_file="",
                detailed_analysis_content={"requirement_analysis": {"component_focus": "TestComponent"}},
                confidence_score=0.75,
                execution_time=2.0
            ),
            MockAgentIntelligencePackage(
                agent_id="agent_c_github_investigation",
                agent_name="GitHub Investigation Agent",
                execution_status="failed",
                findings_summary={"error": "API failure"},
                detailed_analysis_file="",
                detailed_analysis_content={},
                confidence_score=0.0,
                execution_time=1.0
            )
        ]
    return []


def create_mock_qe_intelligence(scenario: str = "success") -> MockQEIntelligencePackage:
    """Create mock QE intelligence package for Phase 2.5/3 input."""
    scenarios = {
        "success": MockQEIntelligencePackage(
            service_name="QEIntelligenceService",
            execution_status="success",
            repository_analysis={
                "target_repositories": ["stolostron/clc-ui-e2e"],
                "test_file_count": 78,
                "analysis_method": "real_github_api"
            },
            test_patterns=[
                {"pattern_name": "Core Workflow", "pattern_type": "End-to-End", "usage_frequency": "High"},
                {"pattern_name": "Validation Pattern", "pattern_type": "Core Functionality", "usage_frequency": "Medium"}
            ],
            coverage_gaps={
                "identified_gaps": ["Advanced upgrade scenarios", "Error recovery workflows"],
                "gap_priority": {"Advanced upgrade scenarios": "High", "Error recovery workflows": "Medium"}
            },
            automation_insights={
                "frameworks_identified": ["Cypress", "Ginkgo"],
                "test_file_count": 78
            },
            testing_recommendations=[
                "Implement comprehensive E2E testing",
                "Focus on error handling scenarios",
                "Leverage Cypress patterns"
            ],
            execution_time=2.5,
            confidence_score=0.92
        ),
        "failed": MockQEIntelligencePackage(
            service_name="QEIntelligenceService",
            execution_status="failed",
            repository_analysis={"error": "Service unavailable"},
            test_patterns=[],
            coverage_gaps={},
            automation_insights={},
            testing_recommendations=[],
            execution_time=1.0,
            confidence_score=0.0
        ),
        "empty": MockQEIntelligencePackage(
            service_name="QEIntelligenceService",
            execution_status="success",
            repository_analysis={},
            test_patterns=[],
            coverage_gaps={},
            automation_insights={},
            testing_recommendations=[],
            execution_time=0.5,
            confidence_score=0.50
        )
    }
    return scenarios.get(scenario, scenarios["success"])


# Phase 3 mock outputs
def create_mock_phase_3_input(scenario: str = "success") -> Dict[str, Any]:
    """Create mock Phase 3 input structure."""
    agent_packages = create_mock_agent_packages(scenario)
    qe_intelligence = create_mock_qe_intelligence(scenario)

    return {
        "phase_1_result": create_mock_phase_1_result(scenario),
        "phase_2_result": create_mock_phase_2_result(scenario),
        "agent_intelligence_packages": agent_packages,
        "qe_intelligence": qe_intelligence,
        "data_flow_timestamp": datetime.now().isoformat(),
        "data_preservation_verified": True,
        "total_context_size_kb": 150.5
    }


def create_mock_strategic_intelligence(scenario: str = "success") -> Dict[str, Any]:
    """Create mock strategic intelligence output from Phase 3."""
    scenarios = {
        "success": {
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_confidence": 0.914,
            "data_preservation_verified": True,
            "qe_enhancement_applied": True,
            "complete_agent_intelligence": {
                "agent_packages_count": 4,
                "average_confidence": 0.895,
                "jira_intelligence": {
                    "summary": {"requirement_analysis": {"component_focus": "ClusterCurator"}},
                    "detailed": {"requirement_analysis": {"component_focus": "ClusterCurator", "priority_level": "High"}}
                }
            },
            "integrated_qe_insights": {
                "integration_successful": True,
                "test_patterns": [{"pattern_name": "Core Workflow", "pattern_type": "End-to-End"}],
                "coverage_gaps": {"identified_gaps": ["Advanced scenarios"]}
            },
            "complexity_analysis": {
                "complexity_score": 0.65,
                "complexity_level": "Medium",
                "optimal_test_steps": 7,
                "recommended_test_cases": 4
            },
            "strategic_analysis": {
                "combined_recommendations": ["Focus on E2E testing", "Test error scenarios"]
            },
            "scoping_analysis": {
                "test_scope": "comprehensive",
                "coverage_approach": "QE-enhanced"
            },
            "title_analysis": {
                "test_titles": [
                    "Verify ClusterCurator Digest-Based Upgrade Workflow",
                    "Validate ClusterCurator Fallback Mechanism",
                    "Comprehensive ClusterCurator Configuration Testing"
                ]
            }
        },
        "low_complexity": {
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_confidence": 0.85,
            "data_preservation_verified": True,
            "qe_enhancement_applied": False,
            "complete_agent_intelligence": {"agent_packages_count": 2, "average_confidence": 0.75},
            "complexity_analysis": {
                "complexity_score": 0.25,
                "complexity_level": "Low",
                "optimal_test_steps": 4,
                "recommended_test_cases": 2
            },
            "title_analysis": {"test_titles": ["Verify Feature Basic Functionality"]}
        },
        "high_complexity": {
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_confidence": 0.92,
            "data_preservation_verified": True,
            "qe_enhancement_applied": True,
            "complete_agent_intelligence": {"agent_packages_count": 4, "average_confidence": 0.90},
            "complexity_analysis": {
                "complexity_score": 0.85,
                "complexity_level": "High",
                "optimal_test_steps": 10,
                "recommended_test_cases": 5
            },
            "title_analysis": {"test_titles": [
                "Complete Feature Integration Testing",
                "Advanced Workflow Validation",
                "Multi-Component Testing",
                "Enterprise Deployment Validation",
                "Error Recovery Testing"
            ]}
        }
    }
    return scenarios.get(scenario, scenarios["success"])


# Phase 4 mock outputs
MOCK_PHASE_4_OUTPUTS = {
    "success": {
        "execution_status": "success",
        "test_cases_generated": 4,
        "test_cases": [
            {
                "title": "Verify ClusterCurator Digest-Based Upgrade Workflow",
                "steps": 7,
                "format_compliant": True
            }
        ],
        "format_validation": {
            "passed": True,
            "compliance_score": 0.95
        },
        "security_validation": {
            "credentials_masked": True,
            "no_sensitive_data": True
        }
    },
    "format_failure": {
        "execution_status": "partial",
        "test_cases_generated": 4,
        "format_validation": {
            "passed": False,
            "compliance_score": 0.65,
            "issues": ["Missing expected output examples", "Incomplete YAML patterns"]
        }
    }
}


# Phase 5 cleanup mock outputs
MOCK_PHASE_5_OUTPUTS = {
    "success": {
        "success": True,
        "cleanup_statistics": {
            "files_removed": 15,
            "directories_removed": 3,
            "bytes_cleaned": 102400
        },
        "essential_files_validation": {
            "preserved_files": ["Test-Cases.md", "Complete-Analysis.md"],
            "validation_passed": True
        },
        "summary": "Cleanup completed successfully",
        "execution_time": 0.5
    },
    "protected_files_preserved": {
        "success": True,
        "cleanup_statistics": {
            "files_removed": 10,
            "directories_removed": 2,
            "bytes_cleaned": 51200
        },
        "essential_files_validation": {
            "preserved_files": ["Test-Cases.md", "Complete-Analysis.md", "run_metadata.json"],
            "validation_passed": True
        }
    },
    "permission_error": {
        "success": False,
        "cleanup_statistics": {
            "files_removed": 0,
            "directories_removed": 0,
            "bytes_cleaned": 0
        },
        "error": "Permission denied for some files",
        "execution_time": 0.1
    }
}


def get_complete_workflow_mock_data() -> Dict[str, Any]:
    """Get complete mock data for full workflow integration testing."""
    return {
        "phase_0": MOCK_PHASE_0_OUTPUTS["clean_start"],
        "phase_1": create_mock_phase_1_result("success"),
        "phase_2": create_mock_phase_2_result("success"),
        "phase_2_5": {
            "agent_packages": create_mock_agent_packages("success"),
            "qe_intelligence": create_mock_qe_intelligence("success")
        },
        "phase_3_input": create_mock_phase_3_input("success"),
        "phase_3_output": create_mock_strategic_intelligence("success"),
        "phase_4": MOCK_PHASE_4_OUTPUTS["success"],
        "phase_5": MOCK_PHASE_5_OUTPUTS["success"]
    }

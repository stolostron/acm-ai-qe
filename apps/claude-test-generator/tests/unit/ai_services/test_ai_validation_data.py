#!/usr/bin/env python3
"""
Comprehensive Test Data Sets for AI-Driven Framework Validation
=============================================================

Contains realistic test scenarios covering all technology stacks and edge cases
for thorough validation of AI-driven test generation vs pattern fallbacks.
"""

import json
from typing import Dict, Any, List
from datetime import datetime

class AIValidationTestData:
    """Comprehensive test data for AI framework validation"""
    
    @staticmethod
    def get_mtv_cnv_scenarios() -> List[Dict[str, Any]]:
        """MTV/CNV addon integration test scenarios"""
        return [
            {
                "scenario_name": "ACM-22348 MTV CNV Addon Integration",
                "jira_data": {
                    "jira_id": "ACM-22348",
                    "jira_title": "Onboard CNV addon and MTV-integrations into ACM Installer",
                    "component": "MTV Addon Integration",
                    "priority": "High",
                    "jira_status": "In Progress",
                    "target_version": "ACM 2.15"
                },
                "expected_technology": "MTV_CNV_Integration",
                "expected_components": ["Migration Toolkit for Virtualization", "CNV Operator", "ForkliftController"],
                "expected_testing_focus": ["webhook_validation", "provider_creation", "certificate_rotation", "conditional_deployment"],
                "expected_scenarios": ["webhook_provider_creation", "conditional_deployment", "certificate_rotation_resilience"],
                "should_use_ai": True,
                "ai_confidence_threshold": 0.8
            },
            {
                "scenario_name": "ACM-21001 ForkliftController Enhancement",
                "jira_data": {
                    "jira_id": "ACM-21001",
                    "jira_title": "Enhance ForkliftController webhook integration for automated provider management",
                    "component": "Migration Toolkit",
                    "priority": "Medium",
                    "jira_status": "New",
                    "target_version": "ACM 2.16"
                },
                "expected_technology": "MTV_CNV_Integration",
                "expected_components": ["Migration Toolkit for Virtualization", "CNV Operator", "ForkliftController"],
                "expected_testing_focus": ["webhook_validation", "provider_creation"],
                "expected_scenarios": ["webhook_provider_creation", "conditional_deployment"],
                "should_use_ai": True,
                "ai_confidence_threshold": 0.7
            }
        ]
    
    @staticmethod
    def get_rbac_scenarios() -> List[Dict[str, Any]]:
        """RBAC security implementation test scenarios"""
        return [
            {
                "scenario_name": "ACM-21333 RBAC UI Implementation", 
                "jira_data": {
                    "jira_id": "ACM-21333",
                    "jira_title": "Implement RBAC UI enforcement for virtualization operations with SDK security hooks",
                    "component": "RBAC Security",
                    "priority": "High",
                    "jira_status": "In Progress",
                    "target_version": "ACM 2.15"
                },
                "expected_technology": "RBAC_Security",
                "expected_components": ["Role-Based Access Control", "Permission Management"],
                "expected_testing_focus": ["permission_validation", "ui_enforcement", "sdk_security_hooks"],
                "expected_scenarios": ["permission_ui_enforcement", "sdk_security_validation"],
                "should_use_ai": True,
                "ai_confidence_threshold": 0.8
            },
            {
                "scenario_name": "ACM-19456 Permission Model Update",
                "jira_data": {
                    "jira_id": "ACM-19456", 
                    "jira_title": "Update permission model for cross-cluster VM operations",
                    "component": "Security",
                    "priority": "Medium",
                    "jira_status": "Testing",
                    "target_version": "ACM 2.14"
                },
                "expected_technology": "RBAC_Security",
                "expected_testing_focus": ["permission_validation"],
                "should_use_ai": True,
                "ai_confidence_threshold": 0.7
            }
        ]
    
    @staticmethod
    def get_sdk_scenarios() -> List[Dict[str, Any]]:
        """Multicluster SDK enhancement test scenarios"""
        return [
            {
                "scenario_name": "ACM-20640 Multicluster SDK Enhancement",
                "jira_data": {
                    "jira_id": "ACM-20640",
                    "jira_title": "Enhance multicluster SDK with bulk operation validation and error propagation",
                    "component": "Multicluster SDK",
                    "priority": "High", 
                    "jira_status": "Code Review",
                    "target_version": "ACM 2.15"
                },
                "expected_technology": "Multicluster_SDK",
                "expected_components": ["Multicluster SDK", "Cross-cluster Communication"],
                "expected_testing_focus": ["sdk_validation", "error_propagation", "bulk_operations"],
                "expected_scenarios": ["multicluster_operation_validation"],
                "should_use_ai": True,
                "ai_confidence_threshold": 0.8
            }
        ]
    
    @staticmethod
    def get_generic_scenarios() -> List[Dict[str, Any]]:
        """Generic ACM scenarios that should use pattern fallback"""
        return [
            {
                "scenario_name": "ACM-18900 Basic Feature Implementation",
                "jira_data": {
                    "jira_id": "ACM-18900",
                    "jira_title": "Update cluster management interface",
                    "component": "Cluster Management",
                    "priority": "Low",
                    "jira_status": "New",
                    "target_version": "ACM 2.14"
                },
                "expected_technology": "ACM_Generic",
                "expected_components": ["Cluster Management"],
                "expected_testing_focus": ["basic_functionality", "integration_testing"],
                "should_use_ai": False,  # Should fall back to patterns
                "ai_confidence_threshold": 0.3
            },
            {
                "scenario_name": "ACM-17500 Unknown Feature Type",
                "jira_data": {
                    "jira_id": "ACM-17500",
                    "jira_title": "Unknown Feature",
                    "component": "Unknown",
                    "priority": "Medium",
                    "jira_status": "New",
                    "target_version": "ACM 2.14"
                },
                "expected_technology": "ACM_Generic",
                "should_use_ai": False,  # Insufficient context
                "ai_confidence_threshold": 0.2
            }
        ]
    
    @staticmethod
    def get_edge_cases() -> List[Dict[str, Any]]:
        """Edge cases and error scenarios"""
        return [
            {
                "scenario_name": "Empty JIRA Data",
                "jira_data": {},
                "expected_technology": "ACM_Generic",
                "should_use_ai": False,
                "ai_confidence_threshold": 0.1
            },
            {
                "scenario_name": "Missing Title",
                "jira_data": {
                    "jira_id": "ACM-99999",
                    "component": "Test",
                    "priority": "Low"
                },
                "expected_technology": "ACM_Generic", 
                "should_use_ai": False,
                "ai_confidence_threshold": 0.2
            },
            {
                "scenario_name": "Malformed Strategic Intelligence",
                "strategic_intelligence": {
                    "invalid_structure": True
                },
                "should_use_ai": False,
                "ai_confidence_threshold": 0.0
            }
        ]
    
    @staticmethod
    def create_strategic_intelligence(jira_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create mock strategic intelligence from JIRA data"""
        return {
            "complete_agent_intelligence": {
                "agents": {
                    "agent_a_jira_intelligence": {
                        "context_metadata": jira_data
                    }
                }
            },
            "phase_4_directives": {
                "test_case_count": 3,
                "steps_per_case": 7,
                "testing_approach": "Comprehensive Testing"
            }
        }
    
    @staticmethod
    def get_all_test_scenarios() -> List[Dict[str, Any]]:
        """Get all test scenarios for comprehensive validation"""
        all_scenarios = []
        all_scenarios.extend(AIValidationTestData.get_mtv_cnv_scenarios())
        all_scenarios.extend(AIValidationTestData.get_rbac_scenarios()) 
        all_scenarios.extend(AIValidationTestData.get_sdk_scenarios())
        all_scenarios.extend(AIValidationTestData.get_generic_scenarios())
        all_scenarios.extend(AIValidationTestData.get_edge_cases())
        
        return all_scenarios
    
    @staticmethod
    def get_performance_test_data() -> Dict[str, Any]:
        """Large dataset for performance testing"""
        return {
            "scenario_name": "Performance Test - Large Context",
            "strategic_intelligence": {
                "complete_agent_intelligence": {
                    "agents": {
                        "agent_a_jira_intelligence": {
                            "context_metadata": {
                                "jira_id": "ACM-50000",
                                "jira_title": "Large scale MTV addon deployment with complex webhook integration patterns for enterprise environments",
                                "component": "MTV Enterprise Integration",
                                "priority": "Critical",
                                "jira_status": "In Progress",
                                "target_version": "ACM 3.0",
                                "additional_context": "x" * 1000  # Large context
                            }
                        }
                    }
                },
                "large_data_structure": ["item"] * 1000  # Large data
            },
            "expected_ai_handling": True,
            "performance_threshold_seconds": 2.0
        }
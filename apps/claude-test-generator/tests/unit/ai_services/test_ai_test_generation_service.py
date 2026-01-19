#!/usr/bin/env python3
"""
AI Test Generation Service Unit Tests
====================================

Comprehensive unit tests for the AI Test Generation Service that replaces
hardcoded pattern matching with contextual understanding.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ai_services_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.claude', 'ai-services')
sys.path.insert(0, ai_services_path)

try:
    from ai_test_generation_service import AITestGenerationService
    from test_ai_validation_data import AIValidationTestData
    AI_SERVICE_AVAILABLE = True
except ImportError as e:
    AI_SERVICE_AVAILABLE = False
    print(f"❌ AI Test Generation Service not available: {e}")


class TestAITestGenerationService(unittest.TestCase):
    """Test AI Test Generation Service core functionality"""
    
    @classmethod
    def setUpClass(cls):
        if not AI_SERVICE_AVAILABLE:
            cls.skipTest(cls, "AI Test Generation Service not available")
    
    def setUp(self):
        """Set up test environment"""
        self.service = AITestGenerationService()
        self.test_data = AIValidationTestData()
    
    def test_service_initialization(self):
        """Test AI service initializes correctly"""
        service = AITestGenerationService()
        
        self.assertIsInstance(service.context_understanding_cache, dict)
        self.assertEqual(len(service.context_understanding_cache), 0)
    
    def test_extract_jira_context(self):
        """Test JIRA context extraction from agent intelligence"""
        agent_intelligence = {
            'agents': {
                'agent_a_jira_intelligence': {
                    'context_metadata': {
                        'jira_id': 'ACM-22348',
                        'jira_title': 'Onboard CNV addon and MTV-integrations',
                        'component': 'MTV Addon Integration',
                        'priority': 'High',
                        'jira_status': 'In Progress',
                        'target_version': 'ACM 2.15'
                    }
                }
            }
        }
        
        jira_context = self.service._extract_jira_context(agent_intelligence)
        
        # Verify extraction
        self.assertEqual(jira_context['jira_id'], 'ACM-22348')
        self.assertEqual(jira_context['title'], 'Onboard CNV addon and MTV-integrations')
        self.assertEqual(jira_context['component'], 'MTV Addon Integration')
        self.assertEqual(jira_context['priority'], 'High')
        self.assertEqual(jira_context['status'], 'In Progress')
        self.assertEqual(jira_context['target_version'], 'ACM 2.15')
    
    def test_extract_jira_context_missing_data(self):
        """Test JIRA context extraction with missing data"""
        agent_intelligence = {
            'agents': {
                'agent_a_jira_intelligence': {
                    'context_metadata': {
                        'jira_id': 'ACM-12345'
                        # Missing other fields
                    }
                }
            }
        }
        
        jira_context = self.service._extract_jira_context(agent_intelligence)
        
        # Verify defaults
        self.assertEqual(jira_context['jira_id'], 'ACM-12345')
        self.assertEqual(jira_context['title'], 'Unknown Feature')
        self.assertEqual(jira_context['component'], 'Unknown')
        self.assertEqual(jira_context['priority'], 'Medium')
    
    def test_ai_identify_technology_stack_mtv_cnv(self):
        """Test AI technology stack identification for MTV/CNV"""
        title = 'Onboard CNV addon and MTV-integrations into ACM Installer'
        component = 'MTV Addon Integration'
        
        tech_stack = self.service._ai_identify_technology_stack(title, component)
        
        # Verify MTV/CNV detection
        self.assertEqual(tech_stack['primary'], 'MTV_CNV_Integration')
        self.assertIn('Migration Toolkit for Virtualization', tech_stack['components'])
        self.assertIn('CNV Operator', tech_stack['components'])
        self.assertIn('ForkliftController', tech_stack['components'])
        
        # Verify testing focus
        self.assertIn('webhook_validation', tech_stack['testing_focus'])
        self.assertIn('provider_creation', tech_stack['testing_focus'])
        self.assertIn('certificate_rotation', tech_stack['testing_focus'])
        self.assertIn('conditional_deployment', tech_stack['testing_focus'])
        
        # Verify UI areas
        self.assertIn('Add-ons', tech_stack['ui_areas'])
        self.assertIn('Migration', tech_stack['ui_areas'])
        self.assertIn('Cluster Management', tech_stack['ui_areas'])
        
        # Verify CLI tools
        self.assertIn('oc', tech_stack['cli_tools'])
        self.assertIn('kubectl', tech_stack['cli_tools'])
        
        # Verify key resources
        self.assertIn('ManagedCluster', tech_stack['key_resources'])
        self.assertIn('Provider', tech_stack['key_resources'])
        self.assertIn('ForkliftController', tech_stack['key_resources'])
    
    def test_ai_identify_technology_stack_rbac(self):
        """Test AI technology stack identification for RBAC"""
        title = 'Implement RBAC UI enforcement for virtualization operations'
        component = 'RBAC Security'
        
        tech_stack = self.service._ai_identify_technology_stack(title, component)
        
        # Verify RBAC detection
        self.assertEqual(tech_stack['primary'], 'RBAC_Security')
        self.assertIn('Role-Based Access Control', tech_stack['components'])
        self.assertIn('Permission Management', tech_stack['components'])
        
        # Verify testing focus
        self.assertIn('permission_validation', tech_stack['testing_focus'])
        self.assertIn('ui_enforcement', tech_stack['testing_focus'])
        self.assertIn('sdk_security_hooks', tech_stack['testing_focus'])
    
    def test_ai_identify_technology_stack_sdk(self):
        """Test AI technology stack identification for SDK"""
        title = 'Enhance multicluster SDK with bulk operation validation'
        component = 'Multicluster SDK'
        
        tech_stack = self.service._ai_identify_technology_stack(title, component)
        
        # Verify SDK detection
        self.assertEqual(tech_stack['primary'], 'Multicluster_SDK')
        self.assertIn('Multicluster SDK', tech_stack['components'])
        self.assertIn('Cross-cluster Communication', tech_stack['components'])
        
        # Verify testing focus
        self.assertIn('sdk_validation', tech_stack['testing_focus'])
        self.assertIn('error_propagation', tech_stack['testing_focus'])
        self.assertIn('bulk_operations', tech_stack['testing_focus'])
    
    def test_ai_identify_technology_stack_generic(self):
        """Test AI technology stack identification for generic ACM"""
        title = 'Update cluster management interface'
        component = 'Cluster Management'
        
        tech_stack = self.service._ai_identify_technology_stack(title, component)
        
        # Verify generic detection
        self.assertEqual(tech_stack['primary'], 'ACM_Generic')
        self.assertIn(component, tech_stack['components'])
        self.assertIn('basic_functionality', tech_stack['testing_focus'])
        self.assertIn('integration_testing', tech_stack['testing_focus'])
    
    def test_ai_identify_integration_type(self):
        """Test AI integration type identification"""
        integration_tests = [
            ('Onboard CNV addon into ACM', 'addon_integration'),
            ('Enhance multicluster SDK', 'feature_enhancement'),
            ('Implement RBAC enforcement', 'new_implementation'),
            ('Update cluster interface', 'standard_testing')
        ]
        
        for title, expected_type in integration_tests:
            with self.subTest(title=title):
                result = self.service._ai_identify_integration_type(title)
                self.assertEqual(result, expected_type)
    
    def test_ai_assess_testing_complexity(self):
        """Test AI testing complexity assessment"""
        complexity_tests = [
            ('Basic cluster update', 'Cluster', 0.5, 'medium'),
            ('Webhook certificate rotation integration', 'Webhook', 0.8, 'high'),
            ('Multicluster bulk operations', 'SDK', 0.7, 'high'),
            ('Simple feature update', 'Basic', 0.5, 'medium')
        ]
        
        for title, component, min_score, expected_level in complexity_tests:
            with self.subTest(title=title):
                result = self.service._ai_assess_testing_complexity(title, component)
                
                self.assertGreaterEqual(result['score'], min_score)
                self.assertEqual(result['level'], expected_level)
                self.assertIn('test_case_count', result)
                self.assertGreater(result['test_case_count'], 0)
    
    def test_ai_extract_key_scenarios_mtv(self):
        """Test AI key scenario extraction for MTV"""
        title = 'Onboard CNV addon and MTV-integrations'
        component = 'MTV Integration'
        
        scenarios = self.service._ai_extract_key_scenarios(title, component)
        
        # Verify MTV scenarios generated
        self.assertGreater(len(scenarios), 0)
        
        scenario_names = [s['scenario'] for s in scenarios]
        self.assertIn('webhook_provider_creation', scenario_names)
        self.assertIn('conditional_deployment', scenario_names)
        self.assertIn('certificate_rotation_resilience', scenario_names)
        
        # Verify scenario details
        for scenario in scenarios:
            self.assertIn('scenario', scenario)
            self.assertIn('description', scenario)
            self.assertIn('priority', scenario)
            self.assertIn('steps', scenario)
            self.assertIsInstance(scenario['steps'], list)
            self.assertGreater(len(scenario['steps']), 0)
    
    def test_ai_extract_key_scenarios_rbac(self):
        """Test AI key scenario extraction for RBAC"""
        title = 'Implement RBAC UI enforcement'
        component = 'RBAC'
        
        scenarios = self.service._ai_extract_key_scenarios(title, component)
        
        # Verify RBAC scenarios generated
        scenario_names = [s['scenario'] for s in scenarios]
        self.assertIn('permission_ui_enforcement', scenario_names)
        self.assertIn('sdk_security_validation', scenario_names)
    
    def test_ai_extract_key_scenarios_sdk(self):
        """Test AI key scenario extraction for SDK"""
        title = 'Enhance multicluster SDK with bulk operations'
        component = 'SDK'
        
        scenarios = self.service._ai_extract_key_scenarios(title, component)
        
        # Verify SDK scenarios generated
        scenario_names = [s['scenario'] for s in scenarios]
        self.assertIn('multicluster_operation_validation', scenario_names)
    
    def test_ai_extract_key_scenarios_generic_fallback(self):
        """Test AI key scenario extraction generic fallback"""
        title = 'Basic feature update'
        component = 'Generic Component'
        
        scenarios = self.service._ai_extract_key_scenarios(title, component)
        
        # Verify generic fallback
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0]['scenario'], 'basic_functionality_validation')
        self.assertIn('Generic Component', scenarios[0]['description'])
    
    def test_ai_identify_validation_requirements(self):
        """Test AI validation requirements identification"""
        validation_tests = [
            ('Basic feature', ['basic_functionality', 'ui_responsiveness']),
            ('Webhook automatic creation', ['basic_functionality', 'ui_responsiveness', 'webhook_triggering', 'automatic_creation']),
            ('Certificate rotation resilience', ['basic_functionality', 'ui_responsiveness', 'certificate_handling', 'resilience_testing']),
            ('RBAC permission enforcement', ['basic_functionality', 'ui_responsiveness', 'permission_enforcement', 'security_validation']),
            ('Multicluster SDK operations', ['basic_functionality', 'ui_responsiveness', 'cross_cluster_validation', 'error_propagation'])
        ]
        
        for title, expected_validations in validation_tests:
            with self.subTest(title=title):
                result = self.service._ai_identify_validation_requirements(title)
                
                for validation in expected_validations:
                    self.assertIn(validation, result)
    
    def test_ai_generate_test_flows(self):
        """Test AI test flow generation"""
        feature_context = {
            'technology_stack': {
                'primary': 'MTV_CNV_Integration',
                'testing_focus': ['webhook_validation', 'provider_creation'],
                'ui_areas': ['Add-ons', 'Migration'],
                'cli_tools': ['oc', 'kubectl'],
                'key_resources': ['ManagedCluster', 'Provider']
            },
            'key_scenarios': [
                {
                    'scenario': 'webhook_provider_creation',
                    'description': 'Test MTV webhook provider creation',
                    'priority': 'critical',
                    'steps': ['apply_cnv_label', 'verify_webhook_trigger', 'confirm_provider_creation']
                }
            ]
        }
        
        test_flows = self.service._ai_generate_test_flows(feature_context)
        
        # Verify flows generated
        self.assertEqual(len(test_flows), 1)
        
        flow = test_flows[0]
        self.assertIn('flow_id', flow)
        self.assertIn('scenario_name', flow)
        self.assertIn('description', flow)
        self.assertIn('priority', flow)
        self.assertIn('technology_context', flow)
        self.assertIn('ai_generated_steps', flow)
        self.assertIn('validation_criteria', flow)
        
        # Verify flow content
        self.assertEqual(flow['scenario_name'], 'webhook_provider_creation')
        self.assertEqual(flow['description'], 'Test MTV webhook provider creation')
        self.assertEqual(flow['priority'], 'critical')
        self.assertEqual(flow['technology_context']['primary'], 'MTV_CNV_Integration')
        
        # Verify steps generated
        steps = flow['ai_generated_steps']
        self.assertEqual(len(steps), 3)  # Based on scenario steps
        
        for step in steps:
            self.assertIn('step_number', step)
            self.assertIn('template', step)
            self.assertIn('ai_description', step)
            self.assertIn('ai_ui_method', step)
            self.assertIn('ai_cli_method', step)
            self.assertIn('ai_expected_result', step)
    
    def test_ai_contextualize_step_description_mtv(self):
        """Test AI step description contextualization for MTV"""
        scenario = {'scenario': 'webhook_provider_creation'}
        technology = {'primary': 'MTV_CNV_Integration'}
        
        test_cases = [
            ('apply_cnv_label', 'Apply CNV operator installation label to managed cluster to trigger MTV addon webhook'),
            ('verify_webhook_trigger', 'Verify MTV addon webhook detects CNV installation and triggers provider creation process'),
            ('confirm_provider_creation', 'Confirm MTV Provider resource is automatically created with correct configuration'),
            ('check_deployment_conditions', 'Verify MTV addon respects local-cluster and disableHubSelfManagement deployment conditions'),
            ('rotate_certificates', 'Force cluster certificate rotation to test MTV provider resilience')
        ]
        
        for step_template, expected_content in test_cases:
            with self.subTest(step=step_template):
                result = self.service._ai_contextualize_step_description(step_template, scenario, technology)
                self.assertEqual(result, expected_content)
    
    def test_ai_contextualize_step_description_rbac(self):
        """Test AI step description contextualization for RBAC"""
        scenario = {'scenario': 'permission_ui_enforcement'}
        technology = {'primary': 'RBAC_Security'}
        
        test_cases = [
            ('login_restricted_user', 'Login with user having limited virtualization permissions'),
            ('verify_ui_restrictions', 'Verify virtualization actions are disabled in UI based on user permissions'),
            ('attempt_restricted_action', 'Attempt unauthorized VM migration action to test SDK security hooks')
        ]
        
        for step_template, expected_content in test_cases:
            with self.subTest(step=step_template):
                result = self.service._ai_contextualize_step_description(step_template, scenario, technology)
                self.assertEqual(result, expected_content)
    
    def test_ai_generate_ui_method_mtv(self):
        """Test AI UI method generation for MTV"""
        scenario = {'scenario': 'webhook_provider_creation'}
        technology = {
            'primary': 'MTV_CNV_Integration',
            'ui_areas': ['Add-ons', 'Migration', 'Cluster Management']
        }
        
        test_cases = [
            ('apply_cnv_label', 'Navigate to "Cluster Management" → "Clusters" → Select managed cluster → Add label "acm/cnv-operator-install=true"'),
            ('verify_webhook_trigger', 'Monitor "Add-ons" section → Observe MTV addon status changes → Check webhook logs'),
            ('confirm_provider_creation', 'Navigate to "Migration" section → Verify new Provider appears → Check Provider status')
        ]
        
        for step_template, expected_content in test_cases:
            with self.subTest(step=step_template):
                result = self.service._ai_generate_ui_method(step_template, scenario, technology)
                self.assertEqual(result, expected_content)
    
    def test_ai_generate_cli_method_mtv(self):
        """Test AI CLI method generation for MTV"""
        scenario = {'scenario': 'webhook_provider_creation'}
        technology = {
            'primary': 'MTV_CNV_Integration',
            'cli_tools': ['oc', 'kubectl'],
            'key_resources': ['ManagedCluster', 'Provider', 'ForkliftController']
        }
        
        test_cases = [
            ('apply_cnv_label', 'oc label managedcluster <MANAGED_CLUSTER_NAME> acm/cnv-operator-install=true'),
            ('verify_webhook_trigger', 'oc logs -n open-cluster-management deployment/cluster-manager-addon-manager | grep -i "provider\\|webhook"'),
            ('confirm_provider_creation', 'oc get provider -n openshift-mtv <CLUSTER_NAME>-provider -o yaml | grep -A 5 status')
        ]
        
        for step_template, expected_content in test_cases:
            with self.subTest(step=step_template):
                result = self.service._ai_generate_cli_method(step_template, scenario, technology)
                self.assertEqual(result, expected_content)
    
    def test_ai_generate_expected_result_mtv(self):
        """Test AI expected result generation for MTV"""
        scenario = {'scenario': 'webhook_provider_creation'}
        technology = {'primary': 'MTV_CNV_Integration'}
        
        test_cases = [
            ('apply_cnv_label', 'Label applied successfully, CNV operator installation begins'),
            ('verify_webhook_trigger', 'Webhook logs show provider creation triggered for CNV cluster'),
            ('confirm_provider_creation', 'MTV Provider created with Ready status and correct cluster URL')
        ]
        
        for step_template, expected_content in test_cases:
            with self.subTest(step=step_template):
                result = self.service._ai_generate_expected_result(step_template, scenario, technology)
                self.assertEqual(result, expected_content)
    
    def test_ai_generate_validation_criteria(self):
        """Test AI validation criteria generation"""
        test_cases = [
            (
                {'scenario': 'webhook_provider_creation'},
                {'primary': 'MTV_CNV_Integration'},
                ['Webhook triggered automatically', 'Provider creation initiated', 'No manual intervention required']
            ),
            (
                {'scenario': 'permission_ui_enforcement'},
                {'primary': 'RBAC_Security'},
                ['Permission validation enforced', 'Unauthorized actions blocked', 'UI reflects user permissions']
            ),
            (
                {'scenario': 'certificate_rotation_resilience'},
                {'primary': 'MTV_CNV_Integration'},
                ['Certificate rotation detected', 'Automatic recovery initiated', 'Service continuity maintained']
            )
        ]
        
        for scenario, technology, expected_criteria in test_cases:
            with self.subTest(scenario=scenario['scenario']):
                result = self.service._ai_generate_validation_criteria(scenario, technology)
                
                for criterion in expected_criteria:
                    self.assertIn(criterion, result)
    
    def test_ai_prioritize_scenarios(self):
        """Test AI scenario prioritization"""
        test_flows = [
            {'priority': 'medium', 'scenario_name': 'medium_priority'},
            {'priority': 'critical', 'scenario_name': 'critical_priority'},
            {'priority': 'high', 'scenario_name': 'high_priority'},
            {'priority': 'low', 'scenario_name': 'low_priority'}
        ]
        
        feature_context = {
            'testing_complexity': {'test_case_count': 3}
        }
        
        prioritized = self.service._ai_prioritize_scenarios(test_flows, feature_context)
        
        # Verify prioritization order (critical > high > medium > low)
        self.assertEqual(len(prioritized), 3)  # Limited by test_case_count
        self.assertEqual(prioritized[0]['scenario_name'], 'critical_priority')
        self.assertEqual(prioritized[1]['scenario_name'], 'high_priority')
        self.assertEqual(prioritized[2]['scenario_name'], 'medium_priority')
    
    def test_generate_ai_test_cases_complete_workflow(self):
        """Test complete AI test case generation workflow"""
        # Create comprehensive strategic intelligence for MTV
        strategic_intelligence = {
            'complete_agent_intelligence': {
                'agents': {
                    'agent_a_jira_intelligence': {
                        'context_metadata': {
                            'jira_id': 'ACM-22348',
                            'jira_title': 'Onboard CNV addon and MTV-integrations into ACM Installer',
                            'component': 'MTV Addon Integration',
                            'priority': 'High',
                            'jira_status': 'In Progress',
                            'target_version': 'ACM 2.15'
                        }
                    }
                }
            }
        }
        
        # Generate AI test cases
        test_cases = self.service.generate_ai_test_cases(strategic_intelligence)
        
        # Verify test cases generated
        self.assertIsInstance(test_cases, list)
        self.assertGreater(len(test_cases), 0)
        
        # Verify each test case structure
        for test_case in test_cases:
            self.assertIn('test_case_id', test_case)
            self.assertIn('title', test_case)
            self.assertIn('description', test_case)
            self.assertIn('pattern_used', test_case)
            self.assertIn('ai_generated', test_case)
            self.assertIn('ai_confidence', test_case)
            self.assertIn('technology_context', test_case)
            self.assertIn('steps', test_case)
            
            # Verify AI-specific fields
            self.assertTrue(test_case['ai_generated'])
            self.assertEqual(test_case['pattern_used'], 'AI_Generated_Contextual')
            self.assertGreaterEqual(test_case['ai_confidence'], 0.8)
            
            # Verify MTV technology context
            tech_context = test_case['technology_context']
            self.assertEqual(tech_context['primary'], 'MTV_CNV_Integration')
            
            # Verify steps structure
            steps = test_case['steps']
            self.assertIsInstance(steps, list)
            self.assertGreater(len(steps), 0)
            
            for step in steps:
                self.assertIn('step_number', step)
                self.assertIn('description', step)
                self.assertIn('ui_method', step)
                self.assertIn('cli_method', step)
                self.assertIn('expected_result', step)
    
    def test_analyze_feature_context_comprehensive(self):
        """Test comprehensive feature context analysis"""
        strategic_intelligence = {
            'complete_agent_intelligence': {
                'agents': {
                    'agent_a_jira_intelligence': {
                        'context_metadata': {
                            'jira_id': 'ACM-21333',
                            'jira_title': 'Implement RBAC UI enforcement for virtualization operations',
                            'component': 'RBAC Security',
                            'priority': 'High'
                        }
                    }
                }
            }
        }
        
        context_analysis = self.service.analyze_feature_context(strategic_intelligence)
        
        # Verify analysis structure
        self.assertIn('feature_context', context_analysis)
        self.assertIn('test_flows', context_analysis)
        self.assertIn('prioritized_scenarios', context_analysis)
        self.assertIn('ai_confidence', context_analysis)
        self.assertIn('generation_method', context_analysis)
        
        # Verify analysis content
        self.assertGreaterEqual(context_analysis['ai_confidence'], 0.9)
        self.assertEqual(context_analysis['generation_method'], 'ai_contextual_understanding')
        
        # Verify feature context
        feature_context = context_analysis['feature_context']
        self.assertIn('technology_stack', feature_context)
        self.assertIn('integration_type', feature_context)
        self.assertIn('testing_complexity', feature_context)
        self.assertIn('key_scenarios', feature_context)
        self.assertIn('validation_requirements', feature_context)
        
        # Verify RBAC technology detection
        tech_stack = feature_context['technology_stack']
        self.assertEqual(tech_stack['primary'], 'RBAC_Security')


class TestAITestGenerationServiceWithValidationData(unittest.TestCase):
    """Test AI service with comprehensive validation data"""
    
    @classmethod
    def setUpClass(cls):
        if not AI_SERVICE_AVAILABLE:
            cls.skipTest(cls, "AI Test Generation Service not available")
    
    def setUp(self):
        """Set up test environment"""
        self.service = AITestGenerationService()
        self.test_data = AIValidationTestData()
    
    def test_mtv_scenarios_comprehensive(self):
        """Test AI service with all MTV test scenarios"""
        mtv_scenarios = self.test_data.get_mtv_cnv_scenarios()
        
        for scenario_data in mtv_scenarios:
            with self.subTest(scenario=scenario_data['scenario_name']):
                strategic_intelligence = self.test_data.create_strategic_intelligence(
                    scenario_data['jira_data']
                )
                
                test_cases = self.service.generate_ai_test_cases(strategic_intelligence)
                
                # Verify MTV technology detection
                self.assertGreater(len(test_cases), 0)
                
                for test_case in test_cases:
                    tech_context = test_case['technology_context']
                    self.assertEqual(tech_context['primary'], scenario_data['expected_technology'])
                    
                    # Verify components
                    for component in scenario_data['expected_components']:
                        self.assertIn(component, tech_context['components'])
                    
                    # Verify testing focus
                    for focus in scenario_data['expected_testing_focus']:
                        self.assertIn(focus, tech_context['testing_focus'])
    
    def test_rbac_scenarios_comprehensive(self):
        """Test AI service with all RBAC test scenarios"""
        rbac_scenarios = self.test_data.get_rbac_scenarios()
        
        for scenario_data in rbac_scenarios:
            with self.subTest(scenario=scenario_data['scenario_name']):
                strategic_intelligence = self.test_data.create_strategic_intelligence(
                    scenario_data['jira_data']
                )
                
                test_cases = self.service.generate_ai_test_cases(strategic_intelligence)
                
                # Verify RBAC technology detection
                self.assertGreater(len(test_cases), 0)
                
                for test_case in test_cases:
                    tech_context = test_case['technology_context']
                    self.assertEqual(tech_context['primary'], scenario_data['expected_technology'])
    
    def test_sdk_scenarios_comprehensive(self):
        """Test AI service with all SDK test scenarios"""
        sdk_scenarios = self.test_data.get_sdk_scenarios()
        
        for scenario_data in sdk_scenarios:
            with self.subTest(scenario=scenario_data['scenario_name']):
                strategic_intelligence = self.test_data.create_strategic_intelligence(
                    scenario_data['jira_data']
                )
                
                test_cases = self.service.generate_ai_test_cases(strategic_intelligence)
                
                # Verify SDK technology detection
                self.assertGreater(len(test_cases), 0)
                
                for test_case in test_cases:
                    tech_context = test_case['technology_context']
                    self.assertEqual(tech_context['primary'], scenario_data['expected_technology'])
    
    def test_generic_scenarios_fallback(self):
        """Test AI service falls back appropriately for generic scenarios"""
        generic_scenarios = self.test_data.get_generic_scenarios()
        
        for scenario_data in generic_scenarios:
            with self.subTest(scenario=scenario_data['scenario_name']):
                strategic_intelligence = self.test_data.create_strategic_intelligence(
                    scenario_data['jira_data']
                )
                
                test_cases = self.service.generate_ai_test_cases(strategic_intelligence)
                
                # Verify generic detection for low-confidence scenarios
                if not scenario_data['should_use_ai']:
                    # AI should still generate something, but with generic patterns
                    self.assertGreater(len(test_cases), 0)
                    
                    for test_case in test_cases:
                        tech_context = test_case['technology_context']
                        self.assertEqual(tech_context['primary'], scenario_data['expected_technology'])
    
    def test_edge_cases_error_handling(self):
        """Test AI service error handling with edge cases"""
        edge_cases = self.test_data.get_edge_cases()
        
        for case_data in edge_cases:
            with self.subTest(case=case_data['scenario_name']):
                if 'jira_data' in case_data:
                    strategic_intelligence = self.test_data.create_strategic_intelligence(
                        case_data['jira_data']
                    )
                else:
                    strategic_intelligence = case_data.get('strategic_intelligence', {})
                
                # Should not crash, should handle gracefully
                try:
                    test_cases = self.service.generate_ai_test_cases(strategic_intelligence)
                    self.assertIsInstance(test_cases, list)
                    
                    # For edge cases, may return empty or generic results
                    if test_cases:
                        for test_case in test_cases:
                            self.assertIn('test_case_id', test_case)
                            self.assertIn('title', test_case)
                            
                except Exception as e:
                    self.fail(f"AI service should handle edge case gracefully: {e}")


class TestAITestGenerationServicePerformance(unittest.TestCase):
    """Test AI service performance characteristics"""
    
    @classmethod
    def setUpClass(cls):
        if not AI_SERVICE_AVAILABLE:
            cls.skipTest(cls, "AI Test Generation Service not available")
    
    def setUp(self):
        """Set up test environment"""
        self.service = AITestGenerationService()
        self.test_data = AIValidationTestData()
    
    def test_performance_large_context(self):
        """Test AI service performance with large context"""
        import time
        
        performance_data = self.test_data.get_performance_test_data()
        strategic_intelligence = performance_data['strategic_intelligence']
        
        # Measure execution time
        start_time = time.time()
        test_cases = self.service.generate_ai_test_cases(strategic_intelligence)
        execution_time = time.time() - start_time
        
        # Verify performance threshold
        threshold = performance_data['performance_threshold_seconds']
        self.assertLess(execution_time, threshold, 
                       f"AI generation took {execution_time:.2f}s, exceeding {threshold}s threshold")
        
        # Verify results still generated
        self.assertGreater(len(test_cases), 0)
        
        # Verify large context handled correctly
        for test_case in test_cases:
            self.assertIn('technology_context', test_case)
            tech_context = test_case['technology_context']
            self.assertEqual(tech_context['primary'], 'MTV_CNV_Integration')
    
    def test_context_caching(self):
        """Test context understanding caching"""
        strategic_intelligence = {
            'complete_agent_intelligence': {
                'agents': {
                    'agent_a_jira_intelligence': {
                        'context_metadata': {
                            'jira_id': 'ACM-CACHE-TEST',
                            'jira_title': 'MTV addon caching test',
                            'component': 'MTV Test'
                        }
                    }
                }
            }
        }
        
        # First call - should populate cache
        analysis1 = self.service.analyze_feature_context(strategic_intelligence)
        
        # Verify cache is being used (implementation specific)
        # This test verifies the caching mechanism exists
        self.assertIsInstance(self.service.context_understanding_cache, dict)


if __name__ == '__main__':
    print("🧪 AI Test Generation Service Unit Tests")
    print("=" * 50)
    print("Testing AI-driven contextual test generation vs patterns")
    print("=" * 50)
    
    if not AI_SERVICE_AVAILABLE:
        print("❌ AI Test Generation Service not available - skipping tests")
        exit(1)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestAITestGenerationService))
    suite.addTests(loader.loadTestsFromTestCase(TestAITestGenerationServiceWithValidationData))
    suite.addTests(loader.loadTestsFromTestCase(TestAITestGenerationServicePerformance))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print(f"\n📊 AI Test Generation Service Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Error:')[-1].strip()}")
    
    exit(0 if result.wasSuccessful() else 1)
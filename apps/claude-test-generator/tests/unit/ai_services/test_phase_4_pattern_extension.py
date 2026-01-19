#!/usr/bin/env python3
"""
Phase 4 Pattern Extension Unit Tests
==================================

Comprehensive unit tests for Phase 4: Pattern Extension Implementation
Testing all components of the PatternExtensionService with thorough validation.
"""

import unittest
import sys
import os
import json
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ai_services_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.claude', 'ai-services')
sys.path.insert(0, ai_services_path)

try:
    from phase_4_pattern_extension import (
        PatternExtensionService,
        execute_phase_4_pattern_extension
    )
    PATTERN_EXTENSION_AVAILABLE = True
except ImportError as e:
    PATTERN_EXTENSION_AVAILABLE = False
    print(f"❌ Phase 4 Pattern Extension not available: {e}")


class TestPatternExtensionService(unittest.TestCase):
    """Test Pattern Extension Service core functionality"""
    
    @classmethod
    def setUpClass(cls):
        if not PATTERN_EXTENSION_AVAILABLE:
            cls.skipTest(cls, "Phase 4 Pattern Extension not available")
    
    def setUp(self):
        """Set up test environment"""
        self.service = PatternExtensionService()
        self.test_dir = tempfile.mkdtemp()
        self.maxDiff = None
        
        # Create comprehensive mock Phase 3 result
        self.mock_phase_3_result = {
            'strategic_intelligence': {
                'overall_confidence': 0.89,
                'phase_4_directives': {
                    'test_case_count': 3,
                    'steps_per_case': 7,
                    'testing_approach': 'Comprehensive',
                    'title_patterns': [
                        'Verify cluster-curator Functionality',
                        'Test cluster-curator Integration',
                        'Validate cluster-curator Operations'
                    ],
                    'focus_areas': ['Core functionality', 'Integration', 'Error handling'],
                    'risk_mitigations': ['Multi-repository complexity']
                },
                'complexity_assessment': {
                    'complexity_level': 'Medium',
                    'overall_complexity': 0.6,
                    'optimal_test_steps': 7,
                    'recommended_test_cases': 3
                },
                'testing_scope': {
                    'testing_scope': 'Comprehensive',
                    'coverage_approach': 'Full feature coverage with integration testing',
                    'optimal_test_steps': 7
                },
                'title_generation': {
                    'base_component': 'cluster-curator-controller',
                    'title_patterns': [
                        'Comprehensive cluster-curator-controller Functionality Testing',
                        'End-to-End cluster-curator-controller Workflow Validation',
                        'Integrated cluster-curator-controller Operations Testing'
                    ],
                    'recommended_count': 3
                },
                'agent_intelligence_summary': {
                    'jira_insights': {
                        'findings': {
                            'requirement_analysis': {
                                'component_focus': 'cluster-curator-controller',
                                'priority_level': 'High'
                            }
                        }
                    }
                }
            }
        }
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_pattern_extension_service_initialization(self):
        """Test Pattern Extension Service initializes correctly"""
        service = PatternExtensionService()
        
        self.assertIsInstance(service.test_patterns, dict)
        self.assertGreater(len(service.test_patterns), 0)
        self.assertIsNone(service.format_enforcer)
        
        # Verify proven patterns are loaded
        self.assertIn('basic_functionality', service.test_patterns)
        self.assertIn('comprehensive_workflow', service.test_patterns)
        self.assertIn('complex_integration', service.test_patterns)
    
    def test_load_proven_patterns(self):
        """Test loading of proven test patterns"""
        patterns = self.service._load_proven_patterns()
        
        # Verify structure
        self.assertIsInstance(patterns, dict)
        self.assertGreater(len(patterns), 0)
        
        # Check each pattern structure
        for pattern_name, pattern_data in patterns.items():
            self.assertIn('pattern_type', pattern_data)
            self.assertIn('steps_range', pattern_data)
            self.assertIn('structure', pattern_data)
            
            # Verify steps range is tuple
            self.assertIsInstance(pattern_data['steps_range'], tuple)
            self.assertEqual(len(pattern_data['steps_range']), 2)
            self.assertLess(pattern_data['steps_range'][0], pattern_data['steps_range'][1])
            
            # Verify structure is list
            self.assertIsInstance(pattern_data['structure'], list)
            self.assertGreater(len(pattern_data['structure']), 0)
    
    async def test_select_patterns_low_complexity(self):
        """Test pattern selection for low complexity"""
        low_complexity_directives = {
            'test_case_count': 2,
            'steps_per_case': 5,
            'testing_approach': 'Focused'
        }
        
        selected_patterns = await self.service._select_patterns(low_complexity_directives)
        
        # Verify selection
        self.assertIsInstance(selected_patterns, list)
        self.assertGreater(len(selected_patterns), 0)
        
        # Should select basic functionality pattern for low complexity
        pattern_types = [p['pattern_type'] for p in selected_patterns]
        self.assertIn('Core Feature Testing', pattern_types)
        
        # Verify each pattern has required fields
        for pattern in selected_patterns:
            self.assertIn('pattern_type', pattern)
            self.assertIn('steps_range', pattern)
            self.assertIn('structure', pattern)
            self.assertIn('selected_reason', pattern)
    
    async def test_select_patterns_medium_complexity(self):
        """Test pattern selection for medium complexity"""
        medium_complexity_directives = {
            'test_case_count': 3,
            'steps_per_case': 7,
            'testing_approach': 'Comprehensive'
        }
        
        selected_patterns = await self.service._select_patterns(medium_complexity_directives)
        
        # Verify selection
        self.assertIsInstance(selected_patterns, list)
        self.assertGreater(len(selected_patterns), 0)
        
        # Should select comprehensive workflow pattern for medium complexity
        pattern_types = [p['pattern_type'] for p in selected_patterns]
        self.assertIn('End-to-End Workflow Testing', pattern_types)
    
    async def test_select_patterns_high_complexity(self):
        """Test pattern selection for high complexity"""
        high_complexity_directives = {
            'test_case_count': 4,
            'steps_per_case': 10,
            'testing_approach': 'Extensive'
        }
        
        selected_patterns = await self.service._select_patterns(high_complexity_directives)
        
        # Verify selection
        self.assertIsInstance(selected_patterns, list)
        self.assertGreater(len(selected_patterns), 0)
        
        # Should select complex integration pattern for high complexity
        pattern_types = [p['pattern_type'] for p in selected_patterns]
        self.assertIn('Multi-Component Integration Testing', pattern_types)
        
        # Should include multiple patterns for higher test case count
        if high_complexity_directives['test_case_count'] > 2:
            self.assertGreater(len(selected_patterns), 1)
    
    async def test_generate_test_cases(self):
        """Test test case generation from patterns"""
        # Use medium complexity patterns
        selected_patterns = [
            {
                'pattern_type': 'End-to-End Workflow Testing',
                'steps_range': (6, 8),
                'structure': [
                    'Access and login to system',
                    'Navigate to feature area',
                    'Configure feature settings',
                    'Execute primary workflow',
                    'Verify workflow completion',
                    'Cleanup and logout'
                ]
            }
        ]
        
        strategic_intelligence = self.mock_phase_3_result['strategic_intelligence']
        
        test_cases = await self.service._generate_test_cases(selected_patterns, strategic_intelligence)
        
        # Verify structure
        self.assertIsInstance(test_cases, list)
        self.assertEqual(len(test_cases), 1)
        
        # Verify test case structure
        test_case = test_cases[0]
        self.assertIn('test_case_id', test_case)
        self.assertIn('title', test_case)
        self.assertIn('description', test_case)
        self.assertIn('setup', test_case)
        self.assertIn('pattern_used', test_case)
        self.assertIn('steps', test_case)
        
        # Verify test case content
        self.assertTrue(test_case['test_case_id'].startswith('TC_'))
        self.assertIn('cluster-curator-controller', test_case['title'])
        self.assertIn('cluster-curator-controller', test_case['description'])
        self.assertEqual(test_case['pattern_used'], 'End-to-End Workflow Testing')
        
        # Verify steps
        self.assertIsInstance(test_case['steps'], list)
        self.assertEqual(len(test_case['steps']), len(selected_patterns[0]['structure']))
        
        # Verify each step structure
        for step in test_case['steps']:
            self.assertIn('step_number', step)
            self.assertIn('description', step)
            self.assertIn('ui_method', step)
            self.assertIn('cli_method', step)
            self.assertIn('expected_result', step)
    
    @patch('phase_4_pattern_extension.PatternExtensionService._try_ai_test_generation')
    async def test_generate_test_cases_with_ai_success(self, mock_ai_generation):
        """Test test case generation with AI service success"""
        # Mock AI generation returning MTV-specific test cases
        mock_ai_test_cases = [
            {
                'test_case_id': 'AI_TC_01',
                'title': 'Verify MTV Addon Webhook Provider Creation',
                'description': 'Verify MTV addon webhook automatically creates providers for CNV clusters',
                'pattern_used': 'AI_Generated_Contextual',
                'ai_generated': True,
                'ai_confidence': 0.92,
                'technology_context': {
                    'primary': 'MTV_CNV_Integration',
                    'components': ['Migration Toolkit for Virtualization', 'CNV Operator']
                },
                'steps': [
                    {
                        'step_number': 1,
                        'description': 'Apply CNV operator installation label to managed cluster',
                        'ui_method': 'Navigate to Cluster Management → Add label',
                        'cli_method': 'oc label managedcluster <CLUSTER> acm/cnv-operator-install=true',
                        'expected_result': 'Label applied successfully, CNV operator installation begins'
                    }
                ]
            }
        ]
        mock_ai_generation.return_value = mock_ai_test_cases
        
        # Create MTV context for AI generation
        mtv_strategic_intelligence = {
            'complete_agent_intelligence': {
                'agents': {
                    'agent_a_jira_intelligence': {
                        'context_metadata': {
                            'jira_id': 'ACM-22348',
                            'jira_title': 'Onboard CNV addon and MTV-integrations into ACM Installer',
                            'component': 'MTV Addon Integration'
                        }
                    }
                }
            }
        }
        
        selected_patterns = [{'pattern_type': 'Basic Pattern'}]
        
        test_cases = await self.service._generate_test_cases(selected_patterns, mtv_strategic_intelligence)
        
        # Verify AI generation was attempted and succeeded
        mock_ai_generation.assert_called_once_with(mtv_strategic_intelligence)
        
        # Verify AI test cases were returned
        self.assertEqual(test_cases, mock_ai_test_cases)
        self.assertEqual(len(test_cases), 1)
        
        # Verify AI-specific fields
        test_case = test_cases[0]
        self.assertTrue(test_case['ai_generated'])
        self.assertEqual(test_case['ai_confidence'], 0.92)
        self.assertEqual(test_case['technology_context']['primary'], 'MTV_CNV_Integration')
    
    @patch('phase_4_pattern_extension.PatternExtensionService._try_ai_test_generation')
    async def test_generate_test_cases_ai_fallback_to_patterns(self, mock_ai_generation):
        """Test test case generation falling back to patterns when AI fails"""
        # Mock AI generation returning None (failure)
        mock_ai_generation.return_value = None
        
        selected_patterns = [
            {
                'pattern_type': 'Basic Functionality Pattern',
                'structure': ['Access system', 'Execute operation', 'Verify results']
            }
        ]
        
        strategic_intelligence = self.mock_phase_3_result['strategic_intelligence']
        
        test_cases = await self.service._generate_test_cases(selected_patterns, strategic_intelligence)
        
        # Verify AI generation was attempted
        mock_ai_generation.assert_called_once_with(strategic_intelligence)
        
        # Verify fallback to pattern-based generation
        self.assertIsInstance(test_cases, list)
        self.assertGreater(len(test_cases), 0)
        
        # Verify pattern-based fields (not AI-generated)
        test_case = test_cases[0]
        self.assertNotIn('ai_generated', test_case)
        self.assertEqual(test_case['pattern_used'], 'Basic Functionality Pattern')
    
    def test_customize_step(self):
        """Test step template customization"""
        component = 'cluster-curator-controller'
        
        # Test various step templates
        test_cases = [
            ('Access and login to system', 'initial cluster authentication'),
            ('Navigate to feature area', f'{component} availability'),
            ('Execute core functionality', f'{component} core operations'),
            ('Verify expected results', f'{component} operation completion')
        ]
        
        for template, expected_content in test_cases:
            result = self.service._customize_step(template, component)
            self.assertIn(expected_content, result)
    
    def test_generate_ui_method(self):
        """Test UI method generation"""
        component = 'cluster-curator-controller'
        
        # Test login step
        ui_method = self.service._generate_ui_method('login', component)
        self.assertIn('<CLUSTER_CONSOLE_URL>', ui_method)
        
        # Test navigate step
        ui_method = self.service._generate_ui_method('navigate to feature', component)
        self.assertIn('All Clusters', ui_method)
        self.assertIn(component, ui_method)
        
        # Test configure step
        ui_method = self.service._generate_ui_method('configure settings', component)
        self.assertIn('Create', ui_method)
        self.assertIn(component, ui_method)
    
    def test_generate_cli_method(self):
        """Test CLI method generation"""
        component = 'cluster-curator-controller'
        
        # Test login step
        cli_method = self.service._generate_cli_method('login', component)
        self.assertIn('oc login', cli_method)
        self.assertIn('<CLUSTER_API_URL>', cli_method)
        
        # Test configure step
        cli_method = self.service._generate_cli_method('configure', component)
        self.assertIn('oc apply', cli_method)
        self.assertIn('apiVersion', cli_method)
        self.assertIn(component, cli_method)
        
        # Test verify step
        cli_method = self.service._generate_cli_method('verify status', component)
        self.assertIn('oc get', cli_method)
        self.assertIn('Expected YAML', cli_method)
    
    def test_generate_expected_result(self):
        """Test expected result generation"""
        component = 'cluster-curator-controller'
        
        # Test login result
        result = self.service._generate_expected_result('login', component)
        self.assertIn('Successfully logged into ACM Console', result)
        
        # Test execute result
        result = self.service._generate_expected_result('execute operation', component)
        self.assertIn(component, result)
        self.assertIn('successfully', result)
        
        # Test verify result
        result = self.service._generate_expected_result('verify status', component)
        self.assertIn(component, result)
        self.assertIn('Ready', result)
    
    async def test_validate_evidence(self):
        """Test evidence validation"""
        test_cases = [
            {
                'test_case_id': 'TC_01',
                'title': 'Test Case',
                'pattern_used': 'Core Feature Testing'
            }
        ]
        
        strategic_intelligence = self.mock_phase_3_result['strategic_intelligence']
        
        validated_cases = await self.service._validate_evidence(test_cases, strategic_intelligence)
        
        # Verify evidence was added
        self.assertEqual(len(validated_cases), 1)
        validated_case = validated_cases[0]
        
        self.assertIn('evidence_sources', validated_case)
        self.assertIn('validation_status', validated_case)
        self.assertIn('pattern_evidence', validated_case)
        
        # Verify evidence sources
        evidence = validated_case['evidence_sources']
        self.assertIn('jira_ticket', evidence)
        self.assertIn('implementation_pr', evidence)
        self.assertIn('documentation', evidence)
        self.assertIn('environment', evidence)
        
        # Verify validation status
        self.assertEqual(validated_case['validation_status'], 'Evidence-validated')
        
        # Verify pattern evidence
        pattern_evidence = validated_case['pattern_evidence']
        self.assertEqual(pattern_evidence['base_pattern'], 'Core Feature Testing')
        self.assertTrue(pattern_evidence['proven_success'])
    
    async def test_enforce_format_standards(self):
        """Test format enforcement"""
        test_cases = [
            {
                'title': 'cluster-curator Functionality',
                'steps': [
                    {
                        'description': 'Test step with <br> HTML tags',
                        'ui_method': 'UI method with <b>bold</b> text',
                        'cli_method': 'CLI method with <br> breaks',
                        'expected_result': 'Result with <i>italic</i> text'
                    }
                ]
            }
        ]
        
        formatted_cases = await self.service._enforce_format_standards(test_cases)
        
        # Verify format enforcement
        self.assertEqual(len(formatted_cases), 1)
        formatted_case = formatted_cases[0]
        
        # Verify title formatting
        self.assertTrue(formatted_case['title'].startswith('Verify'))
        
        # Verify HTML tag removal
        step = formatted_case['steps'][0]
        self.assertNotIn('<br>', step['description'])
        self.assertNotIn('<b>', step['ui_method'])
        self.assertNotIn('</b>', step['ui_method'])
        self.assertNotIn('<i>', step['expected_result'])
        self.assertNotIn('</i>', step['expected_result'])
        
        # Verify replacements
        self.assertIn('**bold**', step['ui_method'])
    
    @patch('phase_4_pattern_extension.PatternExtensionService._apply_enforcement_validation')
    async def test_generate_dual_reports(self, mock_enforcement):
        """Test dual report generation with enforcement validation"""
        # Mock enforcement validation to return original content
        mock_enforcement.return_value = "# Test Cases\n\nMocked test plan content"
        
        test_cases = [
            {
                'title': 'Verify cluster-curator Functionality',
                'description': 'Test cluster-curator operations',
                'setup': 'Access to ACM Console',
                'steps': [
                    {
                        'step_number': 1,
                        'description': 'Log into ACM Console',
                        'ui_method': 'Navigate to console',
                        'cli_method': '```bash\noc login\n```',
                        'expected_result': 'Successfully logged in'
                    }
                ]
            }
        ]
        
        strategic_intelligence = self.mock_phase_3_result['strategic_intelligence']
        
        reports = await self.service._generate_dual_reports(test_cases, strategic_intelligence, self.test_dir)
        
        # Verify enforcement validation was called
        mock_enforcement.assert_called_once()
        
        # Verify reports structure
        self.assertIn('test_cases_report', reports)
        self.assertIn('complete_analysis_report', reports)
        
        # Verify files were created
        test_cases_file = reports['test_cases_report']
        analysis_file = reports['complete_analysis_report']
        
        self.assertTrue(os.path.exists(test_cases_file))
        self.assertTrue(os.path.exists(analysis_file))
        self.assertTrue(test_cases_file.endswith('Test-Cases.md'))
        self.assertTrue(analysis_file.endswith('Complete-Analysis.md'))
        
        # Verify file content includes enforcement validation
        with open(test_cases_file, 'r') as f:
            test_content = f.read()
        
        self.assertIn('# Test Cases', test_content)
        self.assertIn('Mocked test plan content', test_content)
        
        with open(analysis_file, 'r') as f:
            analysis_content = f.read()
        
        self.assertIn('# Complete Analysis Report', analysis_content)
        self.assertIn('## Summary', analysis_content)
        self.assertIn('## 1. Strategic Intelligence Summary', analysis_content)
    
    def test_generate_test_cases_report(self):
        """Test test cases report generation"""
        test_cases = [
            {
                'title': 'Test Case 1',
                'description': 'Test description',
                'setup': 'Test setup',
                'steps': [
                    {
                        'step_number': 1,
                        'description': 'Step 1',
                        'ui_method': 'UI Method 1',
                        'cli_method': 'CLI Method 1',
                        'expected_result': 'Result 1'
                    }
                ]
            }
        ]
        
        content = self.service._generate_test_cases_report(test_cases)
        
        # Verify content structure
        self.assertIn('# Test Cases', content)
        self.assertIn('## Test Case 1', content)
        self.assertIn('**What We\'re Doing**: Test description', content)
        self.assertIn('### Prerequisites', content)
        self.assertIn('### Test Steps', content)
        self.assertIn('| Step | Action | UI Method | CLI Method | Expected Result |', content)
        self.assertIn('| 1 | **What We\'re Doing**: Step 1 | UI Method 1 |', content)
    
    def test_generate_complete_analysis_report(self):
        """Test complete analysis report generation"""
        test_cases = [
            {
                'title': 'Test Case 1',
                'description': 'Test description',
                'pattern_used': 'Core Feature Testing',
                'steps': [{'step_number': 1}]
            }
        ]
        
        strategic_intelligence = self.mock_phase_3_result['strategic_intelligence']
        
        content = self.service._generate_complete_analysis_report(test_cases, strategic_intelligence)
        
        # Verify content structure
        self.assertIn('# Complete Analysis Report', content)
        self.assertIn('## 🎯 Executive Summary', content)
        self.assertIn('## 📊 JIRA Intelligence Analysis', content)
        self.assertIn('## 🌍 Environment Intelligence Assessment', content)
        self.assertIn('## 🧪 Testing Strategy & Scope', content)
        
        # Verify test case information
        self.assertIn('Test Case 1', content)
        self.assertIn('comprehensive test scenarios', content)
    
    def test_calculate_pattern_confidence(self):
        """Test pattern confidence calculation"""
        selected_patterns = [
            {'pattern_type': 'Core Feature Testing'},
            {'pattern_type': 'End-to-End Workflow Testing'},
            {'pattern_type': 'Multi-Component Integration Testing'}
        ]
        
        confidence = self.service._calculate_pattern_confidence(selected_patterns)
        
        # Verify confidence calculation
        self.assertGreaterEqual(confidence, 0.95)  # Base confidence
        self.assertLessEqual(confidence, 1.0)
        
        # Should be higher with more diverse patterns
        single_pattern = [{'pattern_type': 'Core Feature Testing'}]
        single_confidence = self.service._calculate_pattern_confidence(single_pattern)
        
        self.assertGreaterEqual(confidence, single_confidence)
    
    async def test_save_final_results(self):
        """Test saving final results metadata"""
        reports = {
            'test_cases_report': '/test/Test-Cases.md',
            'complete_analysis_report': '/test/Complete-Analysis.md'
        }
        
        metadata = await self.service._save_final_results(reports, self.test_dir)
        
        # Verify metadata structure
        self.assertIn('phase_4_completion', metadata)
        self.assertIn('reports_generated', metadata)
        self.assertIn('pattern_extension_success', metadata)
        self.assertIn('final_deliverables', metadata)
        
        # Verify metadata content
        self.assertTrue(metadata['pattern_extension_success'])
        self.assertEqual(len(metadata['reports_generated']), 2)
        
        deliverables = metadata['final_deliverables']
        self.assertIn('test_cases', deliverables)
        self.assertIn('complete_analysis', deliverables)
        
        # Verify file was saved
        metadata_files = list(Path(self.test_dir).glob('phase_4_completion.json'))
        self.assertEqual(len(metadata_files), 1)
    
    async def test_execute_pattern_extension_phase_success(self):
        """Test complete pattern extension phase execution - success case"""
        result = await self.service.execute_pattern_extension_phase(
            self.mock_phase_3_result,
            self.test_dir
        )
        
        # Verify result structure
        self.assertIn('phase_name', result)
        self.assertIn('execution_status', result)
        self.assertIn('execution_time', result)
        self.assertIn('test_cases_generated', result)
        self.assertIn('reports_generated', result)
        self.assertIn('final_output', result)
        self.assertIn('pattern_confidence', result)
        
        # Verify success
        self.assertEqual(result['execution_status'], 'success')
        self.assertEqual(result['phase_name'], 'Phase 4 - Pattern Extension')
        self.assertGreaterEqual(result['execution_time'], 0)
        self.assertGreater(result['test_cases_generated'], 0)
        self.assertGreaterEqual(result['pattern_confidence'], 0.95)
        
        # Verify reports were generated
        reports = result['reports_generated']
        self.assertIn('test_cases_report', reports)
        self.assertIn('complete_analysis_report', reports)
        
        # Verify files exist
        for report_file in reports.values():
            self.assertTrue(os.path.exists(report_file))
    
    async def test_execute_pattern_extension_phase_failure(self):
        """Test pattern extension phase execution - failure case"""
        # Create invalid phase 3 result to trigger failure
        invalid_phase_3_result = {'invalid': 'data'}
        
        result = await self.service.execute_pattern_extension_phase(
            invalid_phase_3_result,
            self.test_dir
        )
        
        # Verify failure handling
        self.assertEqual(result['execution_status'], 'failed')
        self.assertIn('error_message', result)


class TestPhase4ConvenienceFunctions(unittest.TestCase):
    """Test Phase 4 convenience functions"""
    
    @classmethod
    def setUpClass(cls):
        if not PATTERN_EXTENSION_AVAILABLE:
            cls.skipTest(cls, "Phase 4 Pattern Extension not available")
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create minimal mock Phase 3 result
        self.mock_phase_3_result = {
            'strategic_intelligence': {
                'phase_4_directives': {
                    'test_case_count': 2,
                    'steps_per_case': 5,
                    'testing_approach': 'Focused'
                },
                'complexity_assessment': {
                    'complexity_level': 'Low'
                },
                'testing_scope': {
                    'testing_scope': 'Focused'
                }
            }
        }
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    async def test_execute_phase_4_pattern_extension_convenience_function(self):
        """Test the convenience function for Phase 4 execution"""
        result = await execute_phase_4_pattern_extension(
            self.mock_phase_3_result,
            self.test_dir
        )
        
        # Verify result
        self.assertIn('execution_status', result)
        self.assertEqual(result['execution_status'], 'success')
        self.assertIn('test_cases_generated', result)


class TestPhase4EdgeCases(unittest.TestCase):
    """Test Phase 4 edge cases and error conditions"""
    
    @classmethod
    def setUpClass(cls):
        if not PATTERN_EXTENSION_AVAILABLE:
            cls.skipTest(cls, "Phase 4 Pattern Extension not available")
    
    def setUp(self):
        """Set up test environment"""
        self.service = PatternExtensionService()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    async def test_select_patterns_minimal_directives(self):
        """Test pattern selection with minimal directives"""
        minimal_directives = {}
        
        selected_patterns = await self.service._select_patterns(minimal_directives)
        
        # Should provide sensible defaults
        self.assertIsInstance(selected_patterns, list)
        self.assertGreater(len(selected_patterns), 0)
        
        # Verify each pattern has required fields
        for pattern in selected_patterns:
            self.assertIn('pattern_type', pattern)
            self.assertIn('selected_reason', pattern)
    
    async def test_generate_test_cases_empty_patterns(self):
        """Test test case generation with empty patterns"""
        empty_patterns = []
        strategic_intelligence = {'agent_intelligence_summary': {}}
        
        test_cases = await self.service._generate_test_cases(empty_patterns, strategic_intelligence)
        
        # Should handle empty patterns gracefully
        self.assertIsInstance(test_cases, list)
        self.assertEqual(len(test_cases), 0)
    
    async def test_validate_evidence_empty_test_cases(self):
        """Test evidence validation with empty test cases"""
        empty_test_cases = []
        strategic_intelligence = {}
        
        validated_cases = await self.service._validate_evidence(empty_test_cases, strategic_intelligence)
        
        # Should handle empty input gracefully
        self.assertIsInstance(validated_cases, list)
        self.assertEqual(len(validated_cases), 0)
    
    async def test_enforce_format_standards_edge_cases(self):
        """Test format enforcement with edge cases"""
        edge_case_tests = [
            {
                'title': 'title without Verify',
                'steps': [
                    {
                        'description': 'Normal description',
                        'ui_method': 'Normal UI method',
                        'cli_method': 'Normal CLI method',
                        'expected_result': 'Normal result'
                    }
                ]
            }
        ]
        
        formatted_cases = await self.service._enforce_format_standards(edge_case_tests)
        
        # Verify title was fixed
        self.assertTrue(formatted_cases[0]['title'].startswith('Verify'))
    
    def test_format_methods_edge_cases(self):
        """Test format helper methods with edge cases"""
        # Test empty complexity assessment
        empty_assessment = {}
        result = self.service._format_complexity_summary(empty_assessment)
        self.assertIn('not available', result)
        
        # Test empty testing scope
        empty_scope = {}
        result = self.service._format_testing_scope(empty_scope)
        self.assertIn('not available', result)


class TestPhase4Integration(unittest.TestCase):
    """Test Phase 4 integration scenarios"""
    
    @classmethod
    def setUpClass(cls):
        if not PATTERN_EXTENSION_AVAILABLE:
            cls.skipTest(cls, "Phase 4 Pattern Extension not available")
    
    def setUp(self):
        """Set up test environment"""
        self.service = PatternExtensionService()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    async def test_end_to_end_pattern_extension(self):
        """Test complete end-to-end pattern extension workflow"""
        # Create comprehensive Phase 3 result
        phase_3_result = {
            'strategic_intelligence': {
                'overall_confidence': 0.92,
                'phase_4_directives': {
                    'test_case_count': 2,
                    'steps_per_case': 6,
                    'testing_approach': 'Comprehensive',
                    'title_patterns': ['Test Pattern 1', 'Test Pattern 2'],
                    'focus_areas': ['Core', 'Integration'],
                    'risk_mitigations': []
                },
                'complexity_assessment': {
                    'complexity_level': 'Medium',
                    'overall_complexity': 0.5,
                    'optimal_test_steps': 6,
                    'recommended_test_cases': 2
                },
                'testing_scope': {
                    'testing_scope': 'Comprehensive',
                    'coverage_approach': 'Full feature coverage'
                },
                'title_generation': {
                    'base_component': 'test-component',
                    'title_patterns': ['Pattern 1', 'Pattern 2'],
                    'recommended_count': 2
                },
                'agent_intelligence_summary': {
                    'jira_insights': {
                        'findings': {
                            'requirement_analysis': {
                                'component_focus': 'test-component'
                            }
                        }
                    }
                }
            }
        }
        
        # Execute complete workflow
        result = await self.service.execute_pattern_extension_phase(phase_3_result, self.test_dir)
        
        # Verify complete success
        self.assertEqual(result['execution_status'], 'success')
        self.assertGreater(result['test_cases_generated'], 0)
        self.assertGreaterEqual(result['pattern_confidence'], 0.95)
        
        # Verify all deliverables were created
        final_output = result['final_output']
        self.assertIn('final_deliverables', final_output)
        
        deliverables = final_output['final_deliverables']
        for file_path in deliverables.values():
            if file_path:  # Skip None values
                self.assertTrue(os.path.exists(file_path))




class TestChangeImpactAnalysis(unittest.TestCase):
    """Test Change Impact Analysis functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = PatternExtensionService()
    
    def test_should_skip_test_case_unchanged_acm_integration(self):
        """Test skipping test cases for unchanged ACM integrations"""
        pattern = {
            'pattern_type': 'Multi-Component Integration Testing',
            'description': 'Test ACM integration'
        }
        unchanged_functionality = [
            'ACM ManagedCluster status propagation',
            'Cross-cluster communication mechanisms'
        ]
        
        result = self.service._should_skip_test_case_for_unchanged_functionality(
            pattern, unchanged_functionality
        )
        
        self.assertTrue(result)
    
    def test_should_skip_test_case_unchanged_status_propagation(self):
        """Test skipping test cases for unchanged status propagation"""
        pattern = {
            'pattern_type': 'Integration Validation Testing',
            'description': 'Test status validation'
        }
        unchanged_functionality = [
            'ACM ManagedCluster status propagation'
        ]
        
        result = self.service._should_skip_test_case_for_unchanged_functionality(
            pattern, unchanged_functionality
        )
        
        self.assertTrue(result)
    
    def test_should_not_skip_test_case_new_functionality(self):
        """Test not skipping test cases for new functionality"""
        pattern = {
            'pattern_type': 'Core Feature Testing',
            'description': 'Test new digest functionality'
        }
        unchanged_functionality = [
            'ACM ManagedCluster status propagation'
        ]
        
        result = self.service._should_skip_test_case_for_unchanged_functionality(
            pattern, unchanged_functionality
        )
        
        self.assertFalse(result)
    
    def test_should_not_skip_test_case_no_unchanged_functionality(self):
        """Test not skipping when no unchanged functionality specified"""
        pattern = {
            'pattern_type': 'Multi-Component Integration Testing'
        }
        unchanged_functionality = []
        
        result = self.service._should_skip_test_case_for_unchanged_functionality(
            pattern, unchanged_functionality
        )
        
        self.assertFalse(result)
    
    async def test_generate_test_cases_with_change_impact_filtering(self):
        """Test test case generation with change impact filtering enabled"""
        phase_3_result = {
            'strategic_intelligence': {
                'jira_id': 'ACM-22079',
                'component': 'ClusterCurator',
                'complexity': 'Medium',
                'testing_scope': 'Medium',
                'functionality_categories': {
                    'new_functionality': ['Digest-based upgrade pathway'],
                    'enhanced_functionality': ['ClusterCurator upgrade workflow'],
                    'unchanged_functionality': ['ACM ManagedCluster status propagation']
                },
                'change_impact_filtering_applied': True
            },
            'pattern_generation_directives': {
                'test_case_count': 6,
                'steps_per_case': 8,
                'testing_approach': 'Comprehensive'
            }
        }
        
        test_cases = await self.service._generate_test_cases(phase_3_result)
        
        # Verify test cases were generated
        self.assertIsInstance(test_cases, list)
        self.assertGreater(len(test_cases), 0)
        
        # Verify change impact filtering was applied (should have fewer cases)
        self.assertLessEqual(len(test_cases), 6)
        
        # Verify change impact awareness is marked in test cases
        for test_case in test_cases:
            if 'change_impact_aware' in test_case:
                self.assertTrue(test_case['change_impact_aware'])


class TestPatternExtensionEnforcementIntegration(unittest.TestCase):
    """Test Pattern Extension Service enforcement integration"""
    
    @classmethod
    def setUpClass(cls):
        if not PATTERN_EXTENSION_AVAILABLE:
            cls.skipTest(cls, "Phase 4 Pattern Extension not available")
    
    def setUp(self):
        """Set up test environment"""
        self.service = PatternExtensionService()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('sys.path.append')
    @patch('phase_4_pattern_extension.enforce_e2e_focus')
    @patch('phase_4_pattern_extension.enforce_functional_focus') 
    @patch('phase_4_pattern_extension.integrate_functional_enforcement')
    async def test_apply_enforcement_validation_success(self, mock_integration, mock_functional, mock_e2e, mock_path):
        """Test successful enforcement validation"""
        # Mock successful enforcement
        mock_e2e.return_value = (True, {'e2e_focus_percentage': 100, 'compliance_score': 100}, "E2E Report")
        mock_functional.return_value = (True, {'compliance_score': 100}, "Functional Report")
        mock_integration.return_value = (True, "Original content", "Integration Report")
        
        test_content = "# Test Cases\n\nOriginal test plan content"
        
        result = await self.service._apply_enforcement_validation(test_content, self.test_dir)
        
        # Verify enforcement systems were called
        mock_e2e.assert_called_once()
        mock_functional.assert_called_once()
        mock_integration.assert_called_once()
        
        # Verify original content returned (enforcement passed)
        self.assertEqual(result, test_content)
        
        # Verify enforcement reports directory created
        enforcement_dir = os.path.join(self.test_dir, "enforcement-reports")
        self.assertTrue(os.path.exists(enforcement_dir))
    
    @patch('sys.path.append')
    @patch('phase_4_pattern_extension.enforce_e2e_focus')
    async def test_apply_enforcement_validation_e2e_failure(self, mock_e2e, mock_path):
        """Test enforcement validation with E2E failure (should block delivery)"""
        # Mock E2E enforcement failure
        mock_e2e.return_value = (False, {
            'prohibited_categories_detected': 3,
            'e2e_focus_percentage': 60,
            'compliance_score': 60,
            'violations_detail': ['Unit testing detected', 'Performance testing detected'],
            'corrective_recommendations': ['Remove unit tests', 'Remove performance tests']
        }, "E2E Failure Report")
        
        test_content = "# Test Cases with violations\n\n### 1. Unit Testing\n### 2. Performance Testing"
        
        result = await self.service._apply_enforcement_validation(test_content, self.test_dir)
        
        # Verify E2E enforcement was called
        mock_e2e.assert_called_once()
        
        # Verify delivery was blocked
        self.assertIn('TEST PLAN DELIVERY BLOCKED', result)
        self.assertIn('E2E FOCUS ENFORCEMENT FAILED', result)
        self.assertIn('3', result)  # prohibited categories count
        self.assertIn('60%', result)  # compliance score
        self.assertIn('Unit testing detected', result)
        self.assertIn('Remove unit tests', result)
        
        # Verify enforcement report was saved
        e2e_report_file = os.path.join(self.test_dir, "E2E-Focus-Enforcement-Report.md")
        self.assertTrue(os.path.exists(e2e_report_file))
    
    @patch('sys.path.append')
    @patch('phase_4_pattern_extension.enforce_e2e_focus')
    async def test_apply_enforcement_validation_exception_handling(self, mock_e2e, mock_path):
        """Test enforcement validation with exception handling"""
        # Mock enforcement exception
        mock_e2e.side_effect = Exception("Enforcement system error")
        
        test_content = "# Test Cases\n\nOriginal content"
        
        result = await self.service._apply_enforcement_validation(test_content, self.test_dir)
        
        # Verify exception was handled gracefully
        self.assertIn('WARNING', result)
        self.assertIn('Enforcement validation encountered an error', result)
        self.assertIn('Enforcement system error', result)
        self.assertIn('Original content', result)


if __name__ == '__main__':
    print("🧪 Phase 4 Pattern Extension Unit Tests")
    print("=" * 45)
    print("Testing Pattern Extension Service comprehensive functionality")
    print("=" * 45)
    
    if not PATTERN_EXTENSION_AVAILABLE:
        print("❌ Phase 4 Pattern Extension not available - skipping tests")
        exit(1)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestPatternExtensionService))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase4ConvenienceFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase4EdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase4Integration))
    suite.addTests(loader.loadTestsFromTestCase(TestChangeImpactAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestPatternExtensionEnforcementIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print(f"\n📊 Phase 4 Test Summary:")
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
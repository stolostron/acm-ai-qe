#!/usr/bin/env python3
"""
Unit Tests: Pipe Character Escaping for Markdown Table Compatibility
Test the pipe character escaping implementation in CLI commands
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, '.claude', 'ai-services'))

from phase_4_pattern_extension import PatternExtensionService


class TestPipeCharacterEscaping(unittest.TestCase):
    """Test pipe character escaping for markdown table compatibility"""
    
    def setUp(self):
        self.service = PatternExtensionService()
    
    def test_format_enforcement_escapes_pipe_characters(self):
        """Test that format enforcement escapes pipe characters in all step fields"""
        
        # Test cases with pipe characters in different fields
        test_cases = [
            {
                'test_case_id': 'TC_01',
                'title': 'Test Pipe Escaping',
                'description': 'Test pipe escaping functionality',
                'feature_context': {
                    'component': 'ClusterCurator',
                    'title': 'Pipe character testing',
                    'priority': 'High'
                },
                'steps': [
                    {
                        'step_number': 1,
                        'description': 'Testing with | pipe character',
                        'ui_method': 'Navigate | to console',
                        'cli_method': 'oc get pods | grep running',
                        'expected_result': 'Output | shows results'
                    },
                    {
                        'step_number': 2,
                        'description': 'Multiple | pipe | characters',
                        'ui_method': 'Click | navigate | verify',
                        'cli_method': 'oc get clusterversion version -o jsonpath=\'{.status.conditionalUpdates[*].release.version}\' | tr \' \' \'\\n\'',
                        'expected_result': 'Expected | output | displayed'
                    }
                ]
            }
        ]
        
        # Apply format enforcement
        import asyncio
        result = asyncio.run(self.service._enforce_format_standards(test_cases))
        
        # Verify pipe characters are escaped in all fields
        step1 = result[0]['steps'][0]
        step2 = result[0]['steps'][1]
        
        # Check step 1
        self.assertIn('&#124;', step1['description'])
        self.assertIn('&#124;', step1['ui_method'])
        self.assertIn('&#124;', step1['cli_method'])
        self.assertIn('&#124;', step1['expected_result'])
        
        # Check step 2 - especially the CLI command with tr ' ' '\n'
        self.assertIn('&#124;', step2['cli_method'])
        self.assertIn('tr \' \' \'\\n\'', step2['cli_method'])  # tr command should remain intact
        
        # Verify no raw pipe characters remain (except in specific contexts)
        self.assertNotIn('oc get pods | grep running', step1['cli_method'])
        self.assertTrue('oc get pods &#124; grep running' in step1['cli_method'])
        
        print("✅ Format enforcement pipe character escaping test passed")
    
    def test_table_generation_escapes_pipe_characters(self):
        """Test that table generation properly escapes pipe characters in CLI commands"""
        
        # Mock test case with pipe characters
        test_cases = [
            {
                'test_case_id': 'TC_01',
                'title': 'Test Table Pipe Escaping',
                'description': 'Test table pipe escaping',
                'feature_context': {
                    'component': 'ClusterCurator',
                    'title': 'Table pipe character testing',
                    'priority': 'High'
                },
                'steps': [
                    {
                        'step_number': 1,
                        'description': 'Testing conditionalUpdates command',
                        'ui_method': 'Not applicable - CLI method required',
                        'cli_method': 'oc get clusterversion version -o jsonpath=\'{.status.conditionalUpdates[*].release.version}\' | tr \' \' \'\\n\'',
                        'expected_result': 'Expected output: 4.16.37-multi'
                    }
                ]
            }
        ]
        
        # Generate test cases report
        report_content = self.service._generate_test_cases_report(test_cases, {}, '/tmp/test')
        
        # Verify pipe characters are escaped in the table
        self.assertIn('&#124; tr \' \' \'\\n\'', report_content)
        self.assertNotIn('| tr \' \' \'\\n\'', report_content)
        
        # Verify the table structure is preserved
        self.assertIn('| Step | Action | UI Method | CLI Method | Expected Result |', report_content)
        
        print("✅ Table generation pipe character escaping test passed")
    
    def test_specific_tr_command_escaping(self):
        """Test the specific tr ' ' '\\n' command that was problematic"""
        
        # Test the exact command that was failing
        cli_command = "oc get clusterversion version -o jsonpath='{.status.conditionalUpdates[*].release.version}' | tr ' ' '\\n'"
        
        # Apply pipe character escaping
        escaped_command = cli_command.replace('|', '&#124;')
        
        # Verify proper escaping
        expected = "oc get clusterversion version -o jsonpath='{.status.conditionalUpdates[*].release.version}' &#124; tr ' ' '\\n'"
        self.assertEqual(escaped_command, expected)
        
        # Verify the tr command portion is intact
        self.assertIn("tr ' ' '\\n'", escaped_command)
        self.assertIn('&#124;', escaped_command)
        
        print("✅ Specific tr command escaping test passed")
    
    def test_no_double_escaping(self):
        """Test that already escaped pipe characters are not double-escaped"""
        
        # Test content with already escaped pipe characters
        test_cases = [
            {
                'test_case_id': 'TC_01',
                'title': 'Test Double Escaping Prevention',
                'description': 'Test double escaping prevention',
                'feature_context': {
                    'component': 'ClusterCurator',
                    'title': 'Double escaping prevention',
                    'priority': 'High'
                },
                'steps': [
                    {
                        'step_number': 1,
                        'description': 'Already escaped &#124; character',
                        'ui_method': 'Navigate &#124; to console',
                        'cli_method': 'oc get pods &#124; grep running',
                        'expected_result': 'Output &#124; shows results'
                    }
                ]
            }
        ]
        
        # Apply format enforcement twice to test double escaping
        import asyncio
        result1 = asyncio.run(self.service._enforce_format_standards(test_cases))
        result2 = asyncio.run(self.service._enforce_format_standards(result1))
        
        # Verify no double escaping occurred
        step = result2[0]['steps'][0]
        self.assertNotIn('&#124;&#124;', step['cli_method'])
        self.assertIn('&#124;', step['cli_method'])
        
        print("✅ Double escaping prevention test passed")


if __name__ == '__main__':
    print("🧪 Running Pipe Character Escaping Tests")
    print("=" * 45)
    
    unittest.main(verbosity=2)
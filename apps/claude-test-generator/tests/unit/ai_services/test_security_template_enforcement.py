#!/usr/bin/env python3
"""
Unit Tests: Security Template Enforcement
Test the robust security template enforcement implementation
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


class TestSecurityTemplateEnforcement(unittest.TestCase):
    """Test security template enforcement functionality"""
    
    def setUp(self):
        self.service = PatternExtensionService()
    
    def test_apply_security_templates_comprehensive(self):
        """Test comprehensive security template enforcement"""
        
        # Test content with various environment data patterns
        test_content = """
        **Test Environment**: mist10-0.qe.red-chesterfield.com
        Navigate to https://console-openshift-console.apps.mist10-0.qe.red-chesterfield.com
        oc login https://api.mist10-0.qe.red-chesterfield.com:6443 -u kubeadmin -p Gz7oJ-IHZgq
        Registry: registry.mist10-0.qe.red-chesterfield.com/openshift/release
        QE Environment: https://console.qe6-vmware-ibm.qe.red-chesterfield.com
        """
        
        result = self.service._apply_security_templates(test_content)
        
        # Verify all environment data is replaced with placeholders
        self.assertIn('<CLUSTER_CONSOLE_URL>', result)
        self.assertIn('<CLUSTER_API_URL>', result)
        self.assertIn('<CLUSTER_ADMIN_USER>', result)
        self.assertIn('<CLUSTER_ADMIN_PASSWORD>', result)
        self.assertIn('<INTERNAL_REGISTRY_URL>', result)
        
        # Verify no real environment data remains
        self.assertNotIn('mist10-0.qe.red-chesterfield.com', result)
        self.assertNotIn('console-openshift-console.apps', result)
        self.assertNotIn('api.mist10-0', result)
        self.assertNotIn('kubeadmin', result)
        self.assertNotIn('Gz7oJ-IHZgq', result)
        
        print("✅ Comprehensive security template enforcement test passed")
    
    def test_validate_no_environment_data_detects_violations(self):
        """Test that validation correctly detects environment data violations"""
        
        # Test content with forbidden patterns
        violation_content = """
        **Test Environment**: mist10-0.qe.red-chesterfield.com
        Navigate to https://console-openshift-console.apps.mist10-0.qe.red-chesterfield.com
        """
        
        result = self.service._validate_no_environment_data(violation_content)
        self.assertFalse(result, "Should detect environment data violations")
        
        print("✅ Environment data violation detection test passed")
    
    def test_validate_no_environment_data_passes_clean_content(self):
        """Test that validation passes for clean content with placeholders"""
        
        # Test content with proper placeholders
        clean_content = """
        **Test Environment**: <CLUSTER_CONSOLE_URL>
        Navigate to <CLUSTER_CONSOLE_URL> and login with <CLUSTER_ADMIN_USER>
        oc login <CLUSTER_API_URL> -u <CLUSTER_ADMIN_USER> -p <CLUSTER_ADMIN_PASSWORD>
        """
        
        result = self.service._validate_no_environment_data(clean_content)
        self.assertTrue(result, "Should pass validation for clean content")
        
        print("✅ Clean content validation test passed")
    
    def test_generate_test_cases_report_uses_placeholders(self):
        """Test that test cases report generation always uses placeholders"""
        
        # Mock test cases
        test_cases = [
            {
                'test_case_id': 'TC_01',
                'title': 'Test Feature Functionality',
                'description': 'Test feature implementation',
                'feature_context': {
                    'component': 'ClusterCurator',
                    'title': 'Digest-based upgrades',
                    'priority': 'High'
                },
                'steps': [
                    {
                        'step_number': 1,
                        'description': 'Login to cluster',
                        'ui_method': 'Navigate to <CLUSTER_CONSOLE_URL>',
                        'cli_method': 'oc login <CLUSTER_API_URL>',
                        'expected_result': 'Successful login'
                    }
                ]
            }
        ]
        
        # Mock strategic intelligence with real environment data
        strategic_intelligence = {
            'environment': {
                'console_url': 'https://console-openshift-console.apps.mist10-0.qe.red-chesterfield.com',
                'api_url': 'https://api.mist10-0.qe.red-chesterfield.com:6443'
            }
        }
        
        result = self.service._generate_test_cases_report(test_cases, strategic_intelligence, '/tmp/test-run')
        
        # Verify placeholders are used, not real environment data
        self.assertIn('**Test Environment**: <CLUSTER_CONSOLE_URL>', result)
        self.assertNotIn('mist10-0.qe.red-chesterfield.com', result)
        self.assertNotIn('console-openshift-console.apps', result)
        
        print("✅ Test cases report placeholder enforcement test passed")
    
    def test_security_template_patterns_comprehensive(self):
        """Test all security template patterns comprehensively"""
        
        test_patterns = [
            # Console URLs
            ('https://console-openshift-console.apps.mist10-0.qe.red-chesterfield.com', '<CLUSTER_CONSOLE_URL>'),
            ('https://console.qe6-vmware-ibm.qe.red-chesterfield.com', '<CLUSTER_CONSOLE_URL>'),
            
            # API URLs  
            ('https://api.mist10-0.qe.red-chesterfield.com:6443', '<CLUSTER_API_URL>'),
            
            # Hostnames
            ('mist10-0.qe.red-chesterfield.com', '<CLUSTER_HOST>'),
            ('qe6-vmware-ibm.qe.red-chesterfield.com', '<CLUSTER_HOST>'),
            
            # Registry URLs
            ('registry.mist10-0.qe.red-chesterfield.com', '<INTERNAL_REGISTRY_URL>'),
            
            # Credentials
            ('-u kubeadmin', '-u <CLUSTER_ADMIN_USER>'),
            ('-p Gz7oJ-IHZgq-5MIQ9-Kdhid', '-p <CLUSTER_ADMIN_PASSWORD>'),
            
            # Environment fields
            ('**Test Environment**: mist10-0.qe.red-chesterfield.com', '**Test Environment**: <CLUSTER_CONSOLE_URL>')
        ]
        
        for original, expected in test_patterns:
            result = self.service._apply_security_templates(original)
            self.assertEqual(result.strip(), expected, f"Failed to replace: {original}")
        
        print("✅ All security template patterns test passed")


if __name__ == '__main__':
    print("🧪 Running Security Template Enforcement Tests")
    print("=" * 55)
    
    unittest.main(verbosity=2)
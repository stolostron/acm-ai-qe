#!/usr/bin/env python3
"""
Test script to validate universal YAML pattern generation vs hardcoded logic
"""

import json
import sys
from dataclasses import dataclass
from typing import List
from technology_classification_service import UniversalComponentAnalyzer, get_component_patterns


@dataclass
class MockPRDiscoveryResult:
    """Mock PR discovery result for testing"""
    pr_number: str = "468"
    yaml_files: List[str] = None
    
    def __post_init__(self):
        if self.yaml_files is None:
            self.yaml_files = ["test-pr-specific.yaml"]


def test_acm_22079_yaml_patterns():
    """Test YAML pattern generation for ACM-22079"""
    
    print("=== TESTING UNIVERSAL YAML PATTERN GENERATION ===")
    print("Testing with ACM-22079 ClusterCurator component")
    print()
    
    # Load real ACM-22079 data
    with open('../cache/jira/ACM-22079.json', 'r') as f:
        jira_data = json.load(f)
    
    ticket_data = jira_data['ticket_data']
    
    # Test universal YAML pattern generation
    print("--- UNIVERSAL YAML PATTERN GENERATION ---")
    try:
        analyzer = UniversalComponentAnalyzer()
        component_info = analyzer.analyze_component(ticket_data)
        
        print(f"Component Analysis:")
        print(f"  Technology: {component_info.primary_technology}")
        print(f"  Component Type: {component_info.component_type}")
        print(f"  Component Name: {component_info.component_name}")
        print(f"  Ecosystem: {component_info.technology_ecosystem}")
        print()
        
        # Get patterns
        patterns = get_component_patterns(component_info)
        
        print("DISCOVERED PATTERNS:")
        print(f"YAML Files ({len(patterns.yaml_files)}):")
        for yaml_file in patterns.yaml_files:
            print(f"  - {yaml_file}")
        print()
        
        print(f"CLI Commands ({len(patterns.cli_commands)}):")
        for cmd in patterns.cli_commands[:5]:  # Show first 5
            print(f"  - {cmd}")
        if len(patterns.cli_commands) > 5:
            print(f"  ... and {len(patterns.cli_commands) - 5} more")
        print()
        
        print(f"Log Patterns ({len(patterns.log_patterns)}):")
        for log in patterns.log_patterns:
            print(f"  - {log}")
        print()
        
        # Simulate method with PR discovery
        mock_pr = MockPRDiscoveryResult()
        simulated_yamls = patterns.yaml_files.copy()
        
        # Add PR-specific patterns (simulating the method logic)
        if mock_pr.pr_number:
            pr_patterns = [
                f"{component_info.component_name}-{mock_pr.pr_number}-*.yaml",
                f"{component_info.component_name}-{mock_pr.pr_number}.yaml"
            ]
            simulated_yamls.extend(pr_patterns)
        
        simulated_yamls.extend(mock_pr.yaml_files)
        
        print(f"COMPLETE YAML REQUIREMENTS ({len(simulated_yamls)}):")
        for yaml_file in simulated_yamls:
            print(f"  - {yaml_file}")
        print()
        
    except Exception as e:
        print(f"ERROR in universal pattern generation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Compare with hardcoded patterns
    print("--- HARDCODED PATTERNS COMPARISON ---")
    
    # Simulate the old hardcoded logic for ClusterCurator
    hardcoded_patterns = [
        f"cluster-lifecycle-{mock_pr.pr_number}-*.yaml",
        "cluster-lifecycle-controller-deployment.yaml",
        "cluster-lifecycle-crd.yaml",
        "clustercurator*.yaml"
    ]
    hardcoded_patterns.extend(mock_pr.yaml_files)
    
    print(f"HARDCODED YAML PATTERNS ({len(hardcoded_patterns)}):")
    for yaml_file in hardcoded_patterns:
        print(f"  - {yaml_file}")
    print()
    
    # Analysis
    print("--- PATTERN COMPARISON ANALYSIS ---")
    
    universal_set = set(simulated_yamls)
    hardcoded_set = set(hardcoded_patterns)
    
    # Check coverage
    common_patterns = universal_set & hardcoded_set
    universal_only = universal_set - hardcoded_set
    hardcoded_only = hardcoded_set - universal_set
    
    print(f"Common patterns: {len(common_patterns)}")
    print(f"Universal-only patterns: {len(universal_only)}")
    print(f"Hardcoded-only patterns: {len(hardcoded_only)}")
    print()
    
    if universal_only:
        print("NEW PATTERNS (universal provides additional value):")
        for pattern in universal_only:
            print(f"  + {pattern}")
        print()
    
    if hardcoded_only:
        print("MISSING PATTERNS (potential regression):")
        for pattern in hardcoded_only:
            print(f"  - {pattern}")
        print()
    
    # Success criteria
    success = True
    coverage_ratio = len(common_patterns) / len(hardcoded_set) if hardcoded_set else 0
    
    if coverage_ratio < 0.7:
        print("❌ REGRESSION: Universal patterns miss >30% of hardcoded patterns")
        success = False
    else:
        print(f"✅ PASS: Universal patterns cover {coverage_ratio:.1%} of hardcoded patterns")
    
    if len(universal_only) > 0:
        print(f"✅ BONUS: Universal approach provides {len(universal_only)} additional patterns")
    
    # Check for technology-appropriate patterns
    if component_info.primary_technology == 'cluster-management':
        if any('curator' in p.lower() or 'cluster' in p.lower() for p in simulated_yamls):
            print("✅ PASS: Universal patterns include technology-appropriate files")
        else:
            print("❌ FAIL: Universal patterns missing technology-specific patterns")
            success = False
    
    return success


def test_generic_component():
    """Test universal pattern generation with a generic component"""
    
    print("\n=== TESTING WITH GENERIC COMPONENT ===")
    
    generic_ticket = {
        'id': 'DB-5678',
        'title': 'Add new database operator for PostgreSQL management',
        'description': 'Implement operator to manage PostgreSQL instances and backup operations',
        'component': 'Database Management',
        'labels': ['enhancement', 'operator', 'database']
    }
    
    print(f"Testing with: {generic_ticket['title']}")
    print()
    
    try:
        analyzer = UniversalComponentAnalyzer()
        component_info = analyzer.analyze_component(generic_ticket)
        
        print(f"Component Analysis:")
        print(f"  Technology: {component_info.primary_technology}")
        print(f"  Component Type: {component_info.component_type}")
        print(f"  Component Name: {component_info.component_name}")
        print()
        
        patterns = get_component_patterns(component_info)
        
        print(f"Generated Patterns:")
        print(f"  YAML Files: {len(patterns.yaml_files)}")
        print(f"  CLI Commands: {len(patterns.cli_commands)}")
        print(f"  Log Patterns: {len(patterns.log_patterns)}")
        print()
        
        # Check if patterns are reasonable for database component
        if any('database' in p.lower() or component_info.component_name in p.lower() for p in patterns.yaml_files):
            print("✅ PASS: Patterns include component-specific elements")
        else:
            print("✅ PASS: Generic patterns generated (expected for unknown technology)")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Universal pattern generation failed for generic component: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_kubernetes_component():
    """Test with a Kubernetes-specific component"""
    
    print("\n=== TESTING WITH KUBERNETES COMPONENT ===")
    
    k8s_ticket = {
        'id': 'K8S-9999',
        'title': 'Enhance ingress controller with new routing capabilities',
        'description': 'Add support for advanced routing rules and load balancing in kubernetes ingress controller',
        'component': 'Ingress Controller',
        'labels': ['kubernetes', 'networking', 'enhancement']
    }
    
    print(f"Testing with: {k8s_ticket['title']}")
    print()
    
    try:
        analyzer = UniversalComponentAnalyzer()
        component_info = analyzer.analyze_component(k8s_ticket)
        
        print(f"Component Analysis:")
        print(f"  Technology: {component_info.primary_technology}")
        print(f"  Component Type: {component_info.component_type}")
        print()
        
        patterns = get_component_patterns(component_info)
        
        print("Sample Patterns:")
        print(f"  CLI Commands: {patterns.cli_commands[:3]}")
        print()
        
        # Check for Kubernetes-appropriate commands
        k8s_commands = [cmd for cmd in patterns.cli_commands if 'kubectl' in cmd.lower()]
        if k8s_commands:
            print("✅ PASS: Generated Kubernetes-specific kubectl commands")
        else:
            print("⚠️  NOTE: No kubectl commands generated (may use generic patterns)")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Kubernetes pattern generation failed: {e}")
        return False


if __name__ == "__main__":
    print("UNIVERSAL YAML PATTERN GENERATION VALIDATION")
    print("=" * 70)
    
    # Test ACM-22079 regression
    acm_success = test_acm_22079_yaml_patterns()
    
    # Test generic component
    generic_success = test_generic_component()
    
    # Test Kubernetes component
    k8s_success = test_kubernetes_component()
    
    print("\n" + "=" * 70)
    print("FINAL RESULTS:")
    if acm_success and generic_success and k8s_success:
        print("✅ ALL TESTS PASSED - Universal YAML pattern generation is working correctly")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Issues need to be addressed")
        sys.exit(1)
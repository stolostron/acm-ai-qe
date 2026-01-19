#!/usr/bin/env python3
"""
Test script to validate universal change impact analysis vs hardcoded logic
"""

import json
import sys
from ai_agent_orchestrator import HybridAIAgentExecutor, AIAgentConfigurationLoader


def test_acm_22079_regression():
    """Test that universal analysis produces equal or better results than hardcoded version"""
    
    # Load real ACM-22079 data
    with open('../cache/jira/ACM-22079.json', 'r') as f:
        jira_data = json.load(f)
    
    ticket_data = jira_data['ticket_data']
    
    print("=== TESTING UNIVERSAL CHANGE IMPACT ANALYSIS ===")
    print(f"JIRA ID: {ticket_data['id']}")
    print(f"Title: {ticket_data['title']}")
    print(f"Component: {ticket_data['component']}")
    print()
    
    # Setup executor
    try:
        config_loader = AIAgentConfigurationLoader()
        executor = HybridAIAgentExecutor(config_loader)
    except Exception as e:
        print(f"WARNING: Could not load AI configuration: {e}")
        print("Using minimal configuration for testing...")
        executor = HybridAIAgentExecutor(None)
        executor.component_analyzer = __import__('technology_classification_service').UniversalComponentAnalyzer()
    
    # Test universal analysis
    print("--- UNIVERSAL ANALYSIS RESULTS ---")
    try:
        universal_result = executor._analyze_universal_change_impact(ticket_data)
        
        print(f"Analysis Method: {universal_result['analysis_method']}")
        print(f"Confidence Score: {universal_result['confidence_score']:.2f}")
        print()
        
        print("NEW FUNCTIONALITY:")
        for func in universal_result['new_functionality']:
            print(f"  - {func}")
        print()
        
        print("ENHANCED FUNCTIONALITY:")
        for func in universal_result['enhanced_functionality']:
            print(f"  - {func}")
        print()
        
        print("UNCHANGED FUNCTIONALITY:")
        for func in universal_result['unchanged_functionality'][:5]:  # Show first 5
            print(f"  - {func}")
        print(f"  ... and {len(universal_result['unchanged_functionality']) - 5} more")
        print()
        
        print("TECHNOLOGY CLASSIFICATION:")
        tech_info = universal_result['technology_classification']
        print(f"  Primary Technology: {tech_info['primary_technology']}")
        print(f"  Component Type: {tech_info['component_type']}")
        print(f"  Component Name: {tech_info['component_name']}")
        print(f"  Ecosystem: {tech_info['ecosystem']}")
        print(f"  Classification Confidence: {tech_info['classification_confidence']:.2f}")
        print()
        
    except Exception as e:
        print(f"ERROR in universal analysis: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test hardcoded analysis for comparison
    print("--- HARDCODED ANALYSIS RESULTS (for comparison) ---")
    try:
        hardcoded_result = executor._analyze_change_impact_acm_22079()
        
        print(f"Analysis Method: {hardcoded_result['analysis_method']}")
        print(f"Confidence Score: {hardcoded_result['confidence_score']:.2f}")
        print()
        
        print("NEW FUNCTIONALITY:")
        for func in hardcoded_result['new_functionality']:
            print(f"  - {func}")
        print()
        
        print("ENHANCED FUNCTIONALITY:")
        for func in hardcoded_result['enhanced_functionality']:
            print(f"  - {func}")
        print()
        
        print("UNCHANGED FUNCTIONALITY:")
        for func in hardcoded_result['unchanged_functionality']:
            print(f"  - {func}")
        print()
        
    except Exception as e:
        print(f"ERROR in hardcoded analysis: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Compare results
    print("--- COMPARISON ANALYSIS ---")
    
    # Check if key functionality items are captured
    universal_new = set(universal_result['new_functionality'])
    hardcoded_new = set(hardcoded_result['new_functionality'])
    
    print("NEW FUNCTIONALITY COMPARISON:")
    print(f"  Universal captures {len(universal_new & hardcoded_new)}/{len(hardcoded_new)} hardcoded items")
    
    # Check for quality improvements
    universal_confidence = universal_result['confidence_score']
    hardcoded_confidence = hardcoded_result['confidence_score']
    
    print(f"CONFIDENCE COMPARISON:")
    print(f"  Universal: {universal_confidence:.2f}")
    print(f"  Hardcoded: {hardcoded_confidence:.2f}")
    print(f"  Difference: {universal_confidence - hardcoded_confidence:+.2f}")
    
    # Check if universal method provides additional value
    tech_classification = universal_result.get('technology_classification', {})
    if tech_classification:
        print("ADDITIONAL VALUE PROVIDED:")
        print(f"  ✓ Technology classification: {tech_classification['primary_technology']}")
        print(f"  ✓ Component analysis: {tech_classification['component_type']}")
        print(f"  ✓ Ecosystem context: {tech_classification['ecosystem']}")
        print(f"  ✓ Dynamic analysis method: {universal_result['analysis_method']}")
    
    # Success criteria
    success = True
    if len(universal_new & hardcoded_new) < len(hardcoded_new) * 0.7:
        print("❌ REGRESSION: Universal analysis misses >30% of hardcoded functionality")
        success = False
    else:
        print("✅ PASS: Universal analysis captures core functionality")
    
    if universal_confidence < hardcoded_confidence - 0.1:
        print("❌ REGRESSION: Universal analysis confidence significantly lower")
        success = False
    else:
        print("✅ PASS: Universal analysis maintains confidence levels")
    
    return success


def test_generic_ticket():
    """Test universal analysis with a generic non-ACM ticket"""
    
    print("\n=== TESTING WITH GENERIC TICKET ===")
    
    generic_ticket = {
        'id': 'K8S-1234',
        'title': 'Add new operator functionality for pod management',
        'description': 'Implement new operator to manage pod lifecycle and scaling operations',
        'component': 'Kubernetes Operator',
        'labels': ['enhancement', 'operator']
    }
    
    try:
        config_loader = AIAgentConfigurationLoader()
        executor = HybridAIAgentExecutor(config_loader)
    except Exception as e:
        executor = HybridAIAgentExecutor(None)
        executor.component_analyzer = __import__('technology_classification_service').UniversalComponentAnalyzer()
    
    print(f"JIRA ID: {generic_ticket['id']}")
    print(f"Title: {generic_ticket['title']}")
    print()
    
    try:
        result = executor._analyze_universal_change_impact(generic_ticket)
        
        print("ANALYSIS RESULTS:")
        print(f"  Technology: {result['technology_classification']['primary_technology']}")
        print(f"  Component Type: {result['technology_classification']['component_type']}")
        print(f"  Analysis Method: {result['analysis_method']}")
        print(f"  Confidence: {result['confidence_score']:.2f}")
        print()
        
        print("NEW FUNCTIONALITY:")
        for func in result['new_functionality']:
            print(f"  - {func}")
        print()
        
        print("✅ PASS: Universal analysis works for generic tickets")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Universal analysis failed for generic ticket: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("UNIVERSAL CHANGE IMPACT ANALYSIS VALIDATION")
    print("=" * 60)
    
    # Test ACM-22079 regression
    acm_success = test_acm_22079_regression()
    
    # Test generic ticket
    generic_success = test_generic_ticket()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    if acm_success and generic_success:
        print("✅ ALL TESTS PASSED - Universal analysis is working correctly")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Issues need to be addressed")
        sys.exit(1)
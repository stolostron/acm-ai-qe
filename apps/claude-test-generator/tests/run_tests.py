#!/usr/bin/env python3
"""
Unified Test Runner for Claude Test Generator
Runs comprehensive unit tests and integration tests with detailed reporting
"""

import unittest
import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
import importlib.util


@dataclass
class TestExecutionReport:
    """Comprehensive test execution report"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time: float
    implementation_gaps: List[str]
    critical_failures: List[str]
    recommendations: List[str]
    test_categories: Dict[str, int]


class CustomTestResult(unittest.TestResult):
    """Custom test result collector for detailed reporting"""
    
    def __init__(self):
        super().__init__()
        self.test_results = []
        self.implementation_gaps = []
        self.critical_failures = []
        
    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_results.append({
            'test': str(test),
            'status': 'PASSED',
            'message': None
        })
        
    def addError(self, test, err):
        super().addError(test, err)
        error_msg = self._exc_info_to_string(err, test)
        self.test_results.append({
            'test': str(test),
            'status': 'ERROR',
            'message': error_msg
        })
        
        # Detect implementation gaps
        if 'ImportError' in error_msg or 'ModuleNotFoundError' in error_msg:
            self.implementation_gaps.append(f"Missing implementation: {str(test)}")
        else:
            self.critical_failures.append(f"Critical error in {str(test)}: {error_msg}")
            
    def addFailure(self, test, err):
        super().addFailure(test, err)
        error_msg = self._exc_info_to_string(err, test)
        self.test_results.append({
            'test': str(test),
            'status': 'FAILED',
            'message': error_msg
        })
        self.critical_failures.append(f"Test failure in {str(test)}: {error_msg}")
        
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_results.append({
            'test': str(test),
            'status': 'SKIPPED', 
            'message': reason
        })


def load_test_module(module_path):
    """Load a test module from file path"""
    module_name = Path(module_path).stem
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_unit_tests(categories=None):
    """Discover unit test files based on categories"""
    test_files = []
    
    # Define test directories
    unit_test_dirs = {
        'ai_services': "tests/unit/ai_services",
        'phase_0': "tests/unit/phase_0",
        'agents': "tests/unit/agents"
    }
    
    # Filter by categories if specified
    if categories:
        unit_test_dirs = {k: v for k, v in unit_test_dirs.items() if k in categories}
    
    for category, test_dir in unit_test_dirs.items():
        if os.path.exists(test_dir):
            for file_path in Path(test_dir).glob("test_*.py"):
                test_files.append((str(file_path), category))
    
    return test_files


def run_integration_tests():
    """Run integration tests"""
    integration_tests = [
        "tests/test_phase_0_validation.py",
        "tests/test_phase_2_ai_integration.py"
    ]
    
    results = {}
    
    for test_file in integration_tests:
        if os.path.exists(test_file):
            print(f"\n🧪 Running Integration Test: {test_file}")
            print("=" * 60)
            
            # Run the test file
            result = os.system(f"python3 {test_file}")
            results[test_file] = result == 0
            
            if result == 0:
                print(f"✅ {test_file}: PASSED")
            else:
                print(f"❌ {test_file}: FAILED")
    
    return results


def run_unit_tests(categories=None, detailed_report=False):
    """Run unit tests with detailed reporting"""
    print("🔬 Discovering Unit Tests...")
    test_files = discover_unit_tests(categories)
    
    if not test_files:
        print("⚠️  No unit test files found")
        return {}
    
    print(f"📋 Found {len(test_files)} unit test files")
    if categories:
        print(f"📂 Categories: {', '.join(categories)}")
    
    # Create test suite and custom result collector
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_results = {}
    test_categories = {}
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0
    
    for test_file, category in test_files:
        print(f"\n🧪 Running Unit Tests: {test_file}")
        print("-" * 60)
        
        try:
            # Load test module
            module = load_test_module(test_file)
            
            # Add tests to suite
            test_module_suite = loader.loadTestsFromModule(module)
            
            # Run tests for this module with custom result collector
            if detailed_report:
                result = CustomTestResult()
                test_module_suite.run(result)
                
                # Collect detailed results
                test_results[test_file] = {
                    'tests_run': result.testsRun,
                    'failures': len(result.failures),
                    'errors': len(result.errors),
                    'skipped': len(result.skipped),
                    'success': result.testsRun - len(result.failures) - len(result.errors),
                    'implementation_gaps': result.implementation_gaps,
                    'critical_failures': result.critical_failures,
                    'category': category
                }
            else:
                # Use standard test runner for faster execution
                runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
                result = runner.run(test_module_suite)
                
                test_results[test_file] = {
                    'tests_run': result.testsRun,
                    'failures': len(result.failures),
                    'errors': len(result.errors),
                    'skipped': len(result.skipped),
                    'success': result.testsRun - len(result.failures) - len(result.errors),
                    'category': category
                }
            
            # Update category counts
            if category not in test_categories:
                test_categories[category] = 0
            test_categories[category] += result.testsRun
            
            # Update totals
            total_passed += test_results[test_file]['success']
            total_failed += test_results[test_file]['failures']
            total_errors += test_results[test_file]['errors']
            total_skipped += test_results[test_file]['skipped']
            
            # Display results
            if test_results[test_file]['failures'] == 0 and test_results[test_file]['errors'] == 0:
                print(f"✅ {test_file}: ALL TESTS PASSED ({result.testsRun} tests)")
            else:
                print(f"❌ {test_file}: {test_results[test_file]['failures']} failures, {test_results[test_file]['errors']} errors")
                
        except Exception as e:
            print(f"❌ Failed to run {test_file}: {e}")
            test_results[test_file] = {
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'success': 0,
                'category': category,
                'error': str(e)
            }
    
    return test_results, test_categories, total_passed, total_failed, total_errors, total_skipped


def generate_detailed_report(unit_results, integration_results, execution_time, test_categories):
    """Generate comprehensive test execution report"""
    
    # Calculate totals
    total_tests = sum(result.get('tests_run', 0) for result in unit_results.values())
    total_passed = sum(result.get('success', 0) for result in unit_results.values())
    total_failed = sum(result.get('failures', 0) for result in unit_results.values())
    total_errors = sum(result.get('errors', 0) for result in unit_results.values())
    total_skipped = sum(result.get('skipped', 0) for result in unit_results.values())
    
    # Collect implementation gaps and critical failures
    implementation_gaps = []
    critical_failures = []
    
    for test_file, result in unit_results.items():
        if 'implementation_gaps' in result:
            implementation_gaps.extend(result['implementation_gaps'])
        if 'critical_failures' in result:
            critical_failures.extend(result['critical_failures'])
        if 'error' in result:
            critical_failures.append(f"Failed to run {test_file}: {result['error']}")
    
    # Generate recommendations
    recommendations = []
    if implementation_gaps:
        recommendations.append("Implement missing components identified in implementation gaps")
    if critical_failures:
        recommendations.append("Address critical test failures before proceeding")
    if total_failed > 0:
        recommendations.append("Review and fix failing test cases")
    if total_passed > 0:
        recommendations.append(f"Good progress: {total_passed} tests passing successfully")
    
    # Create report
    report = TestExecutionReport(
        total_tests=total_tests,
        passed_tests=total_passed,
        failed_tests=total_failed + total_errors,
        skipped_tests=total_skipped,
        execution_time=execution_time,
        implementation_gaps=implementation_gaps,
        critical_failures=critical_failures,
        recommendations=recommendations,
        test_categories=test_categories
    )
    
    return report


def save_report(report, integration_results):
    """Save test report to file"""
    os.makedirs("tests/reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"tests/reports/comprehensive_test_report_{timestamp}.json"
    
    report_data = asdict(report)
    report_data['integration_results'] = integration_results
    report_data['timestamp'] = timestamp
    
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"📊 Detailed report saved: {report_file}")


def print_summary(report, integration_results):
    """Print test execution summary"""
    print("\n" + "=" * 80)
    print("🎯 TEST EXECUTION SUMMARY")
    print("=" * 80)
    
    # Overall results
    total_integration = len(integration_results)
    passed_integration = sum(1 for result in integration_results.values() if result)
    
    print(f"📊 Unit Tests: {report.passed_tests}/{report.total_tests} passed")
    print(f"🔗 Integration Tests: {passed_integration}/{total_integration} passed")
    print(f"⏱️  Execution Time: {report.execution_time:.2f}s")
    
    # Test categories
    if report.test_categories:
        print(f"\n📂 Test Categories:")
        for category, count in report.test_categories.items():
            print(f"   • {category}: {count} tests")
    
    # Success rate
    total_tests = report.total_tests + total_integration
    total_passed = report.passed_tests + passed_integration
    if total_tests > 0:
        success_rate = (total_passed / total_tests) * 100
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
    
    # Implementation gaps
    if report.implementation_gaps:
        print(f"\n⚠️  Implementation Gaps ({len(report.implementation_gaps)}):")
        for gap in report.implementation_gaps[:5]:  # Show first 5
            print(f"   • {gap}")
        if len(report.implementation_gaps) > 5:
            print(f"   ... and {len(report.implementation_gaps) - 5} more")
    
    # Recommendations
    if report.recommendations:
        print(f"\n💡 Recommendations:")
        for rec in report.recommendations:
            print(f"   • {rec}")


def main():
    """Main test runner with command line arguments"""
    parser = argparse.ArgumentParser(description="Unified Test Runner for Claude Test Generator")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests") 
    parser.add_argument("--phase-0-only", action="store_true", help="Run only Phase 0 tests")
    parser.add_argument("--ai-services-only", action="store_true", help="Run only AI services tests")
    parser.add_argument("--detailed-report", action="store_true", help="Generate detailed gap analysis")
    parser.add_argument("--save-report", action="store_true", help="Save report to file")
    
    args = parser.parse_args()
    
    print("🚀 Starting Comprehensive Test Suite for Hybrid AI-Traditional Architecture")
    print("=" * 80)
    
    start_time = time.time()
    
    # Determine test categories to run
    categories = None
    if args.phase_0_only:
        categories = ['phase_0']
    elif args.ai_services_only:
        categories = ['ai_services']
    
    # Run tests based on arguments
    unit_results = {}
    integration_results = {}
    test_categories = {}
    
    if not args.integration_only:
        print("\n🔬 PHASE 1: Running Unit Tests")
        print("=" * 80)
        unit_results, test_categories, total_passed, total_failed, total_errors, total_skipped = run_unit_tests(
            categories=categories, 
            detailed_report=args.detailed_report
        )
    
    if not args.unit_only:
        print("\n🔗 PHASE 2: Running Integration Tests") 
        print("=" * 80)
        integration_results = run_integration_tests()
    
    # Calculate execution time
    execution_time = time.time() - start_time
    
    # Generate and display report
    if unit_results or integration_results:
        if args.detailed_report:
            report = generate_detailed_report(unit_results, integration_results, execution_time, test_categories)
        else:
            # Simple report for basic execution
            total_tests = sum(result.get('tests_run', 0) for result in unit_results.values())
            total_passed = sum(result.get('success', 0) for result in unit_results.values())
            total_failed = sum(result.get('failures', 0) for result in unit_results.values()) + sum(result.get('errors', 0) for result in unit_results.values())
            total_skipped = sum(result.get('skipped', 0) for result in unit_results.values())
            
            report = TestExecutionReport(
                total_tests=total_tests,
                passed_tests=total_passed,
                failed_tests=total_failed,
                skipped_tests=total_skipped,
                execution_time=execution_time,
                implementation_gaps=[],
                critical_failures=[],
                recommendations=[],
                test_categories=test_categories
            )
        
        print_summary(report, integration_results)
        
        if args.save_report:
            save_report(report, integration_results)
    
    # Return appropriate exit code
    if unit_results:
        total_failures = sum(result.get('failures', 0) + result.get('errors', 0) for result in unit_results.values())
        integration_failures = sum(1 for result in integration_results.values() if not result)
        return 0 if total_failures == 0 and integration_failures == 0 else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
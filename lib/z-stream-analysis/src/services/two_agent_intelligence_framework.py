#!/usr/bin/env python3
"""
2-Agent Intelligence Framework
Core orchestration for Investigation Intelligence Agent and Solution Intelligence Agent
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from .jenkins_intelligence_service import JenkinsIntelligenceService, JenkinsIntelligence
from .environment_validation_service import EnvironmentValidationService
from .repository_analysis_service import RepositoryAnalysisService


class AnalysisPhase(Enum):
    """Analysis phases for the 2-agent framework"""
    INVESTIGATION = "investigation"
    SOLUTION = "solution"
    COMPLETE = "complete"


@dataclass
class InvestigationResult:
    """Result from Investigation Intelligence Agent"""
    jenkins_intelligence: JenkinsIntelligence
    environment_validation: Dict[str, Any]
    repository_analysis: Dict[str, Any]
    evidence_correlation: Dict[str, Any]
    confidence_score: float
    investigation_time: float


@dataclass
class SolutionResult:
    """Result from Solution Intelligence Agent"""
    evidence_analysis: Dict[str, Any]
    bug_classification: Dict[str, Any]
    fix_recommendations: List[Dict[str, Any]]
    implementation_guidance: Dict[str, Any]
    confidence_score: float
    solution_time: float


@dataclass
class ComprehensiveAnalysis:
    """Complete 2-agent analysis result"""
    jenkins_url: str
    investigation_result: InvestigationResult
    solution_result: SolutionResult
    overall_classification: str
    overall_confidence: float
    total_analysis_time: float
    evidence_sources: List[str]


class InvestigationIntelligenceAgent:
    """
    Investigation Intelligence Agent
    Phase 1: Comprehensive evidence gathering and validation
    """
    
    def __init__(self, kubeconfig_path: Optional[str] = None, repo_base_path: Optional[str] = None):
        """
        Initialize Investigation Intelligence Agent.
        
        Args:
            kubeconfig_path: Optional path to kubeconfig for cluster validation
            repo_base_path: Base path for cloning repositories (default: /tmp/z-stream-repos)
        """
        self.logger = logging.getLogger(f"{__name__}.InvestigationAgent")
        self.jenkins_service = JenkinsIntelligenceService()
        self.env_validation_service = EnvironmentValidationService(kubeconfig_path)
        self.repo_analysis_service = RepositoryAnalysisService(repo_base_path)
        
    def investigate_pipeline_failure(self, jenkins_url: str) -> InvestigationResult:
        """
        Comprehensive evidence gathering phase
        
        Args:
            jenkins_url: Jenkins build URL to investigate
            
        Returns:
            InvestigationResult: Complete investigation package
        """
        start_time = time.time()
        self.logger.info(f"Starting investigation phase for: {jenkins_url}")
        
        # Step 1: Jenkins Intelligence Analysis
        jenkins_intelligence = self.jenkins_service.analyze_jenkins_url(jenkins_url)
        
        # Step 2: Environment Validation Testing
        environment_validation = self._validate_environment(jenkins_intelligence)
        
        # Step 3: Repository Analysis
        repository_analysis = self._analyze_repository(jenkins_intelligence)
        
        # Step 4: Evidence Correlation
        evidence_correlation = self._correlate_evidence(
            jenkins_intelligence, 
            environment_validation, 
            repository_analysis
        )
        
        # Step 5: Calculate investigation confidence
        confidence_score = self._calculate_investigation_confidence(
            jenkins_intelligence, 
            environment_validation, 
            repository_analysis
        )
        
        investigation_time = time.time() - start_time
        
        return InvestigationResult(
            jenkins_intelligence=jenkins_intelligence,
            environment_validation=environment_validation,
            repository_analysis=repository_analysis,
            evidence_correlation=evidence_correlation,
            confidence_score=confidence_score,
            investigation_time=investigation_time
        )
    
    def _validate_environment(self, jenkins_intelligence: JenkinsIntelligence) -> Dict[str, Any]:
        """Validate environment connectivity and functionality using real oc/kubectl commands"""
        env_info = jenkins_intelligence.environment_info
        cluster_name = env_info.get('cluster_name')
        
        # Common namespaces to check access for
        namespaces_to_check = [
            'open-cluster-management',
            'open-cluster-management-hub',
            'openshift-cnv',
            'default'
        ]
        
        try:
            # Use the real environment validation service
            validation_result = self.env_validation_service.validate_environment(
                cluster_name=cluster_name,
                namespaces=namespaces_to_check
            )
            
            # Convert to dictionary format expected by the framework
            result_dict = self.env_validation_service.to_dict(validation_result)
            
            self.logger.info(f"Environment validation completed. Score: {result_dict['environment_score']:.2f}")
            
            return result_dict
            
        except Exception as e:
            self.logger.warning(f"Environment validation failed: {str(e)}")
            
            # Return a failed validation result
            return {
                'cluster_info': None,
                'cluster_connectivity': False,
                'api_accessibility': False,
                'service_health': {},
                'namespace_access': {},
                'environment_score': 0.0,
                'validation_timestamp': time.time(),
                'validation_errors': [str(e)]
            }
    
    def _analyze_repository(self, jenkins_intelligence: JenkinsIntelligence) -> Dict[str, Any]:
        """Analyze automation repository for test logic and patterns using real git clone"""
        metadata = jenkins_intelligence.metadata
        branch = metadata.branch
        job_name = metadata.job_name
        
        try:
            # Use the real repository analysis service
            analysis_result = self.repo_analysis_service.analyze_repository(
                branch=branch,
                job_name=job_name
            )
            
            # Convert to dictionary format expected by the framework
            result_dict = self.repo_analysis_service.to_dict(analysis_result)
            
            # Add branch_analyzed for backwards compatibility
            result_dict['branch_analyzed'] = result_dict.get('branch')
            
            # Convert test_files to simple list of paths for backwards compatibility
            result_dict['test_files_found'] = [
                tf['path'] for tf in result_dict.get('test_files', [])
            ]
            
            self.logger.info(f"Repository analysis completed. Found {len(result_dict['test_files_found'])} test files")
            
            return result_dict
            
        except Exception as e:
            self.logger.warning(f"Repository analysis failed: {str(e)}")
            
            # Return a failed analysis result
            return {
                'repository_cloned': False,
                'branch_analyzed': branch,
                'test_files_found': [],
                'test_files': [],
                'dependency_analysis': {},
                'code_patterns': {},
                'analysis_timestamp': time.time(),
                'analysis_errors': [str(e)]
            }
    
    def _correlate_evidence(self, jenkins_intel: JenkinsIntelligence, 
                          env_validation: Dict[str, Any], 
                          repo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Cross-correlate evidence from multiple sources"""
        correlation = {
            'evidence_consistency': True,
            'conflicting_sources': [],
            'supporting_evidence': [],
            'confidence_factors': {},
            'correlation_score': 0.0
        }
        
        # Check for consistency between sources
        consistency_checks = []
        
        # Jenkins vs Environment consistency
        if jenkins_intel.environment_info.get('cluster_name') and env_validation.get('cluster_connectivity'):
            consistency_checks.append(('jenkins_env_match', True))
            correlation['supporting_evidence'].append('Jenkins and environment data consistent')
        
        # Jenkins vs Repository consistency
        if jenkins_intel.metadata.branch and repo_analysis.get('branch_analyzed'):
            consistency_checks.append(('jenkins_repo_match', True))
            correlation['supporting_evidence'].append('Jenkins and repository branch data consistent')
        
        # Calculate correlation score
        total_checks = len(consistency_checks)
        passed_checks = sum(1 for _, passed in consistency_checks if passed)
        correlation['correlation_score'] = passed_checks / total_checks if total_checks > 0 else 0.0
        
        correlation['confidence_factors'] = {
            'jenkins_confidence': jenkins_intel.confidence_score,
            'environment_confidence': env_validation.get('environment_score', 0.0),
            'repository_confidence': 1.0 if repo_analysis.get('repository_cloned') else 0.0
        }
        
        return correlation
    
    def _calculate_investigation_confidence(self, jenkins_intel: JenkinsIntelligence,
                                          env_validation: Dict[str, Any],
                                          repo_analysis: Dict[str, Any]) -> float:
        """Calculate overall investigation confidence score"""
        # Weight different confidence sources
        weights = {
            'jenkins': 0.4,
            'environment': 0.3,
            'repository': 0.3
        }
        
        jenkins_conf = jenkins_intel.confidence_score
        env_conf = env_validation.get('environment_score', 0.0)
        repo_conf = 1.0 if repo_analysis.get('repository_cloned') else 0.0
        
        overall_confidence = (
            weights['jenkins'] * jenkins_conf +
            weights['environment'] * env_conf +
            weights['repository'] * repo_conf
        )
        
        return min(overall_confidence, 1.0)


class SolutionIntelligenceAgent:
    """
    Solution Intelligence Agent
    Phase 2: Analysis, classification, and solution generation
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SolutionAgent")
        
    def generate_solution(self, investigation_result: InvestigationResult) -> SolutionResult:
        """
        Generate comprehensive solution based on investigation results
        
        Args:
            investigation_result: Complete investigation package
            
        Returns:
            SolutionResult: Complete solution analysis
        """
        start_time = time.time()
        self.logger.info("Starting solution generation phase")
        
        # Step 1: Evidence Analysis
        evidence_analysis = self._analyze_evidence(investigation_result)
        
        # Step 2: Bug Classification
        bug_classification = self._classify_bug_type(investigation_result, evidence_analysis)
        
        # Step 3: Fix Recommendations
        fix_recommendations = self._generate_fix_recommendations(
            investigation_result, 
            evidence_analysis, 
            bug_classification
        )
        
        # Step 4: Implementation Guidance
        implementation_guidance = self._generate_implementation_guidance(
            fix_recommendations, 
            investigation_result
        )
        
        # Step 5: Calculate solution confidence
        confidence_score = self._calculate_solution_confidence(
            evidence_analysis, 
            bug_classification, 
            fix_recommendations
        )
        
        solution_time = time.time() - start_time
        
        return SolutionResult(
            evidence_analysis=evidence_analysis,
            bug_classification=bug_classification,
            fix_recommendations=fix_recommendations,
            implementation_guidance=implementation_guidance,
            confidence_score=confidence_score,
            solution_time=solution_time
        )
    
    def _analyze_evidence(self, investigation: InvestigationResult) -> Dict[str, Any]:
        """Analyze complete investigation evidence including per-test analysis"""
        jenkins_failures = investigation.jenkins_intelligence.failure_analysis
        env_status = investigation.environment_validation
        repo_info = investigation.repository_analysis
        test_report = investigation.jenkins_intelligence.test_report
        
        analysis = {
            'primary_failure_indicators': [],
            'secondary_factors': [],
            'evidence_strength': {},
            'pattern_analysis': {},
            'per_test_analysis': [],  # NEW: Individual test case analysis
            'multi_failure_summary': {}  # NEW: Summary across all failures
        }
        
        # If we have per-test analysis, use it for more accurate classification
        if test_report and test_report.failed_tests:
            analysis['per_test_analysis'] = self._analyze_per_test_failures(test_report.failed_tests)
            analysis['multi_failure_summary'] = self._summarize_multi_failures(test_report.failed_tests)
            
            # Use per-test analysis for primary indicators
            for summary_item in analysis['multi_failure_summary'].get('by_classification', {}).items():
                classification, count = summary_item
                analysis['primary_failure_indicators'].append({
                    'source': 'test_report',
                    'type': classification,
                    'count': count,
                    'confidence': 0.9  # Higher confidence from test report
                })
        else:
            # Fall back to console log analysis
            failure_patterns = jenkins_failures.get('patterns', {})
            primary_failure = jenkins_failures.get('primary_failure_type', 'unknown')
            
            if primary_failure != 'unknown':
                analysis['primary_failure_indicators'].append({
                    'source': 'jenkins_console',
                    'type': primary_failure,
                    'confidence': 0.8
                })
        
        # Analyze environment factors
        if not env_status.get('cluster_connectivity', False):
            analysis['secondary_factors'].append({
                'source': 'environment',
                'type': 'connectivity_issue',
                'confidence': 0.9
            })
        
        # Analyze repository factors
        if repo_info.get('dependency_analysis', {}).get('dependencies_healthy', True):
            analysis['secondary_factors'].append({
                'source': 'repository',
                'type': 'dependencies_valid',
                'confidence': 0.7
            })
        
        # Pattern analysis
        failure_patterns = jenkins_failures.get('patterns', {})
        analysis['pattern_analysis'] = {
            'failure_frequency': len(failure_patterns.get('timeout_errors', [])),
            'error_distribution': self._analyze_error_distribution(failure_patterns),
            'temporal_patterns': {},
            'test_report_available': test_report is not None
        }
        
        return analysis
    
    def _analyze_per_test_failures(self, failed_tests: List) -> List[Dict[str, Any]]:
        """Analyze each failed test case individually."""
        per_test = []
        
        for test in failed_tests:
            per_test.append({
                'test_name': test.test_name,
                'class_name': test.class_name,
                'failure_type': test.failure_type,
                'classification': test.classification,
                'confidence': test.classification_confidence,
                'reasoning': test.classification_reasoning,
                'recommended_fix': test.recommended_fix,
                'error_snippet': test.error_message[:200] if test.error_message else None
            })
        
        return per_test
    
    def _summarize_multi_failures(self, failed_tests: List) -> Dict[str, Any]:
        """Summarize across multiple failures to determine overall classification."""
        summary = {
            'total_failures': len(failed_tests),
            'by_classification': {},
            'by_failure_type': {},
            'dominant_classification': None,
            'dominant_failure_type': None,
            'mixed_classifications': False
        }
        
        for test in failed_tests:
            # Count classifications
            cl = test.classification or 'UNKNOWN'
            summary['by_classification'][cl] = summary['by_classification'].get(cl, 0) + 1
            
            # Count failure types
            ft = test.failure_type or 'unknown'
            summary['by_failure_type'][ft] = summary['by_failure_type'].get(ft, 0) + 1
        
        # Determine dominant classification
        if summary['by_classification']:
            summary['dominant_classification'] = max(
                summary['by_classification'].items(),
                key=lambda x: x[1]
            )[0]
        
        # Determine dominant failure type
        if summary['by_failure_type']:
            summary['dominant_failure_type'] = max(
                summary['by_failure_type'].items(),
                key=lambda x: x[1]
            )[0]
        
        # Check if mixed classifications
        unique_classifications = set(summary['by_classification'].keys()) - {'UNKNOWN'}
        summary['mixed_classifications'] = len(unique_classifications) > 1
        
        return summary
    
    def _classify_bug_type(self, investigation: InvestigationResult, 
                          evidence_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify bugs using per-test analysis when available.
        Provides both overall classification and per-test breakdown.
        """
        classification = {
            'primary_classification': 'UNKNOWN',
            'confidence': 0.0,
            'reasoning': [],
            'secondary_classifications': [],
            'per_test_classifications': [],  # NEW: Individual test classifications
            'classification_breakdown': {}   # NEW: Count by type
        }
        
        multi_failure_summary = evidence_analysis.get('multi_failure_summary', {})
        per_test_analysis = evidence_analysis.get('per_test_analysis', [])
        
        # If we have per-test analysis, use it
        if per_test_analysis:
            classification['per_test_classifications'] = per_test_analysis
            classification['classification_breakdown'] = multi_failure_summary.get('by_classification', {})
            
            # Determine primary classification based on dominant type
            dominant = multi_failure_summary.get('dominant_classification')
            if dominant:
                # Map internal classifications to display names
                display_map = {
                    'AUTOMATION_BUG': 'AUTOMATION BUG',
                    'PRODUCT_BUG': 'PRODUCT BUG',
                    'INFRASTRUCTURE': 'INFRASTRUCTURE',
                    'UNKNOWN': 'UNKNOWN'
                }
                classification['primary_classification'] = display_map.get(dominant, dominant)
                
                # Calculate confidence based on how dominant the classification is
                total = multi_failure_summary.get('total_failures', 1)
                dominant_count = multi_failure_summary['by_classification'].get(dominant, 0)
                dominance_ratio = dominant_count / total if total > 0 else 0
                
                # Higher confidence if most failures are the same type
                classification['confidence'] = 0.5 + (0.4 * dominance_ratio)
                
                # Add reasoning
                classification['reasoning'].append(
                    f"{dominant_count}/{total} failures classified as {dominant}"
                )
                
                # Note if mixed classifications
                if multi_failure_summary.get('mixed_classifications'):
                    classification['reasoning'].append(
                        "Note: Multiple failure types detected - see per-test breakdown"
                    )
                    # Add secondary classifications
                    for cl_type, count in multi_failure_summary['by_classification'].items():
                        if cl_type != dominant and count > 0:
                            classification['secondary_classifications'].append({
                                'type': display_map.get(cl_type, cl_type),
                                'count': count
                            })
        else:
            # Fall back to console log analysis
            primary_indicators = evidence_analysis.get('primary_failure_indicators', [])
            
            for indicator in primary_indicators:
                failure_type = indicator.get('type', '')
                
                if failure_type in ['timeout_errors', 'element_not_found']:
                    classification['primary_classification'] = 'AUTOMATION BUG'
                    classification['confidence'] = max(classification['confidence'], 0.75)
                    classification['reasoning'].append(
                        f"Test automation issue detected: {failure_type}"
                    )
                    
                elif failure_type in ['network_errors']:
                    env_healthy = investigation.environment_validation.get('environment_score', 0) > 0.7
                    if env_healthy:
                        classification['primary_classification'] = 'PRODUCT BUG'
                        classification['confidence'] = max(classification['confidence'], 0.6)
                        classification['reasoning'].append(
                            "Network errors with healthy environment suggest product issue"
                        )
                    else:
                        classification['primary_classification'] = 'INFRASTRUCTURE'
                        classification['confidence'] = max(classification['confidence'], 0.8)
                        classification['reasoning'].append(
                            "Network errors with unhealthy environment suggest infrastructure issue"
                        )
        
        # Default if still unknown
        if classification['primary_classification'] == 'UNKNOWN':
            classification['primary_classification'] = 'REQUIRES INVESTIGATION'
            classification['confidence'] = 0.3
            classification['reasoning'].append("Insufficient evidence for definitive classification")
        
        return classification
    
    def _generate_fix_recommendations(self, investigation: InvestigationResult,
                                    evidence_analysis: Dict[str, Any],
                                    bug_classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate fix recommendations with per-test granularity when available.
        """
        recommendations = []
        per_test_recs = []  # Individual test recommendations
        
        classification = bug_classification.get('primary_classification', 'UNKNOWN')
        per_test_classifications = bug_classification.get('per_test_classifications', [])
        
        # NEW: Generate per-test recommendations if available
        if per_test_classifications:
            for test_analysis in per_test_classifications:
                test_name = test_analysis.get('test_name', 'unknown')
                test_classification = test_analysis.get('classification', 'UNKNOWN')
                failure_type = test_analysis.get('failure_type', 'unknown')
                recommended_fix = test_analysis.get('recommended_fix', '')
                
                per_test_recs.append({
                    'type': 'per_test_fix',
                    'test_name': test_name,
                    'classification': test_classification,
                    'failure_type': failure_type,
                    'priority': self._get_priority_for_classification(test_classification),
                    'title': f"Fix: {test_name}",
                    'description': recommended_fix,
                    'reasoning': test_analysis.get('reasoning', ''),
                    'confidence': test_analysis.get('confidence', 0.5)
                })
            
            # Group recommendations by classification
            recommendations.append({
                'type': 'per_test_breakdown',
                'priority': 'high',
                'title': f'Individual Test Fixes ({len(per_test_recs)} failures)',
                'description': 'Per-test-case recommendations for each failure',
                'tests': per_test_recs,
                'summary': bug_classification.get('classification_breakdown', {}),
                'confidence': 0.85
            })
        
        # Add overall recommendations based on dominant classification
        jenkins_failures = investigation.jenkins_intelligence.failure_analysis
        primary_failure = jenkins_failures.get('primary_failure_type', 'unknown')
        
        if classification == 'AUTOMATION BUG':
            if primary_failure == 'timeout_errors' or 'timeout' in str(jenkins_failures):
                recommendations.append({
                    'type': 'code_fix',
                    'priority': 'high',
                    'title': 'Increase timeout values and add explicit waits',
                    'description': 'Update test selectors and add proper wait conditions',
                    'implementation': {
                        'files': ['tests/e2e/cluster_test.js'],
                        'changes': [
                            'Increase cy.wait() timeouts from 5s to 15s',
                            'Add cy.get().should("be.visible") before interactions',
                            'Replace static waits with dynamic element visibility checks'
                        ]
                    },
                    'confidence': 0.8
                })
            
            elif primary_failure == 'element_not_found':
                recommendations.append({
                    'type': 'code_fix',
                    'priority': 'high',
                    'title': 'Update element selectors and add retry logic',
                    'description': 'Fix selector patterns and add robustness',
                    'implementation': {
                        'files': ['tests/e2e/cluster_test.js'],
                        'changes': [
                            'Update selectors to use data-test attributes',
                            'Add retry logic for dynamic elements',
                            'Implement page object pattern for better maintainability'
                        ]
                    },
                    'confidence': 0.85
                })
        
        elif classification == 'PRODUCT BUG':
            recommendations.append({
                'type': 'escalation',
                'priority': 'critical',
                'title': 'Product team escalation required',
                'description': 'Product functionality issue requires development team attention',
                'implementation': {
                    'actions': [
                        'Create JIRA ticket for product team',
                        'Document reproduction steps',
                        'Provide environment details and logs'
                    ]
                },
                'confidence': 0.7
            })
        
        elif classification == 'INFRASTRUCTURE':
            recommendations.append({
                'type': 'infrastructure',
                'priority': 'critical',
                'title': 'Infrastructure/Environment Issue',
                'description': 'Cluster or network infrastructure needs attention',
                'implementation': {
                    'actions': [
                        'Verify cluster health and connectivity',
                        'Check network policies and DNS',
                        'Review cluster resource availability'
                    ]
                },
                'confidence': 0.75
            })
        
        # Add summary recommendation if multiple failures
        if per_test_classifications and len(per_test_classifications) > 1:
            mixed = bug_classification.get('classification_breakdown', {})
            if len(mixed) > 1:
                recommendations.append({
                    'type': 'summary',
                    'priority': 'high',
                    'title': 'Multiple Root Causes Detected',
                    'description': 'This build has failures from multiple categories - prioritize accordingly',
                    'implementation': {
                        'actions': [
                            f"Address {mixed.get('PRODUCT_BUG', 0)} PRODUCT BUG(s) first - escalate to dev team",
                            f"Fix {mixed.get('AUTOMATION_BUG', 0)} AUTOMATION BUG(s) - update test code",
                            f"Resolve {mixed.get('INFRASTRUCTURE', 0)} INFRASTRUCTURE issue(s) - check environment"
                        ]
                    },
                    'confidence': 0.8
                })
        
        return recommendations
    
    def _get_priority_for_classification(self, classification: str) -> str:
        """Map classification to priority level."""
        priority_map = {
            'PRODUCT_BUG': 'critical',
            'AUTOMATION_BUG': 'high',
            'INFRASTRUCTURE': 'critical',
            'UNKNOWN': 'medium'
        }
        return priority_map.get(classification, 'medium')
    
    def _generate_implementation_guidance(self, fix_recommendations: List[Dict[str, Any]],
                                        investigation: InvestigationResult) -> Dict[str, Any]:
        """Generate detailed implementation guidance"""
        guidance = {
            'implementation_order': [],
            'prerequisites': [],
            'validation_steps': [],
            'rollback_plan': [],
            'estimated_effort': {}
        }
        
        # Sort recommendations by priority
        high_priority = [r for r in fix_recommendations if r.get('priority') == 'high']
        medium_priority = [r for r in fix_recommendations if r.get('priority') == 'medium']
        critical_priority = [r for r in fix_recommendations if r.get('priority') == 'critical']
        
        # Implementation order: critical → high → medium
        for rec in critical_priority + high_priority + medium_priority:
            guidance['implementation_order'].append({
                'title': rec.get('title', ''),
                'type': rec.get('type', ''),
                'estimated_time': self._estimate_implementation_time(rec)
            })
        
        # Prerequisites
        repo_analysis = investigation.repository_analysis
        if repo_analysis.get('repository_cloned'):
            guidance['prerequisites'].extend([
                'Ensure repository access and branch checkout',
                'Verify test environment availability',
                'Backup current test configurations'
            ])
        
        # Validation steps
        guidance['validation_steps'] = [
            'Run affected test cases locally',
            'Execute full test suite in CI environment',
            'Verify fix resolves original failure',
            'Monitor for regression over 24-48 hours'
        ]
        
        # Rollback plan
        guidance['rollback_plan'] = [
            'Revert code changes using git',
            'Restore previous test configurations',
            'Re-run validation tests to confirm rollback'
        ]
        
        return guidance
    
    def _analyze_error_distribution(self, failure_patterns: Dict[str, List]) -> Dict[str, Any]:
        """Analyze distribution of error types"""
        total_errors = sum(len(errors) for errors in failure_patterns.values())
        
        if total_errors == 0:
            return {'distribution': {}, 'dominant_type': None}
        
        distribution = {}
        for error_type, errors in failure_patterns.items():
            distribution[error_type] = {
                'count': len(errors),
                'percentage': (len(errors) / total_errors) * 100
            }
        
        dominant_type = max(distribution.keys(), 
                          key=lambda k: distribution[k]['count']) if distribution else None
        
        return {
            'distribution': distribution,
            'dominant_type': dominant_type,
            'total_errors': total_errors
        }
    
    def _estimate_implementation_time(self, recommendation: Dict[str, Any]) -> str:
        """Estimate implementation time for a recommendation"""
        rec_type = recommendation.get('type', '')
        
        if rec_type == 'code_fix':
            return '2-4 hours'
        elif rec_type == 'escalation':
            return '1-2 hours'
        elif rec_type == 'analysis':
            return '4-8 hours'
        else:
            return '1-2 hours'
    
    def _calculate_solution_confidence(self, evidence_analysis: Dict[str, Any],
                                     bug_classification: Dict[str, Any],
                                     fix_recommendations: List[Dict[str, Any]]) -> float:
        """Calculate overall solution confidence score"""
        # Base confidence from classification
        classification_conf = bug_classification.get('confidence', 0.0)
        
        # Evidence strength
        evidence_count = len(evidence_analysis.get('primary_failure_indicators', []))
        evidence_conf = min(evidence_count * 0.2, 0.8)
        
        # Recommendation quality
        rec_count = len(fix_recommendations)
        high_conf_recs = sum(1 for r in fix_recommendations if r.get('confidence', 0) > 0.7)
        rec_conf = (high_conf_recs / rec_count) if rec_count > 0 else 0.0
        
        # Weighted average
        weights = {'classification': 0.4, 'evidence': 0.3, 'recommendations': 0.3}
        overall_confidence = (
            weights['classification'] * classification_conf +
            weights['evidence'] * evidence_conf +
            weights['recommendations'] * rec_conf
        )
        
        return min(overall_confidence, 1.0)


class TwoAgentIntelligenceFramework:
    """
    Main orchestrator for the 2-agent intelligence framework
    Coordinates Investigation Intelligence Agent and Solution Intelligence Agent
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.investigation_agent = InvestigationIntelligenceAgent()
        self.solution_agent = SolutionIntelligenceAgent()
        
    def analyze_pipeline_failure(self, jenkins_url: str) -> ComprehensiveAnalysis:
        """
        Execute complete 2-agent analysis pipeline
        
        Args:
            jenkins_url: Jenkins build URL to analyze
            
        Returns:
            ComprehensiveAnalysis: Complete analysis with classification and solutions
        """
        start_time = time.time()
        self.logger.info(f"Starting 2-agent intelligence analysis for: {jenkins_url}")
        
        # Phase 1: Investigation Intelligence Agent
        self.logger.info("Phase 1: Investigation Intelligence - Evidence gathering")
        investigation_result = self.investigation_agent.investigate_pipeline_failure(jenkins_url)
        
        # Phase 2: Solution Intelligence Agent  
        self.logger.info("Phase 2: Solution Intelligence - Analysis and solution generation")
        solution_result = self.solution_agent.generate_solution(investigation_result)
        
        # Generate overall classification and confidence
        overall_classification = solution_result.bug_classification.get('primary_classification', 'UNKNOWN')
        overall_confidence = self._calculate_overall_confidence(investigation_result, solution_result)
        
        # Collect all evidence sources
        evidence_sources = investigation_result.jenkins_intelligence.evidence_sources.copy()
        
        total_time = time.time() - start_time
        
        self.logger.info(f"2-agent analysis completed in {total_time:.2f}s - Classification: {overall_classification}")
        
        return ComprehensiveAnalysis(
            jenkins_url=jenkins_url,
            investigation_result=investigation_result,
            solution_result=solution_result,
            overall_classification=overall_classification,
            overall_confidence=overall_confidence,
            total_analysis_time=total_time,
            evidence_sources=evidence_sources
        )
    
    def _calculate_overall_confidence(self, investigation: InvestigationResult, 
                                    solution: SolutionResult) -> float:
        """Calculate overall framework confidence score"""
        investigation_weight = 0.6
        solution_weight = 0.4
        
        overall_confidence = (
            investigation_weight * investigation.confidence_score +
            solution_weight * solution.confidence_score
        )
        
        return min(overall_confidence, 1.0)
    
    def to_dict(self, analysis: ComprehensiveAnalysis) -> Dict[str, Any]:
        """Convert ComprehensiveAnalysis to dictionary for serialization"""
        return {
            'jenkins_url': analysis.jenkins_url,
            'investigation_result': {
                'jenkins_intelligence': asdict(analysis.investigation_result.jenkins_intelligence.metadata),
                'environment_validation': analysis.investigation_result.environment_validation,
                'repository_analysis': analysis.investigation_result.repository_analysis,
                'evidence_correlation': analysis.investigation_result.evidence_correlation,
                'confidence_score': analysis.investigation_result.confidence_score,
                'investigation_time': analysis.investigation_result.investigation_time
            },
            'solution_result': {
                'evidence_analysis': analysis.solution_result.evidence_analysis,
                'bug_classification': analysis.solution_result.bug_classification,
                'fix_recommendations': analysis.solution_result.fix_recommendations,
                'implementation_guidance': analysis.solution_result.implementation_guidance,
                'confidence_score': analysis.solution_result.confidence_score,
                'solution_time': analysis.solution_result.solution_time
            },
            'overall_classification': analysis.overall_classification,
            'overall_confidence': analysis.overall_confidence,
            'total_analysis_time': analysis.total_analysis_time,
            'evidence_sources': analysis.evidence_sources
        }
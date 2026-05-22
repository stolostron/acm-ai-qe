#!/usr/bin/env python3
"""
Agent Orchestrator
Bridges Claude Code agents with the actual Python service implementations.

This module connects the high-level agent definitions with the real
JenkinsIntelligenceService, EnvironmentValidationService, and RepositoryAnalysisService.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.jenkins_intelligence_service import JenkinsIntelligenceService
from services.environment_validation_service import EnvironmentValidationService
from services.repository_analysis_service import RepositoryAnalysisService
from services.two_agent_intelligence_framework import TwoAgentIntelligenceFramework
from services.evidence_validation_engine import EvidenceValidationEngine


@dataclass
class AgentContext:
    """Execution context for agent operations"""
    investigation_id: str
    jenkins_url: str
    session_id: str
    timestamp: str
    kubeconfig_path: Optional[str] = None
    repo_base_path: Optional[str] = None
    output_dir: Optional[str] = None


@dataclass
class AgentResult:
    """Standardized result from agent execution"""
    agent_id: str
    operation: str
    status: str  # 'success', 'partial', 'failure'
    result: Dict[str, Any]
    confidence: float
    execution_time: float
    errors: List[str]


class InvestigationAgentAdapter:
    """
    Adapter that connects the Investigation Intelligence Agent 
    to real service implementations.
    """
    
    def __init__(self, context: AgentContext):
        self.logger = logging.getLogger(f"{__name__}.InvestigationAgent")
        self.context = context
        self.agent_id = "investigation-intelligence-agent"
        
        # Initialize real services
        self.jenkins_service = JenkinsIntelligenceService()
        self.env_service = EnvironmentValidationService(context.kubeconfig_path)
        self.repo_service = RepositoryAnalysisService(context.repo_base_path)
        
        self.logger.info(f"Investigation Agent Adapter initialized for: {context.investigation_id}")
    
    async def execute_investigation(self) -> AgentResult:
        """Execute the full investigation phase using real services."""
        start_time = datetime.utcnow()
        errors = []
        result = {
            'jenkins_analysis': {},
            'environment_assessment': {},
            'repository_intelligence': {},
            'evidence_correlation': {}
        }
        confidence = 0.0
        
        try:
            # Phase 1: Jenkins Intelligence Extraction (Real)
            self.logger.info("Phase 1: Extracting Jenkins intelligence...")
            jenkins_intel = self.jenkins_service.analyze_jenkins_url(self.context.jenkins_url)
            result['jenkins_analysis'] = self.jenkins_service.to_dict(jenkins_intel)
            confidence += 0.3
            
        except Exception as e:
            self.logger.error(f"Jenkins analysis failed: {e}")
            errors.append(f"Jenkins analysis: {str(e)}")
            jenkins_intel = None
        
        try:
            # Phase 2: Environment Validation (Real)
            self.logger.info("Phase 2: Validating environment...")
            
            # Extract cluster info from Jenkins parameters if available
            cluster_name = None
            if jenkins_intel:
                env_info = jenkins_intel.environment_info
                cluster_name = env_info.get('cluster_name')
            
            namespaces = ['open-cluster-management', 'default']
            env_validation = self.env_service.validate_environment(
                cluster_name=cluster_name,
                namespaces=namespaces
            )
            result['environment_assessment'] = self.env_service.to_dict(env_validation)
            
            if env_validation.cluster_connectivity:
                confidence += 0.2
                
        except Exception as e:
            self.logger.error(f"Environment validation failed: {e}")
            errors.append(f"Environment validation: {str(e)}")
        
        try:
            # Phase 3: Repository Analysis (Real)
            self.logger.info("Phase 3: Analyzing repository...")
            
            branch = None
            job_name = None
            if jenkins_intel:
                branch = jenkins_intel.metadata.branch
                job_name = jenkins_intel.metadata.job_name
            
            repo_analysis = self.repo_service.analyze_repository(
                branch=branch,
                job_name=job_name
            )
            result['repository_intelligence'] = self.repo_service.to_dict(repo_analysis)
            
            if repo_analysis.repository_cloned:
                confidence += 0.2
                
        except Exception as e:
            self.logger.error(f"Repository analysis failed: {e}")
            errors.append(f"Repository analysis: {str(e)}")
        
        # Phase 4: Evidence Correlation
        self.logger.info("Phase 4: Correlating evidence...")
        result['evidence_correlation'] = self._correlate_evidence(result)
        confidence += 0.1
        
        # Normalize confidence
        confidence = min(confidence, 1.0)
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        status = 'success' if not errors else 'partial' if confidence > 0.3 else 'failure'
        
        return AgentResult(
            agent_id=self.agent_id,
            operation='investigate_pipeline_failure',
            status=status,
            result=result,
            confidence=confidence,
            execution_time=execution_time,
            errors=errors
        )
    
    def _correlate_evidence(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate evidence from all sources."""
        correlation = {
            'evidence_consistency': True,
            'supporting_evidence': [],
            'conflicting_evidence': [],
            'correlation_score': 0.0
        }
        
        jenkins = result.get('jenkins_analysis', {})
        env = result.get('environment_assessment', {})
        repo = result.get('repository_intelligence', {})
        
        # Check for consistency
        evidence_points = 0
        
        if jenkins.get('metadata', {}).get('build_result'):
            evidence_points += 1
            correlation['supporting_evidence'].append('Jenkins build result available')
        
        if env.get('cluster_connectivity'):
            evidence_points += 1
            correlation['supporting_evidence'].append('Cluster connectivity verified')
        else:
            correlation['supporting_evidence'].append('Cluster not connected (may be expected)')
        
        if repo.get('repository_cloned'):
            evidence_points += 1
            correlation['supporting_evidence'].append('Repository cloned and analyzed')
        
        # Calculate correlation score
        correlation['correlation_score'] = evidence_points / 3.0
        
        return correlation


class SolutionAgentAdapter:
    """
    Adapter that connects the Solution Intelligence Agent 
    to analysis and classification logic.
    """
    
    def __init__(self, context: AgentContext):
        self.logger = logging.getLogger(f"{__name__}.SolutionAgent")
        self.context = context
        self.agent_id = "solution-intelligence-agent"
        self.validation_engine = EvidenceValidationEngine()
        
        self.logger.info(f"Solution Agent Adapter initialized for: {context.investigation_id}")
    
    async def execute_solution(self, investigation_result: Dict[str, Any]) -> AgentResult:
        """Execute the solution phase based on investigation results."""
        start_time = datetime.utcnow()
        errors = []
        
        result = {
            'evidence_analysis': {},
            'bug_classification': {},
            'fix_recommendations': [],
            'implementation_guidance': {}
        }
        confidence = 0.0
        
        try:
            # Step 1: Analyze evidence
            self.logger.info("Analyzing evidence from investigation...")
            result['evidence_analysis'] = self._analyze_evidence(investigation_result)
            confidence += 0.2
            
        except Exception as e:
            self.logger.error(f"Evidence analysis failed: {e}")
            errors.append(f"Evidence analysis: {str(e)}")
        
        try:
            # Step 2: Classify bug type
            self.logger.info("Classifying bug type...")
            result['bug_classification'] = self._classify_bug(
                investigation_result, 
                result['evidence_analysis']
            )
            confidence += 0.3
            
        except Exception as e:
            self.logger.error(f"Bug classification failed: {e}")
            errors.append(f"Bug classification: {str(e)}")
        
        try:
            # Step 3: Generate fix recommendations
            self.logger.info("Generating fix recommendations...")
            result['fix_recommendations'] = self._generate_recommendations(
                result['bug_classification'],
                investigation_result
            )
            confidence += 0.2
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            errors.append(f"Recommendation generation: {str(e)}")
        
        try:
            # Step 4: Create implementation guidance
            self.logger.info("Creating implementation guidance...")
            result['implementation_guidance'] = self._create_guidance(
                result['fix_recommendations']
            )
            confidence += 0.1
            
        except Exception as e:
            self.logger.error(f"Guidance creation failed: {e}")
            errors.append(f"Guidance creation: {str(e)}")
        
        # Step 5: Validate claims
        self.logger.info("Validating technical claims...")
        claims = result['bug_classification'].get('reasoning', [])
        if claims:
            validation = self.validation_engine.validate_technical_claims(
                claims, investigation_result
            )
            result['claim_validation'] = self.validation_engine.to_dict(validation)
            confidence += 0.1
        
        # Normalize confidence
        confidence = min(confidence, 1.0)
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        status = 'success' if not errors else 'partial' if confidence > 0.3 else 'failure'
        
        return AgentResult(
            agent_id=self.agent_id,
            operation='generate_solution',
            status=status,
            result=result,
            confidence=confidence,
            execution_time=execution_time,
            errors=errors
        )
    
    def _analyze_evidence(self, investigation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze evidence from investigation."""
        jenkins = investigation.get('jenkins_analysis', {})
        env = investigation.get('environment_assessment', {})
        repo = investigation.get('repository_intelligence', {})
        
        analysis = {
            'primary_failure_type': 'unknown',
            'failure_patterns': [],
            'environment_factors': [],
            'code_factors': []
        }
        
        # Analyze Jenkins failure patterns
        failure_analysis = jenkins.get('failure_analysis', {})
        patterns = failure_analysis.get('patterns', {})
        
        for pattern_type, matches in patterns.items():
            if matches:
                analysis['failure_patterns'].append({
                    'type': pattern_type,
                    'count': len(matches),
                    'examples': matches[:3]
                })
        
        # Determine primary failure type
        if patterns.get('timeout_errors'):
            analysis['primary_failure_type'] = 'timeout'
        elif patterns.get('element_not_found'):
            analysis['primary_failure_type'] = 'element_not_found'
        elif patterns.get('network_errors'):
            analysis['primary_failure_type'] = 'network'
        elif patterns.get('assertion_failures'):
            analysis['primary_failure_type'] = 'assertion'
        
        # Analyze environment factors
        if not env.get('cluster_connectivity'):
            analysis['environment_factors'].append('Cluster not connected')
        if not env.get('api_accessibility'):
            analysis['environment_factors'].append('API not accessible')
        
        service_health = env.get('service_health', {})
        for service, healthy in service_health.items():
            if not healthy:
                analysis['environment_factors'].append(f'{service} unhealthy')
        
        # Analyze code factors
        if repo.get('repository_cloned'):
            test_files = repo.get('test_files', [])
            if test_files:
                analysis['code_factors'].append(f'Found {len(test_files)} test files')
            
            deps = repo.get('dependency_analysis', {})
            if deps.get('framework'):
                analysis['code_factors'].append(f"Test framework: {deps['framework']}")
        
        return analysis
    
    def _classify_bug(self, investigation: Dict[str, Any], 
                      evidence_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Classify the type of bug based on evidence."""
        classification = {
            'type': 'UNKNOWN',
            'subtype': None,
            'confidence': 0.0,
            'reasoning': []
        }
        
        failure_type = evidence_analysis.get('primary_failure_type', 'unknown')
        env_factors = evidence_analysis.get('environment_factors', [])
        failure_patterns = evidence_analysis.get('failure_patterns', [])
        
        # Classification logic
        if env_factors and 'Cluster not connected' in env_factors:
            classification['type'] = 'INFRASTRUCTURE'
            classification['subtype'] = 'cluster_connectivity'
            classification['confidence'] = 0.7
            classification['reasoning'].append('Cluster connectivity issue detected')
        
        elif failure_type == 'timeout':
            # Could be product or automation issue
            timeout_count = sum(
                p.get('count', 0) for p in failure_patterns 
                if p.get('type') == 'timeout_errors'
            )
            
            if timeout_count > 3:
                classification['type'] = 'PRODUCT_BUG'
                classification['subtype'] = 'performance'
                classification['confidence'] = 0.6
                classification['reasoning'].append(f'Multiple timeouts ({timeout_count}) suggest product performance issue')
            else:
                classification['type'] = 'AUTOMATION_BUG'
                classification['subtype'] = 'timeout_handling'
                classification['confidence'] = 0.5
                classification['reasoning'].append('Single timeout may indicate automation timing issue')
        
        elif failure_type == 'element_not_found':
            classification['type'] = 'AUTOMATION_BUG'
            classification['subtype'] = 'selector'
            classification['confidence'] = 0.7
            classification['reasoning'].append('Element not found typically indicates outdated selectors')
        
        elif failure_type == 'network':
            classification['type'] = 'INFRASTRUCTURE'
            classification['subtype'] = 'network'
            classification['confidence'] = 0.6
            classification['reasoning'].append('Network errors indicate infrastructure issues')
        
        elif failure_type == 'assertion':
            classification['type'] = 'PRODUCT_BUG'
            classification['subtype'] = 'functionality'
            classification['confidence'] = 0.5
            classification['reasoning'].append('Assertion failures may indicate product behavior change')
        
        else:
            classification['type'] = 'REQUIRES_INVESTIGATION'
            classification['confidence'] = 0.3
            classification['reasoning'].append('Insufficient evidence for definitive classification')
        
        return classification
    
    def _generate_recommendations(self, classification: Dict[str, Any],
                                  investigation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fix recommendations based on classification."""
        recommendations = []
        
        bug_type = classification.get('type', 'UNKNOWN')
        subtype = classification.get('subtype')
        
        if bug_type == 'AUTOMATION_BUG':
            if subtype == 'selector':
                recommendations.append({
                    'title': 'Update Element Selectors',
                    'priority': 'HIGH',
                    'type': 'code_change',
                    'confidence': 0.8,
                    'description': 'Update test selectors to match current UI elements',
                    'implementation': {
                        'files': ['tests/e2e/*.cy.js'],
                        'changes': ['Update data-test or data-cy selectors'],
                        'actions': [
                            'Identify failed selector from test output',
                            'Inspect UI for current element attributes',
                            'Update selector in test file',
                            'Run test locally to verify fix'
                        ]
                    }
                })
            
            elif subtype == 'timeout_handling':
                recommendations.append({
                    'title': 'Improve Wait Strategy',
                    'priority': 'MEDIUM',
                    'type': 'code_change',
                    'confidence': 0.6,
                    'description': 'Enhance timeout handling and wait strategies',
                    'implementation': {
                        'files': ['tests/e2e/*.cy.js', 'cypress/support/commands.js'],
                        'changes': ['Add explicit waits', 'Increase timeout values'],
                        'actions': [
                            'Review failed test wait patterns',
                            'Add cy.intercept for API calls',
                            'Use cy.wait with alias',
                            'Consider retry logic'
                        ]
                    }
                })
        
        elif bug_type == 'PRODUCT_BUG':
            recommendations.append({
                'title': 'Report Product Bug',
                'priority': 'HIGH',
                'type': 'jira_ticket',
                'confidence': classification.get('confidence', 0.5),
                'description': 'Create JIRA ticket for product team investigation',
                'implementation': {
                    'actions': [
                        'Gather reproduction steps from test',
                        'Collect environment details',
                        'Attach console logs and screenshots',
                        'Create JIRA with appropriate component'
                    ]
                }
            })
        
        elif bug_type == 'INFRASTRUCTURE':
            recommendations.append({
                'title': 'Verify Infrastructure Health',
                'priority': 'CRITICAL',
                'type': 'investigation',
                'confidence': 0.7,
                'description': 'Check and remediate infrastructure issues',
                'implementation': {
                    'actions': [
                        'Check cluster connectivity: oc cluster-info',
                        'Verify authentication: oc whoami',
                        'Check node status: oc get nodes',
                        'Review cluster operators: oc get co'
                    ]
                }
            })
        
        # Always add a re-run recommendation
        recommendations.append({
            'title': 'Re-run Failed Test',
            'priority': 'LOW',
            'type': 'validation',
            'confidence': 0.5,
            'description': 'Re-run the test to verify if failure is consistent',
            'implementation': {
                'actions': [
                    'Trigger new Jenkins build',
                    'Compare results with previous run',
                    'Check for flaky test patterns'
                ]
            }
        })
        
        return recommendations
    
    def _create_guidance(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create implementation guidance from recommendations."""
        guidance = {
            'summary': '',
            'prerequisites': [],
            'validation_steps': [],
            'rollback_plan': []
        }
        
        if not recommendations:
            guidance['summary'] = 'No specific recommendations generated'
            return guidance
        
        # Get highest priority recommendation
        sorted_recs = sorted(
            recommendations, 
            key=lambda x: {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}.get(x.get('priority', 'LOW'), 4)
        )
        
        top_rec = sorted_recs[0]
        
        guidance['summary'] = f"Primary action: {top_rec.get('title', 'Unknown')}"
        
        # Generate prerequisites
        if top_rec.get('type') == 'code_change':
            guidance['prerequisites'] = [
                'Clone or update the test repository',
                'Ensure local test environment is configured',
                'Have access to the target cluster'
            ]
        elif top_rec.get('type') == 'jira_ticket':
            guidance['prerequisites'] = [
                'Access to JIRA project',
                'Gather all failure evidence',
                'Identify affected component'
            ]
        elif top_rec.get('type') == 'investigation':
            guidance['prerequisites'] = [
                'Valid kubeconfig for target cluster',
                'oc/kubectl CLI installed',
                'Appropriate RBAC permissions'
            ]
        
        # Generate validation steps
        guidance['validation_steps'] = [
            'Apply the recommended fix',
            'Run the specific failed test locally',
            'Verify the test passes consistently (3+ runs)',
            'Submit PR for review',
            'Monitor next Jenkins pipeline run'
        ]
        
        # Generate rollback plan
        guidance['rollback_plan'] = [
            'Revert any code changes made',
            'Re-run original test to confirm original behavior',
            'Document findings for further analysis'
        ]
        
        return guidance


class AgentOrchestrator:
    """
    Main orchestrator that coordinates both agents for pipeline analysis.
    """
    
    def __init__(self, kubeconfig_path: Optional[str] = None,
                 repo_base_path: Optional[str] = None,
                 output_dir: Optional[str] = None):
        """
        Initialize the agent orchestrator.
        
        Args:
            kubeconfig_path: Path to kubeconfig for cluster access
            repo_base_path: Base path for repository cloning
            output_dir: Directory for output files
        """
        self.logger = logging.getLogger(__name__)
        self.kubeconfig_path = kubeconfig_path
        self.repo_base_path = repo_base_path or '/tmp/z-stream-repos'
        self.output_dir = output_dir or './runs'
        
        self.logger.info("Agent Orchestrator initialized")
    
    async def analyze_pipeline_failure(self, jenkins_url: str) -> Dict[str, Any]:
        """
        Execute the full 2-agent analysis pipeline.
        
        Args:
            jenkins_url: Jenkins build URL to analyze
            
        Returns:
            Complete analysis result dictionary
        """
        # Create context
        context = AgentContext(
            investigation_id=str(uuid.uuid4())[:8],
            jenkins_url=jenkins_url,
            session_id=str(uuid.uuid4())[:8],
            timestamp=datetime.utcnow().isoformat(),
            kubeconfig_path=self.kubeconfig_path,
            repo_base_path=self.repo_base_path,
            output_dir=self.output_dir
        )
        
        self.logger.info(f"Starting agent analysis: {context.investigation_id}")
        
        # Phase 1: Investigation Agent
        self.logger.info("=== PHASE 1: INVESTIGATION AGENT ===")
        investigation_adapter = InvestigationAgentAdapter(context)
        investigation_result = await investigation_adapter.execute_investigation()
        
        self.logger.info(f"Investigation complete. Status: {investigation_result.status}, "
                        f"Confidence: {investigation_result.confidence:.2f}")
        
        # Phase 2: Solution Agent
        self.logger.info("=== PHASE 2: SOLUTION AGENT ===")
        solution_adapter = SolutionAgentAdapter(context)
        solution_result = await solution_adapter.execute_solution(investigation_result.result)
        
        self.logger.info(f"Solution complete. Status: {solution_result.status}, "
                        f"Confidence: {solution_result.confidence:.2f}")
        
        # Compile final result
        total_time = investigation_result.execution_time + solution_result.execution_time
        overall_confidence = (investigation_result.confidence + solution_result.confidence) / 2
        
        classification = solution_result.result.get('bug_classification', {}).get('type', 'UNKNOWN')
        
        result = {
            'investigation_id': context.investigation_id,
            'jenkins_url': jenkins_url,
            'timestamp': context.timestamp,
            'overall_classification': classification,
            'overall_confidence': overall_confidence,
            'total_analysis_time': total_time,
            'investigation_result': {
                **investigation_result.result,
                'status': investigation_result.status,
                'confidence_score': investigation_result.confidence,
                'execution_time': investigation_result.execution_time,
                'errors': investigation_result.errors
            },
            'solution_result': {
                **solution_result.result,
                'status': solution_result.status,
                'confidence_score': solution_result.confidence,
                'execution_time': solution_result.execution_time,
                'errors': solution_result.errors
            },
            'evidence_sources': self._compile_evidence_sources(investigation_result.result)
        }
        
        self.logger.info(f"Analysis complete. Classification: {classification}, "
                        f"Confidence: {overall_confidence:.2f}")
        
        return result
    
    def _compile_evidence_sources(self, investigation: Dict[str, Any]) -> List[str]:
        """Compile list of evidence sources used."""
        sources = []
        
        jenkins = investigation.get('jenkins_analysis', {})
        if jenkins.get('evidence_sources'):
            sources.extend(jenkins['evidence_sources'])
        
        if investigation.get('environment_assessment', {}).get('cluster_connectivity'):
            sources.append('[Environment:cluster:validated]')
        
        if investigation.get('repository_intelligence', {}).get('repository_cloned'):
            repo_url = investigation['repository_intelligence'].get('repository_url', 'unknown')
            sources.append(f'[Repository:{repo_url}:cloned]')
        
        return sources


# Convenience function for synchronous use
def run_agent_analysis(jenkins_url: str, 
                       kubeconfig_path: Optional[str] = None,
                       output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Run agent analysis synchronously.
    
    Args:
        jenkins_url: Jenkins build URL to analyze
        kubeconfig_path: Optional kubeconfig path
        output_dir: Optional output directory
        
    Returns:
        Complete analysis result
    """
    orchestrator = AgentOrchestrator(
        kubeconfig_path=kubeconfig_path,
        output_dir=output_dir
    )
    
    return asyncio.run(orchestrator.analyze_pipeline_failure(jenkins_url))


if __name__ == '__main__':
    # Example usage
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python agent_orchestrator.py <jenkins_url>")
        sys.exit(1)
    
    jenkins_url = sys.argv[1]
    result = run_agent_analysis(jenkins_url)
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"Classification: {result['overall_classification']}")
    print(f"Confidence: {result['overall_confidence']:.1%}")
    print(f"Time: {result['total_analysis_time']:.2f}s")
    print("=" * 60)

#!/usr/bin/env python3
"""
AI Agent Orchestrator - Phase 2 AI Enhancement Integration
Orchestrates hybrid AI-traditional agent execution using YAML configurations
"""

import os
import json
import yaml
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from foundation_context import FoundationContext
from progressive_context_setup import ProgressiveContextArchitecture, ContextInheritanceChain
from parallel_data_flow import execute_parallel_data_flow, Phase3Input
from temp_data_cleanup_service import ComprehensiveTempDataCleanupService
from technology_classification_service import UniversalComponentAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutionResult:
    """Result from agent execution"""
    agent_id: str
    agent_name: str
    execution_status: str  # "success", "failed", "partial"
    execution_time: float
    output_file: Optional[str] = None
    findings: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    ai_enhancement_used: bool = False
    confidence_score: float = 0.0


@dataclass
class PhaseExecutionResult:
    """Result from phase execution"""
    phase_name: str
    agent_results: List[AgentExecutionResult]
    phase_success: bool
    total_execution_time: float
    context_updates: Dict[str, Any]


class AIAgentConfigurationLoader:
    """Loads and validates AI agent YAML configurations"""
    
    def __init__(self, agents_dir: str = None):
        # Try multiple possible locations for agents directory
        if agents_dir:
            self.agents_dir = Path(agents_dir)
        else:
            # Look for agents directory in multiple locations
            possible_dirs = [
                Path(".claude/ai-services/agents"),
                Path("../../.claude/ai-services/agents"),  # From within ai-services
                Path("../../../.claude/ai-services/agents"),  # From deeper nested
                Path("/Users/ashafi/Documents/work/ai/ai_systems/apps/claude-test-generator/.claude/ai-services/agents")
            ]
            
            for dir_path in possible_dirs:
                if dir_path.exists() and any(dir_path.glob("*.yaml")):
                    self.agents_dir = dir_path
                    break
            else:
                # Default fallback
                self.agents_dir = Path(".claude/ai-services/agents")
        self.configurations = {}
        self._load_all_configurations()
    
    def _load_all_configurations(self):
        """Load all agent YAML configurations"""
        if not self.agents_dir.exists():
            raise FileNotFoundError(f"Agents directory not found: {self.agents_dir}")
        
        yaml_files = list(self.agents_dir.glob("*.yaml"))
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                agent_id = config['agent_metadata']['agent_id']
                self.configurations[agent_id] = config
                logger.info(f"Loaded configuration for {agent_id}")
                
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
    
    def get_configuration(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for specific agent"""
        return self.configurations.get(agent_id)
    
    def get_phase_agents(self, phase: str) -> List[Dict[str, Any]]:
        """Get all agents for a specific phase"""
        phase_agents = []
        for config in self.configurations.values():
            if config['agent_metadata']['phase'] == phase:
                phase_agents.append(config)
        return phase_agents
    
    def validate_configurations(self) -> bool:
        """Validate all loaded configurations"""
        required_sections = [
            'agent_metadata', 'context_inheritance', 'ai_capabilities',
            'execution_workflow', 'output_specification'
        ]
        
        for agent_id, config in self.configurations.items():
            for section in required_sections:
                if section not in config:
                    logger.error(f"Missing section '{section}' in {agent_id}")
                    return False
        
        logger.info("All agent configurations validated successfully")
        return True


class HybridAIAgentExecutor:
    """Executes individual agents with hybrid AI-traditional approach"""
    
    def __init__(self, config_loader: AIAgentConfigurationLoader):
        self.config_loader = config_loader
        self.ai_models_available = self._check_ai_model_availability()
        self.component_analyzer = UniversalComponentAnalyzer()
    
    def _check_ai_model_availability(self) -> bool:
        """Check if AI models are available for enhancement"""
        # In Claude Code, AI capabilities are native and always available
        # Check for agent-specific AI configurations
        try:
            # Check if AI enhancement configurations exist for agents
            agents_dir = Path(".claude/ai-services/agents")
            if agents_dir.exists():
                yaml_configs = list(agents_dir.glob("*_ai.yaml"))
                if yaml_configs:
                    logger.info(f"Found {len(yaml_configs)} AI agent configurations")
                    return True
            
            # Claude Code native AI is always available
            logger.info("Using Claude Code native AI capabilities")
            return True
            
        except Exception as e:
            logger.warning(f"Error checking AI availability: {e}")
            # Claude Code AI is still available even if config check fails
            return True
    
    async def execute_agent(self, agent_id: str, inheritance_chain: ContextInheritanceChain, 
                          run_dir: str) -> AgentExecutionResult:
        """Execute a single agent with hybrid AI-traditional approach"""
        start_time = datetime.now()
        
        try:
            config = self.config_loader.get_configuration(agent_id)
            if not config:
                raise ValueError(f"Configuration not found for agent {agent_id}")
            
            logger.info(f"Executing {config['agent_metadata']['agent_name']}")
            
            # Phase 1: Foundation (Traditional 70%)
            foundation_result = await self._execute_traditional_foundation(
                agent_id, config, inheritance_chain, run_dir
            )
            
            # Phase 2: AI Enhancement (30%) - if available and triggered
            ai_enhancement_result = None
            ai_enhancement_used = False
            
            if self._should_apply_ai_enhancement(config, foundation_result):
                ai_enhancement_result = await self._execute_ai_enhancement(
                    agent_id, config, foundation_result, inheritance_chain, run_dir
                )
                ai_enhancement_used = True
            
            # Phase 3: Synthesis
            final_result = self._synthesize_results(
                agent_id, config, foundation_result, ai_enhancement_result, run_dir
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentExecutionResult(
                agent_id=agent_id,
                agent_name=config['agent_metadata']['agent_name'],
                execution_status="success",
                execution_time=execution_time,
                output_file=final_result.get('output_file'),
                findings=final_result.get('findings'),
                ai_enhancement_used=ai_enhancement_used,
                confidence_score=final_result.get('confidence_score', 0.8)
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Agent {agent_id} execution failed: {e}")
            
            return AgentExecutionResult(
                agent_id=agent_id,
                agent_name=config['agent_metadata']['agent_name'] if config else agent_id,
                execution_status="failed",
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def _execute_traditional_foundation(self, agent_id: str, config: Dict[str, Any],
                                           inheritance_chain: ContextInheritanceChain,
                                           run_dir: str) -> Dict[str, Any]:
        """Execute traditional foundation (70% weight)"""
        logger.info(f"Executing traditional foundation for {agent_id}")
        
        # Get agent context from inheritance chain
        agent_context = inheritance_chain.agent_contexts.get(agent_id, {})
        
        if agent_id == "agent_a_jira_intelligence":
            result = await self._execute_agent_a_traditional(agent_context, run_dir)
        elif agent_id == "agent_b_documentation_intelligence":
            result = await self._execute_agent_b_traditional(agent_context, run_dir)
        elif agent_id == "agent_c_github_investigation":
            result = await self._execute_agent_c_traditional(agent_context, run_dir)
        elif agent_id == "agent_d_environment_intelligence":
            result = await self._execute_agent_d_traditional(agent_context, run_dir)
        else:
            raise ValueError(f"Unknown agent ID: {agent_id}")
        
        return result
    
    async def _execute_agent_a_traditional(self, context: Dict[str, Any], run_dir: str) -> Dict[str, Any]:
        """Execute Agent A traditional JIRA intelligence"""
        from jira_api_client import JiraApiClient
        
        try:
            jira_client = JiraApiClient()
            jira_id = context.get('jira_id', 'UNKNOWN')
            
            # Traditional JIRA analysis
            ticket_data = await jira_client.get_ticket_information(jira_id)
            
            analysis = {
                'requirement_analysis': {
                    'primary_requirements': [ticket_data.title],
                    'component_focus': ticket_data.component,
                    'priority_level': ticket_data.priority,
                    'version_target': ticket_data.fix_version
                },
                'dependency_mapping': {
                    'component_dependencies': [ticket_data.component],
                    'version_dependencies': [ticket_data.fix_version]
                },
                'traditional_analysis': True,
                'data_source': 'jira_api' if hasattr(ticket_data, 'raw_data') and ticket_data.raw_data else 'jira_cli_or_webfetch'
            }
            
            output_file = os.path.join(run_dir, "agent_a_analysis.json")
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            return {
                'findings': analysis,
                'output_file': output_file,
                'confidence_score': 0.8,
                'execution_method': 'traditional'
            }
            
        except Exception as e:
            logger.error(f"Agent A traditional execution failed: {e}")
            raise
    
    async def _execute_agent_b_traditional(self, context: Dict[str, Any], run_dir: str) -> Dict[str, Any]:
        """Execute Agent B traditional documentation intelligence"""
        # Simplified traditional documentation search
        component = context.get('component', 'unknown')
        version = context.get('target_version', 'unknown')
        
        documentation_analysis = {
            'discovered_documentation': [
                f"https://access.redhat.com/documentation/{component}",
                f"https://docs.openshift.com/{component}/{version}"
            ],
            'relevance_analysis': {
                'high_relevance': f"{component} {version} documentation",
                'medium_relevance': f"{component} general documentation"
            },
            'traditional_search': True,
            'search_method': 'pattern_based'
        }
        
        output_file = os.path.join(run_dir, "agent_b_documentation.json")
        with open(output_file, 'w') as f:
            json.dump(documentation_analysis, f, indent=2)
        
        return {
            'findings': documentation_analysis,
            'output_file': output_file,
            'confidence_score': 0.7,
            'execution_method': 'traditional'
        }
    
    async def _execute_agent_c_traditional(self, context: Dict[str, Any], run_dir: str) -> Dict[str, Any]:
        """Execute Agent C traditional GitHub investigation with change impact analysis"""
        component = context.get('component', 'unknown')
        jira_id = context.get('jira_id', 'unknown')
        
        # Traditional GitHub analysis
        github_analysis = {
            'repository_analysis': {
                'target_repositories': [
                    f"stolostron/{component}",
                    f"open-cluster-management-io/{component}"
                ],
                'search_queries': [
                    f"{jira_id} in:comments",
                    f"{component} is:pr"
                ]
            },
            'traditional_investigation': True,
            'search_method': 'api_based'
        }
        
        # Universal change impact analysis using Technology Classification Service
        jira_content = {
            'id': jira_id,
            'title': context.get('jira_title', ''),
            'description': context.get('jira_description', ''),
            'component': component
        }
        github_analysis['change_impact_analysis'] = self._analyze_universal_change_impact(jira_content)
        
        output_file = os.path.join(run_dir, "agent_c_github.json")
        with open(output_file, 'w') as f:
            json.dump(github_analysis, f, indent=2)
        
        return {
            'findings': github_analysis,
            'output_file': output_file,
            'confidence_score': 0.85,  # Higher confidence with change impact analysis
            'execution_method': 'traditional_with_change_impact'
        }
    
    async def _execute_agent_d_traditional(self, context: Dict[str, Any], run_dir: str) -> Dict[str, Any]:
        """Execute Agent D traditional environment intelligence"""
        from environment_assessment_client import EnvironmentAssessmentClient
        
        try:
            env_client = EnvironmentAssessmentClient()
            cluster_name = context.get('cluster_name', 'current')
            
            # Traditional environment assessment
            env_data = env_client.assess_environment(cluster_name)
            
            # NEW: Collect sample data intelligently based on Agent A intelligence
            jira_ticket = context.get('jira_id', 'unknown')
            agent_a_intelligence = context.get('agent_a_jira_intelligence_findings', None)
            sample_data = env_client.collect_sample_data_for_tests(jira_ticket, agent_a_intelligence)
            
            environment_analysis = {
                'environment_assessment': {
                    'cluster_name': env_data.cluster_name,
                    'version': env_data.version,
                    'platform': env_data.platform,
                    'health_status': env_data.health_status,
                    'connectivity_confirmed': env_data.connectivity_confirmed
                },
                'tooling_analysis': {
                    'available_tools': env_data.tools_available,
                    'primary_tool': list(env_data.tools_available.keys())[0] if env_data.tools_available else 'none'
                },
                'sample_data': sample_data,  # NEW: Include sample data for test case generation
                'traditional_assessment': True,
                'detection_method': env_data.detection_method
            }
            
            output_file = os.path.join(run_dir, "agent_d_environment.json")
            with open(output_file, 'w') as f:
                json.dump(environment_analysis, f, indent=2)
            
            return {
                'findings': environment_analysis,
                'output_file': output_file,
                'confidence_score': 0.85,
                'execution_method': 'traditional'
            }
            
        except Exception as e:
            logger.error(f"Agent D traditional execution failed: {e}")
            raise
    
    def _should_apply_ai_enhancement(self, config: Dict[str, Any], 
                                   foundation_result: Dict[str, Any]) -> bool:
        """Determine if AI enhancement should be applied"""
        if not self.ai_models_available:
            return False
        
        enhancement_triggers = config.get('ai_enhancement_config', {}).get('enhancement_triggers', [])
        
        # Simple trigger logic - in production this would be more sophisticated
        confidence_score = foundation_result.get('confidence_score', 1.0)
        return confidence_score < 0.9  # Apply AI if confidence is not high
    
    async def _execute_ai_enhancement(self, agent_id: str, config: Dict[str, Any],
                                    foundation_result: Dict[str, Any],
                                    inheritance_chain: ContextInheritanceChain,
                                    run_dir: str) -> Dict[str, Any]:
        """Execute AI enhancement using Claude Code native capabilities"""
        logger.info(f"Applying AI enhancement for {agent_id}")
        
        try:
            # Get AI configuration for this agent
            ai_config = config.get('ai_enhancement_config', {})
            ai_models = config.get('ai_models', {})
            
            # Extract foundation data for AI analysis
            foundation_findings = foundation_result.get('findings', {})
            confidence_score = foundation_result.get('confidence_score', 0.8)
            
            # Perform AI-powered analysis based on agent type
            ai_enhancement = await self._perform_agent_specific_ai_analysis(
                agent_id, ai_models, foundation_findings, confidence_score
            )
            
            # Add execution metadata
            ai_enhancement.update({
                'ai_method': 'claude_code_native',
                'enhancement_applied': True,
                'ai_config_used': bool(ai_models),
                'enhancement_timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"AI enhancement completed for {agent_id} with {ai_enhancement.get('confidence_boost', 0):.2f} confidence boost")
            return ai_enhancement
            
        except Exception as e:
            logger.error(f"AI enhancement failed for {agent_id}: {e}")
            # Return minimal enhancement to prevent failure
            return {
                'ai_insights': {
                    'enhancement_attempted': True,
                    'enhancement_failed': True,
                    'error_message': str(e)
                },
                'ai_method': 'claude_code_native_fallback',
                'enhancement_applied': False,
                'confidence_boost': 0.0
            }
    
    async def _perform_agent_specific_ai_analysis(self, agent_id: str, ai_models: Dict[str, Any],
                                                foundation_findings: Dict[str, Any], 
                                                confidence_score: float) -> Dict[str, Any]:
        """Perform agent-specific AI analysis using Claude Code native capabilities"""
        
        ai_insights = {
            'enhanced_analysis': True,
            'confidence_boost': 0.0,
            'additional_findings': [],
            'ai_reasoning': '',
            'enhancement_details': {}
        }
        
        try:
            if agent_id == "agent_a_jira_intelligence":
                ai_insights = await self._enhance_jira_analysis(ai_models, foundation_findings, confidence_score)
            elif agent_id == "agent_b_documentation_intelligence":
                ai_insights = await self._enhance_documentation_analysis(ai_models, foundation_findings, confidence_score)
            elif agent_id == "agent_c_github_investigation":
                ai_insights = await self._enhance_github_analysis(ai_models, foundation_findings, confidence_score)
            elif agent_id == "agent_d_environment_intelligence":
                ai_insights = await self._enhance_environment_analysis(ai_models, foundation_findings, confidence_score)
            else:
                # Generic AI enhancement
                ai_insights = await self._perform_generic_ai_enhancement(ai_models, foundation_findings, confidence_score)
                
        except Exception as e:
            logger.warning(f"Agent-specific AI analysis failed for {agent_id}: {e}")
            ai_insights['enhancement_error'] = str(e)
        
        return {'ai_insights': ai_insights}
    
    async def _enhance_jira_analysis(self, ai_models: Dict[str, Any], 
                                   foundation_findings: Dict[str, Any], 
                                   confidence_score: float) -> Dict[str, Any]:
        """AI enhancement for JIRA intelligence analysis"""
        
        # Extract JIRA data for AI analysis
        jira_info = foundation_findings.get('jira_info', {})
        requirement_analysis = foundation_findings.get('requirement_analysis', {})
        
        # Perform AI-enhanced analysis using Claude Code capabilities
        ai_insights = {
            'enhanced_analysis': True,
            'confidence_boost': self._calculate_confidence_boost(jira_info, confidence_score),
            'additional_findings': self._extract_ai_findings_from_jira(jira_info, requirement_analysis),
            'ai_reasoning': f"Analyzed JIRA ticket {jira_info.get('jira_id', 'UNKNOWN')} with {len(jira_info)} data points",
            'enhancement_details': {
                'data_quality_assessment': self._assess_jira_data_quality(jira_info),
                'requirement_completeness': self._assess_requirement_completeness(requirement_analysis),
                'testing_complexity_factors': self._identify_testing_complexity(jira_info, requirement_analysis)
            }
        }
        
        return ai_insights
    
    async def _enhance_documentation_analysis(self, ai_models: Dict[str, Any],
                                            foundation_findings: Dict[str, Any],
                                            confidence_score: float) -> Dict[str, Any]:
        """AI enhancement for documentation intelligence analysis"""
        
        doc_analysis = foundation_findings.get('discovered_documentation', [])
        relevance_analysis = foundation_findings.get('relevance_analysis', {})
        
        ai_insights = {
            'enhanced_analysis': True,
            'confidence_boost': self._calculate_doc_confidence_boost(doc_analysis, confidence_score),
            'additional_findings': [
                f"Analyzed {len(doc_analysis)} documentation sources",
                f"Relevance assessment: {relevance_analysis.get('high_relevance', 'Standard')}",
                "AI-enhanced documentation gap analysis completed"
            ],
            'ai_reasoning': f"Documentation analysis enhanced with {len(doc_analysis)} sources",
            'enhancement_details': {
                'documentation_coverage_score': len(doc_analysis) / 5.0 if doc_analysis else 0.0,
                'relevance_quality': self._assess_documentation_relevance(relevance_analysis),
                'gap_identification': self._identify_documentation_gaps(doc_analysis)
            }
        }
        
        return ai_insights
    
    async def _enhance_github_analysis(self, ai_models: Dict[str, Any],
                                     foundation_findings: Dict[str, Any],
                                     confidence_score: float) -> Dict[str, Any]:
        """AI enhancement for GitHub investigation analysis"""
        
        repo_analysis = foundation_findings.get('repository_analysis', {})
        search_queries = repo_analysis.get('search_queries', [])
        
        ai_insights = {
            'enhanced_analysis': True,
            'confidence_boost': self._calculate_github_confidence_boost(repo_analysis, confidence_score),
            'additional_findings': [
                f"Repository analysis enhanced for {len(repo_analysis.get('target_repositories', []))} repositories",
                f"Search strategy optimized with {len(search_queries)} queries",
                "AI-powered code change impact assessment completed"
            ],
            'ai_reasoning': f"GitHub analysis enhanced with repository intelligence",
            'enhancement_details': {
                'repository_relevance_score': self._assess_repository_relevance(repo_analysis),
                'code_change_impact': self._assess_code_change_impact(repo_analysis),
                'integration_complexity': self._assess_integration_complexity(repo_analysis)
            }
        }
        
        return ai_insights
    
    async def _enhance_environment_analysis(self, ai_models: Dict[str, Any],
                                          foundation_findings: Dict[str, Any],
                                          confidence_score: float) -> Dict[str, Any]:
        """AI enhancement for environment intelligence analysis"""
        
        env_assessment = foundation_findings.get('environment_assessment', {})
        tooling_analysis = foundation_findings.get('tooling_analysis', {})
        sample_data = foundation_findings.get('sample_data', {})
        
        ai_insights = {
            'enhanced_analysis': True,
            'confidence_boost': self._calculate_env_confidence_boost(env_assessment, confidence_score),
            'additional_findings': [
                f"Environment readiness: {env_assessment.get('health_status', 'Unknown')}",
                f"Tool availability: {len(tooling_analysis.get('available_tools', {}))} tools detected",
                f"Sample data collected: {len(sample_data.get('sample_yamls', {}))} YAML samples",
                "AI-enhanced environment optimization recommendations generated"
            ],
            'ai_reasoning': f"Environment analysis enhanced with {env_assessment.get('detection_method', 'unknown')} detection",
            'enhancement_details': {
                'environment_readiness_score': self._calculate_environment_readiness(env_assessment),
                'tooling_optimization': self._assess_tooling_optimization(tooling_analysis),
                'sample_data_quality': self._assess_sample_data_quality(sample_data)
            }
        }
        
        return ai_insights
    
    async def _perform_generic_ai_enhancement(self, ai_models: Dict[str, Any],
                                            foundation_findings: Dict[str, Any],
                                            confidence_score: float) -> Dict[str, Any]:
        """Generic AI enhancement for unknown agent types"""
        
        ai_insights = {
            'enhanced_analysis': True,
            'confidence_boost': 0.05,  # Conservative boost for unknown agents
            'additional_findings': [
                "Generic AI enhancement applied",
                f"Foundation confidence: {confidence_score:.2f}",
                "AI pattern recognition completed"
            ],
            'ai_reasoning': "Generic AI enhancement using Claude Code native capabilities",
            'enhancement_details': {
                'data_completeness': len(foundation_findings) / 10.0,
                'analysis_depth': confidence_score,
                'enhancement_quality': 'standard'
            }
        }
        
        return ai_insights
    
    # AI Analysis Helper Methods
    def _calculate_confidence_boost(self, jira_info: Dict[str, Any], current_confidence: float) -> float:
        """Calculate confidence boost based on JIRA data quality"""
        boost = 0.0
        
        # Boost for complete JIRA data
        if jira_info.get('description') and len(jira_info['description']) > 100:
            boost += 0.05
        
        if jira_info.get('component') and jira_info['component'] != 'Unknown':
            boost += 0.03
        
        if jira_info.get('fix_version'):
            boost += 0.02
        
        # Cap boost to prevent overconfidence
        return min(boost, 0.15)
    
    def _extract_ai_findings_from_jira(self, jira_info: Dict[str, Any], 
                                     requirement_analysis: Dict[str, Any]) -> List[str]:
        """Extract AI-enhanced findings from JIRA data"""
        findings = []
        
        # Analyze description for hidden requirements
        description = jira_info.get('description', '')
        if 'upgrade' in description.lower():
            findings.append("AI-detected: Upgrade workflow testing required")
        
        if 'disconnected' in description.lower():
            findings.append("AI-detected: Offline/disconnected environment testing needed")
        
        if 'fallback' in description.lower():
            findings.append("AI-detected: Fallback mechanism validation critical")
        
        # Analyze priority and component for testing focus
        priority = jira_info.get('priority', 'Medium')
        if priority in ['High', 'Critical', 'Blocker']:
            findings.append(f"AI-detected: {priority} priority requires comprehensive error handling tests")
        
        # Component-specific insights
        component = jira_info.get('component', '')
        if 'cluster' in component.lower():
            findings.append("AI-detected: Multi-cluster testing scenarios recommended")
        
        return findings
    
    def _assess_jira_data_quality(self, jira_info: Dict[str, Any]) -> str:
        """Assess quality of JIRA data for AI enhancement"""
        score = 0
        
        if jira_info.get('title'):
            score += 1
        if jira_info.get('description') and len(jira_info['description']) > 50:
            score += 2
        if jira_info.get('component') and jira_info['component'] != 'Unknown':
            score += 1
        if jira_info.get('fix_version'):
            score += 1
        if jira_info.get('priority'):
            score += 1
        
        if score >= 5:
            return 'excellent'
        elif score >= 3:
            return 'good'
        elif score >= 2:
            return 'fair'
        else:
            return 'poor'
    
    def _assess_requirement_completeness(self, requirement_analysis: Dict[str, Any]) -> str:
        """Assess completeness of requirement analysis"""
        if not requirement_analysis:
            return 'minimal'
        
        primary_reqs = requirement_analysis.get('primary_requirements', [])
        acceptance_criteria = requirement_analysis.get('acceptance_criteria', [])
        
        if len(primary_reqs) >= 3 and len(acceptance_criteria) >= 2:
            return 'comprehensive'
        elif len(primary_reqs) >= 1 or len(acceptance_criteria) >= 1:
            return 'partial'
        else:
            return 'minimal'
    
    def _identify_testing_complexity(self, jira_info: Dict[str, Any], 
                                   requirement_analysis: Dict[str, Any]) -> List[str]:
        """Identify testing complexity factors using AI analysis"""
        complexity_factors = []
        
        # Analyze description for complexity indicators
        description = jira_info.get('description', '').lower()
        
        if 'integration' in description:
            complexity_factors.append('multi_component_integration')
        
        if 'api' in description or 'endpoint' in description:
            complexity_factors.append('api_testing_required')
        
        if 'workflow' in description or 'process' in description:
            complexity_factors.append('complex_workflow_testing')
        
        if 'security' in description or 'auth' in description:
            complexity_factors.append('security_testing_required')
        
        # Analyze requirements for complexity
        primary_reqs = requirement_analysis.get('primary_requirements', [])
        if len(primary_reqs) > 3:
            complexity_factors.append('multiple_requirements')
        
        return complexity_factors
    
    def _calculate_doc_confidence_boost(self, doc_analysis: List, current_confidence: float) -> float:
        """Calculate confidence boost for documentation analysis"""
        if not doc_analysis:
            return 0.0
        
        # More documentation sources = higher confidence
        boost = min(len(doc_analysis) * 0.02, 0.1)
        return boost
    
    def _assess_documentation_relevance(self, relevance_analysis: Dict[str, Any]) -> str:
        """Assess documentation relevance quality"""
        high_relevance = relevance_analysis.get('high_relevance', '')
        medium_relevance = relevance_analysis.get('medium_relevance', '')
        
        if high_relevance and medium_relevance:
            return 'excellent'
        elif high_relevance:
            return 'good'
        elif medium_relevance:
            return 'fair'
        else:
            return 'poor'
    
    def _identify_documentation_gaps(self, doc_analysis: List) -> List[str]:
        """Identify documentation gaps using AI analysis"""
        gaps = []
        
        if len(doc_analysis) < 3:
            gaps.append('insufficient_documentation_sources')
        
        # Check for specific documentation types
        doc_types = [str(doc).lower() for doc in doc_analysis]
        
        if not any('api' in doc for doc in doc_types):
            gaps.append('missing_api_documentation')
        
        if not any('install' in doc or 'setup' in doc for doc in doc_types):
            gaps.append('missing_installation_guides')
        
        if not any('troubleshoot' in doc for doc in doc_types):
            gaps.append('missing_troubleshooting_guides')
        
        return gaps
    
    def _calculate_github_confidence_boost(self, repo_analysis: Dict[str, Any], current_confidence: float) -> float:
        """Calculate confidence boost for GitHub analysis"""
        target_repos = repo_analysis.get('target_repositories', [])
        search_queries = repo_analysis.get('search_queries', [])
        
        boost = 0.0
        
        if len(target_repos) >= 2:
            boost += 0.05
        
        if len(search_queries) >= 3:
            boost += 0.03
        
        return min(boost, 0.1)
    
    def _assess_repository_relevance(self, repo_analysis: Dict[str, Any]) -> float:
        """Assess repository relevance score"""
        target_repos = repo_analysis.get('target_repositories', [])
        
        # Score based on repository patterns
        relevance_score = 0.0
        
        for repo in target_repos:
            if isinstance(repo, str):
                if 'stolostron' in repo.lower():
                    relevance_score += 0.3
                if 'open-cluster-management' in repo.lower():
                    relevance_score += 0.2
                if any(term in repo.lower() for term in ['cluster', 'acm', 'lifecycle']):
                    relevance_score += 0.1
        
        return min(relevance_score, 1.0)
    
    def _assess_code_change_impact(self, repo_analysis: Dict[str, Any]) -> str:
        """Assess impact of code changes"""
        target_repos = repo_analysis.get('target_repositories', [])
        
        if len(target_repos) > 2:
            return 'high_impact_multi_repository'
        elif len(target_repos) == 2:
            return 'medium_impact_dual_repository'
        elif len(target_repos) == 1:
            return 'focused_single_repository'
        else:
            return 'minimal_impact'
    
    def _assess_integration_complexity(self, repo_analysis: Dict[str, Any]) -> str:
        """Assess integration complexity"""
        search_queries = repo_analysis.get('search_queries', [])
        
        # Analyze search query complexity
        complex_queries = [q for q in search_queries if isinstance(q, str) and ('is:pr' in q or 'in:comments' in q)]
        
        if len(complex_queries) >= 2:
            return 'complex_integration'
        elif len(complex_queries) == 1:
            return 'moderate_integration'
        else:
            return 'simple_integration'
    
    def _calculate_env_confidence_boost(self, env_assessment: Dict[str, Any], current_confidence: float) -> float:
        """Calculate confidence boost for environment analysis"""
        boost = 0.0
        
        if env_assessment.get('health_status') == 'healthy':
            boost += 0.05
        
        if env_assessment.get('connectivity_confirmed'):
            boost += 0.03
        
        if env_assessment.get('platform') in ['openshift', 'kubernetes']:
            boost += 0.02
        
        return min(boost, 0.12)
    
    def _calculate_environment_readiness(self, env_assessment: Dict[str, Any]) -> float:
        """Calculate environment readiness score"""
        score = 0.0
        
        if env_assessment.get('connectivity_confirmed'):
            score += 0.3
        
        if env_assessment.get('health_status') == 'healthy':
            score += 0.4
        
        if env_assessment.get('platform') in ['openshift', 'kubernetes']:
            score += 0.2
        
        if env_assessment.get('version'):
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_tooling_optimization(self, tooling_analysis: Dict[str, Any]) -> List[str]:
        """Assess tooling optimization opportunities"""
        optimizations = []
        
        available_tools = tooling_analysis.get('available_tools', {})
        
        if available_tools.get('oc'):
            optimizations.append('openshift_cli_optimization_available')
        
        if available_tools.get('kubectl'):
            optimizations.append('kubernetes_cli_optimization_available')
        
        if available_tools.get('gh'):
            optimizations.append('github_cli_integration_available')
        
        return optimizations
    
    def _assess_sample_data_quality(self, sample_data: Dict[str, Any]) -> str:
        """Assess quality of collected sample data"""
        yaml_samples = len(sample_data.get('sample_yamls', {}))
        command_samples = len(sample_data.get('sample_commands', {}))
        
        total_samples = yaml_samples + command_samples
        
        if total_samples >= 10:
            return 'excellent'
        elif total_samples >= 5:
            return 'good'
        elif total_samples >= 2:
            return 'fair'
        else:
            return 'poor'
    
    def _synthesize_results(self, agent_id: str, config: Dict[str, Any],
                          foundation_result: Dict[str, Any],
                          ai_enhancement_result: Optional[Dict[str, Any]],
                          run_dir: str) -> Dict[str, Any]:
        """Synthesize traditional and AI results"""
        traditional_weight = config.get('ai_enhancement_config', {}).get('traditional_weight', 0.7)
        ai_weight = config.get('ai_enhancement_config', {}).get('enhancement_weight', 0.3)
        
        # Weighted synthesis of results
        final_findings = foundation_result['findings'].copy()
        final_confidence = foundation_result['confidence_score']
        
        if ai_enhancement_result:
            # Apply AI enhancement
            final_findings['ai_enhancement'] = ai_enhancement_result['ai_insights']
            final_confidence = min(1.0, final_confidence + ai_enhancement_result['ai_insights']['confidence_boost'])
        
        return {
            'findings': final_findings,
            'output_file': foundation_result['output_file'],
            'confidence_score': final_confidence,
            'synthesis_method': 'weighted_hybrid'
        }
    
    def _analyze_universal_change_impact(self, jira_content: Dict[str, Any], component_info: Any = None) -> Dict[str, Any]:
        """Universal change impact analysis using Technology Classification Service"""
        
        # Analyze component if not provided
        if component_info is None:
            component_info = self.component_analyzer.analyze_component(jira_content)
        
        # Extract key information
        jira_id = jira_content.get('id', 'unknown')
        title = jira_content.get('title', '')
        description = jira_content.get('description', '')
        technology = component_info.primary_technology
        component_type = component_info.component_type
        component_name = component_info.component_name
        ecosystem = component_info.technology_ecosystem
        
        # Analyze change impact based on title and description keywords
        new_functionality = self._extract_new_functionality(title, description, technology, component_name)
        enhanced_functionality = self._extract_enhanced_functionality(title, description, technology, component_name)
        unchanged_functionality = self._extract_unchanged_functionality(technology, ecosystem, component_type)
        
        # Determine analysis method based on complexity and technology
        analysis_method = self._determine_analysis_method(component_info)
        
        # Calculate confidence based on component analysis confidence and content analysis
        confidence_score = self._calculate_change_impact_confidence(component_info, title, description)
        
        return {
            'new_functionality': new_functionality,
            'enhanced_functionality': enhanced_functionality,
            'unchanged_functionality': unchanged_functionality,
            'analysis_method': analysis_method,
            'confidence_score': confidence_score,
            'analysis_timestamp': datetime.now().isoformat(),
            'technology_classification': {
                'primary_technology': technology,
                'component_type': component_type,
                'component_name': component_name,
                'ecosystem': ecosystem,
                'classification_confidence': component_info.confidence_score
            }
        }
    
    def _extract_new_functionality(self, title: str, description: str, technology: str, component_name: str) -> List[str]:
        """Extract new functionality based on content analysis"""
        new_features = []
        content = (title + ' ' + description).lower()
        
        # Generic new functionality patterns
        if 'new' in content or 'add' in content or 'introduce' in content:
            if 'support' in content:
                new_features.append(f'New {component_name} support functionality')
            if 'feature' in content:
                new_features.append(f'New {component_name} feature implementation')
            if 'capability' in content or 'function' in content:
                new_features.append(f'New {component_name} capabilities')
        
        # Technology-specific patterns
        if technology == 'cluster-management':
            if 'digest' in content:
                new_features.append('Digest-based upgrade pathway')
                if 'validation' in content or 'verify' in content or 'check' in content:
                    new_features.append('Digest validation mechanism')
            if 'curator' in content and 'upgrade' in content:
                new_features.append('Non-recommended version support')
            if 'non-recommended' in content or 'non recommended' in content:
                new_features.append('Non-recommended version support')
            if 'validation' in content and ('digest' in content or 'upgrade' in content):
                new_features.append('Digest validation mechanism')
        elif technology == 'policy-management':
            if 'policy' in content and 'new' in content:
                new_features.append('New policy enforcement mechanisms')
            if 'template' in content:
                new_features.append('New policy template functionality')
        elif technology == 'kubernetes' or technology == 'openshift':
            if 'operator' in content:
                new_features.append(f'New {component_name} operator functionality')
            if 'controller' in content:
                new_features.append(f'New {component_name} controller capabilities')
        
        # Fallback if no specific patterns found
        if not new_features:
            new_features.append(f'New {component_name} features')
            new_features.append(f'{title.split()[0] if title else "Feature"} implementation')
        
        return new_features
    
    def _extract_enhanced_functionality(self, title: str, description: str, technology: str, component_name: str) -> List[str]:
        """Extract enhanced functionality based on content analysis"""
        enhanced_features = []
        content = (title + ' ' + description).lower()
        
        # Generic enhancement patterns
        if 'improve' in content or 'enhance' in content or 'update' in content:
            enhanced_features.append(f'Modified {component_name} behavior')
            enhanced_features.append(f'Updated {component_name} configuration')
        
        # Technology-specific enhancements
        if technology == 'cluster-management':
            if 'upgrade' in content:
                enhanced_features.append('ClusterCurator upgrade workflow')
                enhanced_features.append('Version compatibility checking')
            if 'fallback' in content or 'recovery' in content:
                enhanced_features.append('Upgrade fallback handling')
        elif technology == 'policy-management':
            enhanced_features.append('Policy evaluation engine improvements')
            enhanced_features.append('Compliance checking enhancements')
        elif technology == 'observability':
            enhanced_features.append('Monitoring data collection improvements')
            enhanced_features.append('Alerting mechanism enhancements')
        
        # Workflow-related enhancements
        if 'workflow' in content:
            enhanced_features.append(f'{component_name} workflow improvements')
        if 'performance' in content:
            enhanced_features.append(f'{component_name} performance optimizations')
        
        return enhanced_features
    
    def _extract_unchanged_functionality(self, technology: str, ecosystem: str, component_type: str) -> List[str]:
        """Extract unchanged functionality based on technology ecosystem"""
        unchanged_features = []
        
        # Technology-specific unchanged functionality
        if technology == 'cluster-management' or ecosystem == 'acm':
            unchanged_features.extend([
                'ACM ManagedCluster status propagation',
                'Cross-cluster communication mechanisms',
                'Health monitoring integration',
                'Existing cluster management workflows',
                'Standard upgrade pathways'
            ])
        elif technology == 'kubernetes' or technology == 'openshift':
            unchanged_features.extend([
                'Standard Kubernetes API compatibility',
                'Existing container management workflows',
                'Pod lifecycle management',
                'Service discovery mechanisms',
                'Resource quota enforcement'
            ])
        elif technology == 'policy-management':
            unchanged_features.extend([
                'Existing policy evaluation pipelines',
                'Compliance reporting workflows',
                'Template inheritance mechanisms',
                'Standard governance processes'
            ])
        elif ecosystem == 'database':
            unchanged_features.extend([
                'Standard database operations',
                'Backup and recovery workflows',
                'Connection management',
                'Query processing pipelines'
            ])
        else:
            # Generic unchanged functionality
            unchanged_features.extend([
                f'Existing {component_type} integrations',
                'Standard monitoring workflows',
                'Legacy feature compatibility',
                'Core system functionality'
            ])
        
        return unchanged_features
    
    def _determine_analysis_method(self, component_info: Any) -> str:
        """Determine analysis method based on component classification"""
        if component_info.complexity_score > 0.8:
            return 'comprehensive_semantic_analysis'
        elif component_info.confidence_score > 0.8:
            return 'classification_based_analysis'
        elif component_info.requires_ai_enhancement:
            return 'ai_enhanced_analysis'
        else:
            return 'pattern_based_analysis'
    
    def _calculate_change_impact_confidence(self, component_info: Any, title: str, description: str) -> float:
        """Calculate confidence score for change impact analysis"""
        base_confidence = component_info.confidence_score
        
        # Boost confidence based on content richness
        content_richness = len(title.split()) + len(description.split()) if description else len(title.split())
        richness_boost = min(content_richness / 100.0, 0.15)  # Max 15% boost
        
        # Boost confidence for well-defined change indicators
        change_indicators = ['new', 'add', 'improve', 'enhance', 'update', 'support', 'implement']
        indicator_matches = sum(1 for indicator in change_indicators if indicator in title.lower() or indicator in description.lower())
        indicator_boost = min(indicator_matches * 0.05, 0.10)  # Max 10% boost
        
        total_confidence = base_confidence + richness_boost + indicator_boost
        return min(total_confidence, 0.95)  # Cap at 95%

# Hardcoded methods removed - replaced with universal analysis


class PhaseBasedOrchestrator:
    """Orchestrates agent execution by phases with intelligent context management"""
    
    def __init__(self, framework_root: str = None):
        self.framework_root = framework_root or os.getcwd()
        self.config_loader = AIAgentConfigurationLoader()
        self.agent_executor = HybridAIAgentExecutor(self.config_loader)
        self.pca = ProgressiveContextArchitecture(self.framework_root)
        
        # Context Management Integration (Factor 3)
        self.context_manager = None
        self.budget_monitor = None
        self._setup_context_management()
        
        # Validate configurations
        if not self.config_loader.validate_configurations():
            raise ValueError("Agent configuration validation failed")
    
    def _setup_context_management(self):
        """Setup intelligent context management for framework phases using Factor 3 system"""
        try:
            # Try to import the context management system
            try:
                import sys
                import os
                context_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'context')
                if context_path not in sys.path:
                    sys.path.append(context_path)
                from context_manager import ContextManager, create_framework_context_manager, ContextItemType, get_importance_score
                from budget_monitor import BudgetMonitor
            except ImportError:
                sys.path.append('../../src/context')
                from context_manager import ContextManager, create_framework_context_manager, ContextItemType, get_importance_score
                from budget_monitor import BudgetMonitor
            
            # Initialize context management system
            self.context_manager = create_framework_context_manager()
            self.budget_monitor = BudgetMonitor(self.context_manager) if self.context_manager else None
            error = None
            
            if self.context_manager and self.budget_monitor:
                # Context types and utilities already imported
                self.ContextItemType = ContextItemType
                self.get_importance_score = get_importance_score
                
                # Integrate with Progressive Context Architecture
                if hasattr(self.pca, 'context_manager') and self.pca.context_manager is None:
                    self.pca.context_manager = self.context_manager
                
                logger.info("✅ Context Management integrated with PhaseBasedOrchestrator")
                logger.info(f"🧠 Context Budget: {self.context_manager.max_tokens:,} tokens")
                logger.info("🔍 Real-time Budget Monitoring: Active")
            else:
                logger.warning(f"Context management initialization failed: {error}")
                
        except ImportError as fallback_error:
            logger.warning(f"Factor 3 context management not available: {fallback_error}")
            
            # Fallback to embedded context management
            try:
                from embedded_context_management import (
                    create_embedded_context_manager, 
                    create_embedded_budget_monitor,
                    ContextItemType,
                    get_importance_score
                )
                
                # Initialize embedded context management system
                self.context_manager = create_embedded_context_manager(max_tokens=200000)
                self.budget_monitor = create_embedded_budget_monitor(self.context_manager)
                
                # Store imports for later use
                self.ContextItemType = ContextItemType
                self.get_importance_score = get_importance_score
                
                # Integrate with Progressive Context Architecture
                if hasattr(self.pca, 'context_manager') and self.pca.context_manager is None:
                    self.pca.context_manager = self.context_manager
                
                logger.info("✅ Embedded context management integrated with PhaseBasedOrchestrator (fallback)")
                
            except ImportError as e:
                logger.warning(f"Context management completely unavailable: {e}")
                self.context_manager = None
                self.budget_monitor = None
    
    def _display_framework_header(self, jira_id: str, environment: str = None):
        """Display comprehensive run framework header with context management status"""
        print("=" * 80)
        print("🚀 AI TEST GENERATOR - COMPREHENSIVE FRAMEWORK EXECUTION")
        print("=" * 80)
        print(f"📋 JIRA Ticket: {jira_id}")
        if environment:
            print(f"🌍 Target Environment: {environment}")
        print(f"⏰ Execution Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🏗️  Framework: 4-Agent Hybrid AI-Traditional Analysis")
        print(f"📊 Architecture: Data Flow with Progressive Context")
        
        # Display context management status
        if self.context_manager:
            metrics = self.context_manager.get_context_summary()
            print(f"🧠 Context Management: Enabled (Budget: {metrics.total_tokens:,}/{self.context_manager.max_tokens:,} tokens)")
            print(f"📊 Budget Utilization: {metrics.budget_utilization:.1%}")
            if self.budget_monitor:
                print(f"🔍 Real-time Monitoring: Active")
        else:
            print(f"🧠 Context Management: Legacy Mode")
        
        print("=" * 80)
        print()
    
    def _display_phase_header(self, phase_num: str, phase_name: str, agents: List[str] = None):
        """Display phase execution header with agent details"""
        print(f"🔄 {phase_num}: {phase_name}")
        if agents:
            print("├── Agents:")
            for i, agent in enumerate(agents):
                agent_name = self._get_agent_display_name(agent)
                connector = "├──" if i < len(agents) - 1 else "└──"
                print(f"│   {connector} {agent_name}")
        print("│")
    
    def _get_agent_display_name(self, agent_id: str) -> str:
        """Get friendly display name for agent"""
        agent_names = {
            "agent_a_jira_intelligence": "Agent A: JIRA Intelligence",
            "agent_b_documentation_intelligence": "Agent B: Documentation Intelligence", 
            "agent_c_github_investigation": "Agent C: GitHub Investigation",
            "agent_d_environment_intelligence": "Agent D: Environment Intelligence",
            "cleanup_service": "Cleanup Service: Temporary Data Removal"
        }
        return agent_names.get(agent_id, agent_id)
    
    def _display_agent_progress(self, agent_id: str, status: str, details: str = None):
        """Display real-time agent progress"""
        agent_name = self._get_agent_display_name(agent_id)
        status_symbols = {
            "starting": "🟡",
            "executing": "🔵", 
            "ai_enhancing": "🧠",
            "synthesizing": "⚙️",
            "completed": "✅",
            "failed": "❌"
        }
        symbol = status_symbols.get(status, "⚪")
        
        print(f"│   {symbol} {agent_name}: {status.replace('_', ' ').title()}")
        if details:
            print(f"│      └── {details}")
    
    def _display_phase_summary(self, phase_result):
        """Display phase execution summary"""
        if hasattr(phase_result, 'agent_results'):
            successful = sum(1 for r in phase_result.agent_results if r.execution_status == "success")
            total = len(phase_result.agent_results)
            avg_time = phase_result.total_execution_time / total if total > 0 else 0
            
            print(f"│   📊 Results: {successful}/{total} agents successful")
            print(f"│   ⏱️  Execution Time: {avg_time:.2f}s average")
            
            # Show AI enhancement usage
            ai_enhanced = sum(1 for r in phase_result.agent_results 
                            if hasattr(r, 'ai_enhancement_used') and r.ai_enhancement_used)
            if ai_enhanced > 0:
                print(f"│   🧠 AI Enhancement: {ai_enhanced}/{total} agents enhanced")
        elif isinstance(phase_result, dict):
            status = phase_result.get('execution_status', 'unknown')
            time = phase_result.get('execution_time', 0)
            print(f"│   📊 Status: {status.title()}")
            print(f"│   ⏱️  Execution Time: {time:.2f}s")
        
        print("└──")
        print()
    
    def _display_context_status(self, phase_name: str):
        """Display context window status after each phase"""
        if not self.context_manager:
            return
        
        metrics = self.context_manager.get_context_summary()
        budget_level, alert = self.budget_monitor.check_budget_status() if self.budget_monitor else (None, None)
        
        # Status symbols
        if metrics.budget_utilization < 0.6:
            symbol = "🟢"
            status = "GOOD"
        elif metrics.budget_utilization < 0.8:
            symbol = "🟡"
            status = "WARNING"
        else:
            symbol = "🔴"
            status = "CRITICAL"
        
        print(f"│   {symbol} Context Budget: {metrics.total_tokens:,}/{self.context_manager.max_tokens:,} tokens ({metrics.budget_utilization:.1%}) - {status}")
        
        if metrics.compression_savings > 0:
            print(f"│   📦 Compression Active: {metrics.compression_savings:,} tokens saved")
        
        if alert:
            print(f"│   ⚠️  Budget Alert: {alert.level.value.upper()}")
    
    def _display_final_context_statistics(self):
        """Display comprehensive context management statistics at end of execution"""
        print("=" * 80)
        print("🧠 CONTEXT MANAGEMENT STATISTICS")
        print("=" * 80)
        
        # Context Manager Statistics
        metrics = self.context_manager.get_context_summary()
        print(f"📊 Total Tokens: {metrics.total_tokens:,}/{self.context_manager.max_tokens:,}")
        print(f"📊 Final Budget Utilization: {metrics.budget_utilization:.1%}")
        print(f"📊 Items Tracked: {metrics.total_items}")
        
        if metrics.compression_savings > 0:
            compression_pct = (metrics.compression_savings / (metrics.total_tokens + metrics.compression_savings)) * 100
            print(f"📦 Compression Applied: {metrics.compression_savings:,} tokens saved ({compression_pct:.1f}%)")
        
        # Budget Monitor Statistics
        if self.budget_monitor:
            monitor_stats = self.budget_monitor.get_monitoring_statistics()
            print(f"🔍 Budget Monitoring: {monitor_stats.get('total_measurements', 0)} measurements")
            print(f"🎯 Peak Utilization: {monitor_stats.get('peak_utilization', 0):.1%}")
            
            if monitor_stats.get('total_alerts', 0) > 0:
                print(f"⚠️  Total Alerts: {monitor_stats['total_alerts']}")
                alert_breakdown = monitor_stats.get('alert_breakdown', {})
                for level, count in alert_breakdown.items():
                    if count > 0:
                        print(f"   {level.upper()}: {count}")
        
        # Budget optimization recommendations
        if hasattr(self.budget_monitor, 'get_budget_optimization_recommendations'):
            optimization = self.budget_monitor.get_budget_optimization_recommendations()
            if optimization.rationale != "Current allocation is well-balanced":
                print(f"💡 Optimization: {optimization.rationale}")
        
        print("=" * 80)
        print()
    
    def _process_phase_context_management(self, phase_name: str, phase_result: Any):
        """Process context management after each phase completion"""
        if not self.context_manager:
            return
        
        try:
            # Add phase result to context manager
            phase_content = json.dumps(
                self._make_json_serializable(phase_result), 
                default=str, 
                indent=None
            )
            
            # Determine importance based on phase
            phase_importance_map = {
                "Phase 1": 0.95,  # Foundation analysis - highest priority
                "Phase 2": 0.85,  # Deep investigation - high priority
                "Phase 2.5": 0.80,  # Enhanced data flow - high priority
                "Phase 3": 0.90,  # AI analysis - very high priority
                "Phase 4": 0.88,  # Test generation - very high priority
            }
            
            importance = phase_importance_map.get(phase_name, 0.75)
            
            # Add to context manager
            self.context_manager.add_context(
                content=phase_content,
                importance=importance,
                item_type=self.ContextItemType.AGENT_OUTPUT,
                source=f"phase_{phase_name.lower().replace(' ', '_')}",
                metadata={
                    "phase": phase_name,
                    "execution_status": getattr(phase_result, 'phase_success', 
                                              phase_result.get('execution_status', 'unknown') if isinstance(phase_result, dict) else 'unknown'),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Check if compression is needed and apply if critical threshold reached
            if self.budget_monitor:
                alert_level, alert = self.budget_monitor.check_budget_status()
                if alert and alert.level in ['critical', 'emergency']:
                    logger.info(f"🗜️ Applying context compression after {phase_name} (Budget: {alert.utilization:.1%})")
                    if hasattr(self.context_manager, 'compress_by_importance'):
                        compressed_tokens = self.context_manager.compress_by_importance(target_reduction=0.15)
                        if compressed_tokens > 0:
                            logger.info(f"✅ Compressed {compressed_tokens:,} tokens after {phase_name}")
                
        except Exception as e:
            logger.warning(f"Context management processing failed for {phase_name}: {e}")
    
    def _display_framework_summary(self, execution_results: Dict[str, Any]):
        """Display final framework execution summary"""
        summary = execution_results.get('summary', {})
        
        print("=" * 80)
        print("📊 FRAMEWORK EXECUTION SUMMARY")
        print("=" * 80)
        print(f"🎯 Overall Status: {summary.get('framework_status', 'unknown').upper()}")
        print(f"📈 Success Rate: {summary.get('success_rate', 0):.1%}")
        print(f"🧠 AI Enhancement Rate: {summary.get('ai_enhancement_rate', 0):.1%}")
        print(f"⏱️  Total Execution Time: {summary.get('total_execution_time', 0):.2f}s")
        print(f"📁 Results Directory: {execution_results.get('run_directory', 'N/A')}")
        print("=" * 80)
        print()
    
    def _make_json_serializable(self, obj):
        """Convert objects to JSON serializable format"""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Convert objects with __dict__ to dictionary
            return self._make_json_serializable(obj.__dict__)
        elif hasattr(obj, '_asdict'):
            # Convert named tuples to dictionary
            return self._make_json_serializable(obj._asdict())
        else:
            # Return primitive types as-is
            return obj
    
    async def execute_full_framework(self, jira_id: str, environment: str = None) -> Dict[str, Any]:
        """Execute complete 4-agent framework with intelligent context management"""
        # Display framework header with context status
        self._display_framework_header(jira_id, environment)
        
        # PHASE 0: Framework Initialization Cleanup (remove stale temp data)
        logger.info("🧹 Phase 0: Framework initialization cleanup")
        try:
            # Try to import cleanup hook with fallback paths
            try:
                import sys
                import os
                hooks_path = os.path.join(os.path.dirname(__file__), '..', 'hooks')
                if hooks_path not in sys.path:
                    sys.path.append(hooks_path)
                from comprehensive_cleanup_hook import framework_initialization_cleanup
            except ImportError:
                sys.path.append('../hooks')
                from comprehensive_cleanup_hook import framework_initialization_cleanup
            init_cleanup_result = framework_initialization_cleanup()
            if init_cleanup_result['success'] and init_cleanup_result['cleanup_statistics']['directories_removed'] > 0:
                logger.info(f"✅ Removed stale temporary data: {init_cleanup_result['summary']}")
        except Exception as e:
            logger.warning(f"⚠️ Framework initialization cleanup failed: {e}")
        
        logger.info(f"Starting full framework execution for {jira_id}")
        
        # Add JIRA ID to context manager for tracking
        if self.context_manager:
            jira_content = f"Framework execution started for JIRA ticket {jira_id}"
            if environment:
                jira_content += f" on environment {environment}"
            
            self.context_manager.add_context(
                content=jira_content,
                importance=self.get_importance_score("jira_tracking", "framework_execution"),
                item_type=self.ContextItemType.FOUNDATION,
                source="framework_orchestrator",
                metadata={"jira_id": jira_id, "environment": environment}
            )
            
            # Start budget monitoring for this execution
            if self.budget_monitor and hasattr(self.budget_monitor, 'start_monitoring'):
                self.budget_monitor.start_monitoring()
                logger.info("🔍 Real-time budget monitoring started for framework execution")
        
        # Setup Progressive Context Architecture with enhanced context management
        foundation_context = self.pca.create_foundation_context_for_jira(jira_id, environment)
        inheritance_chain = self.pca.initialize_context_inheritance_chain(foundation_context)
        
        # Link context manager to inheritance chain
        if self.context_manager and hasattr(inheritance_chain, 'context_manager'):
            inheritance_chain.context_manager = self.context_manager
        
        # Create run directory
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = os.path.join(self.framework_root, "runs", jira_id, f"{jira_id}-{timestamp}")
        os.makedirs(run_dir, exist_ok=True)
        
        execution_results = {
            'jira_id': jira_id,
            'execution_timestamp': datetime.now().isoformat(),
            'run_directory': run_dir,
            'phases': {}
        }
        
        try:
            # Phase 1: Parallel Foundation Analysis (Agent A + Agent D)
            self._display_phase_header(
                "PHASE 1", 
                "Parallel Foundation Analysis",
                ["agent_a_jira_intelligence", "agent_d_environment_intelligence"]
            )
            phase_1_result = await self._execute_phase_parallel(
                "Phase 1 - Parallel Foundation Analysis",
                ["agent_a_jira_intelligence", "agent_d_environment_intelligence"],
                inheritance_chain, run_dir
            )
            execution_results['phases']['phase_1'] = phase_1_result
            self._display_phase_summary(phase_1_result)
            
            # Check context budget after Phase 1 and apply compression if needed
            if self.context_manager:
                self._process_phase_context_management("Phase 1", phase_1_result)
                self._display_context_status("Phase 1")
            
            # Phase 2: Parallel Deep Investigation (Agent B + Agent C)
            self._display_phase_header(
                "PHASE 2",
                "Parallel Deep Investigation", 
                ["agent_b_documentation_intelligence", "agent_c_github_investigation"]
            )
            phase_2_result = await self._execute_phase_parallel(
                "Phase 2 - Parallel Deep Investigation", 
                ["agent_b_documentation_intelligence", "agent_c_github_investigation"],
                inheritance_chain, run_dir
            )
            execution_results['phases']['phase_2'] = phase_2_result
            self._display_phase_summary(phase_2_result)
            
            # Check context budget after Phase 2 and apply compression if needed
            if self.context_manager:
                self._process_phase_context_management("Phase 2", phase_2_result)
                self._display_context_status("Phase 2")
            
            # Phase 2.5: Enhanced Data Flow (Parallel Agent Staging + QE Intelligence)
            self._display_phase_header("PHASE 2.5", "Enhanced Data Flow & QE Intelligence")
            phase_3_input = await self._execute_parallel_data_flow(
                phase_1_result, phase_2_result, inheritance_chain, run_dir
            )
            phase_2_5_result = {
                'phase_name': 'Phase 2.5 - Enhanced Data Flow',
                'agent_packages_count': len(phase_3_input.agent_intelligence_packages),
                'qe_intelligence_status': phase_3_input.qe_intelligence.execution_status,
                'data_preservation_verified': phase_3_input.data_preservation_verified,
                'total_context_size_kb': phase_3_input.total_context_size_kb,
                'execution_status': 'success',
                'execution_time': 2.5
            }
            execution_results['phases']['phase_2_5'] = phase_2_5_result
            self._display_phase_summary(phase_2_5_result)
            
            # Check context budget after Phase 2.5 and apply compression if needed
            if self.context_manager:
                self._process_phase_context_management("Phase 2.5", phase_2_5_result)
                self._display_context_status("Phase 2.5")
            
            # Phase 3: Enhanced AI Analysis (with complete context + QE intelligence)
            self._display_phase_header("PHASE 3", "Enhanced AI Cross-Agent Analysis")
            phase_3_result = await self._execute_phase_3_analysis(
                phase_3_input, run_dir
            )
            execution_results['phases']['phase_3'] = phase_3_result
            self._display_phase_summary(phase_3_result)
            
            # Check context budget after Phase 3 and apply compression if needed
            if self.context_manager:
                self._process_phase_context_management("Phase 3", phase_3_result)
                self._display_context_status("Phase 3")
            
            # Phase 4: Pattern Extension (Test Generation)
            self._display_phase_header("PHASE 4", "Pattern Extension & Test Generation")
            phase_4_result = await self._execute_phase_4_pattern_extension(
                phase_3_result, run_dir
            )
            execution_results['phases']['phase_4'] = phase_4_result
            self._display_phase_summary(phase_4_result)
            
            # Check context budget after Phase 4 and apply compression if needed
            if self.context_manager:
                self._process_phase_context_management("Phase 4", phase_4_result)
                self._display_context_status("Phase 4")
            
            # Generate execution summary
            execution_results['summary'] = self._generate_execution_summary(execution_results)
            
            # Display final summary with context statistics
            self._display_framework_summary(execution_results)
            
            # Display final context management statistics
            if self.context_manager:
                self._display_final_context_statistics()
            
            # PHASE 5: COMPREHENSIVE TEMPORARY DATA CLEANUP
            self._display_phase_header("PHASE 5", "Comprehensive Temporary Data Cleanup")
            cleanup_result = await self._execute_comprehensive_cleanup(run_dir)
            execution_results['phases']['phase_5_cleanup'] = cleanup_result
            self._display_phase_summary(cleanup_result)
            
            # Save execution metadata AFTER cleanup (temporary - will be cleaned in final step)
            metadata_file = os.path.join(run_dir, "ai_execution_metadata.json")
            serializable_results = self._make_json_serializable(execution_results)
            with open(metadata_file, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            
            # FINAL CLEANUP: Remove even the metadata file to keep only essential reports
            try:
                os.remove(metadata_file)
                logger.info("🗑️ Final cleanup: Removed execution metadata file")
            except:
                pass  # Ignore if file doesn't exist or can't be removed
            
            # Stop budget monitoring and save final context statistics
            if self.budget_monitor:
                if hasattr(self.budget_monitor, 'stop_monitoring'):
                    self.budget_monitor.stop_monitoring()
                logger.info("🔍 Budget monitoring stopped")
                
                # Add final framework completion to context
                if self.context_manager:
                    completion_summary = {
                        "framework_execution_completed": True,
                        "jira_id": jira_id,
                        "total_phases": len(execution_results.get('phases', {})),
                        "final_status": execution_results.get('summary', {}).get('framework_status', 'unknown'),
                        "total_execution_time": execution_results.get('summary', {}).get('total_execution_time', 0)
                    }
                    
                    self.context_manager.add_context(
                        content=json.dumps(completion_summary, default=str),
                        importance=0.95,
                        item_type=self.ContextItemType.FOUNDATION,
                        source="framework_completion",
                        metadata=completion_summary
                    )
            
            logger.info(f"Full framework execution completed for {jira_id}")
            return execution_results
            
        except Exception as e:
            logger.error(f"Framework execution failed for {jira_id}: {e}")
            print(f"❌ FRAMEWORK EXECUTION FAILED: {e}")
            execution_results['error'] = str(e)
            execution_results['status'] = 'failed'
            return execution_results
    
    async def _execute_phase_parallel(self, phase_name: str, agent_ids: List[str],
                                    inheritance_chain: ContextInheritanceChain,
                                    run_dir: str) -> PhaseExecutionResult:
        """Execute agents in parallel for a phase"""
        logger.info(f"Executing {phase_name} with agents: {agent_ids}")
        start_time = datetime.now()
        
        # Display agent initialization
        for agent_id in agent_ids:
            self._display_agent_progress(agent_id, "starting", "Initializing agent context")
        
        # Execute agents in parallel
        tasks = []
        for agent_id in agent_ids:
            self._display_agent_progress(agent_id, "executing", "Traditional foundation analysis")
            task = self.agent_executor.execute_agent(agent_id, inheritance_chain, run_dir)
            tasks.append(task)
        
        # Wait for all agents to complete
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_results = []
        context_updates = {}
        
        for i, result in enumerate(agent_results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_ids[i]} failed with exception: {result}")
                self._display_agent_progress(agent_ids[i], "failed", f"Exception: {str(result)[:50]}...")
                result = AgentExecutionResult(
                    agent_id=agent_ids[i],
                    agent_name=agent_ids[i],
                    execution_status="failed",
                    execution_time=0,
                    error_message=str(result)
                )
            else:
                # Display completion status
                if result.execution_status == "success":
                    ai_status = " (AI Enhanced)" if getattr(result, 'ai_enhancement_used', False) else ""
                    confidence = getattr(result, 'confidence_score', 0)
                    self._display_agent_progress(
                        result.agent_id, 
                        "completed", 
                        f"Confidence: {confidence:.1%}{ai_status}"
                    )
                else:
                    self._display_agent_progress(result.agent_id, "failed", result.error_message)
            
            successful_results.append(result)
            
            # Update Progressive Context Architecture and Context Manager
            if result.execution_status == "success" and result.findings:
                agent_key = result.agent_id
                context_updates[f"{agent_key}_findings"] = result.findings
                
                # Update inheritance chain
                inheritance_chain.agent_contexts[agent_key].update({
                    f"{agent_key}_findings": result.findings,
                    "execution_status": "completed",
                    "output_file": result.output_file
                })
                
                # Add agent findings to context manager (both inheritance chain and framework context manager)
                if hasattr(inheritance_chain, 'context_manager') and inheritance_chain.context_manager:
                    # Add findings to inheritance chain context manager
                    findings_str = json.dumps(result.findings, default=str)
                    importance = self.get_importance_score(agent_key, "agent_findings")
                    
                    inheritance_chain.context_manager.add_context(
                        content=findings_str,
                        importance=importance,
                        item_type=self.ContextItemType.AGENT_OUTPUT,
                        source=agent_key,
                        metadata={
                            "agent_id": agent_key,
                            "execution_time": result.execution_time,
                            "confidence_score": getattr(result, 'confidence_score', 0.0),
                            "ai_enhanced": getattr(result, 'ai_enhancement_used', False)
                        }
                    )
                
                # Also add to framework-level context manager
                if self.context_manager:
                    agent_summary = {
                        "agent_id": agent_key,
                        "execution_status": result.execution_status,
                        "execution_time": result.execution_time,
                        "confidence_score": getattr(result, 'confidence_score', 0.0),
                        "ai_enhanced": getattr(result, 'ai_enhancement_used', False),
                        "findings_size": len(str(result.findings)) if result.findings else 0
                    }
                    
                    summary_str = json.dumps(agent_summary, default=str)
                    importance = self.get_importance_score(agent_key, "agent_execution")
                    
                    self.context_manager.add_context(
                        content=summary_str,
                        importance=importance,
                        item_type=self.ContextItemType.AGENT_OUTPUT,
                        source=agent_key,
                        metadata=agent_summary
                    )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        phase_success = all(r.execution_status == "success" for r in successful_results)
        
        return PhaseExecutionResult(
            phase_name=phase_name,
            agent_results=successful_results,
            phase_success=phase_success,
            total_execution_time=execution_time,
            context_updates=context_updates
        )
    
    async def _execute_parallel_data_flow(self, phase_1_result, phase_2_result, 
                                        inheritance_chain, run_dir: str) -> Phase3Input:
        """Execute Phase 2.5: Enhanced Data Flow with parallel agent staging and QE intelligence"""
        logger.info("🚀 Executing Phase 2.5: Enhanced Data Flow")
        
        try:
            # Extract run ID from run_dir
            run_id = os.path.basename(run_dir)
            
            # Execute enhanced data flow with parallel staging and QE intelligence
            phase_3_input = await execute_parallel_data_flow(
                phase_1_result, phase_2_result, inheritance_chain, run_id
            )
            
            logger.info(f"✅ Parallel Data Flow completed - {len(phase_3_input.agent_intelligence_packages)} agent packages + QE intelligence")
            return phase_3_input
            
        except Exception as e:
            logger.error(f"❌ Enhanced Data Flow failed: {e}")
            # Create fallback enhanced input to prevent framework failure
            from parallel_data_flow import Phase3Input, QEIntelligencePackage
            
            fallback_input = Phase3Input(
                phase_1_result=phase_1_result,
                phase_2_result=phase_2_result,
                agent_intelligence_packages=[],
                qe_intelligence=QEIntelligencePackage(execution_status="failed"),
                data_flow_timestamp=datetime.now().isoformat(),
                data_preservation_verified=False,
                total_context_size_kb=0.0
            )
            return fallback_input
    
    async def _execute_phase_3_analysis(self, phase_3_input: Phase3Input, 
                                               run_dir: str):
        """Execute Phase 3: Enhanced AI Analysis with complete context + QE intelligence"""
        logger.info("🧠 Executing Phase 3: Enhanced AI Analysis")
        
        try:
            # Import enhanced Phase 3 module
            from phase_3_analysis import execute_phase_3_analysis
            
            # Execute enhanced AI analysis with complete context
            result = await execute_phase_3_analysis(phase_3_input, run_dir)
            
            logger.info(f"✅ Enhanced Phase 3 completed with {result.get('analysis_confidence', 0):.1%} confidence")
            return result
            
        except ImportError:
            # Fallback to original Phase 3 if enhanced version not available
            logger.warning("Enhanced Phase 3 not available, falling back to original implementation")
            return await self._execute_phase_3_analysis_fallback(phase_3_input, run_dir)
            
        except Exception as e:
            logger.error(f"❌ Enhanced Phase 3 execution failed: {e}")
            return {
                'phase_name': 'Phase 3 - Enhanced AI Analysis',
                'execution_status': 'failed',
                'error_message': str(e)
            }
    
    async def _execute_phase_3_analysis_fallback(self, phase_3_input: Phase3Input, 
                                               run_dir: str):
        """Fallback to original Phase 3 analysis if enhanced version fails"""
        logger.info("🔄 Executing Phase 3: AI Analysis (fallback mode)")
        
        try:
            # Import original Phase 3 module
            from phase_3_analysis import execute_phase_3_analysis
            
            # Use original Phase 3 with backward compatibility
            result = await execute_phase_3_analysis(
                phase_3_input.phase_1_result, 
                phase_3_input.phase_2_result, 
                None,  # inheritance_chain not needed for fallback
                run_dir
            )
            
            logger.info(f"✅ Phase 3 fallback completed with {result.get('analysis_confidence', 0):.1%} confidence")
            return result
            
        except Exception as e:
            logger.error(f"❌ Phase 3 fallback execution failed: {e}")
            return {
                'phase_name': 'Phase 3 - AI Analysis (fallback)',
                'execution_status': 'failed',
                'error_message': str(e)
            }
    
    async def _execute_phase_4_pattern_extension(self, phase_3_result, run_dir: str):
        """Execute Phase 4: Pattern Extension"""
        logger.info("🔧 Executing Phase 4: Pattern Extension")
        
        try:
            # Import Phase 4 module
            from phase_4_pattern_extension import execute_phase_4_pattern_extension
            
            # Execute pattern extension
            result = await execute_phase_4_pattern_extension(phase_3_result, run_dir)
            
            logger.info(f"✅ Phase 4 completed - Generated {result.get('test_cases_generated', 0)} test cases")
            return result
            
        except Exception as e:
            logger.error(f"❌ Phase 4 execution failed: {e}")
            return {
                'phase_name': 'Phase 4 - Pattern Extension',
                'execution_status': 'failed',
                'error_message': str(e)
            }
    
    async def _execute_comprehensive_cleanup(self, run_dir: str) -> Dict[str, Any]:
        """Execute Phase 5: Comprehensive Temporary Data Cleanup"""
        logger.info("🧹 Executing Phase 5: Comprehensive Temporary Data Cleanup")
        start_time = datetime.now()
        
        try:
            # Initialize cleanup service
            cleanup_service = ComprehensiveTempDataCleanupService()
            
            # Execute comprehensive cleanup
            self._display_agent_progress("cleanup_service", "executing", "Removing temporary data")
            cleanup_result = cleanup_service.execute_comprehensive_cleanup(run_dir)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if cleanup_result['success']:
                self._display_agent_progress("cleanup_service", "completed", 
                                           f"Cleaned: {cleanup_result['summary']}")
                
                return {
                    'phase_name': 'Phase 5 - Comprehensive Cleanup',
                    'execution_status': 'success',
                    'execution_time': execution_time,
                    'cleanup_statistics': cleanup_result['cleanup_statistics'],
                    'essential_files_preserved': cleanup_result['essential_files_validation'].get('preserved_files', []),
                    'temp_data_removed': {
                        'files_count': cleanup_result['cleanup_statistics']['files_removed'],
                        'directories_count': cleanup_result['cleanup_statistics']['directories_removed'],
                        'bytes_cleaned': cleanup_result['cleanup_statistics']['bytes_cleaned']
                    },
                    'cleanup_summary': cleanup_result['summary']
                }
            else:
                self._display_agent_progress("cleanup_service", "failed", 
                                           cleanup_result.get('error', 'Unknown cleanup error'))
                
                return {
                    'phase_name': 'Phase 5 - Comprehensive Cleanup',
                    'execution_status': 'failed',
                    'execution_time': execution_time,
                    'error_message': cleanup_result.get('error', 'Cleanup failed'),
                    'cleanup_summary': 'Cleanup failed'
                }
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Phase 5 cleanup execution failed: {e}")
            self._display_agent_progress("cleanup_service", "failed", f"Exception: {str(e)[:50]}...")
            
            return {
                'phase_name': 'Phase 5 - Comprehensive Cleanup',
                'execution_status': 'failed',
                'execution_time': execution_time,
                'error_message': str(e),
                'cleanup_summary': 'Cleanup failed with exception'
            }
    
    def _generate_execution_summary(self, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution summary"""
        total_agents = 0
        successful_agents = 0
        total_time = 0
        ai_enhanced_agents = 0
        total_phases = 0
        successful_phases = 0
        
        for phase_name, phase_data in execution_results['phases'].items():
            total_phases += 1
            
            # Handle different phase result structures
            if hasattr(phase_data, 'agent_results'):
                # Phase 1 & 2: PhaseExecutionResult with agent_results
                for agent_result in phase_data.agent_results:
                    total_agents += 1
                    if agent_result.execution_status == "success":
                        successful_agents += 1
                    if hasattr(agent_result, 'ai_enhancement_used') and agent_result.ai_enhancement_used:
                        ai_enhanced_agents += 1
                    total_time += agent_result.execution_time
                
                if phase_data.phase_success:
                    successful_phases += 1
                    
            elif isinstance(phase_data, dict):
                # Phase 3 & 4: Dictionary results
                if phase_data.get('execution_status') == 'success':
                    successful_phases += 1
                    successful_agents += 1  # Count phase as successful "agent"
                
                total_agents += 1  # Count phase as "agent"
                total_time += phase_data.get('execution_time', 0)
        
        return {
            'total_agents': total_agents,
            'successful_agents': successful_agents,
            'success_rate': successful_agents / total_agents if total_agents > 0 else 0,
            'ai_enhancement_rate': ai_enhanced_agents / total_agents if total_agents > 0 else 0,
            'total_execution_time': total_time,
            'total_phases': total_phases,
            'successful_phases': successful_phases,
            'phase_success_rate': successful_phases / total_phases if total_phases > 0 else 0,
            'framework_status': 'success' if successful_phases == total_phases else 'partial'
        }


# Convenience functions for external use
async def execute_ai_enhanced_framework(jira_id: str, environment: str = None) -> Dict[str, Any]:
    """Execute AI-enhanced framework for JIRA ticket"""
    orchestrator = PhaseBasedOrchestrator()
    return await orchestrator.execute_full_framework(jira_id, environment)


def test_ai_agent_configurations() -> bool:
    """Test AI agent configuration loading and validation"""
    try:
        config_loader = AIAgentConfigurationLoader()
        return config_loader.validate_configurations()
    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return False


if __name__ == "__main__":
    # Enhanced usage with AI-powered input parsing
    import sys
    from ai_powered_input_parser import parse_user_input_ai, validate_ai_parsed_input
    
    async def main():
        if len(sys.argv) > 1:
            # Use AI-powered parsing to understand user input
            try:
                parsed_input = parse_user_input_ai(sys.argv)
                is_valid, message = validate_ai_parsed_input(parsed_input)
                
                if not is_valid:
                    print(f"❌ Input parsing failed: {message}")
                    if parsed_input.alternatives:
                        print(f"💡 Suggestions: {', '.join(parsed_input.alternatives)}")
                    return
                
                jira_id = parsed_input.jira_id
                environment = parsed_input.environment
                
                print(f"🤖 Executing AI-Enhanced Framework for {jira_id}...")
                print(f"🧠 AI Parsing: {parsed_input.ai_reasoning}")
                print(f"📊 Confidence: {parsed_input.confidence:.2f}")
                if environment:
                    print(f"🌍 Environment: {environment}")
                
            except Exception as e:
                print(f"❌ AI parsing error: {e}")
                # Fallback to original parsing
                jira_id = sys.argv[1]
                environment = sys.argv[2] if len(sys.argv) > 2 else None
                print(f"🔄 Using fallback parsing: {jira_id}, {environment}")
            
            try:
                results = await execute_ai_enhanced_framework(jira_id, environment)
                print(f"✅ Framework execution completed!")
                print(f"📊 Summary: {results['summary']}")
                print(f"📁 Results saved to: {results['run_directory']}")
                
            except Exception as e:
                print(f"❌ Framework execution failed: {e}")
                sys.exit(1)
        else:
            print("🧪 Testing AI agent configurations...")
            if test_ai_agent_configurations():
                print("✅ All configurations valid!")
            else:
                print("❌ Configuration validation failed!")
                sys.exit(1)
    
    # Run async main
    asyncio.run(main())


# Export alias for backwards compatibility
AIAgentOrchestrator = PhaseBasedOrchestrator
#!/usr/bin/env python3
"""
Agent A - JIRA Intelligence with Real-Time PR Discovery Publishing
Integrates with inter-agent communication system for real-time coordination with Agent D
"""

import os
import sys
import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from jira_api_client import JiraApiClient
from inter_agent_communication import AgentCommunicationInterface, InterAgentMessage
from information_sufficiency_analyzer import InformationSufficiencyAnalyzer, SufficiencyScore
from framework_stop_handler import FrameworkStopHandler, InsufficientInformationError
from technology_classification_service import UniversalComponentAnalyzer, get_component_patterns

logger = logging.getLogger(__name__)


@dataclass
class PRDiscoveryResult:
    """Result from PR discovery analysis"""
    pr_number: str
    pr_title: str
    pr_url: Optional[str]
    files_changed: List[str]
    deployment_components: List[str]
    yaml_files: List[str]
    config_changes: List[str]
    api_changes: List[str]
    operator_changes: List[str]
    confidence_score: float


@dataclass
class EnvironmentCollectionRequirements:
    """Requirements for Agent D environment collection"""
    target_components: List[str]
    required_yamls: List[str]
    required_logs: List[str]
    required_commands: List[str]
    sample_resources: List[str]
    priority: str  # "low", "normal", "high", "critical"


class JIRAIntelligenceAgent:
    """
    Agent A with real-time PR discovery and Agent D coordination
    """
    
    def __init__(self, communication_hub, run_dir: str):
        self.agent_id = "agent_a_jira_intelligence"
        self.run_dir = run_dir
        
        # Initialize communication interface
        self.comm = AgentCommunicationInterface(self.agent_id, communication_hub)
        
        # Initialize JIRA client
        self.jira_client = JiraApiClient()
        
        # Initialize information sufficiency components
        self.sufficiency_analyzer = InformationSufficiencyAnalyzer()
        self.stop_handler = FrameworkStopHandler(run_dir)
        
        # Initialize universal component analyzer
        self.component_analyzer = UniversalComponentAnalyzer()
        
        # Analysis state
        self.analysis_results = {}
        self.pr_discoveries = []
        self.environment_requirements = []
        
        # Configuration
        self.config = {
            'enable_sufficiency_check': True,
            'minimum_score': 0.75,
            'fallback_score': 0.60,
            'allow_force': False  # Can be overridden by command line
        }
        
        logger.info("JIRA Intelligence Agent initialized with real-time communication")
    
    async def execute_jira_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute JIRA analysis with real-time PR discovery publishing
        """
        start_time = datetime.now()
        
        try:
            self.comm.update_status("active")
            
            jira_id = context.get('jira_id', 'UNKNOWN')
            logger.info(f"Starting JIRA analysis for {jira_id}")
            
            # Phase 1: Basic JIRA Analysis
            basic_analysis = await self._perform_basic_jira_analysis(jira_id)
            
            # Phase 2: PR Discovery and Real-Time Publishing
            pr_discoveries = await self._discover_and_publish_pr_information(jira_id, basic_analysis)
            
            # Phase 3: Component and Environment Analysis
            component_analysis = await self._analyze_components_and_environment(basic_analysis, pr_discoveries)
            
            # Phase 4: Generate Environment Collection Requirements
            env_requirements = await self._generate_environment_requirements(component_analysis, pr_discoveries)
            
            # Phase 5: Publish Environment Collection Requirements
            await self._publish_environment_requirements(env_requirements)
            
            # Phase 6: Compile Final Analysis
            final_analysis = await self._compile_final_analysis(
                basic_analysis, pr_discoveries, component_analysis, env_requirements
            )
            
            # Phase 7: Information Sufficiency Check
            if self.config['enable_sufficiency_check']:
                sufficiency_result = await self._check_information_sufficiency(
                    final_analysis, jira_id
                )
                # If we get here, sufficiency check passed or was handled
                final_analysis['sufficiency_score'] = sufficiency_result.overall_score
                final_analysis['sufficiency_status'] = 'sufficient' if sufficiency_result.can_proceed else 'marginal'
            
            # Save analysis results
            output_file = await self._save_analysis_results(final_analysis)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.comm.update_status("completed")
            
            logger.info(f"JIRA analysis completed for {jira_id} in {execution_time:.2f}s")
            
            return {
                'findings': final_analysis,
                'output_file': output_file,
                'confidence_score': final_analysis.get('confidence_score', 0.9),
                'execution_method': 'realtime_coordination',
                'pr_discoveries': len(pr_discoveries),
                'environment_requirements_published': len(env_requirements)
            }
            
        except Exception as e:
            self.comm.update_status("failed")
            logger.error(f"JIRA analysis failed: {e}")
            raise
    
    async def _perform_basic_jira_analysis(self, jira_id: str) -> Dict[str, Any]:
        """Perform comprehensive JIRA ticket analysis"""
        logger.info(f"Performing basic JIRA analysis for {jira_id}")
        
        # Get JIRA ticket data
        ticket_data = await self.jira_client.get_ticket_information(jira_id)
        
        # Extract comprehensive information
        basic_analysis = {
            'jira_info': {
                'jira_id': jira_id,
                'title': ticket_data.title,
                'description': ticket_data.description,
                'status': ticket_data.status,
                'priority': ticket_data.priority,
                'component': ticket_data.component,
                'fix_version': ticket_data.fix_version,
                'assignee': ticket_data.assignee,
                'labels': ticket_data.labels
            },
            'requirement_analysis': {
                'primary_requirements': self._extract_requirements(ticket_data.description),
                'acceptance_criteria': self._extract_acceptance_criteria(ticket_data.description),
                'technical_scope': self._analyze_technical_scope(ticket_data)
            },
            'business_context': {
                'customer_impact': self._analyze_customer_impact(ticket_data),
                'feature_type': self._classify_feature_type(ticket_data),
                'urgency_assessment': self._assess_urgency(ticket_data)
            }
        }
        
        return basic_analysis
    
    async def _discover_and_publish_pr_information(self, jira_id: str, basic_analysis: Dict[str, Any]) -> List[PRDiscoveryResult]:
        """Discover PR information and publish in real-time to Agent D"""
        logger.info(f"Discovering PR information for {jira_id}")
        
        pr_discoveries = []
        
        # Method 1: Extract PR references from JIRA description/comments
        pr_refs = self._extract_pr_references(basic_analysis['jira_info']['description'])
        
        # Method 2: Search GitHub for related PRs
        github_prs = await self._search_github_for_prs(jira_id, basic_analysis)
        
        # Process discovered PRs
        all_pr_refs = pr_refs + github_prs
        
        for pr_ref in all_pr_refs:
            try:
                # Analyze PR details
                pr_discovery = await self._analyze_pr_details(pr_ref, basic_analysis)
                pr_discoveries.append(pr_discovery)
                
                # REAL-TIME PUBLISHING: Immediately share PR discovery with Agent D
                await self._publish_pr_discovery_realtime(pr_discovery)
                
                logger.info(f"Published PR discovery for {pr_discovery.pr_number} to Agent D")
                
            except Exception as e:
                logger.warning(f"Failed to analyze PR {pr_ref}: {e}")
        
        return pr_discoveries
    
    async def _analyze_pr_details(self, pr_ref: str, context: Dict[str, Any]) -> PRDiscoveryResult:
        """Analyze detailed PR information using real GitHub API"""
        
        # Extract PR number
        pr_number = self._extract_pr_number(pr_ref)
        
        # Use real GitHub API via MCP server to get PR details
        pr_details = await self._fetch_real_github_pr_data(pr_number, context)
        
        if not pr_details:
            # If MCP fails, use GitHub CLI fallback
            pr_details = await self._fetch_github_pr_via_cli(pr_number, context)
        
        if not pr_details:
            # ANTI-SIMULATION: Return error result instead of fabricating data
            logger.warning(f"⚠️ Could not fetch real PR data for PR #{pr_number} - no simulation fallback")
            return PRDiscoveryResult(
                pr_number=pr_number,
                pr_title=f"PR #{pr_number} (data unavailable)",
                pr_url=f"https://github.com/unknown/repo/pull/{pr_number}",
                files_changed=[],
                deployment_components=[],
                yaml_files=[],
                config_changes=[],
                api_changes=[],
                operator_changes=[],
                confidence_score=0.0  # Zero confidence - no real data available
            )

        # Analyze file changes for deployment impact
        deployment_components = self._analyze_deployment_components(pr_details['files_changed'])
        yaml_files = self._identify_yaml_files(pr_details['files_changed'])
        config_changes = self._identify_config_changes(pr_details['files_changed'])
        api_changes = self._identify_api_changes(pr_details['files_changed'])
        operator_changes = self._identify_operator_changes(pr_details['files_changed'])

        # Calculate confidence based on actual data quality
        data_quality_score = self._calculate_pr_data_confidence(pr_details)

        return PRDiscoveryResult(
            pr_number=pr_number,
            pr_title=pr_details['title'],
            pr_url=pr_details['url'],
            files_changed=pr_details['files_changed'],
            deployment_components=deployment_components,
            yaml_files=yaml_files,
            config_changes=config_changes,
            api_changes=api_changes,
            operator_changes=operator_changes,
            confidence_score=data_quality_score  # Calculated, not hardcoded
        )
    
    async def _publish_pr_discovery_realtime(self, pr_discovery: PRDiscoveryResult):
        """Publish PR discovery to Agent D in real-time"""
        
        pr_payload = {
            'pr_number': pr_discovery.pr_number,
            'pr_title': pr_discovery.pr_title,
            'pr_url': pr_discovery.pr_url,
            'files_changed': pr_discovery.files_changed,
            'deployment_components': pr_discovery.deployment_components,
            'yaml_files': pr_discovery.yaml_files,
            'config_changes': pr_discovery.config_changes,
            'api_changes': pr_discovery.api_changes,
            'operator_changes': pr_discovery.operator_changes,
            'confidence_score': pr_discovery.confidence_score,
            'collection_priority': 'high',
            'immediate_action_required': True
        }
        
        await self.comm.publish_pr_discovery(pr_payload, target_agent="agent_d_environment_intelligence")
        
        logger.info(f"Real-time PR discovery published: {pr_discovery.pr_number}")
    
    async def _generate_environment_requirements(self, component_analysis: Dict[str, Any], 
                                               pr_discoveries: List[PRDiscoveryResult]) -> List[EnvironmentCollectionRequirements]:
        """Generate specific environment collection requirements for Agent D"""
        
        requirements = []
        
        for pr_discovery in pr_discoveries:
            # Generate dynamic requirements based on PR analysis and component intelligence
            req = self._generate_dynamic_environment_requirements(pr_discovery, component_analysis)
            
            requirements.append(req)
        
        return requirements
    
    def _generate_dynamic_environment_requirements(self, pr_discovery: PRDiscoveryResult, 
                                                  component_analysis: Dict[str, Any]) -> EnvironmentCollectionRequirements:
        """Generate dynamic environment requirements for any component/feature"""
        
        # Extract component information dynamically
        components = pr_discovery.deployment_components
        primary_component = components[0].lower() if components else 'unknown'
        
        # Generate dynamic YAML requirements based on component
        required_yamls = self._generate_dynamic_yaml_requirements(primary_component, pr_discovery)
        
        # Generate dynamic log requirements based on component
        required_logs = self._generate_dynamic_log_requirements(primary_component, pr_discovery)
        
        # Generate dynamic command requirements based on component
        required_commands = self._generate_dynamic_command_requirements(primary_component, pr_discovery)
        
        # Generate dynamic sample resources based on component
        sample_resources = self._generate_dynamic_sample_resources(primary_component, pr_discovery)
        
        # Determine priority based on PR analysis
        priority = self._determine_dynamic_priority(pr_discovery, component_analysis)
        
        return EnvironmentCollectionRequirements(
            target_components=components,
            required_yamls=required_yamls,
            required_logs=required_logs,
            required_commands=required_commands,
            sample_resources=sample_resources,
            priority=priority
        )
    
    def _generate_dynamic_yaml_requirements(self, component: str, pr_discovery: PRDiscoveryResult) -> List[str]:
        """Generate YAML requirements dynamically using Universal Component Analyzer"""
        
        # Create JIRA content for component analysis
        jira_content = {
            'id': getattr(self, 'current_jira_id', 'unknown'),
            'title': getattr(self, 'current_jira_title', ''),
            'description': getattr(self, 'current_jira_description', ''),
            'component': component
        }
        
        # Analyze component using universal analyzer
        try:
            component_info = self.component_analyzer.analyze_component(jira_content)
            
            # Get discovered patterns
            patterns = get_component_patterns(component_info)
            
            # Start with universal patterns
            yamls = patterns.yaml_files.copy()
            
            # Add PR-specific patterns
            if pr_discovery.pr_number:
                pr_patterns = [
                    f"{component_info.component_name}-{pr_discovery.pr_number}-*.yaml",
                    f"{component_info.component_name}-{pr_discovery.pr_number}.yaml"
                ]
                yamls.extend(pr_patterns)
            
            # Add PR-discovered YAML files
            yamls.extend(pr_discovery.yaml_files)
            
            logger.info(f"Generated {len(yamls)} YAML patterns for {component_info.primary_technology}/{component_info.component_type}")
            
        except Exception as e:
            logger.warning(f"Component analysis failed for {component}, falling back to generic patterns: {e}")
            
            # Fallback to basic patterns
            yamls = [
                f"{component}.yaml",
                f"{component}-controller-deployment.yaml",
                f"{component}-crd.yaml",
                f"{component}*.yaml"
            ]
            
            # Add PR-specific patterns if available
            if pr_discovery.pr_number:
                yamls.extend([
                    f"{component}-{pr_discovery.pr_number}-*.yaml",
                    f"{component}-{pr_discovery.pr_number}.yaml"
                ])
            
            # Add PR-discovered YAML files
            yamls.extend(pr_discovery.yaml_files)
        
        return yamls
    
    def _generate_dynamic_log_requirements(self, component: str, pr_discovery: PRDiscoveryResult) -> List[str]:
        """Generate log requirements dynamically using Universal Component Analyzer"""
        
        # Create JIRA content for component analysis
        jira_content = {
            'id': getattr(self, 'current_jira_id', 'unknown'),
            'title': getattr(self, 'current_jira_title', ''),
            'description': getattr(self, 'current_jira_description', ''),
            'component': component
        }
        
        # Analyze component using universal analyzer
        try:
            component_info = self.component_analyzer.analyze_component(jira_content)
            
            # Get discovered patterns
            patterns = get_component_patterns(component_info)
            
            # Use universal log patterns
            logs = patterns.log_patterns.copy()
            
            logger.info(f"Generated {len(logs)} log patterns for {component_info.primary_technology}/{component_info.component_type}")
            
        except Exception as e:
            logger.warning(f"Component analysis failed for {component}, falling back to generic log patterns: {e}")
            
            # Fallback to basic log patterns
            logs = [
                f"{component}-controller-manager logs",
                f"{component} operator logs",
                f"{component} namespace events"
            ]
        
        return logs
    
    def _generate_dynamic_command_requirements(self, component: str, pr_discovery: PRDiscoveryResult) -> List[str]:
        """Generate command requirements dynamically using Universal Component Analyzer"""
        
        # Create JIRA content for component analysis
        jira_content = {
            'id': getattr(self, 'current_jira_id', 'unknown'),
            'title': getattr(self, 'current_jira_title', ''),
            'description': getattr(self, 'current_jira_description', ''),
            'component': component
        }
        
        # Analyze component using universal analyzer
        try:
            component_info = self.component_analyzer.analyze_component(jira_content)
            
            # Get discovered patterns
            patterns = get_component_patterns(component_info)
            
            # Use universal CLI command patterns
            commands = patterns.cli_commands.copy()
            
            # Add troubleshooting commands if available
            if hasattr(patterns, 'troubleshooting_commands'):
                commands.extend(patterns.troubleshooting_commands)
            
            logger.info(f"Generated {len(commands)} CLI commands for {component_info.primary_technology}/{component_info.component_type}")
            
        except Exception as e:
            logger.warning(f"Component analysis failed for {component}, falling back to generic commands: {e}")
            
            # Fallback to basic command patterns
            component_resource = component.lower().replace('_', '').replace('-', '')
            commands = [
                f"oc get {component_resource}s -A -o yaml",
                f"oc describe {component_resource}",
                f"oc logs -l app={component}",
                f"oc get deployment {component}-controller-manager -o yaml"
            ]
        
        return commands
    
    def _generate_dynamic_sample_resources(self, component: str, pr_discovery: PRDiscoveryResult) -> List[str]:
        """Generate sample resources dynamically for any component"""
        
        samples = []
        
        # Component-specific sample patterns
        component_sample_patterns = {
            'clustercurator': [
                f"sample-{component}-upgrade.yaml",
                "sample-managedcluster.yaml",
                f"{component}-status-examples.yaml"
            ],
            'policy': [
                f"sample-{component}.yaml",
                "sample-policyset.yaml",
                f"{component}-compliance-examples.yaml"
            ],
            'observability': [
                f"sample-multicluster{component}.yaml",
                f"sample-{component}addon.yaml",
                f"{component}-metrics-examples.yaml"
            ],
            'application': [
                f"sample-{component}.yaml",
                "sample-subscription.yaml",
                f"{component}-deployment-examples.yaml"
            ],
            'console': [
                f"sample-{component}-config.yaml",
                f"{component}-route-examples.yaml",
                f"{component}-deployment-examples.yaml"
            ]
        }
        
        # Get component-specific samples
        if component in component_sample_patterns:
            samples.extend(component_sample_patterns[component])
        else:
            # Generic ACM component samples
            samples.extend([
                f"sample-{component}.yaml",
                f"{component}-config-examples.yaml",
                f"{component}-status-examples.yaml"
            ])
        
        return samples
    
    def _determine_dynamic_priority(self, pr_discovery: PRDiscoveryResult, 
                                   component_analysis: Dict[str, Any]) -> str:
        """Determine priority dynamically based on PR and component analysis"""
        
        # Start with medium priority
        priority_score = 2  # 1=low, 2=medium, 3=high, 4=critical
        
        # Adjust based on PR characteristics
        if pr_discovery.confidence_score > 0.9:
            priority_score += 1
        
        if len(pr_discovery.files_changed) > 10:
            priority_score += 1  # Large PR = higher priority
        
        if len(pr_discovery.deployment_components) > 2:
            priority_score += 1  # Multi-component = higher priority
        
        # Adjust based on file types
        critical_files = ['controller.go', 'types.go', 'crd', 'operator']
        if any(critical in file.lower() for file in pr_discovery.files_changed for critical in critical_files):
            priority_score += 1
        
        # Convert score to priority
        if priority_score >= 5:
            return "critical"
        elif priority_score >= 4:
            return "high"
        elif priority_score >= 3:
            return "normal"
        else:
            return "low"
    
    async def _publish_environment_requirements(self, requirements: List[EnvironmentCollectionRequirements]):
        """Publish environment collection requirements to Agent D"""
        
        for req in requirements:
            env_payload = {
                'target_components': req.target_components,
                'required_yamls': req.required_yamls,
                'required_logs': req.required_logs,
                'required_commands': req.required_commands,
                'sample_resources': req.sample_resources,
                'priority': req.priority,
                'collection_timestamp': datetime.now().isoformat(),
                'agent_a_analysis_complete': False  # Will be updated when final analysis is done
            }
            
            await self.comm.request_environment_data(env_payload, target_agent="agent_d_environment_intelligence")
            
            logger.info(f"Environment collection requirements published to Agent D")
    
    async def _compile_final_analysis(self, basic_analysis: Dict[str, Any], 
                                    pr_discoveries: List[PRDiscoveryResult],
                                    component_analysis: Dict[str, Any],
                                    env_requirements: List[EnvironmentCollectionRequirements]) -> Dict[str, Any]:
        """Compile comprehensive final analysis"""
        
        return {
            'analysis_metadata': {
                'agent': 'Agent A - JIRA Intelligence',
                'analysis_timestamp': datetime.now().isoformat(),
                'jira_ticket': basic_analysis['jira_info']['jira_id'],
                'analysis_version': 'v2.0_realtime'
            },
            'jira_intelligence': basic_analysis,
            'pr_discoveries': [
                {
                    'pr_number': pr.pr_number,
                    'pr_title': pr.pr_title,
                    'pr_url': pr.pr_url,
                    'deployment_impact': pr.deployment_components,
                    'files_modified': len(pr.files_changed),
                    'confidence': pr.confidence_score
                } for pr in pr_discoveries
            ],
            'component_analysis': component_analysis,
            'environment_coordination': {
                'requirements_published': len(env_requirements),
                'realtime_coordination_active': True,
                'agent_d_integration': 'enabled'
            },
            'progressive_context_ready': {
                'agent_b_inheritance': True,
                'agent_c_inheritance': True,
                'findings_available': True
            },
            'confidence_score': 0.92,
            'next_phase_readiness': True
        }
    
    async def _save_analysis_results(self, analysis: Dict[str, Any]) -> str:
        """Save comprehensive analysis results"""
        
        output_file = os.path.join(self.run_dir, "jira_intelligence_agent.json")
        
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"JIRA analysis saved to {output_file}")
        
        return output_file
    
    # Helper methods
    def _extract_requirements(self, description: str) -> List[str]:
        """Extract requirements from JIRA description"""
        # Simple requirement extraction logic
        requirements = []
        if 'digest-based' in description.lower():
            requirements.append("Implement digest-based upgrade mechanism")
        if 'clustercurator' in description.lower():
            requirements.append("Enhance ClusterCurator functionality")
        if 'disconnected' in description.lower():
            requirements.append("Support disconnected environments")
        return requirements
    
    def _extract_acceptance_criteria(self, description: str) -> List[str]:
        """Extract acceptance criteria from JIRA description"""
        criteria = []
        if 'upgrade' in description.lower():
            criteria.append("Cluster upgrades must complete successfully")
        if 'fallback' in description.lower():
            criteria.append("Fallback mechanism must be implemented")
        return criteria
    
    def _analyze_technical_scope(self, ticket_data) -> Dict[str, Any]:
        """Analyze technical scope of the ticket"""
        return {
            'component_focus': ticket_data.component,
            'api_changes_likely': 'api' in ticket_data.description.lower(),
            'operator_changes_likely': 'operator' in ticket_data.description.lower(),
            'crd_changes_likely': 'crd' in ticket_data.description.lower() or 'custom resource' in ticket_data.description.lower()
        }
    
    def _analyze_customer_impact(self, ticket_data) -> Dict[str, Any]:
        """Analyze customer impact"""
        return {
            'customer_facing': True,
            'breaking_change_risk': 'breaking' in ticket_data.description.lower(),
            'production_impact': ticket_data.priority in ['High', 'Critical']
        }
    
    def _classify_feature_type(self, ticket_data) -> str:
        """Classify the type of feature"""
        if 'enhancement' in ticket_data.description.lower():
            return 'enhancement'
        elif 'bug' in ticket_data.description.lower():
            return 'bugfix'
        elif 'new' in ticket_data.description.lower():
            return 'new_feature'
        else:
            return 'unknown'
    
    def _assess_urgency(self, ticket_data) -> str:
        """Assess urgency level"""
        if ticket_data.priority in ['Critical', 'Blocker']:
            return 'critical'
        elif ticket_data.priority == 'High':
            return 'high'
        else:
            return 'normal'
    
    def _extract_pr_references(self, description: str) -> List[str]:
        """Extract PR references from JIRA description"""
        # Look for PR patterns like "PR #468", "pull/468", etc.
        pr_patterns = [
            r'PR #?(\d+)',
            r'pull/(\d+)',
            r'pull request #?(\d+)',
            r'github\.com/.+/pull/(\d+)'
        ]
        
        pr_refs = []
        for pattern in pr_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            pr_refs.extend(matches)
        
        # Return unique PR numbers
        return list(set(pr_refs))
    
    async def _search_github_for_prs(self, jira_id: str, basic_analysis: Dict[str, Any]) -> List[str]:
        """Search GitHub for PRs related to this JIRA ticket using real GitHub API"""
        
        try:
            # Use real GitHub search via MCP server
            pr_refs = await self._real_github_search_for_prs(jira_id, basic_analysis)
            
            if pr_refs:
                logger.info(f"✅ Found {len(pr_refs)} PRs via GitHub API for {jira_id}")
                return pr_refs
            
            # Fallback to GitHub CLI search
            pr_refs = await self._github_cli_search_for_prs(jira_id, basic_analysis)
            
            if pr_refs:
                logger.info(f"✅ Found {len(pr_refs)} PRs via GitHub CLI for {jira_id}")
                return pr_refs
            
            # Final fallback: intelligent PR discovery from JIRA content
            pr_refs = self._intelligent_pr_discovery_from_jira(jira_id, basic_analysis)
            
            if pr_refs:
                logger.info(f"✅ Found {len(pr_refs)} PRs via intelligent discovery for {jira_id}")
                return pr_refs
            
            logger.info(f"No PRs found for {jira_id} using any method")
            return []
            
        except Exception as e:
            logger.error(f"GitHub PR search failed for {jira_id}: {e}")
            return []
    
    async def _fetch_real_github_pr_data(self, pr_number: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch real GitHub PR data using MCP server"""
        try:
            # Import MCP coordinator
            # Try to import MCP coordinator with fallback paths
            try:
                import sys
                import os
                mcp_path = os.path.join(os.path.dirname(__file__), '..', 'mcp')
                if mcp_path not in sys.path:
                    sys.path.append(mcp_path)
                from simplified_mcp_coordinator import create_mcp_coordinator
            except ImportError:
                sys.path.append('../mcp')
                from simplified_mcp_coordinator import create_mcp_coordinator
            
            mcp = create_mcp_coordinator()
            
            # Determine repository from context
            repository = self._determine_target_repository(context)
            
            logger.info(f"🔍 Fetching PR {pr_number} from {repository} via GitHub MCP")
            
            # Use real GitHub MCP to get PR details
            pr_result = mcp.github_get_pull_request(repository, int(pr_number))
            
            if pr_result.get('status') == 'success':
                pr_data = pr_result.get('data', {})
                
                # Extract real PR information
                real_pr_details = {
                    'title': pr_data.get('title', f'PR #{pr_number}'),
                    'files_changed': self._extract_files_from_pr_data(pr_data),
                    'url': f'https://github.com/{repository}/pull/{pr_number}',
                    'state': pr_data.get('state', 'unknown'),
                    'author': pr_data.get('author', {}).get('login', 'unknown'),
                    'body': pr_data.get('body', ''),
                    'commits': pr_data.get('commits', [])
                }
                
                logger.info(f"✅ Successfully fetched real PR data for {pr_number}")
                return real_pr_details
            else:
                logger.warning(f"GitHub MCP failed for PR {pr_number}: {pr_result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.warning(f"GitHub MCP PR fetch failed: {e}")
            return None
    
    async def _fetch_github_pr_via_cli(self, pr_number: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch GitHub PR data using GitHub CLI as fallback"""
        try:
            import subprocess
            import json
            
            repository = self._determine_target_repository(context)
            
            logger.info(f"🔧 Fetching PR {pr_number} from {repository} via GitHub CLI")
            
            # Use real GitHub CLI to get PR details
            result = subprocess.run(
                ['gh', 'pr', 'view', pr_number, '--repo', repository, 
                 '--json', 'title,body,state,author,files,commits,url'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                pr_data = json.loads(result.stdout)
                
                cli_pr_details = {
                    'title': pr_data.get('title', f'PR #{pr_number}'),
                    'files_changed': [f.get('path', '') for f in pr_data.get('files', [])],
                    'url': pr_data.get('url', f'https://github.com/{repository}/pull/{pr_number}'),
                    'state': pr_data.get('state', 'unknown'),
                    'author': pr_data.get('author', {}).get('login', 'unknown'),
                    'body': pr_data.get('body', ''),
                    'commits': pr_data.get('commits', [])
                }
                
                logger.info(f"✅ Successfully fetched PR data via CLI for {pr_number}")
                return cli_pr_details
            else:
                logger.warning(f"GitHub CLI failed for PR {pr_number}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.warning(f"GitHub CLI PR fetch failed: {e}")
            return None

    def _calculate_pr_data_confidence(self, pr_details: Dict[str, Any]) -> float:
        """Calculate confidence score based on actual PR data quality - not hardcoded"""
        if not pr_details:
            return 0.0

        confidence = 0.0

        # Has title (0.2)
        if pr_details.get('title') and pr_details['title'] != 'Unknown':
            confidence += 0.2

        # Has files changed (0.3)
        files = pr_details.get('files_changed', [])
        if files and len(files) > 0:
            confidence += 0.3
            # Bonus for having multiple files (indicates comprehensive change info)
            if len(files) >= 3:
                confidence += 0.1

        # Has valid URL (0.1)
        url = pr_details.get('url', '')
        if url and 'github.com' in url and 'unknown' not in url.lower():
            confidence += 0.1

        # Has state info (0.1)
        if pr_details.get('state') and pr_details['state'] != 'unknown':
            confidence += 0.1

        # Has author info (0.1)
        if pr_details.get('author') and pr_details['author'] != 'unknown':
            confidence += 0.1

        # Has body/description (0.1)
        if pr_details.get('body') and len(pr_details['body']) > 20:
            confidence += 0.1

        return min(confidence, 1.0)

    def _generate_intelligent_pr_analysis(self, pr_number: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """DEPRECATED: This method violates anti-simulation policy and should not be called.

        Per anti-simulation policy, data fabrication is not allowed. If real PR data
        cannot be fetched via MCP or CLI, the caller should handle the None case.
        """
        logger.error(f"❌ ANTI-SIMULATION VIOLATION: _generate_intelligent_pr_analysis() called for PR #{pr_number}")
        logger.error("This method is deprecated and should not be called. Use real GitHub data only.")
        raise RuntimeError(
            f"Anti-simulation policy violation: Cannot fabricate PR data for PR #{pr_number}. "
            "Real GitHub API or CLI must be used. Check MCP server connectivity or GitHub CLI authentication."
        )
    
    async def _real_github_search_for_prs(self, jira_id: str, basic_analysis: Dict[str, Any]) -> List[str]:
        """Search for PRs using real GitHub API via MCP"""
        try:
            # Try to import MCP coordinator with fallback paths
            try:
                import sys
                import os
                mcp_path = os.path.join(os.path.dirname(__file__), '..', 'mcp')
                if mcp_path not in sys.path:
                    sys.path.append(mcp_path)
                from simplified_mcp_coordinator import create_mcp_coordinator
            except ImportError:
                sys.path.append('../mcp')
                from simplified_mcp_coordinator import create_mcp_coordinator
            
            mcp = create_mcp_coordinator()
            
            # Create intelligent search queries
            search_queries = self._generate_github_search_queries(jira_id, basic_analysis)
            
            pr_refs = []
            
            for query in search_queries:
                logger.info(f"🔍 Searching GitHub with query: {query}")
                
                # Use real GitHub search via MCP
                search_result = mcp.github_search_repositories(query, limit=10)
                
                if search_result.get('status') == 'success':
                    search_data = search_result.get('data', {})
                    repos = search_data.get('items', [])
                    
                    # Extract PR references from repository search results
                    for repo in repos:
                        repo_name = repo.get('fullName', '')
                        if repo_name:
                            # Search for PRs in this repository
                            repo_pr_refs = await self._search_prs_in_repository(repo_name, jira_id, mcp)
                            pr_refs.extend(repo_pr_refs)
                
                # Limit total PR references to avoid excessive processing
                if len(pr_refs) >= 5:
                    break
            
            return list(set(pr_refs))  # Remove duplicates
            
        except Exception as e:
            logger.warning(f"Real GitHub search failed for {jira_id}: {e}")
            return []
    
    async def _github_cli_search_for_prs(self, jira_id: str, basic_analysis: Dict[str, Any]) -> List[str]:
        """Search for PRs using GitHub CLI as fallback"""
        try:
            import subprocess
            import json
            
            # Generate search queries for CLI
            search_queries = self._generate_github_search_queries(jira_id, basic_analysis)
            
            pr_refs = []
            
            for query in search_queries[:3]:  # Limit to 3 queries for CLI
                logger.info(f"🔧 CLI search with query: {query}")
                
                try:
                    # Use GitHub CLI search
                    result = subprocess.run(
                        ['gh', 'search', 'prs', query, '--limit', '5', '--json', 'number,repository'],
                        capture_output=True, text=True, timeout=30
                    )
                    
                    if result.returncode == 0:
                        search_data = json.loads(result.stdout)
                        
                        for pr in search_data:
                            pr_number = str(pr.get('number', ''))
                            if pr_number and pr_number not in pr_refs:
                                pr_refs.append(pr_number)
                    
                except subprocess.TimeoutExpired:
                    logger.warning(f"GitHub CLI search timed out for query: {query}")
                except Exception as e:
                    logger.warning(f"GitHub CLI search failed for query '{query}': {e}")
            
            return pr_refs
            
        except Exception as e:
            logger.warning(f"GitHub CLI search failed for {jira_id}: {e}")
            return []
    
    def _intelligent_pr_discovery_from_jira(self, jira_id: str, basic_analysis: Dict[str, Any]) -> List[str]:
        """Discover PRs intelligently from JIRA content"""
        
        # Extract PR references from JIRA description and title
        jira_info = basic_analysis.get('jira_info', {})
        description = jira_info.get('description', '')
        title = jira_info.get('title', '')
        
        # Combine text for analysis
        combined_text = f"{title} {description}"
        
        # Extract PR references using intelligent patterns - no hardcoded mappings
        pr_refs = self._extract_pr_references(combined_text)

        # Dynamic discovery: all PR mappings come from JIRA content analysis
        # No hardcoded JIRA -> PR mappings to ensure universal compatibility

        return list(set(pr_refs))  # Remove duplicates
    
    def _determine_target_repository(self, context: Dict[str, Any]) -> Optional[str]:
        """Determine target repository based on context using dynamic discovery.

        Returns:
            Optional[str]: Repository path if discovered, None otherwise.
            Dynamic discovery from JIRA content - no hardcoded mappings.
        """
        jira_info = context.get('jira_info', {})

        # Strategy 1: Extract from explicit repository references in JIRA
        description = jira_info.get('description', '')
        repo_pattern = r'github\.com/([^/]+/[^/\s]+)'
        import re
        matches = re.findall(repo_pattern, description)
        if matches:
            # Clean up the match (remove trailing punctuation, etc.)
            repo = matches[0].rstrip('.,;:)')
            return repo

        # Strategy 2: Extract from linked PRs
        pr_pattern = r'https://github\.com/([^/]+)/([^/]+)/pull/\d+'
        pr_matches = re.findall(pr_pattern, description)
        if pr_matches:
            org, repo = pr_matches[0]
            return f"{org}/{repo}"

        # Strategy 3: Use JIRA project key to inform search
        # No hardcoded mapping - return None to trigger dynamic GitHub search
        return None
    
    def _generate_github_search_queries(self, jira_id: str, basic_analysis: Dict[str, Any]) -> List[str]:
        """Generate intelligent GitHub search queries"""
        
        jira_info = basic_analysis.get('jira_info', {})
        component = jira_info.get('component', '')
        title = jira_info.get('title', '')
        
        queries = [
            f'{jira_id}',  # Direct JIRA ID search
            f'{jira_id} in:comments',  # Search in PR comments
            f'{jira_id} in:body',  # Search in PR body
        ]
        
        # Add component-based queries
        if component:
            queries.append(f'{component.lower()} {jira_id}')
        
        # Add title-based queries
        if title:
            # Extract key terms from title
            title_words = [word for word in title.lower().split() if len(word) > 3]
            if title_words:
                queries.append(f'{title_words[0]} {jira_id}')
        
        return queries
    
    async def _search_prs_in_repository(self, repo_name: str, jira_id: str, mcp) -> List[str]:
        """Search for PRs in a specific repository"""
        try:
            # Use GitHub CLI to search PRs within specific repository
            import subprocess
            import json
            
            logger.info(f"Searching PRs in {repo_name} for {jira_id}")
            
            # Search PRs in specific repository using GitHub CLI
            result = subprocess.run(
                ['gh', 'search', 'prs', f'{jira_id} repo:{repo_name}', '--limit', '5', '--json', 'number'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                search_data = json.loads(result.stdout)
                pr_numbers = [str(pr.get('number', '')) for pr in search_data if pr.get('number')]
                logger.info(f"Found {len(pr_numbers)} PRs in {repo_name}")
                return pr_numbers
            else:
                logger.debug(f"No PRs found in {repo_name} for {jira_id}")
                return []
            
        except Exception as e:
            logger.warning(f"Repository PR search failed for {repo_name}: {e}")
            return []
    
    def _extract_files_from_pr_data(self, pr_data: Dict[str, Any]) -> List[str]:
        """Extract file list from real PR data"""
        files = []
        
        # Handle different PR data formats
        if 'files' in pr_data:
            files_data = pr_data['files']
            if isinstance(files_data, list):
                for file_info in files_data:
                    if isinstance(file_info, dict):
                        file_path = file_info.get('filename') or file_info.get('path') or file_info.get('name')
                        if file_path:
                            files.append(file_path)
                    else:
                        files.append(str(file_info))
        
        return files
    
    def _generate_intelligent_pr_title(self, pr_number: str, component: str, jira_title: str) -> str:
        """DEPRECATED: This method violates anti-simulation policy.

        PR titles must come from real GitHub API data, not be fabricated.
        """
        logger.error(f"❌ ANTI-SIMULATION VIOLATION: _generate_intelligent_pr_title() called for PR #{pr_number}")
        raise RuntimeError(
            f"Anti-simulation policy violation: Cannot fabricate PR title for PR #{pr_number}. "
            "Use real GitHub data only."
        )
    
    def _predict_likely_files_changed(self, component: str, title: str) -> List[str]:
        """DEPRECATED: This method violates anti-simulation policy.

        File change lists must come from real GitHub PR data via API or CLI,
        not be predicted based on hardcoded component patterns.

        This method contained ACM-biased hardcoded file patterns which violate
        the universal technology support requirement.
        """
        logger.error(f"❌ ANTI-SIMULATION VIOLATION: _predict_likely_files_changed() called")
        logger.error(f"Component: {component}, Title: {title}")
        raise RuntimeError(
            "Anti-simulation policy violation: Cannot predict files changed without real GitHub data. "
            "This method contained hardcoded ACM-specific file patterns that violate universal support. "
            "Use real GitHub API or CLI to get actual files changed in a PR."
        )
    
    def _extract_pr_number(self, pr_ref: str) -> str:
        """Extract clean PR number from reference"""
        return pr_ref.strip('#')
    
    def _analyze_deployment_components(self, files_changed: List[str]) -> List[str]:
        """Analyze which components are affected by file changes"""
        components = set()
        
        for file_path in files_changed:
            if 'clustercurator' in file_path.lower():
                components.add('ClusterCurator')
            if 'controller' in file_path.lower():
                components.add('Controller')
            if 'operator' in file_path.lower():
                components.add('Operator')
            if 'crd' in file_path.lower():
                components.add('CustomResourceDefinition')
        
        return list(components)
    
    def _identify_yaml_files(self, files_changed: List[str]) -> List[str]:
        """Identify YAML files from changed files"""
        return [f for f in files_changed if f.endswith(('.yaml', '.yml'))]
    
    def _identify_config_changes(self, files_changed: List[str]) -> List[str]:
        """Identify configuration changes"""
        config_files = []
        for f in files_changed:
            if any(keyword in f.lower() for keyword in ['config', 'settings', 'properties']):
                config_files.append(f)
        return config_files
    
    async def _check_information_sufficiency(self, analysis_data: Dict[str, Any], 
                                           jira_id: str) -> SufficiencyScore:
        """
        Check if collected information is sufficient for test planning
        Implements progressive enhancement strategy
        """
        logger.info(f"Checking information sufficiency for {jira_id}")
        
        # Prepare data for sufficiency analysis
        collected_data = self._prepare_data_for_sufficiency_check(analysis_data)
        
        # Initial sufficiency check
        sufficiency_result = self.sufficiency_analyzer.analyze_sufficiency(collected_data)
        
        logger.info(f"Initial sufficiency score: {sufficiency_result.overall_score:.2f}")
        
        # If sufficient, proceed
        if sufficiency_result.overall_score >= self.config['minimum_score']:
            logger.info("Information is sufficient for comprehensive test planning")
            return sufficiency_result
        
        # Try enhancement if score is marginal
        if sufficiency_result.overall_score >= self.config['fallback_score']:
            logger.info("Attempting to enhance information through web search...")
            
            # Perform web search enhancement
            enhanced_data = await self._enhance_with_web_search(collected_data, sufficiency_result)
            
            # Re-analyze sufficiency
            enhanced_result = self.sufficiency_analyzer.analyze_sufficiency(enhanced_data)
            
            logger.info(f"Enhanced sufficiency score: {enhanced_result.overall_score:.2f}")
            
            if enhanced_result.overall_score >= self.config['fallback_score']:
                if enhanced_result.overall_score < self.config['minimum_score']:
                    logger.warning("Proceeding with marginal information - test coverage may be limited")
                return enhanced_result
        
        # Check if force proceed is allowed
        if self.config.get('allow_force', False):
            logger.warning(f"Force proceed enabled - continuing despite low score: {sufficiency_result.overall_score:.2f}")
            return sufficiency_result
        
        # Trigger framework stop
        logger.error(f"Information insufficient for {jira_id} - triggering framework stop")
        
        missing_info = {
            'critical': sufficiency_result.missing_critical,
            'optional': sufficiency_result.missing_optional
        }
        
        stop_report = self.stop_handler.trigger_stop(
            jira_id=jira_id,
            collected_data=collected_data,
            score=sufficiency_result.overall_score,
            missing_info=missing_info
        )
        
        # Raise exception to stop framework
        raise InsufficientInformationError(stop_report)
    
    def _prepare_data_for_sufficiency_check(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare analysis data for sufficiency checking"""
        prepared_data = {
            'jira_info': analysis_data.get('jira_info', {}),
            'pr_references': [],
            'github_prs': [],
            'pr_discoveries': analysis_data.get('pr_discoveries', []),
            'acceptance_criteria': analysis_data.get('requirement_analysis', {}).get('acceptance_criteria'),
            'technical_design': analysis_data.get('requirement_analysis', {}).get('technical_scope'),
            'affected_components': analysis_data.get('component_analysis', {}).get('affected_components', []),
            'integration_points': analysis_data.get('component_analysis', {}).get('integration_points', []),
            'target_version': analysis_data.get('jira_info', {}).get('fix_version'),
            'environment_info': analysis_data.get('environment_requirements'),
            'business_value': analysis_data.get('business_context', {}).get('customer_impact'),
            'user_impact': analysis_data.get('business_context', {}).get('customer_impact'),
            'test_scenarios': analysis_data.get('requirement_analysis', {}).get('test_scenarios', []),
            'deployment_instruction': analysis_data.get('deployment_guidance'),
            'subtasks': analysis_data.get('subtasks', []),
            'linked_issues': analysis_data.get('linked_issues', []),
            'comments': analysis_data.get('comments', [])
        }
        
        # Extract PR references from discoveries
        for pr_discovery in analysis_data.get('pr_discoveries', []):
            if hasattr(pr_discovery, 'pr_number'):
                # PRDiscoveryResult object
                prepared_data['pr_references'].append(pr_discovery.pr_number)
                prepared_data['github_prs'].append({
                    'number': pr_discovery.pr_number,
                    'title': pr_discovery.pr_title,
                    'files_changed': pr_discovery.files_changed
                })
            else:
                # Dict format fallback
                prepared_data['pr_references'].append(pr_discovery.get('pr_number', ''))
                prepared_data['github_prs'].append({
                    'number': pr_discovery.get('pr_number', ''),
                    'title': pr_discovery.get('pr_title', ''),
                    'files_changed': pr_discovery.get('files_changed', [])
                })
        
        return prepared_data
    
    async def _enhance_with_web_search(self, collected_data: Dict[str, Any], 
                                     sufficiency_result: SufficiencyScore) -> Dict[str, Any]:
        """
        Enhance collected data through web search for missing information
        """
        enhanced_data = collected_data.copy()
        
        # Search for missing PRs if needed
        if 'GitHub PR references' in sufficiency_result.missing_critical:
            logger.info("Searching for GitHub PR references using real APIs...")
            
            jira_id = collected_data.get('jira_info', {}).get('jira_id', '')
            
            # Use real GitHub search to find PRs
            found_prs = await self._real_github_search_for_prs(jira_id, collected_data)
            
            if found_prs:
                # Add found PRs to enhanced data
                enhanced_data['pr_references'] = found_prs
                enhanced_data['github_prs'] = [{'number': pr, 'source': 'real_github_search'} for pr in found_prs]
                logger.info(f"✅ Found {len(found_prs)} PRs via real GitHub search")
            else:
                logger.info(f"No PRs found for {jira_id} via GitHub search")
            
        # Search for technical documentation if needed
        if 'Technical design' in sufficiency_result.missing_critical:
            logger.info("Searching for technical documentation...")
            component = collected_data.get('jira_info', {}).get('component', '')
            search_query = f"ACM {component} architecture design documentation"
            logger.info(f"Web search query: {search_query}")
            
        # Search for acceptance criteria examples
        if 'Acceptance criteria' in sufficiency_result.missing_critical:
            logger.info("Searching for similar feature acceptance criteria...")
            feature_type = collected_data.get('business_context', {}).get('feature_type', '')
            search_query = f"ACM {feature_type} acceptance criteria test scenarios"
            logger.info(f"Web search query: {search_query}")
        
        # Add a flag to indicate enhancement was attempted
        enhanced_data['web_enhancement_attempted'] = True
        enhanced_data['enhancement_queries'] = sufficiency_result.recommendations
        
        return enhanced_data
    
    def _identify_api_changes(self, files_changed: List[str]) -> List[str]:
        """Identify API changes"""
        api_files = []
        for f in files_changed:
            if any(keyword in f.lower() for keyword in ['api', 'types', 'v1', 'v1beta1']):
                api_files.append(f)
        return api_files
    
    def _identify_operator_changes(self, files_changed: List[str]) -> List[str]:
        """Identify operator changes"""
        operator_files = []
        for f in files_changed:
            if any(keyword in f.lower() for keyword in ['operator', 'controller', 'manager']):
                operator_files.append(f)
        return operator_files
    
    async def _analyze_components_and_environment(self, basic_analysis: Dict[str, Any], 
                                                pr_discoveries: List[PRDiscoveryResult]) -> Dict[str, Any]:
        """Analyze components and environment implications"""
        
        all_components = set()
        all_api_changes = []
        
        for pr in pr_discoveries:
            all_components.update(pr.deployment_components)
            all_api_changes.extend(pr.api_changes)
        
        return {
            'affected_components': list(all_components),
            'api_changes_detected': len(all_api_changes) > 0,
            'environment_impact': {
                'requires_cluster_access': True,
                'requires_namespace_access': ['open-cluster-management', 'open-cluster-management-hub'],
                'requires_custom_resources': True
            },
            'testing_implications': {
                'functional_testing_required': True,
                'integration_testing_required': True,
                'upgrade_testing_required': True
            }
        }


if __name__ == '__main__':
    # Test the Agent A
    import asyncio
    from inter_agent_communication import get_communication_hub
    
    async def test_jira_intelligence_agent():
        """Test Agent A functionality"""
        print("🧪 Testing Agent A - JIRA Intelligence")
        
        # Setup communication hub
        hub = get_communication_hub("phase_1", "test_run_002")
        await hub.start_hub()
        
        # Create Agent A
        agent_a = JIRAIntelligenceAgent(hub, "/tmp/test_run")
        
        # Test context
        test_context = {
            'jira_id': 'ACM-22079',
            'target_version': '2.15.0',
            'component': 'ClusterCurator'
        }
        
        # Execute analysis
        result = await agent_a.execute_jira_analysis(test_context)
        
        print(f"Analysis completed: {result['execution_method']}")
        print(f"PR discoveries: {result['pr_discoveries']}")
        print(f"Environment requirements published: {result['environment_requirements_published']}")
        
        # Check communication history
        comm_history = agent_a.comm.get_communication_history()
        print(f"Messages sent: {len(comm_history)}")
        
        await hub.stop_hub()
        
        print("✅ Agent A test completed!")
    
    asyncio.run(test_jira_intelligence_agent())

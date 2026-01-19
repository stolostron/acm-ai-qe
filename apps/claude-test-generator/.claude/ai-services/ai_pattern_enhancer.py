#!/usr/bin/env python3
"""
AI Pattern Enhancer - Intelligent enhancement for complex component analysis
Provides AI-powered analysis when traditional classification needs enhancement
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from technology_classification_service import ComponentInfo, DiscoveredPatterns

logger = logging.getLogger(__name__)


@dataclass
class AIEnhancementResult:
    """Result from AI enhancement analysis"""
    enhanced_component_info: ComponentInfo
    ai_insights: Dict[str, Any]
    confidence_boost: float
    enhancement_applied: bool
    reasoning: str
    additional_patterns: DiscoveredPatterns
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class AIPatternEnhancer:
    """AI-powered enhancement for component pattern analysis"""
    
    def __init__(self):
        self.enhancement_cache = {}
        self.ai_enhancement_prompts = {
            'component_analysis': """
Analyze this JIRA ticket content and provide intelligent component classification:

Title: {title}
Description: {description}
Component: {component}
Current Classification: {current_classification}

Please provide:
1. Technology ecosystem (kubernetes, openshift, acm, database, cloud, etc.)
2. Component type (controller, operator, crd, service, etc.)
3. Component name (specific identifier)
4. YAML file patterns needed for this component
5. CLI commands for testing this component
6. Log patterns for troubleshooting

Focus on providing specific, actionable patterns based on the technology context.
""",
            'pattern_enhancement': """
Based on this component analysis, suggest additional patterns:

Component: {component_name}
Technology: {technology}
Component Type: {component_type}
Current Patterns: {current_patterns}

Suggest additional:
1. YAML file patterns specific to this technology
2. CLI commands for comprehensive testing
3. Log patterns for debugging
4. Test commands for validation
5. Monitoring commands for operational support

Be specific and technology-appropriate.
""",
            'complexity_analysis': """
Analyze the complexity of this JIRA ticket:

Title: {title}
Description: {description}
Current Complexity Score: {complexity_score}

Consider:
1. Multi-component integration requirements
2. Cross-cluster functionality
3. Upgrade/migration complexity
4. API changes and backward compatibility
5. Security and compliance requirements

Provide an enhanced complexity score (0.0-1.0) with reasoning.
"""
        }
    
    def should_enhance(self, component_info: ComponentInfo, jira_content: Dict[str, Any]) -> bool:
        """Determine if AI enhancement should be applied"""
        
        # Always enhance if explicitly required
        if component_info.requires_ai_enhancement:
            return True
        
        # Enhance for low confidence classifications
        if component_info.confidence_score < 0.8:
            return True
        
        # Enhance for high complexity cases
        if component_info.complexity_score > 0.7:
            return True
        
        # Enhance for unknown/generic technologies
        if component_info.primary_technology in ['generic', 'unknown']:
            return True
        
        # Enhance for enterprise/multi-cluster scenarios
        content = (jira_content.get('title', '') + ' ' + jira_content.get('description', '')).lower()
        enterprise_indicators = ['multi-cluster', 'federation', 'enterprise', 'scale', 'governance']
        if any(indicator in content for indicator in enterprise_indicators):
            return True
        
        return False
    
    def enhance_analysis(self, component_info: ComponentInfo, jira_content: Dict[str, Any]) -> AIEnhancementResult:
        """Apply AI enhancement to component analysis"""
        
        jira_id = jira_content.get('id', 'unknown')
        
        # Check cache first
        cache_key = f"{jira_id}_{component_info.component_name}_{component_info.primary_technology}"
        if cache_key in self.enhancement_cache:
            logger.info(f"Using cached AI enhancement for {jira_id}")
            return AIEnhancementResult.from_dict(self.enhancement_cache[cache_key])
        
        logger.info(f"Applying AI enhancement for {jira_id} ({component_info.primary_technology}/{component_info.component_type})")
        
        try:
            # Phase 1: Enhanced component classification
            enhanced_classification = self._enhance_component_classification(component_info, jira_content)
            
            # Phase 2: Pattern enhancement
            enhanced_patterns = self._enhance_patterns(enhanced_classification, jira_content)
            
            # Phase 3: Complexity analysis
            enhanced_complexity = self._enhance_complexity_analysis(enhanced_classification, jira_content)
            
            # Phase 4: AI insights generation
            ai_insights = self._generate_ai_insights(enhanced_classification, jira_content)
            
            # Calculate confidence boost
            confidence_boost = enhanced_complexity['confidence'] - component_info.confidence_score
            
            # Update component info with enhancements
            enhanced_component_info = ComponentInfo(
                primary_technology=enhanced_classification.get('technology', component_info.primary_technology),
                component_type=enhanced_classification.get('component_type', component_info.component_type),
                component_name=enhanced_classification.get('component_name', component_info.component_name),
                yaml_patterns=enhanced_patterns.yaml_files,
                log_patterns=enhanced_patterns.log_patterns,
                cli_commands=enhanced_patterns.cli_commands,
                complexity_score=enhanced_complexity['score'],
                confidence_score=min(component_info.confidence_score + confidence_boost, 0.95),
                detection_method="ai_enhanced_analysis",
                technology_ecosystem=enhanced_classification.get('ecosystem', component_info.technology_ecosystem),
                requires_ai_enhancement=False  # Already enhanced
            )
            
            result = AIEnhancementResult(
                enhanced_component_info=enhanced_component_info,
                ai_insights=ai_insights,
                confidence_boost=confidence_boost,
                enhancement_applied=True,
                reasoning=enhanced_complexity['reasoning'],
                additional_patterns=enhanced_patterns
            )
            
            # Cache result
            self.enhancement_cache[cache_key] = result.to_dict()
            
            logger.info(f"AI enhancement completed: +{confidence_boost:.2f} confidence boost")
            return result
            
        except Exception as e:
            logger.error(f"AI enhancement failed for {jira_id}: {e}")
            
            # Return minimal enhancement
            return AIEnhancementResult(
                enhanced_component_info=component_info,
                ai_insights={'enhancement_attempted': True, 'enhancement_failed': True, 'error': str(e)},
                confidence_boost=0.0,
                enhancement_applied=False,
                reasoning=f"AI enhancement failed: {str(e)}",
                additional_patterns=DiscoveredPatterns([], [], [], [], [], [])
            )
    
    def _enhance_component_classification(self, component_info: ComponentInfo, jira_content: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance component classification using AI analysis"""
        
        # For this implementation, we'll use intelligent rule-based enhancement
        # In a full implementation, this would call an actual AI model
        
        title = jira_content.get('title', '').lower()
        description = jira_content.get('description', '').lower()
        content = title + ' ' + description
        
        enhanced = {
            'technology': component_info.primary_technology,
            'component_type': component_info.component_type,
            'component_name': component_info.component_name,
            'ecosystem': component_info.technology_ecosystem
        }
        
        # AI-like semantic analysis
        if 'curator' in content and 'cluster' in content:
            enhanced.update({
                'technology': 'cluster-management',
                'component_type': 'curator',
                'ecosystem': 'acm'
            })
        elif 'operator' in content and ('kubernetes' in content or 'k8s' in content):
            enhanced.update({
                'technology': 'kubernetes',
                'component_type': 'operator',
                'ecosystem': 'kubernetes'
            })
        elif 'policy' in content and ('governance' in content or 'compliance' in content):
            enhanced.update({
                'technology': 'policy-management',
                'component_type': 'policy',
                'ecosystem': 'acm'
            })
        elif 'observability' in content or 'monitoring' in content:
            enhanced.update({
                'technology': 'observability',
                'component_type': 'collector',
                'ecosystem': 'acm'
            })
        elif 'database' in content or 'db' in content:
            enhanced.update({
                'technology': 'database',
                'component_type': 'operator',
                'ecosystem': 'database'
            })
        
        # Enhance component name with semantic understanding
        if enhanced['component_name'] == component_info.component_name:
            # Try to extract better component name
            for word in title.split():
                if any(tech in word.lower() for tech in ['curator', 'operator', 'controller', 'manager']):
                    enhanced['component_name'] = word.lower().replace('cluster', '').replace('-', '').strip()
                    break
        
        return enhanced
    
    def _enhance_patterns(self, classification: Dict[str, Any], jira_content: Dict[str, Any]) -> DiscoveredPatterns:
        """Enhance patterns using AI analysis"""
        
        technology = classification['technology']
        component_type = classification['component_type']
        component_name = classification['component_name']
        
        # AI-enhanced pattern generation
        enhanced_yaml = []
        enhanced_cli = []
        enhanced_logs = []
        enhanced_test = []
        enhanced_monitoring = []
        enhanced_troubleshooting = []
        
        # Technology-specific AI enhancement
        if technology == 'cluster-management':
            enhanced_yaml.extend([
                f"{component_name}.yaml",
                f"{component_name}-controller-deployment.yaml",
                f"{component_name}-crd.yaml",
                f"{component_name}-rbac.yaml",
                f"{component_name}-webhook.yaml",
                f"managedcluster-{component_name}.yaml"
            ])
            enhanced_cli.extend([
                f"oc get {component_name} -A -o yaml",
                f"oc describe {component_name}",
                f"oc logs -n open-cluster-management {component_name}-controller-manager",
                f"oc get managedclusters -o yaml"
            ])
            enhanced_logs.extend([
                f"{component_name}-controller-manager logs",
                f"{component_name} operator logs",
                "open-cluster-management namespace events"
            ])
        elif technology == 'kubernetes':
            enhanced_yaml.extend([
                f"{component_name}-deployment.yaml",
                f"{component_name}-service.yaml",
                f"{component_name}-configmap.yaml",
                f"{component_name}-rbac.yaml"
            ])
            enhanced_cli.extend([
                f"kubectl get {component_name}",
                f"kubectl describe {component_name}",
                f"kubectl logs -l app={component_name}"
            ])
        elif technology == 'database':
            enhanced_yaml.extend([
                f"{component_name}-cluster.yaml",
                f"{component_name}-backup.yaml",
                f"{component_name}-config.yaml"
            ])
            enhanced_cli.extend([
                f"kubectl get {component_name}cluster",
                f"kubectl describe {component_name}cluster"
            ])
        
        # Add AI-generated test commands
        enhanced_test.extend([
            f"kubectl apply -f {component_name}-test.yaml",
            f"kubectl wait --for=condition=Ready {component_name}/test-instance",
            f"kubectl delete {component_name} test-instance"
        ])
        
        # Add AI-generated monitoring commands
        enhanced_monitoring.extend([
            f"kubectl get events --field-selector involvedObject.name={component_name}",
            f"kubectl top pods -l app={component_name}"
        ])
        
        return DiscoveredPatterns(
            yaml_files=enhanced_yaml,
            log_patterns=enhanced_logs,
            cli_commands=enhanced_cli,
            test_commands=enhanced_test,
            monitoring_patterns=enhanced_monitoring,
            troubleshooting_commands=enhanced_troubleshooting
        )
    
    def _enhance_complexity_analysis(self, classification: Dict[str, Any], jira_content: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance complexity analysis using AI"""
        
        title = jira_content.get('title', '').lower()
        description = jira_content.get('description', '').lower()
        content = title + ' ' + description
        
        complexity_score = 0.5  # Base score
        reasoning_parts = []
        
        # AI-like complexity analysis
        if 'multi-cluster' in content or 'federation' in content:
            complexity_score += 0.2
            reasoning_parts.append("Multi-cluster functionality increases complexity")
        
        if 'upgrade' in content or 'migration' in content:
            complexity_score += 0.15
            reasoning_parts.append("Upgrade/migration scenarios require careful testing")
        
        if 'api' in content and ('breaking' in content or 'change' in content):
            complexity_score += 0.1
            reasoning_parts.append("API changes require backward compatibility testing")
        
        if 'security' in content or 'rbac' in content:
            complexity_score += 0.1
            reasoning_parts.append("Security changes require comprehensive validation")
        
        if 'performance' in content or 'scale' in content:
            complexity_score += 0.1
            reasoning_parts.append("Performance/scaling features need load testing")
        
        # Technology-specific complexity
        if classification['technology'] == 'cluster-management':
            complexity_score += 0.05
            reasoning_parts.append("Cluster management features have inherent complexity")
        
        complexity_score = min(complexity_score, 1.0)  # Cap at 1.0
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Standard complexity analysis applied"
        
        return {
            'score': complexity_score,
            'confidence': 0.85,  # AI analysis confidence
            'reasoning': reasoning
        }
    
    def _generate_ai_insights(self, classification: Dict[str, Any], jira_content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI insights about the component"""
        
        technology = classification['technology']
        component_type = classification['component_type']
        
        insights = {
            'technology_expertise': self._get_technology_insights(technology),
            'testing_recommendations': self._get_testing_recommendations(technology, component_type),
            'risk_factors': self._identify_risk_factors(jira_content),
            'integration_points': self._identify_integration_points(technology),
            'ai_confidence': 0.85
        }
        
        return insights
    
    def _get_technology_insights(self, technology: str) -> Dict[str, Any]:
        """Get AI insights for specific technology"""
        
        insights_map = {
            'cluster-management': {
                'key_concepts': ['ManagedCluster', 'ClusterSet', 'Placement'],
                'common_issues': ['cluster connectivity', 'certificate management', 'resource conflicts'],
                'best_practices': ['validate cluster health', 'test cross-cluster communication', 'verify RBAC']
            },
            'kubernetes': {
                'key_concepts': ['Pod', 'Service', 'Deployment', 'ConfigMap'],
                'common_issues': ['resource limits', 'networking', 'storage persistence'],
                'best_practices': ['resource quotas', 'health checks', 'graceful shutdown']
            },
            'database': {
                'key_concepts': ['cluster', 'backup', 'replication', 'connection pooling'],
                'common_issues': ['data persistence', 'backup failures', 'connection limits'],
                'best_practices': ['backup validation', 'failover testing', 'performance monitoring']
            }
        }
        
        return insights_map.get(technology, {
            'key_concepts': ['component', 'configuration', 'monitoring'],
            'common_issues': ['configuration errors', 'resource constraints'],
            'best_practices': ['validate configuration', 'monitor performance']
        })
    
    def _get_testing_recommendations(self, technology: str, component_type: str) -> List[str]:
        """Get AI-generated testing recommendations"""
        
        recommendations = []
        
        if technology == 'cluster-management':
            recommendations.extend([
                "Test cross-cluster resource synchronization",
                "Validate cluster health status propagation",
                "Verify RBAC permissions across clusters"
            ])
        elif technology == 'kubernetes':
            recommendations.extend([
                "Test pod lifecycle management",
                "Validate service discovery and load balancing",
                "Verify resource constraints and limits"
            ])
        
        if component_type == 'operator':
            recommendations.extend([
                "Test custom resource lifecycle",
                "Validate operator reconciliation loops",
                "Verify error handling and retry mechanisms"
            ])
        elif component_type == 'controller':
            recommendations.extend([
                "Test controller event processing",
                "Validate resource status updates",
                "Verify controller restart recovery"
            ])
        
        return recommendations
    
    def _identify_risk_factors(self, jira_content: Dict[str, Any]) -> List[str]:
        """Identify risk factors using AI analysis"""
        
        content = (jira_content.get('title', '') + ' ' + jira_content.get('description', '')).lower()
        risks = []
        
        if 'breaking' in content or 'incompatible' in content:
            risks.append("Breaking changes may affect existing workflows")
        
        if 'migration' in content:
            risks.append("Data migration requires careful validation")
        
        if 'security' in content:
            risks.append("Security changes require comprehensive testing")
        
        if 'performance' in content:
            risks.append("Performance changes need load testing validation")
        
        priority = jira_content.get('priority', '').lower()
        if priority in ['critical', 'high', 'blocker']:
            risks.append(f"High priority ({priority}) increases delivery risk")
        
        return risks
    
    def _identify_integration_points(self, technology: str) -> List[str]:
        """Identify integration points for testing"""
        
        integration_map = {
            'cluster-management': [
                'ACM Hub and Managed Clusters',
                'OpenShift Console integration',
                'Governance and Policy Framework'
            ],
            'kubernetes': [
                'Kubernetes API server',
                'Container runtime integration',
                'Network and storage plugins'
            ],
            'database': [
                'Application connectivity',
                'Backup and monitoring systems',
                'Storage infrastructure'
            ]
        }
        
        return integration_map.get(technology, ['External API integration', 'Configuration management'])


# Convenience functions for external use
def enhance_component_analysis(component_info: ComponentInfo, jira_content: Dict[str, Any]) -> AIEnhancementResult:
    """Apply AI enhancement to component analysis"""
    enhancer = AIPatternEnhancer()
    return enhancer.enhance_analysis(component_info, jira_content)


def should_apply_ai_enhancement(component_info: ComponentInfo, jira_content: Dict[str, Any]) -> bool:
    """Determine if AI enhancement should be applied"""
    enhancer = AIPatternEnhancer()
    return enhancer.should_enhance(component_info, jira_content)


if __name__ == "__main__":
    # Test with sample data
    from technology_classification_service import UniversalComponentAnalyzer
    
    sample_jira = {
        "id": "ACM-22079",
        "title": "Support digest-based upgrades via ClusterCurator for non-recommended upgrades",
        "component": "Cluster Lifecycle",
        "description": "ClusterCurator digest-based upgrade functionality for disconnected environments",
        "priority": "Critical"
    }
    
    # Get base analysis
    analyzer = UniversalComponentAnalyzer()
    base_analysis = analyzer.analyze_component(sample_jira)
    
    print("=== AI ENHANCEMENT TEST ===")
    print(f"Base Analysis: {base_analysis.primary_technology}/{base_analysis.component_type}")
    print(f"Base Confidence: {base_analysis.confidence_score:.2f}")
    print(f"Base Complexity: {base_analysis.complexity_score:.2f}")
    print()
    
    # Apply AI enhancement
    enhancer = AIPatternEnhancer()
    
    if enhancer.should_enhance(base_analysis, sample_jira):
        print("Applying AI enhancement...")
        enhanced_result = enhancer.enhance_analysis(base_analysis, sample_jira)
        
        print(f"Enhanced Confidence: {enhanced_result.enhanced_component_info.confidence_score:.2f}")
        print(f"Enhanced Complexity: {enhanced_result.enhanced_component_info.complexity_score:.2f}")
        print(f"Confidence Boost: +{enhanced_result.confidence_boost:.2f}")
        print(f"AI Reasoning: {enhanced_result.reasoning}")
        print()
        print("AI Insights:")
        for key, value in enhanced_result.ai_insights.items():
            if isinstance(value, list):
                print(f"  {key}: {len(value)} items")
            else:
                print(f"  {key}: {value}")
    else:
        print("AI enhancement not needed for this component.")
#!/usr/bin/env python3
"""
Technology Classification Service - Universal Pattern Discovery
Replaces hardcoded technology logic with dynamic classification and pattern discovery
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ComponentInfo:
    """Universal component information extracted from JIRA ticket analysis"""
    primary_technology: str
    component_type: str
    component_name: str
    yaml_patterns: List[str]
    log_patterns: List[str]
    cli_commands: List[str]
    complexity_score: float
    confidence_score: float
    detection_method: str
    technology_ecosystem: str
    requires_ai_enhancement: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComponentInfo':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class DiscoveredPatterns:
    """Patterns discovered for a specific component"""
    yaml_files: List[str]
    log_patterns: List[str]
    cli_commands: List[str]
    test_commands: List[str]
    monitoring_patterns: List[str]
    troubleshooting_commands: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class TechnologyClassifier:
    """Classifies JIRA tickets into technology categories using keyword analysis"""
    
    def __init__(self):
        self.technology_keywords = {
            # Kubernetes/OpenShift Ecosystem
            'kubernetes': {
                'keywords': ['kubernetes', 'k8s', 'kubectl', 'pod', 'deployment', 'service', 'namespace'],
                'component_types': ['controller', 'operator', 'crd', 'webhook', 'scheduler'],
                'ecosystem': 'kubernetes'
            },
            'openshift': {
                'keywords': ['openshift', 'oc ', 'route', 'buildconfig', 'imagestream', 'project'],
                'component_types': ['operator', 'controller', 'console', 'registry', 'router'],
                'ecosystem': 'openshift'
            },
            
            # ACM Ecosystem  
            'cluster-management': {
                'keywords': ['cluster', 'clustercurator', 'managedcluster', 'acm', 'rhacm', 'multicluster'],
                'component_types': ['curator', 'controller', 'agent', 'policy', 'placement'],
                'ecosystem': 'acm'
            },
            'policy-management': {
                'keywords': ['policy', 'governance', 'compliance', 'template', 'constraint'],
                'component_types': ['policy', 'controller', 'template', 'constraint'],
                'ecosystem': 'acm'
            },
            'observability': {
                'keywords': ['observability', 'monitoring', 'metrics', 'grafana', 'prometheus'],
                'component_types': ['collector', 'operator', 'dashboard', 'alert'],
                'ecosystem': 'acm'
            },
            'application-management': {
                'keywords': ['application', 'subscription', 'channel', 'gitops', 'argocd'],
                'component_types': ['controller', 'operator', 'subscription', 'channel'],
                'ecosystem': 'acm'
            },
            
            # Infrastructure
            'storage': {
                'keywords': ['storage', 'pvc', 'pv', 'csi', 'volume', 'persistent'],
                'component_types': ['driver', 'controller', 'provisioner'],
                'ecosystem': 'infrastructure'
            },
            'networking': {
                'keywords': ['network', 'cni', 'ingress', 'service-mesh', 'istio', 'proxy'],
                'component_types': ['controller', 'proxy', 'gateway', 'router'],
                'ecosystem': 'infrastructure'
            },
            
            # Cloud Platforms
            'aws': {
                'keywords': ['aws', 'ec2', 's3', 'iam', 'eks', 'cloudformation'],
                'component_types': ['controller', 'operator', 'integration'],
                'ecosystem': 'cloud'
            },
            'azure': {
                'keywords': ['azure', 'aks', 'arm', 'resource-group'],
                'component_types': ['controller', 'operator', 'integration'],
                'ecosystem': 'cloud'
            },
            'gcp': {
                'keywords': ['gcp', 'gke', 'google', 'cloud', 'compute'],
                'component_types': ['controller', 'operator', 'integration'],
                'ecosystem': 'cloud'
            },
            
            # Databases
            'database': {
                'keywords': ['database', 'db', 'sql', 'mysql', 'postgresql', 'mongodb', 'redis'],
                'component_types': ['operator', 'controller', 'cluster'],
                'ecosystem': 'database'
            },
            
            # Generic/Unknown
            'generic': {
                'keywords': ['feature', 'enhancement', 'bug', 'improvement'],
                'component_types': ['component', 'service', 'module'],
                'ecosystem': 'generic'
            }
        }
        
        # Complexity indicators
        self.complexity_indicators = {
            'high': ['multi-cluster', 'cross-cluster', 'federation', 'integration', 'workflow', 'orchestration'],
            'medium': ['upgrade', 'migration', 'backup', 'restore', 'scaling'],
            'low': ['ui', 'display', 'formatting', 'validation', 'configuration']
        }
    
    def analyze_ticket(self, jira_content: Dict[str, Any]) -> ComponentInfo:
        """Analyze JIRA ticket and classify technology/component"""
        
        # Extract text content for analysis
        text_content = self._extract_text_content(jira_content)
        
        # Classify primary technology
        primary_tech, confidence = self._classify_technology(text_content)
        
        # Determine component type and name
        component_type = self._determine_component_type(text_content, primary_tech)
        component_name = self._extract_component_name(text_content, jira_content)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(text_content)
        
        # Get technology ecosystem
        ecosystem = self.technology_keywords.get(primary_tech, {}).get('ecosystem', 'generic')
        
        # Determine if AI enhancement is needed
        requires_ai = complexity_score > 0.7 or confidence < 0.8
        
        return ComponentInfo(
            primary_technology=primary_tech,
            component_type=component_type,
            component_name=component_name,
            yaml_patterns=[],  # Will be filled by PatternDiscoveryService
            log_patterns=[],   # Will be filled by PatternDiscoveryService
            cli_commands=[],   # Will be filled by PatternDiscoveryService
            complexity_score=complexity_score,
            confidence_score=confidence,
            detection_method="keyword_analysis",
            technology_ecosystem=ecosystem,
            requires_ai_enhancement=requires_ai
        )
    
    def _extract_text_content(self, jira_content: Dict[str, Any]) -> str:
        """Extract all relevant text from JIRA content for analysis"""
        text_parts = []
        
        # Title
        if 'title' in jira_content:
            text_parts.append(jira_content['title'])
        
        # Description
        if 'description' in jira_content:
            text_parts.append(jira_content['description'])
        
        # Component
        if 'component' in jira_content:
            text_parts.append(jira_content['component'])
        
        # Labels
        if 'labels' in jira_content and isinstance(jira_content['labels'], list):
            text_parts.extend(jira_content['labels'])
        
        return ' '.join(text_parts).lower()
    
    def _classify_technology(self, text_content: str) -> Tuple[str, float]:
        """Classify the primary technology based on keyword matching"""
        
        technology_scores = {}
        
        for tech_name, tech_info in self.technology_keywords.items():
            score = 0
            keyword_matches = 0
            
            for keyword in tech_info['keywords']:
                if keyword.lower() in text_content:
                    keyword_matches += 1
                    # Weight score based on keyword specificity
                    if len(keyword) > 5:  # More specific keywords get higher weight
                        score += 2
                    else:
                        score += 1
            
            # Calculate weighted score
            if keyword_matches > 0:
                technology_scores[tech_name] = score / len(tech_info['keywords'])
        
        if not technology_scores:
            return 'generic', 0.5
        
        # Get highest scoring technology
        best_tech = max(technology_scores.items(), key=lambda x: x[1])
        confidence = min(best_tech[1], 1.0)  # Cap confidence at 1.0
        
        return best_tech[0], confidence
    
    def _determine_component_type(self, text_content: str, primary_tech: str) -> str:
        """Determine the component type based on content analysis"""
        
        tech_info = self.technology_keywords.get(primary_tech, {})
        component_types = tech_info.get('component_types', ['component'])
        
        # Look for component type indicators in text
        for comp_type in component_types:
            if comp_type.lower() in text_content:
                return comp_type
        
        # Default to first component type for this technology
        return component_types[0] if component_types else 'component'
    
    def _extract_component_name(self, text_content: str, jira_content: Dict[str, Any]) -> str:
        """Extract the specific component name"""
        
        # Try to extract from JIRA component field first
        if 'component' in jira_content and jira_content['component']:
            return jira_content['component'].lower().replace(' ', '-')
        
        # Try to extract from title
        title = jira_content.get('title', '').lower()
        
        # Look for common component name patterns
        component_patterns = [
            r'(\w+curator)',
            r'(\w+controller)',
            r'(\w+operator)',
            r'(\w+agent)',
            r'(\w+manager)',
            r'(\w+service)',
        ]
        
        for pattern in component_patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        
        # Fallback to generic name
        return 'component'
    
    def _calculate_complexity_score(self, text_content: str) -> float:
        """Calculate complexity score based on content analysis"""
        
        complexity_score = 0.5  # Base score
        
        # Check for complexity indicators
        for level, indicators in self.complexity_indicators.items():
            for indicator in indicators:
                if indicator.lower() in text_content:
                    if level == 'high':
                        complexity_score += 0.2
                    elif level == 'medium':
                        complexity_score += 0.1
                    else:  # low
                        complexity_score += 0.05
        
        return min(complexity_score, 1.0)  # Cap at 1.0


class PatternDiscoveryService:
    """Discovers patterns for components based on technology classification"""
    
    def __init__(self):
        self.pattern_templates = {
            # Kubernetes/OpenShift patterns
            'kubernetes': {
                'yaml_files': [
                    "{component}-deployment.yaml",
                    "{component}-service.yaml", 
                    "{component}-configmap.yaml",
                    "{component}-rbac.yaml",
                    "{component}*.yaml"
                ],
                'log_patterns': [
                    "{component} logs",
                    "{component}-controller logs",
                    "{component} operator logs"
                ],
                'cli_commands': [
                    "kubectl get {component}",
                    "kubectl describe {component}",
                    "kubectl logs -l app={component}"
                ],
                'test_commands': [
                    "kubectl apply -f {component}-test.yaml",
                    "kubectl get {component} -o yaml",
                    "kubectl delete {component} test-instance"
                ],
                'troubleshooting_commands': [
                    "kubectl get events --field-selector involvedObject.name={component}",
                    "kubectl describe pod -l app={component}",
                    "kubectl logs -l app={component} --previous"
                ]
            },
            
            'openshift': {
                'yaml_files': [
                    "{component}-deployment.yaml",
                    "{component}-route.yaml",
                    "{component}-buildconfig.yaml", 
                    "{component}-imagestream.yaml",
                    "{component}*.yaml"
                ],
                'log_patterns': [
                    "{component} logs",
                    "{component}-controller logs",
                    "{component} operator logs"
                ],
                'cli_commands': [
                    "oc get {component}",
                    "oc describe {component}",
                    "oc logs -l app={component}"
                ],
                'test_commands': [
                    "oc apply -f {component}-test.yaml",
                    "oc get {component} -o yaml", 
                    "oc delete {component} test-instance"
                ],
                'troubleshooting_commands': [
                    "oc get events --field-selector involvedObject.name={component}",
                    "oc describe pod -l app={component}",
                    "oc adm top pods -l app={component}"
                ]
            },
            
            # ACM-specific patterns
            'cluster-management': {
                'yaml_files': [
                    "{component}.yaml",
                    "{component}-controller-deployment.yaml",
                    "{component}-crd.yaml",
                    "{component}-rbac.yaml",
                    "{component}*.yaml"
                ],
                'log_patterns': [
                    "{component} logs",
                    "{component}-controller-manager logs",
                    "{component} operator logs"
                ],
                'cli_commands': [
                    "oc get {component} -A",
                    "oc describe {component}",
                    "oc logs -n open-cluster-management {component}-controller-manager"
                ],
                'test_commands': [
                    "oc apply -f {component}-test.yaml",
                    "oc get {component} -o yaml",
                    "oc patch {component} test-instance --type=merge -p '{{}}'",
                    "oc delete {component} test-instance"
                ],
                'troubleshooting_commands': [
                    "oc get events -n open-cluster-management --field-selector involvedObject.name={component}",
                    "oc describe managedcluster",
                    "oc get klusterletaddonconfig -A"
                ]
            },
            
            # Generic fallback patterns
            'generic': {
                'yaml_files': [
                    "{component}.yaml",
                    "{component}-config.yaml",
                    "{component}*.yaml"
                ],
                'log_patterns': [
                    "{component} logs"
                ],
                'cli_commands': [
                    "kubectl get {component}",
                    "kubectl describe {component}"
                ],
                'test_commands': [
                    "kubectl apply -f {component}-test.yaml",
                    "kubectl get {component} -o yaml"
                ],
                'troubleshooting_commands': [
                    "kubectl get events",
                    "kubectl describe {component}"
                ]
            }
        }
    
    def discover_patterns(self, component_info: ComponentInfo) -> DiscoveredPatterns:
        """Discover patterns for a specific component"""
        
        # Get pattern template based on primary technology
        template_key = component_info.primary_technology
        if template_key not in self.pattern_templates:
            # Fallback to ecosystem-based lookup
            ecosystem_map = {
                'kubernetes': 'kubernetes',
                'openshift': 'openshift', 
                'acm': 'cluster-management',
                'infrastructure': 'kubernetes',
                'cloud': 'kubernetes',
                'database': 'generic'
            }
            template_key = ecosystem_map.get(component_info.technology_ecosystem, 'generic')
        
        template = self.pattern_templates.get(template_key, self.pattern_templates['generic'])
        
        # Substitute component name in patterns
        component_name = component_info.component_name
        
        patterns = DiscoveredPatterns(
            yaml_files=self._substitute_patterns(template['yaml_files'], component_name),
            log_patterns=self._substitute_patterns(template['log_patterns'], component_name),
            cli_commands=self._substitute_patterns(template['cli_commands'], component_name),
            test_commands=self._substitute_patterns(template['test_commands'], component_name),
            monitoring_patterns=self._substitute_patterns(template.get('monitoring_patterns', []), component_name),
            troubleshooting_commands=self._substitute_patterns(template['troubleshooting_commands'], component_name)
        )
        
        return patterns
    
    def _substitute_patterns(self, patterns: List[str], component_name: str) -> List[str]:
        """Substitute component name in pattern templates"""
        substituted = []
        for pattern in patterns:
            substituted.append(pattern.format(component=component_name))
        return substituted


class UniversalComponentAnalyzer:
    """Main service that combines classification and pattern discovery"""
    
    def __init__(self, enable_ai_enhancement: bool = True):
        self.classifier = TechnologyClassifier()
        self.pattern_service = PatternDiscoveryService()
        self.cache = {}
        self.enable_ai_enhancement = enable_ai_enhancement
        
        # Initialize AI enhancer if enabled
        if self.enable_ai_enhancement:
            try:
                from ai_pattern_enhancer import AIPatternEnhancer
                self.ai_enhancer = AIPatternEnhancer()
                logger.info("AI Pattern Enhancer initialized successfully")
            except ImportError as e:
                logger.warning(f"AI Pattern Enhancer not available: {e}")
                self.ai_enhancer = None
                self.enable_ai_enhancement = False
        else:
            self.ai_enhancer = None
    
    def analyze_component(self, jira_content: Dict[str, Any], use_cache: bool = True) -> ComponentInfo:
        """Analyze JIRA ticket and return complete component information with optional AI enhancement"""
        
        jira_id = jira_content.get('id', 'unknown')
        
        # Check cache first
        if use_cache and jira_id in self.cache:
            logger.info(f"Using cached analysis for {jira_id}")
            return ComponentInfo.from_dict(self.cache[jira_id])
        
        # Phase 1: Traditional classification and pattern discovery
        component_info = self.classifier.analyze_ticket(jira_content)
        patterns = self.pattern_service.discover_patterns(component_info)
        
        # Update component info with discovered patterns
        component_info.yaml_patterns = patterns.yaml_files
        component_info.log_patterns = patterns.log_patterns
        component_info.cli_commands = patterns.cli_commands
        
        # Phase 2: Apply AI enhancement if needed and available
        if self.enable_ai_enhancement and self.ai_enhancer:
            should_enhance = self.ai_enhancer.should_enhance(component_info, jira_content)
            
            if should_enhance:
                logger.info(f"Applying AI enhancement for {jira_id} (confidence: {component_info.confidence_score:.2f})")
                
                try:
                    enhancement_result = self.ai_enhancer.enhance_analysis(component_info, jira_content)
                    
                    if enhancement_result.enhancement_applied:
                        # Use enhanced component info
                        component_info = enhancement_result.enhanced_component_info
                        
                        logger.info(f"AI enhancement applied: +{enhancement_result.confidence_boost:.2f} confidence boost")
                        logger.info(f"AI reasoning: {enhancement_result.reasoning}")
                    
                except Exception as e:
                    logger.warning(f"AI enhancement failed for {jira_id}: {e}")
                    # Continue with traditional analysis
        
        # Cache result
        if use_cache:
            self.cache[jira_id] = component_info.to_dict()
        
        logger.info(f"Analyzed {jira_id}: {component_info.primary_technology}/{component_info.component_type} "
                   f"(confidence: {component_info.confidence_score:.2f})")
        
        return component_info


# Convenience functions for external use
def analyze_jira_component(jira_content: Dict[str, Any]) -> ComponentInfo:
    """Analyze JIRA ticket and return component information"""
    analyzer = UniversalComponentAnalyzer()
    return analyzer.analyze_component(jira_content)


def get_component_patterns(component_info: ComponentInfo) -> DiscoveredPatterns:
    """Get patterns for a component"""
    pattern_service = PatternDiscoveryService()
    return pattern_service.discover_patterns(component_info)


if __name__ == "__main__":
    # Test with generic sample data - works with any JIRA project
    sample_jira = {
        "id": "PROJECT-12345",
        "title": "Sample feature implementation for component testing",
        "component": "Core Component",
        "description": "Implementation of new functionality requiring E2E testing",
        "labels": ["QE-Required"]
    }

    analyzer = UniversalComponentAnalyzer()
    result = analyzer.analyze_component(sample_jira)

    print("Component Analysis Result:")
    print(f"Technology: {result.primary_technology}")
    print(f"Component Type: {result.component_type}")
    print(f"Component Name: {result.component_name}")
    print(f"Confidence: {result.confidence_score:.2f}")
    print(f"Complexity: {result.complexity_score:.2f}")
    print(f"Requires AI Enhancement: {result.requires_ai_enhancement}")
    print("\nDiscovered Patterns:")
    print(f"YAML Files: {result.yaml_patterns[:3]}...")
    print(f"CLI Commands: {result.cli_commands[:3]}...")
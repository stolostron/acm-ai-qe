"""
Z-Stream Analysis Services Module (v3.5)

Core services for Jenkins pipeline failure data gathering.

Architecture Note (v3.5):
- Cluster investigation service for targeted pod diagnostics
- Feature area service for grounding analysis in feature context
- Feedback service for classification accuracy tracking
- Classification services removed - AI now performs all classification
- Repos cloned to run directory for AI full access
- Services provide FACTUAL DATA only
- Native Claude Code MCP integration for Phase 2 analysis

MCP Note:
- Phase 2 (AI Analysis) uses Claude Code's native MCP integration
- Python MCP clients provide fallback for Phase 1 data gathering
"""

# Jenkins API Client
from .jenkins_api_client import (
    JenkinsAPIClient,
    get_jenkins_api_client,
    is_jenkins_available,
)


from .acm_ui_mcp_client import (
    ACMUIMCPClient,
    ElementInfo,
    SearchResult,
    CNVVersionInfo,
    FleetVirtSelectors,
    get_acm_ui_mcp_client,
    is_acm_ui_mcp_available
)
from .jenkins_intelligence_service import (
    JenkinsIntelligenceService,
    JenkinsIntelligence,
    JenkinsMetadata,
    TestCaseFailure,
    TestReport
)
from .environment_validation_service import (
    EnvironmentValidationService,
    EnvironmentValidationResult,
    ClusterInfo
)
from .repository_analysis_service import (
    RepositoryAnalysisService,
    SelectorHistory
)

from .schema_validation_service import (
    SchemaValidationService,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity
)

# Factual data services (no classification)
from .stack_trace_parser import (
    StackTraceParser,
    StackFrame,
    ParsedStackTrace,
    parse_stack_trace
)

from .timeline_comparison_service import (
    TimelineComparisonService,
    TimelineComparisonResult,
    ElementTimeline,
    SelectorTimeline,
    TimeoutPatternResult
)
from .acm_console_knowledge import ACMConsoleKnowledge

# Component extraction and Knowledge Graph (optional RHACM integration)
from .component_extractor import (
    ComponentExtractor,
    ExtractedComponent
)
from .knowledge_graph_client import (
    KnowledgeGraphClient,
    ComponentInfo,
    DependencyChain,
    get_knowledge_graph_client,
    is_knowledge_graph_available
)

# Cluster Investigation (v3.0)
from .cluster_investigation_service import (
    ClusterInvestigationService,
    ClusterLandscape,
    PodDiagnostics,
    ComponentDiagnostics,
)

# Cluster Health Service (v3.7)
from .cluster_health_service import (
    ClusterHealthService,
    ClusterHealthReport,
    ClusterIdentity,
    HealthFinding,
    SubsystemHealth,
    ManagedClusterHealth,
)

# Feature Area Grounding (v3.0)
from .feature_area_service import (
    FeatureAreaService,
    FeatureGrounding,
    FeatureMapping,
    FeatureGrouping,
)

# Feedback (v3.0)
from .feedback_service import (
    FeedbackService,
    ClassificationFeedback,
    RunFeedback,
)

# Feature Knowledge Playbooks (v3.0)
from .feature_knowledge_service import (
    FeatureKnowledgeService,
    PrerequisiteCheck,
    MatchedFailurePath,
    FeatureReadiness,
)

# Shared utilities
from .shared_utils import (
    # Configuration classes
    TimeoutConfig,
    RepositoryConfig,
    ThresholdConfig,
    TIMEOUTS,
    REPOS,
    THRESHOLDS,
    # Subprocess utilities
    run_subprocess,
    build_curl_command,
    execute_curl,
    # JSON utilities
    parse_json_response,
    safe_json_loads,
    # Dataclass utilities
    dataclass_to_dict,
    # Command validation utilities
    validate_command_readonly,
    # Credential utilities
    get_jenkins_credentials,
    encode_basic_auth,
    get_auth_header,
    # File detection utilities
    TEST_FILE_PATTERNS,
    FRAMEWORK_FILE_PATTERNS,
    SUPPORT_FILE_PATTERNS,
    is_test_file,
    is_framework_file,
    is_support_file,
    # Credential masking
    SENSITIVE_PATTERNS,
    mask_sensitive_value,
    mask_sensitive_dict,
)

__all__ = [
    # Jenkins API Client
    'JenkinsAPIClient',
    'get_jenkins_api_client',
    'is_jenkins_available',
    # ACM UI MCP Client
    'ACMUIMCPClient',
    'ElementInfo',
    'SearchResult',
    'CNVVersionInfo',
    'FleetVirtSelectors',
    'get_acm_ui_mcp_client',
    'is_acm_ui_mcp_available',
    # Jenkins Service
    'JenkinsIntelligenceService',
    'JenkinsIntelligence',
    'JenkinsMetadata',
    'TestCaseFailure',
    'TestReport',
    # Environment Service
    'EnvironmentValidationService',
    'EnvironmentValidationResult',
    'ClusterInfo',
    # Repository Service
    'RepositoryAnalysisService',
    'SelectorHistory',
    # Schema Validation
    'SchemaValidationService',
    'ValidationResult',
    'ValidationIssue',
    'ValidationSeverity',
    # Stack Trace Parser (factual data)
    'StackTraceParser',
    'StackFrame',
    'ParsedStackTrace',
    'parse_stack_trace',
    # Timeline Comparison Service (factual data, no classification)
    'TimelineComparisonService',
    'TimelineComparisonResult',
    'ElementTimeline',
    'SelectorTimeline',
    'TimeoutPatternResult',
    # ACM Console Knowledge
    'ACMConsoleKnowledge',
    # Component Extraction and Knowledge Graph
    'ComponentExtractor',
    'ExtractedComponent',
    'KnowledgeGraphClient',
    'ComponentInfo',
    'DependencyChain',
    'get_knowledge_graph_client',
    'is_knowledge_graph_available',
    # Cluster Investigation (v3.0)
    'ClusterInvestigationService',
    'ClusterLandscape',
    'PodDiagnostics',
    'ComponentDiagnostics',
    # Cluster Health Service (v3.7)
    'ClusterHealthService',
    'ClusterHealthReport',
    'ClusterIdentity',
    'HealthFinding',
    'SubsystemHealth',
    'ManagedClusterHealth',
    # Feature Area Grounding (v3.0)
    'FeatureAreaService',
    'FeatureGrounding',
    'FeatureMapping',
    'FeatureGrouping',
    # Feedback (v3.0)
    'FeedbackService',
    'ClassificationFeedback',
    'RunFeedback',
    # Feature Knowledge Playbooks (v3.0)
    'FeatureKnowledgeService',
    'PrerequisiteCheck',
    'MatchedFailurePath',
    'FeatureReadiness',
    # Configuration Classes
    'TimeoutConfig',
    'RepositoryConfig',
    'ThresholdConfig',
    'TIMEOUTS',
    'REPOS',
    'THRESHOLDS',
    # Shared Utilities
    'run_subprocess',
    'build_curl_command',
    'execute_curl',
    'parse_json_response',
    'safe_json_loads',
    'dataclass_to_dict',
    'validate_command_readonly',
    'get_jenkins_credentials',
    'encode_basic_auth',
    'get_auth_header',
    'TEST_FILE_PATTERNS',
    'FRAMEWORK_FILE_PATTERNS',
    'SUPPORT_FILE_PATTERNS',
    'is_test_file',
    'is_framework_file',
    'is_support_file',
    'SENSITIVE_PATTERNS',
    'mask_sensitive_value',
    'mask_sensitive_dict',
]

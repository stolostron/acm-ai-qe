"""
Z-Stream Analysis Services Module
Core services for Jenkins pipeline failure analysis.
"""

from .jenkins_mcp_client import (
    JenkinsMCPClient,
    get_mcp_client,
    is_mcp_available
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
    RepositoryAnalysisResult,
    TestFileInfo,
    DependencyInfo,
    SelectorHistory
)
from .two_agent_intelligence_framework import (
    TwoAgentIntelligenceFramework,
    InvestigationIntelligenceAgent,
    SolutionIntelligenceAgent,
    ComprehensiveAnalysis,
    InvestigationResult,
    SolutionResult
)
from .evidence_validation_engine import EvidenceValidationEngine
from .report_generator import ReportGenerator
from .schema_validation_service import (
    SchemaValidationService,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity
)

# New services for Approach 3: Hybrid AI + Script
from .stack_trace_parser import (
    StackTraceParser,
    StackFrame,
    ParsedStackTrace,
    parse_stack_trace
)
from .classification_decision_matrix import (
    ClassificationDecisionMatrix,
    Classification,
    FailureType,
    ClassificationScores,
    ClassificationResult,
    classify_failure
)
from .confidence_calculator import (
    ConfidenceCalculator,
    EvidenceCompleteness,
    SourceConsistency,
    ConfidenceBreakdown,
    calculate_confidence
)
from .cross_reference_validator import (
    CrossReferenceValidator,
    ValidationAction,
    ValidationResult as CrossValidationResult,
    CrossValidationReport,
    validate_classification
)
from .evidence_package_builder import (
    EvidencePackageBuilder,
    EvidencePackage,
    TestFailureEvidencePackage,
    FailureEvidence,
    RepositoryEvidence,
    EnvironmentEvidence,
    ConsoleEvidence,
    SelectorEvidence,
    build_evidence_package
)
from .ast_integration_service import (
    ASTIntegrationService,
    ResolvedSelector,
    ImportTrace,
    ASTAnalysisResult,
    create_ast_service
)
from .timeline_comparison_service import (
    TimelineComparisonService,
    TimelineComparisonResult,
    ElementTimeline,
    SelectorTimeline,
    TimeoutPatternResult
)

# Shared utilities
from .shared_utils import (
    # Subprocess utilities
    run_subprocess,
    build_curl_command,
    execute_curl,
    # JSON utilities
    parse_json_response,
    safe_json_loads,
    # Credential utilities
    get_jenkins_credentials,
    encode_basic_auth,
    decode_basic_auth,
    get_auth_header,
    # File detection utilities
    is_test_file,
    is_framework_file,
    detect_test_framework,
    # Dataclass utilities
    dataclass_to_dict,
    # Base class
    ServiceBase,
    # Credential masking
    mask_sensitive_value,
    mask_sensitive_dict,
)

__all__ = [
    # Jenkins MCP Client
    'JenkinsMCPClient',
    'get_mcp_client',
    'is_mcp_available',
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
    'RepositoryAnalysisResult',
    'TestFileInfo',
    'DependencyInfo',
    'SelectorHistory',
    # Framework
    'TwoAgentIntelligenceFramework',
    'InvestigationIntelligenceAgent',
    'SolutionIntelligenceAgent',
    'ComprehensiveAnalysis',
    'InvestigationResult',
    'SolutionResult',
    # Validation & Reporting
    'EvidenceValidationEngine',
    'ReportGenerator',
    # Schema Validation
    'SchemaValidationService',
    'ValidationResult',
    'ValidationIssue',
    'ValidationSeverity',
    # Stack Trace Parser
    'StackTraceParser',
    'StackFrame',
    'ParsedStackTrace',
    'parse_stack_trace',
    # Classification Decision Matrix
    'ClassificationDecisionMatrix',
    'Classification',
    'FailureType',
    'ClassificationScores',
    'ClassificationResult',
    'classify_failure',
    # Confidence Calculator
    'ConfidenceCalculator',
    'EvidenceCompleteness',
    'SourceConsistency',
    'ConfidenceBreakdown',
    'calculate_confidence',
    # Cross-Reference Validator
    'CrossReferenceValidator',
    'ValidationAction',
    'CrossValidationResult',
    'CrossValidationReport',
    'validate_classification',
    # Evidence Package Builder
    'EvidencePackageBuilder',
    'EvidencePackage',
    'TestFailureEvidencePackage',
    'FailureEvidence',
    'RepositoryEvidence',
    'EnvironmentEvidence',
    'ConsoleEvidence',
    'SelectorEvidence',
    'build_evidence_package',
    # AST Integration Service
    'ASTIntegrationService',
    'ResolvedSelector',
    'ImportTrace',
    'ASTAnalysisResult',
    'create_ast_service',
    # Timeline Comparison Service
    'TimelineComparisonService',
    'TimelineComparisonResult',
    'ElementTimeline',
    'SelectorTimeline',
    'TimeoutPatternResult',
    # Shared Utilities
    'run_subprocess',
    'build_curl_command',
    'execute_curl',
    'parse_json_response',
    'safe_json_loads',
    'get_jenkins_credentials',
    'encode_basic_auth',
    'decode_basic_auth',
    'get_auth_header',
    'is_test_file',
    'is_framework_file',
    'detect_test_framework',
    'dataclass_to_dict',
    'ServiceBase',
    'mask_sensitive_value',
    'mask_sensitive_dict',
]

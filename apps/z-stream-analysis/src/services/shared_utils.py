#!/usr/bin/env python3
"""
Shared Utilities Module

Common functions and base classes used across services to eliminate code duplication.
"""

import base64
import json
import logging
import os
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# CENTRALIZED CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class TimeoutConfig:
    """
    Centralized timeout configuration for all services.

    All timeouts are in seconds. Use these constants instead of hardcoding values.
    """
    # Command execution timeouts
    DEFAULT_COMMAND: int = 30       # Default for simple commands
    CONSOLE_LOG_FETCH: int = 60     # Fetching Jenkins console logs (can be large)
    TEST_REPORT_FETCH: int = 45     # Fetching test reports
    API_REQUEST: int = 30           # General API requests

    # Git operations
    GIT_CLONE: int = 180            # Cloning repositories (can be large)
    GIT_LOG: int = 30               # Git log/history queries
    GIT_LS_REMOTE: int = 30         # Branch verification

    # Cluster operations
    CLUSTER_COMMAND: int = 30       # oc/kubectl commands

    # Quick checks (Node.js, CLI availability)
    NODE_VERSION_CHECK: int = 5     # Checking if node is available
    CLI_WHICH_CHECK: int = 5        # Checking if oc/kubectl is available (which command)
    AST_HELPER_CHECK: int = 10      # Checking if AST helper works

    # Subprocess buffer: subprocess timeout = curl --max-time + buffer
    # This ensures curl can complete gracefully before subprocess kills it
    SUBPROCESS_BUFFER: int = 5


# Global timeout instance
TIMEOUTS = TimeoutConfig()


@dataclass
class RepositoryConfig:
    """
    Repository configuration with environment variable overrides.

    Environment Variables:
        Z_STREAM_CONSOLE_REPO_URL: Override console repository URL
        Z_STREAM_KUBEVIRT_REPO_URL: Override kubevirt-plugin repository URL
        Z_STREAM_AUTOMATION_REPOS: JSON dict of repo name -> URL mappings
    """
    # Console repository (stolostron/console)
    CONSOLE_REPO_URL: str = field(
        default_factory=lambda: os.environ.get(
            'Z_STREAM_CONSOLE_REPO_URL',
            'https://github.com/stolostron/console.git'
        )
    )

    # KubeVirt plugin repository (kubevirt-ui/kubevirt-plugin)
    # Used for virtualization feature UI components
    KUBEVIRT_REPO_URL: str = field(
        default_factory=lambda: os.environ.get(
            'Z_STREAM_KUBEVIRT_REPO_URL',
            'https://github.com/kubevirt-ui/kubevirt-plugin.git'
        )
    )

    # Known automation repository mappings
    # Can be overridden with Z_STREAM_AUTOMATION_REPOS env var (JSON)
    KNOWN_REPOS: Dict[str, str] = field(default_factory=lambda: {
        'clc-e2e': 'https://github.com/stolostron/clc-ui-e2e.git',
        'clc-ui-e2e': 'https://github.com/stolostron/clc-ui-e2e.git',
        'console-e2e': 'https://github.com/stolostron/console-e2e.git',
        'acm-e2e': 'https://github.com/stolostron/acm-e2e.git',
        'grc-ui-e2e': 'https://github.com/stolostron/grc-ui-e2e.git',
        'search-e2e': 'https://github.com/stolostron/search-e2e-test.git',
    })

    def __post_init__(self):
        """Load repository overrides from environment."""
        repos_override = os.environ.get('Z_STREAM_AUTOMATION_REPOS')
        if repos_override:
            try:
                override_dict = json.loads(repos_override)
                self.KNOWN_REPOS.update(override_dict)
            except json.JSONDecodeError:
                pass  # Ignore invalid JSON


# Global repository config instance
REPOS = RepositoryConfig()


@dataclass(frozen=True)
class ThresholdConfig:
    """
    Centralized threshold configuration for analysis and classification.

    These values control how the system interprets patterns and calculates confidence.
    """
    # Timeout pattern detection
    MULTIPLE_TIMEOUTS_MIN: int = 2          # Minimum count to consider "multiple"
    MAJORITY_TIMEOUT_PERCENT: float = 50.0  # Percentage to consider "majority"

    # Confidence score thresholds
    HIGH_CONFIDENCE: float = 0.80           # High confidence threshold
    MEDIUM_CONFIDENCE: float = 0.60         # Medium confidence threshold
    LOW_CONFIDENCE: float = 0.50            # Low confidence / UNKNOWN threshold

    # Stack trace limits
    MAX_STACK_FRAMES: int = 20              # Maximum frames to process
    CONSOLE_LOG_SNIPPET_SIZE: int = 2000    # Characters for console snippets

    # Repository analysis limits
    MAX_SELECTORS_PER_FILE: int = 50        # Max selectors to extract per file
    GIT_SHALLOW_CLONE_DEPTH: int = 500      # Depth for shallow clones (500 for better history coverage)


# Global thresholds instance
THRESHOLDS = ThresholdConfig()


# =============================================================================
# SUBPROCESS UTILITIES
# =============================================================================

def run_subprocess(
    cmd: List[str],
    timeout: int = 60,
    cwd: Optional[str] = None,
    check: bool = False,
    capture_output: bool = True,
) -> Tuple[bool, str, str]:
    """
    Execute a subprocess command with standardized error handling.

    Args:
        cmd: Command and arguments as list
        timeout: Timeout in seconds (default 60)
        cwd: Working directory for command
        check: If True, raise on non-zero return code
        capture_output: Capture stdout/stderr

    Returns:
        Tuple of (success, stdout, stderr)
    """
    logger = logging.getLogger(__name__)

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=check,
        )
        return result.returncode == 0, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out after {timeout}s: {' '.join(cmd[:3])}...")
        return False, "", f"Timeout after {timeout} seconds"
    except subprocess.CalledProcessError as e:
        logger.warning(f"Command failed with code {e.returncode}: {' '.join(cmd[:3])}...")
        return False, e.stdout or "", e.stderr or ""
    except FileNotFoundError:
        logger.error(f"Command not found: {cmd[0]}")
        return False, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        logger.error(f"Subprocess error: {e}")
        return False, "", str(e)


def build_curl_command(
    url: str,
    username: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = 30,
    extra_args: Optional[List[str]] = None,
    verify_ssl: bool = False,
) -> List[str]:
    """
    Build a curl command with optional authentication.

    Args:
        url: Target URL
        username: Optional username for basic auth
        token: Optional token/password for basic auth
        timeout: Request timeout in seconds
        extra_args: Additional curl arguments
        verify_ssl: Whether to verify SSL certificates (default False for internal servers)

    Returns:
        List of command arguments
    """
    cmd = ['curl', '-s', '--max-time', str(timeout)]

    # Skip SSL verification for internal servers (common for Jenkins)
    if not verify_ssl:
        cmd.append('-k')

    if username and token:
        cmd.extend(['-u', f'{username}:{token}'])

    if extra_args:
        cmd.extend(extra_args)

    cmd.append(url)
    return cmd


def execute_curl(
    url: str,
    username: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = 30,
    extra_args: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """
    Execute a curl request with authentication.

    Args:
        url: Target URL
        username: Optional username for basic auth
        token: Optional token/password for basic auth
        timeout: Request timeout in seconds
        extra_args: Additional curl arguments

    Returns:
        Tuple of (success, response_body)
    """
    cmd = build_curl_command(url, username, token, timeout, extra_args)
    success, stdout, stderr = run_subprocess(cmd, timeout=timeout + 5)
    return success, stdout


# =============================================================================
# JSON UTILITIES
# =============================================================================

def parse_json_response(
    response: str,
    default: Optional[Any] = None,
) -> Tuple[bool, Any]:
    """
    Parse JSON response with HTML detection and error handling.

    Args:
        response: Raw response string
        default: Default value if parsing fails

    Returns:
        Tuple of (success, parsed_data or default)
    """
    logger = logging.getLogger(__name__)

    if not response or not response.strip():
        return False, default

    # Check for HTML response (common auth failure indicator)
    stripped = response.strip()
    if stripped.startswith('<') or stripped.startswith('<!DOCTYPE'):
        logger.warning("Received HTML response instead of JSON (possible auth failure)")
        return False, default

    try:
        data = json.loads(response)
        return True, data
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return False, default


def safe_json_loads(
    response: str,
    default: Optional[Any] = None,
) -> Any:
    """
    Safely parse JSON, returning default on failure.

    Args:
        response: Raw response string
        default: Default value if parsing fails

    Returns:
        Parsed data or default
    """
    success, data = parse_json_response(response, default)
    return data


# =============================================================================
# CREDENTIAL UTILITIES
# =============================================================================

def get_jenkins_credentials() -> Tuple[Optional[str], Optional[str]]:
    """
    Get Jenkins credentials from environment variables.

    Returns:
        Tuple of (username, api_token)
    """
    username = os.environ.get('JENKINS_USER')
    api_token = os.environ.get('JENKINS_API_TOKEN')
    return username, api_token


def encode_basic_auth(username: str, password: str) -> str:
    """
    Encode credentials as Basic auth header.

    Args:
        username: Username
        password: Password or token

    Returns:
        Basic auth header value (e.g., "Basic base64encoded...")
    """
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def decode_basic_auth(auth_header: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Decode Basic auth header to username and password.

    Args:
        auth_header: Full auth header (e.g., "Basic base64encoded...")

    Returns:
        Tuple of (username, password) or (None, None) on failure
    """
    if not auth_header or not auth_header.startswith('Basic '):
        return None, None

    try:
        encoded = auth_header.split(' ', 1)[1]
        decoded = base64.b64decode(encoded).decode('utf-8')
        if ':' in decoded:
            username, password = decoded.split(':', 1)
            return username, password
    except (IndexError, ValueError, UnicodeDecodeError):
        pass

    return None, None


def get_auth_header() -> Optional[str]:
    """
    Get Basic auth header from environment credentials.

    Returns:
        Basic auth header or None
    """
    username, api_token = get_jenkins_credentials()
    if username and api_token:
        return encode_basic_auth(username, api_token)
    return None


# =============================================================================
# FILE/PATH DETECTION UTILITIES
# =============================================================================

# Common test file patterns
TEST_FILE_PATTERNS = [
    '/tests/', '/test/', '/spec/', '/specs/',
    '_test.', '.test.', '_spec.', '.spec.',
    'test_', 'spec_', '.cy.',
]

# Common framework/library patterns
FRAMEWORK_FILE_PATTERNS = [
    'node_modules/', 'cypress_runner', '/runner/',
    '/packages/cypress/', 'webpack://', 'internal/',
    'site-packages/', 'dist-packages/', '__pycache__/',
    '__cypress', 'bluebird', 'promise',
]

# Common support/helper file patterns
SUPPORT_FILE_PATTERNS = [
    '/support/', '/commands', '/helpers/', '/utils/',
    '/views/', '/pages/', '/fixtures/',
]


def is_test_file(file_path: str) -> bool:
    """
    Check if a file path is a test file.

    Args:
        file_path: File path to check

    Returns:
        True if test file
    """
    path_lower = file_path.lower()
    return any(pattern in path_lower for pattern in TEST_FILE_PATTERNS)


def is_framework_file(file_path: str) -> bool:
    """
    Check if a file path is a framework/library file.

    Args:
        file_path: File path to check

    Returns:
        True if framework file
    """
    path_lower = file_path.lower()
    return any(pattern in path_lower for pattern in FRAMEWORK_FILE_PATTERNS)


def is_support_file(file_path: str) -> bool:
    """
    Check if a file path is a support/helper file.

    Args:
        file_path: File path to check

    Returns:
        True if support file
    """
    path_lower = file_path.lower()
    return any(pattern in path_lower for pattern in SUPPORT_FILE_PATTERNS)


def detect_test_framework(file_path: str) -> Optional[str]:
    """
    Detect the test framework from a file path.

    Args:
        file_path: File path to analyze

    Returns:
        Framework name or None
    """
    path_lower = file_path.lower()

    # Cypress patterns
    if '.cy.' in path_lower or 'cypress/' in path_lower:
        return 'cypress'

    # Jest patterns
    if '.test.' in path_lower or '__tests__' in path_lower:
        return 'jest'

    # Pytest patterns
    if path_lower.endswith('.py') and ('test_' in path_lower or '_test.' in path_lower):
        return 'pytest'

    # Mocha patterns
    if '.spec.' in path_lower:
        return 'mocha'

    return None


# =============================================================================
# DATACLASS UTILITIES
# =============================================================================

def dataclass_to_dict(obj: Any, exclude_none: bool = False) -> Dict[str, Any]:
    """
    Convert a dataclass to dictionary with optional None exclusion.

    Args:
        obj: Dataclass instance
        exclude_none: If True, exclude None values

    Returns:
        Dictionary representation
    """
    if hasattr(obj, '__dataclass_fields__'):
        result = asdict(obj)
        if exclude_none:
            result = {k: v for k, v in result.items() if v is not None}
        return result
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    else:
        return dict(obj) if hasattr(obj, '__iter__') else {}


# =============================================================================
# SERVICE BASE CLASS
# =============================================================================

class ServiceBase:
    """
    Base class for services with common functionality.

    Provides:
    - Standardized logging setup
    - Common utility method access
    - Subprocess execution helpers
    """

    def __init__(self, logger_name: Optional[str] = None):
        """
        Initialize service with logger.

        Args:
            logger_name: Custom logger name (defaults to module name)
        """
        self.logger = logging.getLogger(logger_name or self.__class__.__name__)

    def _run_command(
        self,
        cmd: List[str],
        timeout: int = 60,
        cwd: Optional[str] = None,
    ) -> Tuple[bool, str, str]:
        """
        Run a subprocess command.

        Args:
            cmd: Command and arguments
            timeout: Timeout in seconds
            cwd: Working directory

        Returns:
            Tuple of (success, stdout, stderr)
        """
        return run_subprocess(cmd, timeout, cwd)

    def _curl(
        self,
        url: str,
        username: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 30,
    ) -> Tuple[bool, str]:
        """
        Execute a curl request.

        Args:
            url: Target URL
            username: Optional username
            token: Optional token
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, response_body)
        """
        return execute_curl(url, username, token, timeout)

    def _parse_json(
        self,
        response: str,
        default: Optional[Any] = None,
    ) -> Any:
        """
        Parse JSON response safely.

        Args:
            response: Raw response
            default: Default value on failure

        Returns:
            Parsed data or default
        """
        return safe_json_loads(response, default)


# =============================================================================
# CREDENTIAL MASKING
# =============================================================================

SENSITIVE_PATTERNS = [
    'password', 'token', 'secret', 'key', 'credential',
    'api_key', 'apikey', 'auth', 'bearer',
]


def mask_sensitive_value(value: str, visible_chars: int = 3) -> str:
    """
    Mask a sensitive value, keeping only first few characters visible.

    Args:
        value: Value to mask
        visible_chars: Number of characters to keep visible

    Returns:
        Masked value
    """
    if not value or len(value) <= visible_chars:
        return '***MASKED***'
    return f"{value[:visible_chars]}***MASKED***"


def mask_sensitive_dict(
    data: Dict[str, Any],
    patterns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Recursively mask sensitive values in a dictionary.

    Args:
        data: Dictionary to process
        patterns: Sensitive key patterns (default: SENSITIVE_PATTERNS)

    Returns:
        Dictionary with masked values
    """
    if patterns is None:
        patterns = SENSITIVE_PATTERNS

    result = {}
    for key, value in data.items():
        key_lower = key.lower()

        if any(p in key_lower for p in patterns):
            if isinstance(value, str):
                result[key] = mask_sensitive_value(value)
            else:
                result[key] = '***MASKED***'
        elif isinstance(value, dict):
            result[key] = mask_sensitive_dict(value, patterns)
        elif isinstance(value, list):
            result[key] = [
                mask_sensitive_dict(item, patterns) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result

#!/usr/bin/env python3
"""
Environment Validation Service
Real cluster connectivity and environment testing using oc/kubectl commands

IMPORTANT: This service operates in READ-ONLY mode.
All operations are non-destructive and only query cluster state.

Usage:
    # Option 1: Use target cluster URL with credentials (from Jenkins parameters)
    service = EnvironmentValidationService()
    result = service.validate_environment(
        target_api_url="https://api.cluster.example.com:6443",
        username="kubeadmin",
        password="xxx"
    )

    # Option 2: Use existing kubeconfig context
    service = EnvironmentValidationService(kubeconfig_path="/path/to/kubeconfig")
    result = service.validate_environment()
"""

import json
import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class ClusterInfo:
    """Cluster information from validation"""
    name: str
    api_url: str
    version: str
    platform: str
    connected: bool
    authenticated: bool


@dataclass
class EnvironmentValidationResult:
    """Complete environment validation result"""
    cluster_info: Optional[ClusterInfo]
    cluster_connectivity: bool
    api_accessibility: bool
    service_health: Dict[str, bool]
    namespace_access: Dict[str, bool]
    environment_score: float
    validation_timestamp: float
    validation_errors: List[str]
    target_cluster_used: bool = False  # True if we logged into target cluster


class EnvironmentValidationService:
    """
    Environment Validation Service
    Real-time validation of OpenShift/Kubernetes cluster connectivity and health

    IMPORTANT: All operations are READ-ONLY. This service only queries cluster
    state and never modifies any resources.

    Supported read-only operations:
    - oc login (authentication only)
    - oc cluster-info
    - oc whoami
    - oc get nodes (read)
    - oc get componentstatuses (read)
    - oc get clusteroperators (read)
    - oc auth can-i get pods (permission check)
    - oc api-resources (discovery)
    - oc version
    """

    # Read-only commands whitelist - only these commands are allowed
    ALLOWED_COMMANDS = {
        'login', 'logout', 'whoami', 'cluster-info', 'version',
        'get', 'describe', 'api-resources', 'auth', 'config'
    }

    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        Initialize Environment Validation Service.

        Args:
            kubeconfig_path: Optional path to kubeconfig file.
                           Falls back to KUBECONFIG env var or ~/.kube/config
        """
        self.logger = logging.getLogger(__name__)
        self.kubeconfig = kubeconfig_path or os.environ.get('KUBECONFIG')
        self._temp_kubeconfig = None  # For target cluster login
        self._logged_into_target = False

        # Determine which CLI to use (oc for OpenShift, kubectl for plain k8s)
        self.cli = self._detect_cli()

        if self.kubeconfig:
            self.logger.info(f"Using kubeconfig: {self.kubeconfig}")
        else:
            self.logger.info("Using default kubeconfig (~/.kube/config)")
    
    def _detect_cli(self) -> str:
        """Detect whether to use oc or kubectl"""
        # Try oc first (OpenShift)
        try:
            result = subprocess.run(
                ['which', 'oc'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return 'oc'
        except (subprocess.TimeoutExpired, Exception):
            pass
        
        # Fall back to kubectl
        try:
            result = subprocess.run(
                ['which', 'kubectl'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return 'kubectl'
        except (subprocess.TimeoutExpired, Exception):
            pass
        
        # Default to oc and let it fail if not available
        return 'oc'
    
    def _build_command(self, args: List[str]) -> List[str]:
        """Build command with kubeconfig if specified"""
        cmd = [self.cli]

        # Use temp kubeconfig if we logged into target cluster
        kubeconfig = self._temp_kubeconfig or self.kubeconfig
        if kubeconfig:
            cmd.extend(['--kubeconfig', kubeconfig])

        cmd.extend(args)
        return cmd

    def _validate_command_readonly(self, args: List[str]) -> bool:
        """
        Validate that a command is read-only.

        SECURITY: This enforces read-only mode by only allowing whitelisted commands.

        Args:
            args: Command arguments

        Returns:
            True if command is allowed, False otherwise
        """
        if not args:
            return False

        # Get the primary command (first argument)
        primary_cmd = args[0]

        # Check if it's in the allowed list
        if primary_cmd not in self.ALLOWED_COMMANDS:
            self.logger.warning(f"READ-ONLY VIOLATION: Command '{primary_cmd}' not allowed. "
                              f"Allowed: {self.ALLOWED_COMMANDS}")
            return False

        # Additional checks for specific commands
        if primary_cmd == 'get' or primary_cmd == 'describe':
            # These are always read-only
            return True

        if primary_cmd == 'auth':
            # Only allow 'auth can-i' which is read-only
            if len(args) >= 2 and args[1] == 'can-i':
                return True
            self.logger.warning(f"READ-ONLY VIOLATION: 'auth' only allows 'can-i' subcommand")
            return False

        if primary_cmd == 'config':
            # Only allow read operations on config
            if len(args) >= 2 and args[1] in ('current-context', 'get-contexts', 'view'):
                return True
            self.logger.warning(f"READ-ONLY VIOLATION: 'config' only allows read operations")
            return False

        return True

    def _run_command(self, args: List[str], timeout: int = 30,
                    skip_readonly_check: bool = False) -> Tuple[bool, str, str]:
        """
        Run a CLI command and return result.

        IMPORTANT: All commands are validated for read-only operation unless
        skip_readonly_check is True (used only for login).

        Args:
            args: Command arguments (without the CLI binary)
            timeout: Command timeout in seconds
            skip_readonly_check: Skip read-only validation (for login only)

        Returns:
            Tuple of (success, stdout, stderr)
        """
        # Enforce read-only mode
        if not skip_readonly_check and not self._validate_command_readonly(args):
            return False, '', 'Command blocked: READ-ONLY mode violation'

        cmd = self._build_command(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return result.returncode == 0, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, '', f'Command timed out after {timeout}s'
        except Exception as e:
            return False, '', str(e)

    def login_to_cluster(self, api_url: str, username: str, password: str) -> Tuple[bool, str]:
        """
        Login to a target cluster using oc login.

        Uses --insecure-skip-tls-verify for test environments.
        Creates a temporary kubeconfig to avoid polluting the user's config.

        Args:
            api_url: Cluster API URL (e.g., https://api.cluster.example.com:6443)
            username: Username for authentication
            password: Password for authentication

        Returns:
            Tuple of (success, error_message)
        """
        self.logger.info(f"Logging into target cluster: {api_url}")

        # Create a temporary kubeconfig file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.kubeconfig', prefix='z-stream-')
        os.close(temp_fd)
        self._temp_kubeconfig = temp_path

        # Build login command
        # Note: We use --insecure-skip-tls-verify for test environments
        login_cmd = [
            self.cli,
            'login',
            api_url,
            '--username', username,
            '--password', password,
            '--insecure-skip-tls-verify=true',
            '--kubeconfig', temp_path
        ]

        try:
            # Mask password in logs
            masked_cmd = login_cmd.copy()
            pwd_idx = masked_cmd.index('--password')
            masked_cmd[pwd_idx + 1] = '***'
            self.logger.debug(f"Running: {' '.join(masked_cmd)}")

            result = subprocess.run(
                login_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self._logged_into_target = True
                self.logger.info(f"Successfully logged into: {api_url}")
                return True, ''
            else:
                error = result.stderr.strip() or result.stdout.strip()
                self.logger.error(f"Login failed: {error}")
                self._cleanup_temp_kubeconfig()
                return False, error

        except subprocess.TimeoutExpired:
            self._cleanup_temp_kubeconfig()
            return False, 'Login timed out after 30s'
        except Exception as e:
            self._cleanup_temp_kubeconfig()
            return False, str(e)

    def _cleanup_temp_kubeconfig(self):
        """Clean up temporary kubeconfig file."""
        if self._temp_kubeconfig and os.path.exists(self._temp_kubeconfig):
            try:
                os.remove(self._temp_kubeconfig)
                self.logger.debug(f"Cleaned up temp kubeconfig: {self._temp_kubeconfig}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp kubeconfig: {e}")
            self._temp_kubeconfig = None
            self._logged_into_target = False

    def cleanup(self):
        """Clean up resources (call when done with service)."""
        self._cleanup_temp_kubeconfig()
    
    def validate_environment(self, cluster_name: Optional[str] = None,
                            namespaces: Optional[List[str]] = None,
                            target_api_url: Optional[str] = None,
                            username: Optional[str] = None,
                            password: Optional[str] = None) -> EnvironmentValidationResult:
        """
        Perform comprehensive environment validation.

        IMPORTANT: All operations are READ-ONLY. This method only queries
        cluster state and never modifies any resources.

        Args:
            cluster_name: Expected cluster name (optional, for verification)
            namespaces: List of namespaces to check access for
            target_api_url: Target cluster API URL (from Jenkins parameters)
            username: Username for target cluster authentication
            password: Password for target cluster authentication

        Returns:
            EnvironmentValidationResult: Complete validation result
        """
        self.logger.info("Starting environment validation...")
        validation_timestamp = time.time()
        validation_errors = []
        target_cluster_used = False

        # Step 0: Login to target cluster if credentials provided
        if target_api_url and username and password:
            self.logger.info(f"Target cluster specified: {target_api_url}")
            login_success, login_error = self.login_to_cluster(
                target_api_url, username, password
            )
            if login_success:
                target_cluster_used = True
            else:
                validation_errors.append(f"Failed to login to target cluster: {login_error}")
                self.logger.warning("Falling back to local kubeconfig")

        try:
            # Step 1: Check cluster connectivity
            cluster_info, connected, conn_error = self._check_cluster_connectivity()
            if conn_error:
                validation_errors.append(conn_error)

            # Step 2: Check API accessibility
            api_accessible, api_error = self._check_api_accessibility()
            if api_error:
                validation_errors.append(api_error)

            # Step 3: Check service health
            service_health = self._check_service_health()

            # Step 4: Check namespace access
            namespace_access = {}
            if namespaces and connected:
                namespace_access = self._check_namespace_access(namespaces)

            # Calculate environment score
            score = self._calculate_environment_score(
                connected, api_accessible, service_health, namespace_access
            )

            result = EnvironmentValidationResult(
                cluster_info=cluster_info,
                cluster_connectivity=connected,
                api_accessibility=api_accessible,
                service_health=service_health,
                namespace_access=namespace_access,
                environment_score=score,
                validation_timestamp=validation_timestamp,
                validation_errors=validation_errors,
                target_cluster_used=target_cluster_used
            )

            self.logger.info(f"Environment validation complete. Score: {score:.2f}")
            return result

        finally:
            # Always cleanup temp kubeconfig
            if target_cluster_used:
                self._cleanup_temp_kubeconfig()
    
    def _check_cluster_connectivity(self) -> Tuple[Optional[ClusterInfo], bool, Optional[str]]:
        """Check if we can connect to the cluster"""
        self.logger.debug("Checking cluster connectivity...")
        
        # Try to get cluster info
        success, stdout, stderr = self._run_command(['cluster-info'])
        
        if not success:
            return None, False, f"Cluster connectivity failed: {stderr}"
        
        # Extract API URL from cluster-info
        api_url = ""
        match = re.search(r'https?://[^\s]+', stdout)
        if match:
            api_url = match.group(0)
        
        # Get current context info
        success, context_stdout, _ = self._run_command(['config', 'current-context'])
        context_name = context_stdout.strip() if success else "unknown"
        
        # Get cluster version
        version = self._get_cluster_version()
        
        # Get platform info
        platform = self._get_cluster_platform()
        
        # Check authentication
        authenticated = self._check_authentication()
        
        cluster_info = ClusterInfo(
            name=context_name,
            api_url=api_url,
            version=version,
            platform=platform,
            connected=True,
            authenticated=authenticated
        )
        
        return cluster_info, True, None
    
    def _get_cluster_version(self) -> str:
        """Get cluster version"""
        success, stdout, _ = self._run_command(['version', '--short'])
        if success:
            # Parse version from output
            for line in stdout.split('\n'):
                if 'Server' in line or 'Kubernetes' in line:
                    match = re.search(r'v?(\d+\.\d+\.\d+)', line)
                    if match:
                        return match.group(1)
        
        return "unknown"
    
    def _get_cluster_platform(self) -> str:
        """Get cluster platform (OpenShift, vanilla k8s, etc.)"""
        # Check if it's OpenShift
        success, stdout, _ = self._run_command(['api-resources', '--api-group=config.openshift.io'])
        
        if success and 'config.openshift.io' in stdout:
            return "OpenShift"
        
        return "Kubernetes"
    
    def _check_authentication(self) -> bool:
        """Check if we are authenticated to the cluster"""
        success, stdout, _ = self._run_command(['whoami'])
        return success
    
    def _check_api_accessibility(self) -> Tuple[bool, Optional[str]]:
        """Check if Kubernetes API is accessible"""
        self.logger.debug("Checking API accessibility...")
        
        # Try to get API resources
        success, stdout, stderr = self._run_command(['api-resources', '--cached=false'])
        
        if not success:
            return False, f"API not accessible: {stderr}"
        
        return True, None
    
    def _check_service_health(self) -> Dict[str, bool]:
        """Check health of key cluster services"""
        self.logger.debug("Checking service health...")
        
        health = {
            'api_server': False,
            'etcd': False,
            'scheduler': False,
            'controller_manager': False
        }
        
        # Check if we can get nodes (basic API server check)
        success, _, _ = self._run_command(['get', 'nodes', '--no-headers'])
        health['api_server'] = success
        
        # Check component statuses (if available)
        success, stdout, _ = self._run_command(['get', 'componentstatuses', '-o', 'json'])
        
        if success:
            try:
                data = json.loads(stdout)
                for item in data.get('items', []):
                    name = item.get('metadata', {}).get('name', '')
                    conditions = item.get('conditions', [])
                    
                    is_healthy = any(
                        c.get('type') == 'Healthy' and c.get('status') == 'True'
                        for c in conditions
                    )
                    
                    if 'etcd' in name:
                        health['etcd'] = is_healthy
                    elif 'scheduler' in name:
                        health['scheduler'] = is_healthy
                    elif 'controller-manager' in name:
                        health['controller_manager'] = is_healthy
            except json.JSONDecodeError:
                pass
        
        # For OpenShift, check cluster operators
        if self.cli == 'oc':
            success, stdout, _ = self._run_command(['get', 'clusteroperators', '--no-headers'])
            if success:
                # Check if any operators are degraded
                lines = stdout.strip().split('\n')
                all_healthy = True
                for line in lines:
                    if 'Degraded' in line or 'False' in line:
                        all_healthy = False
                        break
                
                if all_healthy:
                    health['etcd'] = True
                    health['scheduler'] = True
                    health['controller_manager'] = True
        
        return health
    
    def _check_namespace_access(self, namespaces: List[str]) -> Dict[str, bool]:
        """Check access to specified namespaces"""
        self.logger.debug(f"Checking namespace access for: {namespaces}")
        
        access = {}
        
        for ns in namespaces:
            success, _, _ = self._run_command(['auth', 'can-i', 'get', 'pods', '-n', ns])
            access[ns] = success
        
        return access
    
    def _calculate_environment_score(self, connected: bool, api_accessible: bool,
                                     service_health: Dict[str, bool],
                                     namespace_access: Dict[str, bool]) -> float:
        """Calculate overall environment health score"""
        score = 0.0
        
        # Connectivity worth 40%
        if connected:
            score += 0.2
        if api_accessible:
            score += 0.2
        
        # Service health worth 40%
        healthy_services = sum(1 for v in service_health.values() if v)
        total_services = len(service_health)
        if total_services > 0:
            score += 0.4 * (healthy_services / total_services)
        
        # Namespace access worth 20%
        if namespace_access:
            accessible = sum(1 for v in namespace_access.values() if v)
            total = len(namespace_access)
            if total > 0:
                score += 0.2 * (accessible / total)
        else:
            # No namespaces to check, give partial credit
            score += 0.1
        
        return min(score, 1.0)
    
    def check_specific_resource(self, resource_type: str, resource_name: str,
                               namespace: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a specific resource exists and get its details.
        
        Args:
            resource_type: Type of resource (e.g., 'deployment', 'pod')
            resource_name: Name of the resource
            namespace: Namespace (optional, uses default if not specified)
            
        Returns:
            Tuple of (exists, resource_details)
        """
        args = ['get', resource_type, resource_name, '-o', 'json']
        
        if namespace:
            args.extend(['-n', namespace])
        
        success, stdout, stderr = self._run_command(args)
        
        if success:
            try:
                return True, json.loads(stdout)
            except json.JSONDecodeError:
                return True, {'raw': stdout}
        
        return False, {'error': stderr}
    
    def to_dict(self, result: EnvironmentValidationResult) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            'cluster_info': asdict(result.cluster_info) if result.cluster_info else None,
            'cluster_connectivity': result.cluster_connectivity,
            'api_accessibility': result.api_accessibility,
            'service_health': result.service_health,
            'namespace_access': result.namespace_access,
            'environment_score': result.environment_score,
            'validation_timestamp': result.validation_timestamp,
            'validation_errors': result.validation_errors,
            'target_cluster_used': result.target_cluster_used
        }

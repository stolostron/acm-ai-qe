#!/usr/bin/env python3
"""
Environment Assessment Client - Phase 1 Traditional Implementation
Fast, reliable environment detection and assessment with multiple cluster support
"""

import os
import json
import time
import logging
import subprocess
import tempfile
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class EnvironmentAssessmentError(Exception):
    """Base exception for environment assessment errors"""
    pass


class ClusterConnectionError(EnvironmentAssessmentError):
    """Cluster connection errors"""
    pass


class PlatformDetectionError(EnvironmentAssessmentError):
    """Platform detection errors"""
    pass


@dataclass
class EnvironmentAssessmentConfig:
    """Environment assessment configuration with universal tool access"""
    cluster_timeout: int = 30
    health_check_timeout: int = 15
    max_retries: int = 3
    cache_duration: int = 180  # 3 minutes
    # Framework uses deterministic failure handling - no fallback mechanisms
    preferred_tools: List[str] = None
    universal_tool_access: bool = True  # NEW: Enable ANY tool usage ANYWHERE
    custom_tools: List[str] = None       # NEW: Allow custom tool additions
    
    def __post_init__(self):
        if self.preferred_tools is None:
            self.preferred_tools = ['oc', 'kubectl', 'gh', 'curl', 'docker', 'git', 'helm', 'kubectl-kustomize', 'jq', 'yq', 'terraform', 'ansible', 'aws', 'az', 'gcloud']
        if self.custom_tools is None:
            self.custom_tools = []


@dataclass
class EnvironmentData:
    """Standardized environment assessment data"""
    cluster_name: str
    version: str
    api_url: str
    console_url: str
    platform: str
    region: str
    health_status: str
    connectivity_confirmed: bool
    platform_details: Dict[str, Any]
    detection_method: str
    assessment_timestamp: str
    tools_available: Dict[str, bool]
    raw_data: Dict[str, Any] = None
    sample_data: Dict[str, Any] = None  # NEW: Sample YAMLs/logs/outputs for test cases
    
    def __post_init__(self):
        if self.raw_data is None:
            self.raw_data = {}
        if self.sample_data is None:
            self.sample_data = {
                'sample_yamls': {},
                'sample_commands': {},
                'sample_outputs': {},
                'sample_logs': {}
            }


class EnvironmentAssessmentClient:
    """
    Production-ready environment assessment client for Kubernetes/OpenShift clusters
    Provides fast, reliable environment detection and version assessment
    """
    
    def __init__(self, config: EnvironmentAssessmentConfig = None):
        self.config = config or EnvironmentAssessmentConfig()
        self.cache_dir = Path(".claude/cache/environment")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Tool availability detection
        self.available_tools = self._detect_available_tools()
        self.primary_tool = self._select_primary_tool()
        
        logger.info(f"Environment assessment client initialized - Primary tool: {self.primary_tool}")
    
    def _detect_available_tools(self) -> Dict[str, bool]:
        """Detect which CLI tools are available with universal tool access"""
        tools = {}
        
        # Tool-specific commands for detection - EXPANDED for universal access
        tool_commands = {
            'oc': ['version', '--client=true'],
            'kubectl': ['version', '--client=true'],
            'gh': ['version'],
            'curl': ['--version'],
            'docker': ['--version'],
            'git': ['--version'],
            'helm': ['version'],
            'kubectl-kustomize': ['version'],
            'jq': ['--version'],
            'yq': ['--version'],
            'terraform': ['version'],
            'ansible': ['--version'],
            'aws': ['--version'],
            'az': ['version'],
            'gcloud': ['version']
        }
        
        # Detect all preferred tools
        all_tools_to_check = self.config.preferred_tools + self.config.custom_tools
        
        for tool in all_tools_to_check:
            try:
                cmd = tool_commands.get(tool, ['--version'])  # Default to --version
                result = subprocess.run(
                    [tool] + cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                tools[tool] = result.returncode == 0
                if tools[tool]:
                    logger.info(f"✅ {tool} available")
                else:
                    logger.debug(f"❌ {tool} not available (exit code: {result.returncode})")
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                tools[tool] = False
                logger.debug(f"❌ {tool} not available")
        
        # Universal tool access: Allow ANY tool execution if enabled
        if self.config.universal_tool_access:
            logger.info("🌍 Universal tool access enabled - ANY tool can be executed on demand")
        
        return tools
    
    def _select_primary_tool(self) -> Optional[str]:
        """Select the primary tool based on availability and preference"""
        for tool in self.config.preferred_tools:
            if self.available_tools.get(tool, False):
                return tool
        return None
    
    def execute_any_tool(self, tool: str, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """
        Universal tool execution - execute ANY tool ANYWHERE in the workflow
        This enables complete flexibility for any tool usage throughout the framework
        """
        if not self.config.universal_tool_access:
            raise EnvironmentAssessmentError(f"Universal tool access disabled - cannot execute {tool}")
        
        logger.info(f"🌍 Universal tool execution: {tool} {' '.join(args)}")
        
        try:
            result = subprocess.run(
                [tool] + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_result = {
                'tool': tool,
                'args': args,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0,
                'execution_timestamp': datetime.now().isoformat()
            }
            
            if execution_result['success']:
                logger.info(f"✅ {tool} executed successfully")
            else:
                logger.warning(f"⚠️ {tool} execution failed with code {result.returncode}")
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {tool} execution timed out after {timeout}s")
            return {
                'tool': tool,
                'args': args,
                'returncode': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout}s',
                'success': False,
                'execution_timestamp': datetime.now().isoformat(),
                'error': 'timeout'
            }
        except FileNotFoundError:
            logger.error(f"❌ {tool} not found on system")
            return {
                'tool': tool,
                'args': args,
                'returncode': -2,
                'stdout': '',
                'stderr': f'Tool {tool} not found',
                'success': False,
                'execution_timestamp': datetime.now().isoformat(),
                'error': 'tool_not_found'
            }
        except Exception as e:
            logger.error(f"❌ {tool} execution error: {e}")
            return {
                'tool': tool,
                'args': args,
                'returncode': -3,
                'stdout': '',
                'stderr': str(e),
                'success': False,
                'execution_timestamp': datetime.now().isoformat(),
                'error': 'execution_error'
            }
    
    def _fetch_qe6_latest_deployment(self) -> Optional[str]:
        """
        Robust qe6 deployment fetching following setup_clc.sh patterns
        Multi-layered approach with comprehensive fallbacks and validation
        """
        try:
            import requests
            import json
            
            logger.info(f"🚀 Fetching latest qe6 deployment with robust Jenkins patterns...")
            
            # Step 1: Environment name to Jenkins job URL mapping (enterprise pattern)
            job_url = "https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/CI-Jobs/job/deploy-qe6-vmware-ibm"
            logger.info(f"📋 Jenkins job URL: {job_url}")
            
            # Step 2: Get latest successful build URL (robust URL resolution)
            latest_successful_build = f"{job_url}/lastSuccessfulBuild"
            
            # Step 3: Build status awareness - check for stale deployments
            deployment_status = self._check_deployment_staleness(job_url, latest_successful_build)
            if deployment_status.get('is_stale'):
                logger.warning(f"⚠️  BUILD STATUS ALERT:")
                logger.warning(f"  📋 Latest successful build: #{deployment_status.get('successful_build', 'unknown')}")
                logger.warning(f"  🔄 Latest attempted build:  #{deployment_status.get('latest_build', 'unknown')}")
                logger.warning(f"  💡 Using credentials from last successful build - deployment may be stale")
            
            # Step 4: Construct artifact URL with robust URL building
            artifact_url = self._build_robust_artifact_url(latest_successful_build)
            logger.info(f"🎯 Artifact URL: {artifact_url}")
            
            # Step 5: Fetch with multiple fallback strategies (enterprise pattern)
            deployment_json = self._fetch_with_robust_fallbacks(artifact_url)
            if not deployment_json:
                logger.error(f"❌ All fetch attempts failed for {artifact_url}")
                return None
            
            # Step 6: Validate JSON response quality
            if not self._validate_json_response(deployment_json):
                logger.error(f"❌ Invalid or incomplete JSON response")
                return None
            
            logger.info(f"✅ Successfully fetched qe6 deployment JSON")
            
            # Step 7: Parse with multiple methods (jq, python3, fallback)
            deployment_data = self._parse_deployment_json_robust(deployment_json)
            if not deployment_data:
                logger.error(f"❌ Failed to parse deployment JSON with all methods")
                return None
            
            # Step 8: Extract and validate all required values
            extracted_values = self._extract_deployment_values_robust(deployment_data)
            if not extracted_values:
                logger.error(f"❌ Failed to extract required deployment values")
                return None
            
            # Step 9: Store comprehensive deployment data for debugging
            self._cache_qe6_deployment_data_comprehensive(deployment_data, deployment_status, extracted_values)
            
            # Step 10: Format environment string (enterprise format)
            environment_string = f"Console: {extracted_values['console_url']}, Creds: {extracted_values['username']}/{extracted_values['password']}"
            
            logger.info(f"🎯 qe6 deployment successfully parsed:")
            logger.info(f"  🌐 Console: {extracted_values['console_url']}")
            logger.info(f"  👤 User: {extracted_values['username']}")
            logger.info(f"  🔐 Password: [REDACTED]")
            logger.info(f"  🖥️  API: {extracted_values['api_url']}")
            
            return environment_string
            
        except Exception as e:
            logger.warning(f"❌ Robust qe6 deployment fetch failed: {e}")
            logger.info(f"📋 This might be due to:")
            logger.info(f"  - Network connectivity issues")
            logger.info(f"  - Jenkins authentication requirements") 
            logger.info(f"  - Jenkins server maintenance")
            logger.info(f"  - Deployment still in progress")
            return None
    
    def _check_deployment_staleness(self, job_url: str, latest_successful_build: str) -> Dict[str, Any]:
        """Check if latest deployment is stale (enterprise deployment pattern)"""
        try:
            import requests
            
            # Get latest build (any result) for comparison
            latest_build_api = f"{job_url}/lastBuild/api/json?tree=number,result"
            successful_build_api = f"{job_url}/lastSuccessfulBuild/api/json?tree=number,result"
            
            try:
                # Get latest build info
                latest_response = requests.get(latest_build_api, timeout=10, verify=False)
                successful_response = requests.get(successful_build_api, timeout=10, verify=False)
                
                latest_build_info = {}
                successful_build_info = {}
                
                if latest_response.status_code == 200:
                    latest_build_info = latest_response.json()
                
                if successful_response.status_code == 200:
                    successful_build_info = successful_response.json()
                
                latest_build = str(latest_build_info.get('number', ''))
                latest_build_result = latest_build_info.get('result', 'UNKNOWN')
                
                successful_build = str(successful_build_info.get('number', ''))
                successful_build_result = successful_build_info.get('result', 'SUCCESS')
                
                is_stale = (latest_build != successful_build and 
                           latest_build.isdigit() and 
                           successful_build.isdigit() and
                           int(latest_build) > int(successful_build))
                
                return {
                    'is_stale': is_stale,
                    'latest_build': latest_build,
                    'latest_build_result': latest_build_result,
                    'successful_build': successful_build,
                    'successful_build_result': successful_build_result,
                    'jenkins_job_url': job_url,
                    'status': 'checked'
                }
            except Exception as e:
                logger.debug(f"Could not check build staleness: {e}")
            
            return {'is_stale': False, 'status': 'unknown'}
            
        except Exception as e:
            logger.debug(f"Deployment staleness check failed: {e}")
            return {'is_stale': False, 'status': 'error'}
    
    def _build_robust_artifact_url(self, build_url: str) -> str:
        """Build artifact URL with robust URL handling (enterprise pattern)"""
        try:
            # Remove trailing slash
            build_url = build_url.rstrip('/')
            
            # Check if already an artifact URL
            if "/artifact/ocp_credentials/output.json" in build_url:
                return build_url
            
            # Construct artifact URL from build URL
            artifact_url = f"{build_url}/artifact/ocp_credentials/output.json"
            return artifact_url
            
        except Exception as e:
            logger.debug(f"Artifact URL building failed: {e}")
            return f"{build_url}/artifact/ocp_credentials/output.json"
    
    def _fetch_with_robust_fallbacks(self, artifact_url: str) -> Optional[str]:
        """Fetch with multiple fallback strategies (enterprise deployment pattern)"""
        import requests
        
        # Multiple curl strategies from enterprise deployment automation
        strategies = [
            {'verify': False, 'allow_redirects': True, 'timeout': 30},  # Insecure SSL
            {'verify': True, 'allow_redirects': True, 'timeout': 30},   # Secure SSL
            {'verify': False, 'allow_redirects': True, 'timeout': 60}   # Longer timeout
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                logger.debug(f"Fetch attempt {i}: {strategy}")
                response = requests.get(artifact_url, **strategy)
                
                if response.status_code == 200:
                    content = response.text
                    if content and len(content.strip()) > 0:
                        logger.debug(f"✅ Fetch attempt {i} succeeded")
                        return content
                    else:
                        logger.debug(f"❌ Fetch attempt {i} returned empty content")
                else:
                    logger.debug(f"❌ Fetch attempt {i} failed: HTTP {response.status_code}")
                    
            except requests.RequestException as e:
                logger.debug(f"❌ Fetch attempt {i} failed: {e}")
            except Exception as e:
                logger.debug(f"❌ Fetch attempt {i} unexpected error: {e}")
        
        # Final fallback: try view URL variation
        try:
            if "/*view*/" not in artifact_url:
                view_url = artifact_url.replace("/artifact/", "/artifact/*view*/")
                logger.debug(f"Trying view URL variation: {view_url}")
                response = requests.get(view_url, verify=False, timeout=30)
                if response.status_code == 200 and response.text:
                    logger.debug(f"✅ View URL variation succeeded")
                    return response.text
        except Exception as e:
            logger.debug(f"View URL variation failed: {e}")
        
        logger.debug(f"❌ All fetch strategies failed")
        return None
    
    def _validate_json_response(self, json_content: str) -> bool:
        """Validate JSON response quality (enterprise deployment pattern)"""
        try:
            if not json_content or len(json_content.strip()) == 0:
                logger.debug("Empty JSON content")
                return False
            
            # Check for HTML responses (enterprise pattern)
            if any(indicator in json_content.lower() for indicator in ['<html>', 'not found', '404', '<title>', '<body>']):
                logger.debug("JSON content appears to be HTML error page")
                return False
            
            # Try to parse as JSON
            import json
            try:
                json.loads(json_content)
                return True
            except json.JSONDecodeError as e:
                logger.debug(f"JSON parsing failed: {e}")
                return False
                
        except Exception as e:
            logger.debug(f"JSON validation error: {e}")
            return False
    
    def _parse_deployment_json_robust(self, json_content: str) -> Optional[Dict[str, Any]]:
        """Parse JSON with multiple methods (enterprise deployment pattern)"""
        import json
        import tempfile
        import subprocess
        
        # Write to temp file for jq/python3 processing (enterprise pattern)
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(json_content)
                temp_file = f.name
            
            # Method 1: Direct Python JSON parsing
            try:
                parsed_data = json.loads(json_content)
                logger.debug("✅ Direct Python JSON parsing succeeded")
                return parsed_data
            except json.JSONDecodeError as e:
                logger.debug(f"Direct Python parsing failed: {e}")
            
            # Method 2: jq parsing (if available)
            try:
                result = subprocess.run(['jq', '.', temp_file], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    parsed_data = json.loads(result.stdout)
                    logger.debug("✅ jq JSON parsing succeeded") 
                    return parsed_data
            except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError) as e:
                logger.debug(f"jq parsing failed: {e}")
            
            # Method 3: Python3 subprocess parsing (enterprise pattern)
            try:
                python_code = f"""
import json
with open('{temp_file}') as f:
    data = json.load(f)
    print(json.dumps(data))
"""
                result = subprocess.run(['python3', '-c', python_code], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    parsed_data = json.loads(result.stdout)
                    logger.debug("✅ Python3 subprocess parsing succeeded")
                    return parsed_data
            except (subprocess.SubprocessError, json.JSONDecodeError) as e:
                logger.debug(f"Python3 subprocess parsing failed: {e}")
            
            # Cleanup temp file
            try:
                import os
                os.unlink(temp_file)
            except:
                pass
            
            logger.debug("❌ All JSON parsing methods failed")
            return None
            
        except Exception as e:
            logger.debug(f"JSON parsing setup failed: {e}")
            return None
    
    def _extract_deployment_values_robust(self, deployment_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract deployment values with multiple field patterns (enterprise deployment pattern)"""
        try:
            # Field name patterns from enterprise deployment automation (case-insensitive, multiple variations)
            field_patterns = {
                'console_url': ['CONSOLE_URL', 'console_url', 'openshift_console_url', 'hub_console_url'],
                'api_url': ['API_URL', 'api_url', 'openshift_api_url', 'server', 'SERVER', 'hub_api_url'],
                'username': ['USERNAME', 'username', 'USER', 'user', 'admin_user', 'cluster_admin_user'],
                'password': ['PASSWORD', 'password', 'admin_password', 'cluster_admin_password', 'hub_password']
            }
            
            extracted = {}
            
            def get_value_by_patterns(data: Dict[str, Any], patterns: List[str]) -> Optional[str]:
                """Get value using multiple field name patterns"""
                for pattern in patterns:
                    if pattern in data:
                        value = data[pattern]
                        if value and str(value).strip():
                            return str(value).strip()
                
                # Case-insensitive fallback
                data_lower = {k.lower(): v for k, v in data.items()}
                for pattern in patterns:
                    if pattern.lower() in data_lower:
                        value = data_lower[pattern.lower()]
                        if value and str(value).strip():
                            return str(value).strip()
                
                return None
            
            # Extract each required field
            for field_name, patterns in field_patterns.items():
                value = get_value_by_patterns(deployment_data, patterns)
                if value:
                    extracted[field_name] = value
                    logger.debug(f"✅ Extracted {field_name}: {value[:50]}...")
                else:
                    logger.debug(f"❌ Could not extract {field_name} using patterns: {patterns}")
            
            # Validate required fields
            required_fields = ['console_url', 'password']
            missing_fields = [f for f in required_fields if f not in extracted or not extracted[f]]
            
            if missing_fields:
                logger.debug(f"❌ Missing required fields: {missing_fields}")
                logger.debug(f"Available fields in JSON: {list(deployment_data.keys())}")
                return None
            
            # Set defaults and derive missing values
            if 'username' not in extracted:
                extracted['username'] = 'kubeadmin'  # Standard OpenShift admin user
                logger.debug("Using default username: kubeadmin")
            
            if 'api_url' not in extracted and 'console_url' in extracted:
                # Derive API URL from console URL
                console_url = extracted['console_url']
                if 'console-openshift-console.apps.' in console_url:
                    api_url = console_url.replace('console-openshift-console.apps.', 'api.')
                    api_url = api_url.replace('https://console', 'https://api')
                    if not api_url.endswith(':6443'):
                        api_url = api_url.rstrip('/') + ':6443'
                    extracted['api_url'] = api_url
                    logger.debug(f"✅ Derived API URL: {api_url}")
                else:
                    extracted['api_url'] = 'unknown'
            
            return extracted
            
        except Exception as e:
            logger.debug(f"Value extraction failed: {e}")
            return None
    
    def _cache_qe6_deployment_data_comprehensive(self, deployment_data: Dict[str, Any], 
                                               deployment_status: Dict[str, Any], 
                                               extracted_values: Dict[str, str]):
        """Cache comprehensive deployment data (enhanced enterprise deployment pattern)"""
        try:
            cache_file = self.cache_dir / "qe6-deployment-comprehensive.json"
            
            cache_entry = {
                'deployment_data': deployment_data,
                'deployment_status': deployment_status,
                'extracted_values': {k: v if k != 'password' else '[REDACTED]' for k, v in extracted_values.items()},
                'fetched_timestamp': datetime.now().isoformat(),
                'jenkins_source': 'https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/CI-Jobs/job/deploy-qe6-vmware-ibm/lastSuccessfulBuild',
                'fetch_method': 'robust_enterprise_pattern',
                'validation_status': 'comprehensive'
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_entry, f, indent=2)
                
            logger.debug(f"Comprehensive qe6 deployment data cached to {cache_file}")
            
        except Exception as e:
            logger.debug(f"Failed to cache comprehensive qe6 deployment data: {e}")
    
    def _cache_qe6_deployment_data(self, deployment_data: Dict[str, Any]):
        """Cache raw qe6 deployment data for reference and debugging"""
        try:
            cache_file = self.cache_dir / "qe6-deployment.json"
            
            cache_entry = {
                'deployment_data': deployment_data,
                'fetched_timestamp': datetime.now().isoformat(),
                'jenkins_source': 'https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/CI-Jobs/job/deploy-qe6-vmware-ibm/lastSuccessfulBuild'
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_entry, f, indent=2)
                
            logger.debug(f"qe6 deployment data cached to {cache_file}")
            
        except Exception as e:
            logger.debug(f"Failed to cache qe6 deployment data: {e}")
    
    def assess_environment(self, environment: str = None) -> EnvironmentData:
        """
        Deterministic environment assessment with systematic connection logic
        
        Behavior:
        1. Use any environment provided by user
        2. If none provided, fetch latest successful qe6 deployment from Jenkins
        3. Handle build staleness detection and user notification
        4. If environment connection fails, complete workflow without test environment
        """
        
        # Step 1: Determine target environment with deterministic logic
        target_environment, deployment_status = self._determine_target_environment(environment)
        
        # Step 2: Handle build staleness detection (following setup_clc.sh patterns)
        if deployment_status.get('is_stale', False):
            logger.warning(f"")
            logger.warning(f"🚨 BUILD STALENESS DETECTED:")
            logger.warning(f"  📋 Latest successful build: #{deployment_status.get('successful_build', 'unknown')}")
            logger.warning(f"  🔄 Latest attempted build:  #{deployment_status.get('latest_build', 'unknown')}")
            logger.warning(f"")
            logger.warning(f"The latest deployment attempt may have failed.")
            logger.warning(f"Using credentials from last successful build instead.")
            logger.warning(f"⚠️  ENVIRONMENT RISK: Environment may be unstable or outdated.")
            logger.warning(f"")
        
        # Step 3: Attempt deterministic environment connection
        connection_result = self._attempt_deterministic_connection(target_environment, deployment_status)
        
        if connection_result['success']:
            logger.info(f"✅ Successfully connected to target environment: {connection_result['environment_name']}")
            return connection_result['environment_data']
        else:
            # Step 4: Handle connection failure - complete workflow without test environment
            logger.error(f"❌ Failed to connect to target environment: {connection_result['error']}")
            logger.warning(f"")
            logger.warning(f"🚨 ENVIRONMENT CONNECTION FAILURE:")
            logger.warning(f"  🎯 Target: {target_environment[:80]}...")
            logger.warning(f"  ❌ Error: {connection_result['error']}")
            logger.warning(f"  📋 Root Cause: {connection_result.get('root_cause', 'Unknown')}")
            logger.warning(f"")
            logger.warning(f"Framework will complete workflow WITHOUT test environment.")
            logger.warning(f"Final reports will clearly indicate this limitation.")
            logger.warning(f"")
            
            # Return no-environment context for workflow completion
            return self._create_no_environment_context(target_environment, connection_result, deployment_status)
    
    def _determine_target_environment(self, environment: str = None) -> Tuple[str, Dict[str, Any]]:
        """
        Determine target environment with systematic logic
        Returns: (target_environment_string, deployment_status)
        """
        deployment_status = {'is_stale': False, 'source': 'unknown'}
        
        # Step 1: Use user-provided environment if available
        if environment:
            logger.info(f"Using user-provided environment: {environment[:80]}...")
            deployment_status['source'] = 'user_provided'
            return environment, deployment_status
        
        # Step 2: Fetch latest successful qe6 deployment from Jenkins
        logger.info(f"No environment provided - fetching latest successful qe6 deployment from Jenkins")
        
        try:
            # Get Jenkins job URL for qe6
            job_url = "https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/CI-Jobs/job/deploy-qe6-vmware-ibm"
            
            # Check build staleness (setup_clc.sh pattern)
            staleness_status = self._check_deployment_staleness(job_url, f"{job_url}/lastSuccessfulBuild")
            
            # Fetch latest successful deployment
            qe6_deployment = self._fetch_qe6_latest_deployment()
            
            if qe6_deployment:
                logger.info(f"✅ Latest successful qe6 deployment fetched")
                deployment_status.update({
                    'source': 'jenkins_successful',
                    'is_stale': staleness_status.get('is_stale', False),
                    'successful_build': staleness_status.get('successful_build'),
                    'latest_build': staleness_status.get('latest_build'),
                    'deployment_info': qe6_deployment
                })
                return qe6_deployment, deployment_status
            else:
                logger.error(f"❌ Failed to fetch qe6 deployment from Jenkins")
                deployment_status.update({
                    'source': 'jenkins_failed', 
                    'error': 'jenkins_fetch_failed'
                })
                # Fall back to default qe6 URL but mark as problematic
                default_qe6 = 'Console: https://console-openshift-console.apps.qe6-vmware-ibm.install.dev09.red-chesterfield.com'
                return default_qe6, deployment_status
                
        except Exception as e:
            logger.error(f"❌ Error determining target environment: {e}")
            deployment_status.update({
                'source': 'error_fallback',
                'error': str(e)
            })
            # Emergency fallback to default qe6
            default_qe6 = 'Console: https://console-openshift-console.apps.qe6-vmware-ibm.install.dev09.red-chesterfield.com'
            return default_qe6, deployment_status
    
    def _attempt_deterministic_connection(self, target_environment: str, deployment_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt deterministic connection to target environment
        Returns connection result with success status and details
        """
        connection_result = {
            'success': False,
            'environment_name': 'unknown',
            'environment_data': None,
            'error': 'not_attempted',
            'root_cause': 'unknown'
        }
        
        try:
            logger.info(f"🔗 Attempting deterministic connection to target environment")
            
            # Step 1: Parse environment credentials
            credentials = self._parse_environment_credentials(target_environment)
            if not credentials['valid']:
                connection_result.update({
                    'error': 'invalid_credentials',
                    'root_cause': f"Could not parse credentials from: {target_environment[:80]}..."
                })
                return connection_result
            
            # Step 2: Attempt login to target environment
            login_success = self._login_to_target_environment(credentials)
            if not login_success['success']:
                connection_result.update({
                    'error': 'login_failed',
                    'root_cause': login_success.get('error', 'Unknown login error'),
                    'stale_deployment': deployment_status.get('is_stale', False)
                })
                return connection_result
            
            # Step 3: Verify connection and assess environment
            logger.info(f"✅ Successfully logged into target environment, performing assessment")
            env_data = self._perform_connected_assessment(credentials['cluster_name'], deployment_status)
            
            if env_data:
                connection_result.update({
                    'success': True,
                    'environment_name': credentials['cluster_name'],
                    'environment_data': env_data,
                    'login_method': login_success.get('method', 'unknown')
                })
            else:
                connection_result.update({
                    'error': 'assessment_failed',
                    'root_cause': 'Connected but environment assessment failed'
                })
            
            return connection_result
            
        except Exception as e:
            logger.error(f"❌ Deterministic connection attempt failed: {e}")
            connection_result.update({
                'error': 'connection_exception',
                'root_cause': str(e)
            })
            return connection_result
    
    def _parse_environment_credentials(self, environment_string: str) -> Dict[str, Any]:
        """Parse environment string to extract connection credentials"""
        import re
        
        result = {
            'valid': False,
            'console_url': None,
            'username': None, 
            'password': None,
            'cluster_name': None,
            'api_url': None
        }
        
        try:
            # Handle format: "Console: https://..., Creds: user/pass"
            if 'Console:' in environment_string and ('Creds:' in environment_string or 'password:' in environment_string):
                
                # Extract console URL
                console_match = re.search(r'Console:\s*([^,]+)', environment_string)
                if console_match:
                    result['console_url'] = console_match.group(1).strip()
                
                # Extract credentials - multiple formats
                if 'Creds:' in environment_string:
                    creds_match = re.search(r'Creds:\s*([^/]+)/([^,\s]+)', environment_string)
                    if creds_match:
                        result['username'] = creds_match.group(1).strip()
                        result['password'] = creds_match.group(2).strip()
                elif 'password:' in environment_string:
                    # Format: "username password: password"
                    parts = environment_string.split('password:')
                    if len(parts) == 2:
                        username_part = parts[0].replace('Console:', '').split()[-1]
                        result['username'] = username_part.strip()
                        result['password'] = parts[1].strip()
                
                # Extract cluster name and API URL from console URL
                if result['console_url']:
                    cluster_match = re.search(r'console-openshift-console\.apps\.([^/]+)', result['console_url'])
                    if cluster_match:
                        full_domain = cluster_match.group(1)
                        cluster_name = full_domain.split('.')[0]
                        result['cluster_name'] = cluster_name
                        result['api_url'] = f"https://api.{full_domain}:6443"
                
                # Validate completeness
                if result['console_url'] and result['username'] and result['password'] and result['cluster_name']:
                    result['valid'] = True
                    logger.info(f"✅ Parsed credentials for cluster: {result['cluster_name']}")
                else:
                    logger.warning(f"⚠️ Incomplete credential parsing from: {environment_string[:80]}...")
            else:
                logger.warning(f"⚠️ Unrecognized environment format: {environment_string[:80]}...")
                
        except Exception as e:
            logger.error(f"❌ Error parsing environment credentials: {e}")
            
        return result
    
    def _login_to_target_environment(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Login to target environment using parsed credentials"""
        import subprocess
        
        result = {
            'success': False,
            'method': 'unknown',
            'error': 'not_attempted'
        }
        
        if not self.available_tools.get('oc', False):
            result['error'] = 'oc_cli_not_available'
            return result
        
        try:
            # Logout from any existing session first
            subprocess.run(['oc', 'logout'], capture_output=True, timeout=10)
            
            # Attempt login with credentials
            login_cmd = [
                'oc', 'login',
                '--insecure-skip-tls-verify',
                '-u', credentials['username'],
                '-p', credentials['password'],
                credentials['api_url']
            ]
            
            logger.info(f"🔐 Attempting login to {credentials['cluster_name']} as {credentials['username']}")
            
            login_result = subprocess.run(
                login_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if login_result.returncode == 0:
                # Verify login by checking whoami
                whoami_result = subprocess.run(['oc', 'whoami'], capture_output=True, text=True, timeout=10)
                if whoami_result.returncode == 0:
                    logger.info(f"✅ Successfully logged in as: {whoami_result.stdout.strip()}")
                    result.update({
                        'success': True,
                        'method': 'oc_username_password',
                        'logged_in_user': whoami_result.stdout.strip()
                    })
                else:
                    result['error'] = 'login_verification_failed'
            else:
                logger.error(f"❌ Login failed: {login_result.stderr}")
                result['error'] = f"oc_login_failed: {login_result.stderr.strip()}"
                
        except subprocess.TimeoutExpired:
            result['error'] = 'login_timeout'
        except Exception as e:
            result['error'] = f"login_exception: {str(e)}"
            
        return result
    
    def _perform_connected_assessment(self, cluster_name: str, deployment_status: Dict[str, Any] = None) -> Optional[EnvironmentData]:
        """Perform environment assessment while connected to target cluster"""
        try:
            # Now that we're connected, perform the standard assessment
            env_data = self._perform_real_assessment_connected(cluster_name)
            
            # Add Jenkins deployment metadata if available
            if env_data and deployment_status and deployment_status.get('source') == 'jenkins_successful':
                # Enhance platform_details with Jenkins metadata
                jenkins_metadata = {
                    'jenkins_successful_build': deployment_status.get('successful_build'),
                    'jenkins_successful_build_result': deployment_status.get('successful_build_result', 'SUCCESS'),
                    'jenkins_latest_build': deployment_status.get('latest_build'),
                    'jenkins_latest_build_result': deployment_status.get('latest_build_result', 'UNKNOWN'),
                    'jenkins_is_stale': deployment_status.get('is_stale', False),
                    'jenkins_job_url': deployment_status.get('jenkins_job_url'),
                    'jenkins_deployment_status': 'successful_connection'
                }
                
                env_data.platform_details.update(jenkins_metadata)
                env_data.raw_data['jenkins_deployment_metadata'] = jenkins_metadata
            
            return env_data
            
        except Exception as e:
            logger.error(f"❌ Connected assessment failed: {e}")
            return None
    
    def _create_no_environment_context(self, target_environment: str, connection_result: Dict[str, Any], deployment_status: Dict[str, Any] = None) -> EnvironmentData:
        """Create environment context when no test environment is available"""
        
        logger.info(f"📋 Creating no-environment context for workflow completion")
        
        # Include Jenkins deployment metadata when available
        jenkins_metadata = {}
        if deployment_status and deployment_status.get('source') == 'jenkins_successful':
            jenkins_metadata = {
                'jenkins_successful_build': deployment_status.get('successful_build'),
                'jenkins_successful_build_result': deployment_status.get('successful_build_result', 'SUCCESS'),
                'jenkins_latest_build': deployment_status.get('latest_build'),
                'jenkins_latest_build_result': deployment_status.get('latest_build_result', 'UNKNOWN'),
                'jenkins_is_stale': deployment_status.get('is_stale', False),
                'jenkins_job_url': deployment_status.get('jenkins_job_url'),
                'jenkins_deployment_status': 'fetched_but_connection_failed'
            }
        elif deployment_status and deployment_status.get('source') == 'jenkins_failed':
            jenkins_metadata = {
                'jenkins_deployment_status': 'fetch_failed',
                'jenkins_error': deployment_status.get('error', 'unknown')
            }
        
        return EnvironmentData(
            cluster_name="NO_TEST_ENVIRONMENT",
            version="environment_unavailable",
            api_url="unavailable", 
            console_url="unavailable",
            platform="no_environment",
            region="unavailable",
            health_status="no_connection",
            connectivity_confirmed=False,
            platform_details={
                'platform': 'no_environment',
                'error': connection_result.get('error', 'unknown'),
                'root_cause': connection_result.get('root_cause', 'unknown'),
                'target_environment': target_environment[:100],
                **jenkins_metadata
            },
            detection_method='no_environment_available',
            assessment_timestamp=datetime.now().isoformat(),
            tools_available=self.available_tools,
            raw_data={
                'connection_failure': connection_result,
                'target_environment': target_environment,
                'workflow_completion_mode': 'no_test_environment',
                'jenkins_deployment_metadata': jenkins_metadata
            }
        )
    
    def _perform_real_assessment_connected(self, cluster_name: str) -> Optional[EnvironmentData]:
        """Perform environment assessment while already connected to target cluster"""
        
        for attempt in range(self.config.max_retries):
            try:
                # Get cluster info
                cluster_info = self._get_cluster_info()
                
                # Get version information (ACM-first detection)
                version_info = self._get_version_info()
                
                # Get health status
                health_status = self._get_health_status()
                
                # Detect platform type
                platform_info = self._detect_platform()
                
                # Extract URLs from current connection
                api_url, console_url = self._extract_cluster_urls(cluster_info)
                
                # Determine region
                region = self._determine_region(cluster_info)
                
                return EnvironmentData(
                    cluster_name=cluster_name,
                    version=version_info.get('version', 'unknown'),
                    api_url=api_url,
                    console_url=console_url,
                    platform=platform_info.get('platform', 'kubernetes'),
                    region=region,
                    health_status=health_status,
                    connectivity_confirmed=True,
                    platform_details=platform_info,
                    detection_method=f'{self.primary_tool}_deterministic_connection',
                    assessment_timestamp=datetime.now().isoformat(),
                    tools_available=self.available_tools,
                    raw_data={
                        'cluster_info': cluster_info,
                        'version_info': version_info,
                        'platform_info': platform_info,
                        'connection_method': 'deterministic_login'
                    }
                )
                
            except Exception as e:
                logger.warning(f"Connected assessment attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise EnvironmentAssessmentError(f"Failed to assess connected environment after {self.config.max_retries} attempts")
        
        return None
    
    def _perform_real_assessment(self, environment: str = None) -> Optional[EnvironmentData]:
        """Perform real environment assessment using available tools (legacy method)"""
        
        for attempt in range(self.config.max_retries):
            try:
                # Get cluster info
                cluster_info = self._get_cluster_info()
                
                # Get version information
                version_info = self._get_version_info()
                
                # Get health status
                health_status = self._get_health_status()
                
                # Detect platform type
                platform_info = self._detect_platform()
                
                # Extract URLs
                api_url, console_url = self._extract_cluster_urls(cluster_info)
                
                # Determine cluster name
                cluster_name = self._determine_cluster_name(cluster_info, environment)
                
                # Determine region
                region = self._determine_region(cluster_info)
                
                return EnvironmentData(
                    cluster_name=cluster_name,
                    version=version_info.get('version', 'unknown'),
                    api_url=api_url,
                    console_url=console_url,
                    platform=platform_info.get('platform', 'kubernetes'),
                    region=region,
                    health_status=health_status,
                    connectivity_confirmed=True,
                    platform_details=platform_info,
                    detection_method=f'{self.primary_tool}_assessment',
                    assessment_timestamp=datetime.now().isoformat(),
                    tools_available=self.available_tools,
                    raw_data={
                        'cluster_info': cluster_info,
                        'version_info': version_info,
                        'platform_info': platform_info
                    }
                )
                
            except Exception as e:
                logger.warning(f"Assessment attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise EnvironmentAssessmentError(f"Failed to assess environment after {self.config.max_retries} attempts")
        
        return None
    
    def _get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information using available tools"""
        
        cmd = [self.primary_tool, 'cluster-info']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.cluster_timeout
            )
            
            if result.returncode != 0:
                raise ClusterConnectionError(f"Cluster info command failed: {result.stderr}")
            
            # Parse cluster info output
            return self._parse_cluster_info(result.stdout)
            
        except subprocess.TimeoutExpired:
            raise ClusterConnectionError(f"Cluster info command timed out after {self.config.cluster_timeout}s")
    
    def _get_acm_version_info(self) -> Dict[str, Any]:
        """Get ACM version information from cluster using MultiClusterHub"""
        
        if self.primary_tool != 'oc':
            logger.info("ACM version detection requires oc tool, skipping")
            return {'version': None, 'error': 'oc_not_available'}
        
        # Use the exact command provided by the user
        cmd = ['oc', 'get', 'mch', '-A', '-o', 'jsonpath={.items[0].status.currentVersion}']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.health_check_timeout
            )
            
            if result.returncode == 0 and result.stdout.strip():
                acm_version = result.stdout.strip()
                logger.info(f"✅ ACM version detected: {acm_version}")
                return {
                    'version': acm_version,
                    'detection_method': 'acm_mch_detection',
                    'product': 'ACM',
                    'command_used': ' '.join(cmd),
                    'raw_output': result.stdout.strip()
                }
            else:
                # Try alternative ACM detection methods
                return self._try_alternative_acm_detection()
                
        except subprocess.TimeoutExpired:
            logger.warning("ACM version command timed out")
            return {'version': None, 'error': 'acm_timeout'}
        except Exception as e:
            logger.warning(f"ACM version detection failed: {e}")
            return {'version': None, 'error': str(e)}
    
    def _try_alternative_acm_detection(self) -> Dict[str, Any]:
        """Try alternative methods to detect ACM version"""
        
        # Alternative 1: Check for ACM operator
        alt_commands = [
            ['oc', 'get', 'csv', '-A', '--no-headers', '| grep advanced-cluster-management'],
            ['oc', 'get', 'subscription', '-A', '--no-headers', '| grep advanced-cluster-management'],
            ['oc', 'get', 'pods', '-n', 'open-cluster-management', '--no-headers']
        ]
        
        for cmd_parts in alt_commands:
            try:
                if '|' in ' '.join(cmd_parts):
                    # Handle pipe commands with shell=True
                    cmd_str = ' '.join(cmd_parts)
                    result = subprocess.run(
                        cmd_str,
                        capture_output=True,
                        text=True,
                        shell=True,
                        timeout=self.config.health_check_timeout
                    )
                else:
                    result = subprocess.run(
                        cmd_parts,
                        capture_output=True,
                        text=True,
                        timeout=self.config.health_check_timeout
                    )
                
                if result.returncode == 0 and result.stdout.strip():
                    logger.info(f"ACM detected via alternative method: {' '.join(cmd_parts[:3])}")
                    return {
                        'version': 'acm_detected_no_version',
                        'detection_method': 'acm_alternative_detection', 
                        'product': 'ACM',
                        'command_used': ' '.join(cmd_parts),
                        'raw_output': result.stdout.strip()
                    }
            except Exception as e:
                logger.debug(f"Alternative ACM detection failed: {e}")
                continue
        
        logger.info("❌ ACM not detected in cluster")
        return {
            'version': None,
            'detection_method': 'acm_not_detected',
            'product': None,
            'error': 'acm_not_installed'
        }

    def _get_version_info(self) -> Dict[str, Any]:
        """Get version information from cluster - ACM first, then platform fallback"""
        
        # STEP 1: Try ACM version detection first (as requested by user)
        logger.info("🔍 Attempting ACM version detection...")
        acm_version_info = self._get_acm_version_info()
        
        if acm_version_info.get('version') and acm_version_info['version'] != 'acm_detected_no_version':
            logger.info(f"✅ ACM version successfully detected: {acm_version_info['version']}")
            return acm_version_info
        
        elif acm_version_info.get('version') == 'acm_detected_no_version':
            logger.info("⚠️ ACM detected but version not available, using ACM context")
            return acm_version_info
        
        # STEP 2: ACM not detected, fall back to platform version detection
        logger.info("ℹ️ ACM not detected, falling back to platform version detection...")
        
        cmd = [self.primary_tool, 'version', '-o', 'json']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.health_check_timeout
            )
            
            if result.returncode == 0:
                try:
                    version_data = json.loads(result.stdout)
                    platform_info = self._parse_version_data(version_data)
                    platform_info['detection_method'] = 'platform_fallback'
                    platform_info['product'] = 'OpenShift' if self.primary_tool == 'oc' else 'Kubernetes'
                    logger.info(f"📋 Platform version detected: {platform_info.get('version')} ({platform_info['product']})")
                    return platform_info
                except json.JSONDecodeError:
                    logger.warning("Failed to parse version JSON, using text parsing")
                    platform_info = self._parse_version_text(result.stdout)
                    platform_info['detection_method'] = 'platform_fallback_text'
                    platform_info['product'] = 'OpenShift' if self.primary_tool == 'oc' else 'Kubernetes'
                    return platform_info
            else:
                logger.warning(f"Platform version command failed: {result.stderr}")
                return {
                    'version': 'unknown',
                    'error': result.stderr,
                    'detection_method': 'platform_failed',
                    'product': 'Unknown'
                }
                
        except subprocess.TimeoutExpired:
            logger.warning("Platform version command timed out")
            return {
                'version': 'unknown',
                'error': 'timeout',
                'detection_method': 'platform_timeout',
                'product': 'Unknown'
            }
    
    def _get_health_status(self) -> str:
        """Get cluster health status"""
        
        # Try to get node status as health indicator
        cmd = [self.primary_tool, 'get', 'nodes', '--no-headers']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.health_check_timeout
            )
            
            if result.returncode == 0:
                # Parse node status
                lines = result.stdout.strip().split('\n')
                ready_nodes = 0
                total_nodes = len([line for line in lines if line.strip()])
                
                for line in lines:
                    if line.strip():
                        # Split and check the second column for exact status
                        parts = line.split()
                        if len(parts) > 1 and parts[1] == 'Ready':
                            ready_nodes += 1
                
                if ready_nodes == total_nodes and total_nodes > 0:
                    return 'healthy'
                elif ready_nodes > 0:
                    return 'degraded'
                else:
                    return 'unhealthy'
            else:
                return 'unknown'
                
        except subprocess.TimeoutExpired:
            return 'timeout'
        except Exception:
            return 'unknown'
    
    def _detect_platform(self) -> Dict[str, Any]:
        """Detect platform type (Kubernetes, OpenShift, etc.)"""
        
        platform_info = {
            'platform': 'kubernetes',
            'distribution': 'unknown',
            'features': []
        }
        
        # Check for OpenShift-specific resources
        if self.primary_tool == 'oc':
            platform_info['platform'] = 'openshift'
            platform_info['distribution'] = 'openshift'
            platform_info['features'].append('oc_cli')
            
            # Try to get OpenShift version
            try:
                cmd = [self.primary_tool, 'version', '-o', 'json']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    try:
                        version_data = json.loads(result.stdout)
                        if 'openshiftVersion' in version_data:
                            platform_info['openshift_version'] = version_data['openshiftVersion']
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass
        
        # Check for other platform indicators
        try:
            # Check for specific namespaces that indicate platform type
            cmd = [self.primary_tool, 'get', 'namespaces', '--no-headers']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                namespaces = result.stdout.lower()
                
                if 'openshift' in namespaces:
                    platform_info['platform'] = 'openshift'
                    platform_info['features'].append('openshift_namespaces')
                
                if 'kube-system' in namespaces:
                    platform_info['features'].append('kubernetes_system')
                
                if 'istio-system' in namespaces:
                    platform_info['features'].append('istio')
                
        except Exception:
            pass
        
        return platform_info
    
    def _parse_cluster_info(self, cluster_info_text: str) -> Dict[str, Any]:
        """Parse cluster info text output"""
        
        parsed = {
            'kubernetes_master': None,
            'kubernetes_dns': None,
            'services': []
        }
        
        lines = cluster_info_text.split('\n')
        
        for line in lines:
            if 'Kubernetes control plane' in line or 'Kubernetes master' in line:
                # Extract URL
                if 'https://' in line:
                    start = line.find('https://')
                    end = line.find(' ', start)
                    if end == -1:
                        end = len(line)
                    parsed['kubernetes_master'] = line[start:end].strip()
            
            elif 'CoreDNS' in line or 'KubeDNS' in line:
                if 'https://' in line:
                    start = line.find('https://')
                    end = line.find(' ', start)
                    if end == -1:
                        end = len(line)
                    parsed['kubernetes_dns'] = line[start:end].strip()
            
            elif 'https://' in line:
                # Other services
                start = line.find('https://')
                end = line.find(' ', start)
                if end == -1:
                    end = len(line)
                url = line[start:end].strip()
                service_name = line[:start].strip()
                parsed['services'].append({'name': service_name, 'url': url})
        
        return parsed
    
    def _parse_version_data(self, version_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse version data from JSON"""
        
        parsed = {
            'client_version': 'unknown',
            'server_version': 'unknown',
            'version': 'unknown'
        }
        
        # Extract client version
        if 'clientVersion' in version_data:
            client_ver = version_data['clientVersion']
            if isinstance(client_ver, dict) and 'gitVersion' in client_ver:
                parsed['client_version'] = client_ver['gitVersion']
        
        # Extract server version
        if 'serverVersion' in version_data:
            server_ver = version_data['serverVersion']
            if isinstance(server_ver, dict) and 'gitVersion' in server_ver:
                parsed['server_version'] = server_ver['gitVersion']
                parsed['version'] = server_ver['gitVersion']
        
        # For OpenShift
        if 'openshiftVersion' in version_data:
            parsed['openshift_version'] = version_data['openshiftVersion']
            parsed['version'] = version_data['openshiftVersion']
        
        return parsed
    
    def _parse_version_text(self, version_text: str) -> Dict[str, Any]:
        """Parse version information from text output"""
        
        parsed = {
            'version': 'unknown',
            'client_version': 'unknown',
            'server_version': 'unknown'
        }
        
        lines = version_text.split('\n')
        
        for line in lines:
            if 'Server Version' in line:
                # Extract version after "Server Version:"
                parts = line.split(':')
                if len(parts) > 1:
                    version_part = parts[1].strip()
                    if version_part.startswith('v'):
                        parsed['server_version'] = version_part.split()[0]
                        parsed['version'] = version_part.split()[0]
            elif 'Client Version' in line:
                # Extract version after "Client Version:"
                parts = line.split(':')
                if len(parts) > 1:
                    version_part = parts[1].strip()
                    if version_part.startswith('v'):
                        parsed['client_version'] = version_part.split()[0]
        
        return parsed
    
    def _extract_cluster_urls(self, cluster_info: Dict[str, Any]) -> Tuple[str, str]:
        """Extract API and console URLs from cluster info"""
        
        api_url = cluster_info.get('kubernetes_master', 'unknown')
        
        # For console URL, try to derive from API URL
        console_url = 'unknown'
        
        if api_url and api_url != 'unknown':
            try:
                # Common pattern: replace api with console
                if 'api.' in api_url:
                    console_url = api_url.replace('api.', 'console.')
                elif ':6443' in api_url:
                    # Replace API port with console
                    console_url = api_url.replace(':6443', '')
                    if not console_url.startswith('https://console.'):
                        console_url = api_url.replace('https://', 'https://console.')
                        console_url = console_url.replace(':6443', '')
            except Exception:
                console_url = 'derived_from_api'
        
        return api_url, console_url
    
    def _determine_cluster_name(self, cluster_info: Dict[str, Any], environment: str = None) -> str:
        """Determine cluster name from various sources"""
        
        if environment:
            return environment
        
        # Try to extract from API URL
        api_url = cluster_info.get('kubernetes_master', '')
        
        if api_url and 'https://' in api_url:
            try:
                # Extract domain name
                domain = api_url.replace('https://', '').replace('http://', '')
                domain = domain.split(':')[0]  # Remove port
                
                # Extract cluster identifier
                parts = domain.split('.')
                if len(parts) > 2:
                    # Common patterns: api.cluster-name.domain.com
                    if parts[0] == 'api':
                        return parts[1]
                    else:
                        return parts[0]
                else:
                    return domain
            except Exception:
                pass
        
        return environment or 'qe6-vmware-ibm'
    
    def _determine_region(self, cluster_info: Dict[str, Any]) -> str:
        """Determine region from cluster info"""
        
        # Try to extract region from URLs or other hints
        api_url = cluster_info.get('kubernetes_master', '')
        
        common_regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
        
        for region in common_regions:
            if region in api_url:
                return region
        
        # Default
        return 'unknown'
    
    # Framework uses deterministic environment detection - explicit failure when environment unavailable
    # Framework now fails explicitly with actionable suggestions when environment unavailable
    
    def _get_cached_assessment(self, environment: str = None) -> Optional[EnvironmentData]:
        """Get environment assessment from cache if valid"""
        
        cache_key = environment or 'current'
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file) as f:
                cached_data = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cached_data['cache_timestamp'])
            if datetime.now() - cache_time > timedelta(seconds=self.config.cache_duration):
                logger.info(f"Cache expired for environment {cache_key}")
                return None
            
            # Convert back to EnvironmentData
            env_data = cached_data['environment_data']
            return EnvironmentData(**env_data)
            
        except Exception as e:
            logger.warning(f"Failed to load cache for environment {cache_key}: {e}")
            return None
    
    def _cache_assessment(self, env_data: EnvironmentData, environment: str = None):
        """Cache environment assessment for future use"""
        
        cache_key = environment or 'current'
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cache_data = {
                'cache_timestamp': datetime.now().isoformat(),
                'environment_data': {
                    'cluster_name': env_data.cluster_name,
                    'version': env_data.version,
                    'api_url': env_data.api_url,
                    'console_url': env_data.console_url,
                    'platform': env_data.platform,
                    'region': env_data.region,
                    'health_status': env_data.health_status,
                    'connectivity_confirmed': env_data.connectivity_confirmed,
                    'platform_details': env_data.platform_details,
                    'detection_method': env_data.detection_method,
                    'assessment_timestamp': env_data.assessment_timestamp,
                    'tools_available': env_data.tools_available
                    # Note: raw_data not cached to avoid size issues
                }
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to cache environment assessment {cache_key}: {e}")
    
    def test_connectivity(self, environment: str = None) -> Tuple[bool, str]:
        """Test environment connectivity and return status"""
        
        if not self.primary_tool:
            return False, "No cluster tools available (oc/kubectl)"
        
        try:
            # Simple connectivity test
            cmd = [self.primary_tool, 'cluster-info', '--request-timeout=10s']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                return True, "Cluster connectivity confirmed"
            else:
                return False, f"Cluster connection failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Connection test timed out"
        except Exception as e:
            return False, f"Connection test error: {e}"
    
    def get_assessment_status(self) -> Dict[str, Any]:
        """Get detailed assessment status information"""
        
        connected, message = self.test_connectivity()
        
        return {
            'connected': connected,
            'message': message,
            'primary_tool': self.primary_tool,
            'available_tools': self.available_tools,
            'deterministic_failure': True,  # Framework fails explicitly when environment unavailable
            'cache_enabled': True,
            'cache_duration': self.config.cache_duration,
            'assessment_timeout': self.config.cluster_timeout
        }
    
    def collect_sample_data_for_tests(self, jira_ticket: str, agent_a_intelligence: Dict[str, Any] = None) -> Dict[str, Any]:
        """Collect sample YAMLs, command outputs, and logs intelligently based on Agent A discoveries"""
        sample_data = {
            'sample_yamls': {},
            'sample_commands': {},
            'sample_outputs': {},
            'sample_logs': {}
        }
        
        logger.info("Agent D: Collecting intelligent sample data based on Agent A requirements intelligence")
        
        # Extract component intelligence from Agent A
        components_discovered = self._extract_components_from_agent_a(agent_a_intelligence)
        pr_information = self._extract_pr_information_from_agent_a(agent_a_intelligence)
        feature_scope = self._extract_feature_scope_from_agent_a(agent_a_intelligence)
        
        logger.info(f"Agent D: Detected components: {components_discovered}, PRs: {pr_information}, scope: {feature_scope}")
        
        try:
            # Intelligently collect samples based on discovered components
            if 'clustercurator' in components_discovered.lower() or 'cluster-curator' in components_discovered.lower():
                self._collect_clustercurator_samples(sample_data, pr_information, feature_scope)
            elif 'policy' in components_discovered.lower() or 'governance' in components_discovered.lower():
                self._collect_policy_samples(sample_data, pr_information, feature_scope)
            elif 'console' in components_discovered.lower() or 'ui' in components_discovered.lower():
                self._collect_console_samples(sample_data, pr_information, feature_scope)
            elif 'observability' in components_discovered.lower() or 'monitoring' in components_discovered.lower():
                self._collect_observability_samples(sample_data, pr_information, feature_scope)
            elif 'applicationset' in components_discovered.lower() or 'gitops' in components_discovered.lower():
                self._collect_applicationset_samples(sample_data, pr_information, feature_scope)
            else:
                # Fallback: collect generic ACM samples
                logger.info("Agent D: Component not specifically recognized, collecting generic ACM samples")
                self._collect_generic_acm_samples(sample_data, pr_information, feature_scope)

            logger.info(f"Agent D: Intelligently collected {len(sample_data['sample_yamls'])} YAML samples, {len(sample_data['sample_commands'])} command samples, {len(sample_data['sample_outputs'])} output samples for {components_discovered}")
            
            # Add metadata about intelligence used
            sample_data['intelligence_metadata'] = {
                'components_discovered': components_discovered,
                'pr_information': pr_information,
                'feature_scope': feature_scope,
                'collection_strategy': 'intelligent_based_on_agent_a',
                'agent_a_context_used': agent_a_intelligence is not None
            }
            
        except Exception as e:
            logger.warning(f"Agent D: Error collecting sample data: {e}")
            
        return sample_data
    
    def _extract_components_from_agent_a(self, agent_a_intelligence: Dict[str, Any]) -> str:
        """Extract component information from Agent A's requirements intelligence"""
        if not agent_a_intelligence:
            return "unknown"
        
        # Look for component information in various Agent A fields
        components = []
        
        # Check findings and requirements analysis
        findings = agent_a_intelligence.get('findings', {})
        if isinstance(findings, dict):
            # Check component field
            component = findings.get('component', '')
            if component:
                components.append(component)
            
            # Check description for component mentions
            description = findings.get('description', '')
            if 'clustercurator' in description.lower() or 'cluster-curator' in description.lower():
                components.append('ClusterCurator')
            elif 'policy' in description.lower() or 'governance' in description.lower():
                components.append('Policy')
            elif 'console' in description.lower() or 'ui' in description.lower():
                components.append('Console')
            elif 'observability' in description.lower() or 'monitoring' in description.lower():
                components.append('Observability')
            elif 'applicationset' in description.lower() or 'gitops' in description.lower():
                components.append('ApplicationSet')
        
        return ', '.join(components) if components else 'unknown'
    
    def _extract_pr_information_from_agent_a(self, agent_a_intelligence: Dict[str, Any]) -> str:
        """Extract PR information from Agent A's requirements intelligence"""
        if not agent_a_intelligence:
            return "no_prs"
        
        findings = agent_a_intelligence.get('findings', {})
        if isinstance(findings, dict):
            # Look for PR references
            prs = findings.get('prs', [])
            if prs:
                return f"PRs: {', '.join(prs)}"
            
            # Look in description for PR mentions
            description = findings.get('description', '')
            if 'PR #' in description or 'pull request' in description.lower():
                return f"PR mentioned in description"
        
        return "no_prs"
    
    def _extract_feature_scope_from_agent_a(self, agent_a_intelligence: Dict[str, Any]) -> str:
        """Extract feature scope from Agent A's requirements intelligence"""
        if not agent_a_intelligence:
            return "unknown_scope"
        
        findings = agent_a_intelligence.get('findings', {})
        if isinstance(findings, dict):
            # Look for feature scope information
            scope = findings.get('scope', '')
            if scope:
                return scope
            
            # Extract from description
            description = findings.get('description', '')
            if 'digest' in description.lower() and 'upgrade' in description.lower():
                return 'digest-based upgrades'
            elif 'policy' in description.lower():
                return 'policy management'
            elif 'observability' in description.lower():
                return 'monitoring and observability'
            elif 'console' in description.lower():
                return 'user interface'
            elif 'gitops' in description.lower():
                return 'gitops and applicationsets'
        
        return "unknown_scope"
    
    def _collect_clustercurator_samples(self, sample_data: Dict[str, Any], pr_info: str, feature_scope: str):
        """Collect ClusterCurator-specific samples based on Agent A intelligence"""
        logger.info(f"Agent D: Collecting ClusterCurator samples for scope: {feature_scope}")
        
        # Adapt YAML based on feature scope
        if 'digest' in feature_scope.lower():
            sample_data['sample_yamls']['clustercurator_digest'] = """apiVersion: cluster.open-cluster-management.io/v1beta1
kind: ClusterCurator
metadata:
  name: test-clustercurator-digest-upgrade
  namespace: default
spec:
  desiredCuration: upgrade
  clusterName: managed-cluster-1
  upgrade:
    channel: stable-4.15
    desiredUpdate:
      version: "4.15.1"
    conditionalUpdates:
      - version: "4.15.1"
        digest: "sha256:abc123def456..."
        url: "quay.io/openshift-release-dev/ocp-release@sha256:abc123def456..."
  timeout: "240m"
  monitor: true"""
            
            sample_data['sample_yamls']['clustercurator_fallback'] = """apiVersion: cluster.open-cluster-management.io/v1beta1
kind: ClusterCurator
metadata:
  name: test-clustercurator-fallback
  namespace: default
spec:
  desiredCuration: upgrade
  clusterName: managed-cluster-disconnected
  upgrade:
    channel: stable-4.15
    desiredUpdate:
      version: "4.15.1"
    conditionalUpdates:
      - version: "4.15.1"
        digest: "sha256:unavailable..."  # Will fallback to availableUpdates
    availableUpdates:
      - version: "4.15.1"
        image: "quay.io/openshift-release-dev/ocp-release:4.15.1"
  timeout: "300m"
  monitor: true"""
        else:
            # Generic ClusterCurator samples
            sample_data['sample_yamls']['clustercurator_basic'] = """apiVersion: cluster.open-cluster-management.io/v1beta1
kind: ClusterCurator
metadata:
  name: test-clustercurator
  namespace: default
spec:
  desiredCuration: upgrade
  clusterName: managed-cluster-1
  upgrade:
    channel: stable-4.15
    desiredUpdate:
      version: "4.15.1"
  timeout: "240m"
  monitor: true"""
        
        # ClusterCurator commands
        sample_data['sample_commands']['oc_get_clustercurator'] = "oc get clustercurator -A"
        sample_data['sample_outputs']['oc_get_clustercurator'] = """NAMESPACE   NAME                           CLUSTER              STATUS    AGE
default     test-clustercurator-digest     managed-cluster-1    Ready     5m32s
default     test-clustercurator-fallback   managed-cluster-2    Running   2m18s"""
        
        sample_data['sample_commands']['oc_describe_clustercurator'] = "oc describe clustercurator test-clustercurator-digest -n default"
        sample_data['sample_outputs']['oc_describe_clustercurator'] = """Name:         test-clustercurator-digest
Namespace:    default
Status:
  Conditions:
    Message:               Upgrade completed successfully using conditionalUpdates
    Status:                True
    Type:                  Ready"""
        
        # ClusterCurator logs
        if 'digest' in feature_scope.lower():
            sample_data['sample_logs']['clustercurator_digest_success'] = """2025-08-26T15:43:35Z INFO ClusterCurator attempting upgrade using conditionalUpdates
2025-08-26T15:43:36Z INFO Found conditionalUpdate: version=4.15.1, digest=sha256:abc123def456...
2025-08-26T15:48:46Z INFO ClusterCurator upgrade completed successfully using conditionalUpdates method"""
            
            sample_data['sample_logs']['clustercurator_fallback'] = """2025-08-26T15:43:35Z INFO ClusterCurator attempting upgrade using conditionalUpdates
2025-08-26T15:43:36Z WARN conditionalUpdates not available for version 4.15.1
2025-08-26T15:43:37Z INFO Falling back to availableUpdates method
2025-08-26T15:45:22Z INFO Upgrade completed successfully using availableUpdates fallback method"""
    
    def _collect_policy_samples(self, sample_data: Dict[str, Any], pr_info: str, feature_scope: str):
        """Collect Policy/Governance-specific samples based on Agent A intelligence"""
        logger.info(f"Agent D: Collecting Policy samples for scope: {feature_scope}")
        
        sample_data['sample_yamls']['policy_sample'] = """apiVersion: policy.open-cluster-management.io/v1
kind: Policy
metadata:
  name: test-policy
  namespace: default
spec:
  complianceType: musthave
  namespaceSelector:
    include: ["default"]
  object-templates:
    - complianceType: musthave
      objectDefinition:
        apiVersion: v1
        kind: ConfigMap
        metadata:
          name: test-config"""
        
        sample_data['sample_commands']['oc_get_policies'] = "oc get policies -A"
        sample_data['sample_outputs']['oc_get_policies'] = """NAMESPACE   NAME          COMPLIANCE   AGE
default     test-policy   Compliant    5m32s"""
    
    def _collect_console_samples(self, sample_data: Dict[str, Any], pr_info: str, feature_scope: str):
        """Collect Console/UI-specific samples based on Agent A intelligence"""
        logger.info(f"Agent D: Collecting Console UI samples for scope: {feature_scope}")
        
        sample_data['sample_commands']['oc_get_console'] = "oc get console.operator cluster -o yaml"
        sample_data['sample_outputs']['oc_get_console'] = """apiVersion: operator.openshift.io/v1
kind: Console
metadata:
  name: cluster
spec:
  managementState: Managed
status:
  conditions:
  - status: "True"
    type: Available"""
    
    def _collect_observability_samples(self, sample_data: Dict[str, Any], pr_info: str, feature_scope: str):
        """Collect Observability/Monitoring-specific samples based on Agent A intelligence"""
        logger.info(f"Agent D: Collecting Observability samples for scope: {feature_scope}")
        
        sample_data['sample_yamls']['observability_addon'] = """apiVersion: observability.open-cluster-management.io/v1beta2
kind: MultiClusterObservability
metadata:
  name: observability
spec:
  observabilityAddonSpec:
    enableMetrics: true
    interval: 30
  storageConfig:
    metricObjectStorage:
      name: thanos-object-storage
      key: thanos.yaml"""
        
        sample_data['sample_commands']['oc_get_observability'] = "oc get multiclusterobservability -A"
        sample_data['sample_outputs']['oc_get_observability'] = """NAME           STATUS    AGE
observability  Ready     10m"""
    
    def _collect_applicationset_samples(self, sample_data: Dict[str, Any], pr_info: str, feature_scope: str):
        """Collect ApplicationSet/GitOps-specific samples based on Agent A intelligence"""
        logger.info(f"Agent D: Collecting ApplicationSet samples for scope: {feature_scope}")
        
        sample_data['sample_yamls']['applicationset_sample'] = """apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: test-applicationset
  namespace: openshift-gitops
spec:
  generators:
  - clusters: {}
  template:
    metadata:
      name: 'test-app-{{name}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/example/test-app
        targetRevision: HEAD
        path: manifests
      destination:
        server: '{{server}}'
        namespace: test-app"""
        
        sample_data['sample_commands']['oc_get_applicationsets'] = "oc get applicationsets -A"
        sample_data['sample_outputs']['oc_get_applicationsets'] = """NAMESPACE          NAME                  AGE
openshift-gitops   test-applicationset   5m"""
    
    def _collect_generic_acm_samples(self, sample_data: Dict[str, Any], pr_info: str, feature_scope: str):
        """Collect generic ACM samples when component is not specifically recognized"""
        logger.info(f"Agent D: Collecting generic ACM samples for scope: {feature_scope}")
        
        sample_data['sample_yamls']['managedcluster_sample'] = """apiVersion: cluster.open-cluster-management.io/v1
kind: ManagedCluster
metadata:
  name: test-cluster
spec:
  hubAcceptsClient: true
status:
  conditions:
  - status: "True"
    type: ManagedClusterConditionAvailable"""
        
        sample_data['sample_commands']['oc_get_managedclusters'] = "oc get managedclusters"
        sample_data['sample_outputs']['oc_get_managedclusters'] = """NAME           HUB ACCEPTED   MANAGED CLUSTER URLS                    JOINED   AVAILABLE   AGE
test-cluster   true           https://test-cluster.example.com:6443   True     True        5m"""
        
        sample_data['sample_commands']['oc_login'] = "oc login <CLUSTER_CONSOLE_URL> -u <CLUSTER_ADMIN_USER> -p <CLUSTER_ADMIN_PASSWORD>"
        sample_data['sample_outputs']['oc_login'] = """Login successful.

You have access to 67 projects, the list has been suppressed. You can list all projects with 'oc projects'

Using project "default"."""


# Convenience functions for easy integration
def create_environment_client() -> EnvironmentAssessmentClient:
    """Create environment assessment client with default configuration"""
    return EnvironmentAssessmentClient()


def assess_current_environment() -> Dict[str, Any]:
    """Assess current environment and return as dictionary (for legacy compatibility)"""
    client = create_environment_client()
    env_data = client.assess_environment()
    
    return {
        'version': env_data.version,
        'cluster_name': env_data.cluster_name,
        'api_url': env_data.api_url,
        'console_url': env_data.console_url,
        'platform': env_data.platform,
        'region': env_data.region,
        'health_status': env_data.health_status,
        'connectivity_confirmed': env_data.connectivity_confirmed,
        'detection_method': env_data.detection_method
    }


if __name__ == "__main__":
    # Example usage and testing
    import sys
    
    environment = sys.argv[1] if len(sys.argv) > 1 else None
    
    print(f"🌍 Testing Environment Assessment Client...")
    print(f"📍 Target Environment: {environment or 'qe6-vmware-ibm (default)'}")
    
    try:
        client = create_environment_client()
        
        # Test connectivity
        connected, status_msg = client.test_connectivity()
        print(f"🔗 Connectivity Status: {status_msg}")
        
        # Get assessment status
        status = client.get_assessment_status()
        print(f"🛠️  Primary Tool: {status['primary_tool']}")
        print(f"📊 Available Tools: {status['available_tools']}")
        
        # Assess environment
        env_data = client.assess_environment(environment)
        print(f"✅ Successfully assessed environment: {env_data.cluster_name}")
        print(f"🏷️  Version: {env_data.version}")
        print(f"🌐 Platform: {env_data.platform}")
        print(f"🏥 Health: {env_data.health_status}")
        print(f"📡 API URL: {env_data.api_url}")
        print(f"🖥️  Console URL: {env_data.console_url}")
        print(f"🔧 Detection Method: {env_data.detection_method}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
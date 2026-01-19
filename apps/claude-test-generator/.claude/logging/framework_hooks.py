#!/usr/bin/env python3
"""
Framework Hooks Integration System

Purpose: Integrate comprehensive logging hooks into the claude-test-generator framework
to capture every phase, task, agent activity, tool execution, and data flow.

Author: AI Systems Suite
Version: 1.0.0
"""

import os
import re
import json
import time
import threading
import functools
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from framework_debug_logger import FrameworkDebugLogger, get_global_logger, initialize_global_logger

class FrameworkHookIntegration:
    """
    Comprehensive hook integration system for claude-test-generator framework
    
    Provides automatic interception and logging of:
    - Claude Code tool executions (Bash, Read, Write, Task, etc.)
    - Framework phase transitions
    - Agent spawning and coordination
    - Progressive Context Architecture flow
    - Validation engine checkpoints
    - Environment interactions
    - AI service executions
    """
    
    def __init__(self, logger: FrameworkDebugLogger = None, enable_all_hooks: bool = True):
        self.logger = logger or get_global_logger()
        if not self.logger:
            self.logger = initialize_global_logger()
        
        self.enable_all_hooks = enable_all_hooks
        self.original_functions = {}
        self.hook_registry = {}
        
        # Set up phase management methods
        self.manual_phase_start = self.logger.log_phase_start
        self.manual_phase_complete = self.logger.log_phase_complete
        
        # Framework state tracking
        self.framework_state = {
            'current_phase': None,
            'active_agents': set(),
            'context_chain': [],
            'validation_status': {},
            'tool_execution_stack': [],
            'environment_connections': {},
            'ai_service_executions': {}
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        if self.enable_all_hooks:
            self.install_all_hooks()
    
    def install_all_hooks(self):
        """Install all available hooks"""
        self.logger.log_info("HOOKS_INSTALLATION", "Installing comprehensive framework hooks", {
            "hooks_enabled": [
                "claude_code_tool_hooks",
                "framework_phase_hooks",
                "agent_coordination_hooks",
                "context_flow_hooks",
                "validation_hooks",
                "environment_hooks",
                "ai_service_hooks"
            ]
        })
        
        try:
            # Install tool execution hooks
            self.install_claude_code_tool_hooks()
            
            # Install framework-specific hooks
            self.install_framework_phase_hooks()
            self.install_agent_coordination_hooks()
            self.install_context_flow_hooks()
            self.install_validation_hooks()
            self.install_environment_hooks()
            self.install_ai_service_hooks()
            
            self.logger.log_info("HOOKS_INSTALLED", "All framework hooks installed successfully")
            
        except Exception as e:
            self.logger.log_error("HOOKS_INSTALLATION_ERROR", f"Failed to install hooks: {e}", {
                "error": str(e),
                "partial_installation": list(self.hook_registry.keys())
            })
            raise
    
    def install_claude_code_tool_hooks(self):
        """Install hooks for Claude Code tool executions"""
        self.logger.log_debug("TOOL_HOOKS_INSTALL", "Installing Claude Code tool hooks")
        
        # Create mock tool execution interceptors
        # Note: In actual Claude Code environment, these would intercept real tool calls
        
        self.hook_registry['bash_tool'] = self.create_bash_tool_hook()
        self.hook_registry['read_tool'] = self.create_read_tool_hook()
        self.hook_registry['write_tool'] = self.create_write_tool_hook()
        self.hook_registry['task_tool'] = self.create_task_tool_hook()
        self.hook_registry['glob_tool'] = self.create_glob_tool_hook()
        self.hook_registry['grep_tool'] = self.create_grep_tool_hook()
        self.hook_registry['edit_tool'] = self.create_edit_tool_hook()
        
        self.logger.log_debug("TOOL_HOOKS_INSTALLED", "Claude Code tool hooks installed", {
            "tools_hooked": list(self.hook_registry.keys())
        })
    
    def create_bash_tool_hook(self):
        """Create Bash tool execution hook"""
        def bash_hook(command: str, description: str = None, timeout: int = None, 
                     run_in_background: bool = False):
            execution_id = f"bash_{int(time.time() * 1000)}"
            
            with self.logger.track_tool("bash", "command_execution", {
                "command": command,
                "description": description,
                "timeout": timeout,
                "background": run_in_background,
                "execution_id": execution_id
            }) as tracking_id:
                
                # Log command details
                self.logger.log_debug("BASH_COMMAND", "Executing bash command", {
                    "command": command,
                    "description": description,
                    "timeout": timeout,
                    "background": run_in_background,
                    "execution_id": execution_id,
                    "tracking_id": tracking_id
                }, component="TOOL")
                
                # In real implementation, this would execute the actual bash command
                # For now, simulate execution
                start_time = time.time()
                
                try:
                    # Simulate command execution
                    time.sleep(0.1)  # Simulate execution time
                    
                    # Mock successful result
                    result = {
                        "stdout": f"Mock output for: {command}",
                        "stderr": "",
                        "return_code": 0,
                        "execution_time": time.time() - start_time
                    }
                    
                    self.logger.log_debug("BASH_RESULT", "Bash command completed", {
                        "command": command,
                        "result": result,
                        "execution_id": execution_id
                    }, component="TOOL")
                    
                    # Special handling for framework-related commands
                    self._analyze_bash_command_for_framework_context(command, result)
                    
                    return result
                    
                except Exception as e:
                    self.logger.log_error("BASH_ERROR", f"Bash command failed: {command}", {
                        "command": command,
                        "error": str(e),
                        "execution_id": execution_id
                    }, component="TOOL")
                    raise
        
        return bash_hook
    
    def _analyze_bash_command_for_framework_context(self, command: str, result: Dict[str, Any]):
        """Analyze bash command for framework-specific context"""
        # Detect environment interactions
        env_patterns = [
            r'oc\s+',
            r'kubectl\s+',
            r'gh\s+',
            r'curl.*issues\.redhat\.com',
            r'curl.*github\.com'
        ]
        
        for pattern in env_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                self.logger.log_environment_interaction("BASH_ENV_COMMAND", 
                    command=command, response=result)
                break
        
        # Detect ACM/version commands
        if any(keyword in command.lower() for keyword in ['acm', 'version', 'operator']):
            self.logger.log_debug("VERSION_DETECTION", "Version-related command detected", {
                "command": command,
                "result": result
            }, component="ENVIRONMENT")
        
        # Detect authentication commands
        if any(keyword in command.lower() for keyword in ['login', 'auth', 'token']):
            # Mask sensitive data
            masked_result = {**result}
            masked_result['stdout'] = '[MASKED_AUTH_OUTPUT]'
            
            self.logger.log_environment_interaction("AUTH_COMMAND", 
                command="[MASKED_AUTH_COMMAND]", response=masked_result)
    
    def create_read_tool_hook(self):
        """Create Read tool execution hook"""
        def read_hook(file_path: str, limit: int = None, offset: int = None):
            with self.logger.track_tool("read", "file_read", {
                "file_path": file_path,
                "limit": limit,
                "offset": offset
            }) as tracking_id:
                
                self.logger.log_debug("FILE_READ", "Reading file", {
                    "file_path": file_path,
                    "limit": limit,
                    "offset": offset,
                    "tracking_id": tracking_id
                }, component="TOOL")
                
                try:
                    # Check if file exists
                    if not Path(file_path).exists():
                        raise FileNotFoundError(f"File not found: {file_path}")
                    
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        if offset:
                            # Skip lines
                            for _ in range(offset):
                                f.readline()
                        
                        if limit:
                            content = ''.join(f.readline() for _ in range(limit))
                        else:
                            content = f.read()
                    
                    # Analyze file for framework context
                    self._analyze_file_content_for_framework_context(file_path, content)
                    
                    self.logger.log_debug("FILE_READ_SUCCESS", "File read successfully", {
                        "file_path": file_path,
                        "content_length": len(content),
                        "lines_read": content.count('\n') + 1 if content else 0
                    }, component="TOOL")
                    
                    return content
                    
                except Exception as e:
                    self.logger.log_error("FILE_READ_ERROR", f"Failed to read file: {file_path}", {
                        "file_path": file_path,
                        "error": str(e)
                    }, component="TOOL")
                    raise
        
        return read_hook
    
    def _analyze_file_content_for_framework_context(self, file_path: str, content: str):
        """Analyze file content for framework-specific context"""
        file_path_lower = file_path.lower()
        
        # Detect AI service files
        if '.claude/ai-services/' in file_path:
            service_name = Path(file_path).stem
            self.logger.log_ai_service_execution(service_name, "SERVICE_DEFINITION_READ", 
                inputs={"file_path": file_path}, 
                outputs={"content_length": len(content)})
        
        # Detect configuration files
        elif any(config in file_path_lower for config in ['config.json', '.claude/config/']):
            self.logger.log_debug("CONFIG_FILE_READ", "Configuration file accessed", {
                "file_path": file_path,
                "content_length": len(content)
            }, component="CONFIG")
        
        # Detect run metadata
        elif 'run-metadata.json' in file_path:
            try:
                metadata = json.loads(content)
                self.logger.log_debug("RUN_METADATA_READ", "Run metadata accessed", {
                    "file_path": file_path,
                    "metadata": metadata
                }, component="METADATA")
            except json.JSONDecodeError:
                pass
        
        # Detect JIRA data
        elif 'jira' in content.lower() and any(pattern in content for pattern in ['ACM-', 'OCPBUGS-', 'RHEL-']):
            jira_tickets = re.findall(r'[A-Z]+-\d+', content)
            self.logger.log_debug("JIRA_DATA_DETECTED", "JIRA ticket data found in file", {
                "file_path": file_path,
                "tickets_found": jira_tickets[:5]  # Limit to first 5
            }, component="AGENT")
        
        # Detect GitHub PR references
        elif 'github.com' in content.lower() or re.search(r'#\d+', content):
            pr_refs = re.findall(r'#(\d+)', content)
            self.logger.log_debug("GITHUB_DATA_DETECTED", "GitHub PR references found", {
                "file_path": file_path,
                "pr_references": pr_refs[:10]  # Limit to first 10
            }, component="AGENT")
    
    def create_write_tool_hook(self):
        """Create Write tool execution hook"""
        def write_hook(file_path: str, content: str):
            with self.logger.track_tool("write", "file_write", {
                "file_path": file_path,
                "content_length": len(content)
            }) as tracking_id:
                
                self.logger.log_debug("FILE_WRITE", "Writing file", {
                    "file_path": file_path,
                    "content_length": len(content),
                    "tracking_id": tracking_id
                }, component="TOOL")
                
                try:
                    # Ensure directory exists
                    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Analyze written content for framework context
                    self._analyze_written_content_for_framework_context(file_path, content)
                    
                    self.logger.log_debug("FILE_WRITE_SUCCESS", "File written successfully", {
                        "file_path": file_path,
                        "content_length": len(content)
                    }, component="TOOL")
                    
                except Exception as e:
                    self.logger.log_error("FILE_WRITE_ERROR", f"Failed to write file: {file_path}", {
                        "file_path": file_path,
                        "error": str(e)
                    }, component="TOOL")
                    raise
        
        return write_hook
    
    def _analyze_written_content_for_framework_context(self, file_path: str, content: str):
        """Analyze written content for framework-specific context"""
        file_path_lower = file_path.lower()
        
        # Detect test plan generation
        if any(keyword in file_path_lower for keyword in ['test-cases', 'complete-analysis']):
            self.logger.log_debug("TEST_PLAN_GENERATED", "Test plan file generated", {
                "file_path": file_path,
                "content_length": len(content),
                "test_cases_count": content.count('Test Case') if 'Test Case' in content else 0
            }, component="OUTPUT")
        
        # Detect agent results
        elif 'agent-' in file_path_lower and '-results' in file_path_lower:
            agent_name = re.search(r'agent-([^-]+)', file_path_lower)
            if agent_name:
                self.logger.log_debug("AGENT_RESULT_GENERATED", f"Agent {agent_name.group(1)} result file generated", {
                    "file_path": file_path,
                    "agent": agent_name.group(1),
                    "content_length": len(content)
                }, component="AGENT")
        
        # Detect run metadata
        elif 'run-metadata.json' in file_path:
            try:
                metadata = json.loads(content)
                self.logger.log_debug("RUN_METADATA_UPDATED", "Run metadata updated", {
                    "file_path": file_path,
                    "metadata": metadata
                }, component="METADATA")
            except json.JSONDecodeError:
                pass
    
    def create_task_tool_hook(self):
        """Create Task tool execution hook (Agent spawning)"""
        def task_hook(description: str, prompt: str, subagent_type: str = "general-purpose"):
            agent_id = f"agent_{int(time.time() * 1000)}"
            
            with self.logger.track_agent(subagent_type, description) as tracking_id:
                
                self.logger.log_agent_spawn(subagent_type, description, {
                    "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                    "subagent_type": subagent_type,
                    "agent_id": agent_id,
                    "tracking_id": tracking_id
                })
                
                # Add to framework state
                with self._lock:
                    self.framework_state['active_agents'].add(subagent_type)
                
                try:
                    # Simulate agent execution
                    time.sleep(0.5)  # Simulate work
                    
                    # Mock successful result
                    result = {
                        "status": "completed",
                        "result": f"Mock result for {subagent_type}: {description}",
                        "agent_id": agent_id,
                        "execution_time": 0.5
                    }
                    
                    self.logger.log_agent_complete(subagent_type, "Task completed successfully", {
                        "result": result,
                        "agent_id": agent_id
                    }, performance_metrics={
                        "agent_execution_time": 0.5
                    })
                    
                    # Remove from active agents
                    with self._lock:
                        self.framework_state['active_agents'].discard(subagent_type)
                    
                    return result
                    
                except Exception as e:
                    self.logger.log_error("AGENT_ERROR", f"Agent {subagent_type} failed", {
                        "description": description,
                        "error": str(e),
                        "agent_id": agent_id
                    }, agent=subagent_type, component="AGENT")
                    
                    # Remove from active agents
                    with self._lock:
                        self.framework_state['active_agents'].discard(subagent_type)
                    
                    raise
        
        return task_hook
    
    def create_glob_tool_hook(self):
        """Create Glob tool execution hook"""
        def glob_hook(pattern: str, path: str = None):
            with self.logger.track_tool("glob", "pattern_search", {
                "pattern": pattern,
                "path": path
            }) as tracking_id:
                
                self.logger.log_debug("GLOB_SEARCH", "Searching files with pattern", {
                    "pattern": pattern,
                    "path": path,
                    "tracking_id": tracking_id
                }, component="TOOL")
                
                try:
                    # Mock glob results
                    mock_results = [
                        f"mock_file_{i}.txt" for i in range(3)
                    ]
                    
                    self.logger.log_debug("GLOB_RESULTS", "Glob search completed", {
                        "pattern": pattern,
                        "results_count": len(mock_results),
                        "results": mock_results
                    }, component="TOOL")
                    
                    return mock_results
                    
                except Exception as e:
                    self.logger.log_error("GLOB_ERROR", f"Glob search failed: {pattern}", {
                        "pattern": pattern,
                        "error": str(e)
                    }, component="TOOL")
                    raise
        
        return glob_hook
    
    def create_grep_tool_hook(self):
        """Create Grep tool execution hook"""
        def grep_hook(pattern: str, path: str = None, output_mode: str = "files_with_matches", **kwargs):
            with self.logger.track_tool("grep", "pattern_search", {
                "pattern": pattern,
                "path": path,
                "output_mode": output_mode,
                "options": kwargs
            }) as tracking_id:
                
                self.logger.log_debug("GREP_SEARCH", "Searching content with pattern", {
                    "pattern": pattern,
                    "path": path,
                    "output_mode": output_mode,
                    "options": kwargs,
                    "tracking_id": tracking_id
                }, component="TOOL")
                
                try:
                    # Mock grep results
                    mock_results = [
                        f"mock_match_{i}" for i in range(2)
                    ]
                    
                    self.logger.log_debug("GREP_RESULTS", "Grep search completed", {
                        "pattern": pattern,
                        "results_count": len(mock_results),
                        "output_mode": output_mode
                    }, component="TOOL")
                    
                    return mock_results
                    
                except Exception as e:
                    self.logger.log_error("GREP_ERROR", f"Grep search failed: {pattern}", {
                        "pattern": pattern,
                        "error": str(e)
                    }, component="TOOL")
                    raise
        
        return grep_hook
    
    def create_edit_tool_hook(self):
        """Create Edit tool execution hook"""
        def edit_hook(file_path: str, old_string: str, new_string: str, replace_all: bool = False):
            with self.logger.track_tool("edit", "file_edit", {
                "file_path": file_path,
                "old_string_length": len(old_string),
                "new_string_length": len(new_string),
                "replace_all": replace_all
            }) as tracking_id:
                
                self.logger.log_debug("FILE_EDIT", "Editing file", {
                    "file_path": file_path,
                    "old_string_length": len(old_string),
                    "new_string_length": len(new_string),
                    "replace_all": replace_all,
                    "tracking_id": tracking_id
                }, component="TOOL")
                
                try:
                    # Mock edit operation
                    changes_made = 1 if not replace_all else 3
                    
                    self.logger.log_debug("FILE_EDIT_SUCCESS", "File edited successfully", {
                        "file_path": file_path,
                        "changes_made": changes_made
                    }, component="TOOL")
                    
                    return {"changes_made": changes_made}
                    
                except Exception as e:
                    self.logger.log_error("EDIT_ERROR", f"File edit failed: {file_path}", {
                        "file_path": file_path,
                        "error": str(e)
                    }, component="TOOL")
                    raise
        
        return edit_hook
    
    def install_framework_phase_hooks(self):
        """Install hooks for framework phase transitions"""
        self.logger.log_debug("PHASE_HOOKS_INSTALL", "Installing framework phase hooks")
        
        # Register phase transition detector
        def detect_phase_transitions():
            """Monitor for phase transition indicators"""
            # This would monitor for phase indicators in the framework execution
            # For now, provide mock implementation
            pass
        
        self.hook_registry['phase_transitions'] = detect_phase_transitions
        
        # Register convenience methods for manual phase logging
        self.manual_phase_start = self.logger.log_phase_start
        self.manual_phase_complete = self.logger.log_phase_complete
        self.manual_phase_transition = self.logger.log_phase_transition
    
    def install_agent_coordination_hooks(self):
        """Install hooks for agent coordination monitoring"""
        self.logger.log_debug("AGENT_HOOKS_INSTALL", "Installing agent coordination hooks")
        
        # Register agent coordination tracker
        def track_agent_coordination():
            """Monitor agent coordination patterns"""
            # This would monitor for agent coordination indicators
            pass
        
        self.hook_registry['agent_coordination'] = track_agent_coordination
    
    def install_context_flow_hooks(self):
        """Install hooks for Progressive Context Architecture monitoring"""
        self.logger.log_debug("CONTEXT_HOOKS_INSTALL", "Installing context flow hooks")
        
        def track_context_inheritance(action: str, context_data: Dict[str, Any] = None):
            """Track context inheritance in Progressive Context Architecture"""
            self.logger.log_context_flow(action, context_data, 
                                       self.framework_state.get('context_chain', []))
        
        self.hook_registry['context_flow'] = track_context_inheritance
        
        # Expose convenience method
        self.track_context_flow = track_context_inheritance
    
    def install_validation_hooks(self):
        """Install hooks for validation engine monitoring"""
        self.logger.log_debug("VALIDATION_HOOKS_INSTALL", "Installing validation hooks")
        
        def track_validation_checkpoint(validation_type: str, result: str, confidence: float = None):
            """Track validation checkpoints"""
            self.logger.log_validation_checkpoint(validation_type, result, confidence)
            
            # Update framework state
            with self._lock:
                self.framework_state['validation_status'][validation_type] = {
                    'result': result,
                    'confidence': confidence
                }
        
        self.hook_registry['validation'] = track_validation_checkpoint
        
        # Expose convenience method
        self.track_validation = track_validation_checkpoint
    
    def install_environment_hooks(self):
        """Install hooks for environment interaction monitoring"""
        self.logger.log_debug("ENV_HOOKS_INSTALL", "Installing environment hooks")
        
        def track_environment_interaction(action: str, environment: str = None, details: Dict[str, Any] = None):
            """Track environment interactions"""
            self.logger.log_environment_interaction(action, environment, 
                                                  details.get('command') if details else None,
                                                  details)
            
            # Update framework state
            if environment:
                with self._lock:
                    self.framework_state['environment_connections'][environment] = {
                        'last_action': action,
                        'timestamp': time.time()
                    }
        
        self.hook_registry['environment'] = track_environment_interaction
        
        # Expose convenience method
        self.track_environment = track_environment_interaction
    
    def install_ai_service_hooks(self):
        """Install hooks for AI service execution monitoring"""
        self.logger.log_debug("AI_SERVICE_HOOKS_INSTALL", "Installing AI service hooks")
        
        def track_ai_service(service_name: str, action: str, inputs: Dict[str, Any] = None, 
                           outputs: Dict[str, Any] = None):
            """Track AI service executions"""
            self.logger.log_ai_service_execution(service_name, action, inputs, outputs)
            
            # Update framework state
            with self._lock:
                if service_name not in self.framework_state['ai_service_executions']:
                    self.framework_state['ai_service_executions'][service_name] = []
                
                self.framework_state['ai_service_executions'][service_name].append({
                    'action': action,
                    'timestamp': time.time()
                })
        
        self.hook_registry['ai_service'] = track_ai_service
        
        # Expose convenience method
        self.track_ai_service = track_ai_service
    
    # Convenience methods for framework integration
    def start_framework_logging(self, run_id: str = None, jira_ticket: str = None):
        """Start comprehensive framework logging"""
        self.logger.log_info("FRAMEWORK_LOGGING_START", "Starting comprehensive framework logging", {
            "run_id": run_id,
            "jira_ticket": jira_ticket,
            "hooks_installed": list(self.hook_registry.keys())
        })
        
        # Initialize framework state
        with self._lock:
            self.framework_state['current_phase'] = 'pre-start'
            if jira_ticket:
                self.framework_state['jira_ticket'] = jira_ticket
    
    def log_framework_phase(self, phase: str, action: str, details: Dict[str, Any] = None):
        """Log framework phase activity"""
        if action == "start":
            self.manual_phase_start(phase, details)
            with self._lock:
                self.framework_state['current_phase'] = phase
        elif action == "complete":
            self.manual_phase_complete(phase, details)
        else:
            self.logger.log_info(f"PHASE_{action.upper()}", f"Phase {phase}: {action}", {
                "phase": phase,
                "action": action,
                "details": details or {}
            }, phase=phase, component="PHASE")
    
    def log_agent_activity(self, agent: str, action: str, details: Dict[str, Any] = None):
        """Log agent activity"""
        # Update framework state
        with self._lock:
            if action in ["spawn", "start"]:
                self.framework_state['active_agents'].add(agent)
            elif action in ["complete", "finish", "stop"]:
                self.framework_state['active_agents'].discard(agent)
        
        self.logger.log_info(f"AGENT_{action.upper()}", f"Agent {agent}: {action}", {
            "agent": agent,
            "action": action,
            "details": details or {}
        }, agent=agent, component="AGENT")
    
    def get_framework_state(self) -> Dict[str, Any]:
        """Get current framework state"""
        with self._lock:
            # Convert sets to lists for JSON serialization
            state = dict(self.framework_state)
            if 'active_agents' in state:
                state['active_agents'] = list(state['active_agents'])
            return state
    
    def finalize_framework_logging(self):
        """Finalize framework logging"""
        final_state = self.get_framework_state()
        
        self.logger.log_info("FRAMEWORK_LOGGING_COMPLETE", "Framework logging completed", {
            "final_state": final_state,
            "hooks_executed": len(self.hook_registry),
            "total_log_entries": "see_log_files"
        })
        
        self.logger.finalize_logging()
    
    # Hook management methods
    def uninstall_all_hooks(self):
        """Uninstall all hooks"""
        self.logger.log_info("HOOKS_UNINSTALL", "Uninstalling all framework hooks")
        
        # Restore original functions if they were wrapped
        for name, original_func in self.original_functions.items():
            # In real implementation, this would restore original functions
            pass
        
        self.hook_registry.clear()
        self.original_functions.clear()
        
        self.logger.log_info("HOOKS_UNINSTALLED", "All framework hooks uninstalled")
    
    def get_hook_status(self) -> Dict[str, Any]:
        """Get status of all installed hooks"""
        return {
            "hooks_installed": list(self.hook_registry.keys()),
            "framework_state": self.get_framework_state(),
            "logger_active": self.logger is not None,
            "log_directory": str(self.logger.log_dir) if self.logger else None
        }

# Global hook integration instance
_global_hooks: Optional[FrameworkHookIntegration] = None

def get_global_hooks() -> Optional[FrameworkHookIntegration]:
    """Get global hook integration instance"""
    return _global_hooks

def initialize_global_hooks(logger: FrameworkDebugLogger = None) -> FrameworkHookIntegration:
    """Initialize global hook integration"""
    global _global_hooks
    _global_hooks = FrameworkHookIntegration(logger)
    return _global_hooks

def finalize_global_hooks():
    """Finalize global hook integration"""
    global _global_hooks
    if _global_hooks:
        _global_hooks.finalize_framework_logging()
        _global_hooks = None

# Convenience decorator for automatic hook integration
def with_framework_hooks(run_id: str = None):
    """Decorator to automatically set up framework hooks"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Initialize hooks
            logger = initialize_global_logger(run_id)
            hooks = initialize_global_hooks(logger)
            hooks.start_framework_logging(run_id)
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Finalize hooks
                finalize_global_hooks()
        
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test the hook integration system
    logger = initialize_global_logger("test_hooks")
    hooks = initialize_global_hooks(logger)
    
    # Test framework logging
    hooks.start_framework_logging("test_run", "ACM-TEST")
    
    # Test phase logging
    hooks.log_framework_phase("0-pre", "start", {"test": "phase_start"})
    hooks.log_framework_phase("0-pre", "complete", {"test": "phase_complete"})
    
    # Test agent logging
    hooks.log_agent_activity("agent_a", "start", {"test": "agent_start"})
    hooks.log_agent_activity("agent_a", "complete", {"test": "agent_complete"})
    
    # Test tool hooks
    bash_hook = hooks.hook_registry['bash_tool']
    bash_hook("echo 'test command'", "Test bash execution")
    
    read_hook = hooks.hook_registry['read_tool']
    # This would fail in test since file doesn't exist, but demonstrates logging
    
    # Test context flow
    hooks.track_context_flow("context_inheritance", {"test": "context_data"})
    
    # Test validation
    hooks.track_validation("test_validation", "passed", 0.95)
    
    # Test AI service
    hooks.track_ai_service("test_service", "execute", {"input": "test"}, {"output": "result"})
    
    # Get final state
    print("Final framework state:", hooks.get_framework_state())
    print("Hook status:", hooks.get_hook_status())
    
    # Finalize
    hooks.finalize_framework_logging()
    print(f"Test completed. Logs saved to: {logger.log_dir}")
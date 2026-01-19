#!/usr/bin/env python3
"""
Comprehensive Command Interceptor - Captures ALL Agent Command Executions
========================================================================

This interceptor hooks into subprocess.run() calls to capture detailed command
execution logs from agents including:
- oc commands (environment assessment)
- jira CLI commands (JIRA data collection) 
- All tool interactions with real data

SOLVES: Agent internal activities not being captured by hooks
PROVIDES: Complete command-level execution logging with real data
"""

import os
import sys
import json
import subprocess
import threading
import functools
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

# Import mandatory logger
from mandatory_comprehensive_logger import get_mandatory_logger

class ComprehensiveCommandInterceptor:
    """Intercepts and logs ALL subprocess command executions during agent execution"""
    
    def __init__(self, jira_ticket: str = None):
        self.jira_ticket = jira_ticket
        self.logger = get_mandatory_logger(jira_ticket)
        self.active = False
        self.original_subprocess_run = None
        self.command_count = 0
        self.captured_commands = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        print(f"🎯 COMPREHENSIVE COMMAND INTERCEPTOR INITIALIZED: {jira_ticket}")
    
    def activate_interception(self):
        """Activate command interception by hooking subprocess.run"""
        if self.active:
            return
        
        with self._lock:
            # Store original subprocess.run
            self.original_subprocess_run = subprocess.run
            
            # Replace with our hooked version
            subprocess.run = self._hooked_subprocess_run
            
            self.active = True
            
            self.logger.log_framework_phase(
                phase="command_interception",
                operation="activate", 
                details={
                    "interception_active": True,
                    "subprocess_hooked": True,
                    "capture_mode": "comprehensive"
                }
            )
            
            print("🎯 Command interception ACTIVATED - All subprocess calls will be logged")
    
    def deactivate_interception(self):
        """Deactivate command interception and restore original subprocess.run"""
        if not self.active:
            return
        
        with self._lock:
            # Restore original subprocess.run
            if self.original_subprocess_run:
                subprocess.run = self.original_subprocess_run
            
            self.active = False
            
            self.logger.log_framework_phase(
                phase="command_interception",
                operation="deactivate",
                details={
                    "commands_captured": len(self.captured_commands),
                    "total_command_count": self.command_count
                }
            )
            
            print(f"🎯 Command interception DEACTIVATED - Captured {len(self.captured_commands)} commands")
    
    def _hooked_subprocess_run(self, *args, **kwargs):
        """Hooked version of subprocess.run that logs all command executions"""
        with self._lock:
            self.command_count += 1
            
            # Extract command information
            if args:
                cmd = args[0]
            else:
                cmd = kwargs.get('args', ['unknown'])
            
            # Convert command to string for analysis
            if isinstance(cmd, list):
                cmd_str = ' '.join(str(x) for x in cmd)
                cmd_list = cmd
            else:
                cmd_str = str(cmd)
                cmd_list = [cmd_str]
            
            # Determine command type and context
            cmd_type = self._classify_command(cmd_str)
            execution_context = self._determine_execution_context()
            
            start_time = datetime.now()
            
            # Log command start
            self.logger.log_tool_execution(
                tool_name=cmd_list[0] if cmd_list else 'unknown',
                parameters={
                    "command": cmd_str,
                    "command_type": cmd_type,
                    "execution_context": execution_context,
                    "interception_active": True,
                    "command_number": self.command_count
                }
            )
            
            print(f"🔍 INTERCEPTED: {cmd_str[:80]}{'...' if len(cmd_str) > 80 else ''}")
            
            try:
                # Execute the original command
                result = self.original_subprocess_run(*args, **kwargs)
                
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                
                # Extract result data
                stdout = getattr(result, 'stdout', '')
                stderr = getattr(result, 'stderr', '')
                returncode = getattr(result, 'returncode', 0)
                
                # Log detailed command result
                command_data = {
                    "timestamp": start_time.isoformat(),
                    "command": cmd_str,
                    "command_type": cmd_type,
                    "execution_context": execution_context,
                    "return_code": returncode,
                    "success": returncode == 0,
                    "stdout": stdout.strip() if isinstance(stdout, str) else str(stdout),
                    "stderr": stderr.strip() if isinstance(stderr, str) else str(stderr),
                    "execution_time": execution_time,
                    "command_number": self.command_count,
                    "real_execution": True,
                    "intercepted": True
                }
                
                self.captured_commands.append(command_data)
                
                # Log to comprehensive system
                self.logger.log_tool_execution(
                    tool_name=cmd_list[0] if cmd_list else 'unknown',
                    parameters={
                        "command": cmd_str,
                        "command_type": cmd_type,
                        "execution_context": execution_context,
                        "interception_complete": True
                    },
                    response={
                        "return_code": returncode,
                        "success": returncode == 0,
                        "stdout": stdout.strip() if isinstance(stdout, str) else str(stdout),
                        "stderr": stderr.strip() if isinstance(stderr, str) else str(stderr),
                        "execution_time": execution_time
                    }
                )
                
                # Save command to specialized logs
                self._save_command_specific_logs(command_data)
                
                success_indicator = "✅" if returncode == 0 else "❌"
                print(f"  {success_indicator} Result: {returncode} | Output: {str(stdout)[:50]}{'...' if len(str(stdout)) > 50 else ''}")
                
                return result
                
            except Exception as e:
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                
                # Log command error
                error_data = {
                    "timestamp": start_time.isoformat(),
                    "command": cmd_str,
                    "command_type": cmd_type,
                    "execution_context": execution_context,
                    "error": str(e),
                    "execution_time": execution_time,
                    "command_number": self.command_count,
                    "real_execution": True,
                    "intercepted": True,
                    "failed": True
                }
                
                self.captured_commands.append(error_data)
                
                self.logger.log_error(
                    "COMMAND_EXECUTION_ERROR",
                    f"Intercepted command failed: {cmd_str}",
                    {
                        "command": cmd_str,
                        "error": str(e),
                        "command_type": cmd_type,
                        "execution_time": execution_time
                    }
                )
                
                print(f"  ❌ Command failed: {e}")
                
                # Re-raise the exception to maintain original behavior
                raise
    
    def _classify_command(self, cmd_str: str) -> str:
        """Classify the type of command being executed"""
        cmd_lower = cmd_str.lower()
        
        if 'oc ' in cmd_lower:
            if 'whoami' in cmd_lower:
                return 'openshift_authentication'
            elif 'get nodes' in cmd_lower:
                return 'openshift_cluster_topology'
            elif 'get ns' in cmd_lower or 'get namespaces' in cmd_lower:
                return 'openshift_namespace_discovery'
            elif 'cluster-info' in cmd_lower:
                return 'openshift_cluster_info'
            elif 'get managedclusters' in cmd_lower:
                return 'acm_managed_clusters'
            elif 'login' in cmd_lower:
                return 'openshift_authentication'
            else:
                return 'openshift_command'
        
        elif 'jira ' in cmd_lower:
            if 'issue view' in cmd_lower:
                return 'jira_issue_retrieval'
            elif 'issue list' in cmd_lower:
                return 'jira_issue_search'
            else:
                return 'jira_command'
        
        elif 'kubectl' in cmd_lower:
            return 'kubernetes_command'
        
        elif 'gh ' in cmd_lower:
            return 'github_command'
        
        elif any(tool in cmd_lower for tool in ['curl', 'wget']):
            return 'http_request'
        
        else:
            return 'general_command'
    
    def _determine_execution_context(self) -> str:
        """Determine the context of command execution"""
        import inspect
        
        # Get the call stack to determine context
        stack = inspect.stack()
        
        for frame_info in stack:
            filename = frame_info.filename
            function_name = frame_info.function
            
            if 'agent_' in filename:
                if 'jira' in filename:
                    return 'agent_a_jira_intelligence'
                elif 'environment' in filename:
                    return 'agent_d_environment_intelligence'
                else:
                    return 'agent_execution'
            elif 'jira_api_client' in filename:
                return 'jira_data_collection'
            elif 'environment_assessment' in filename:
                return 'environment_assessment'
        
        return 'framework_execution'
    
    def _save_command_specific_logs(self, command_data: Dict[str, Any]):
        """Save command data to specialized log files"""
        try:
            # Create command-specific directory
            cmd_log_dir = self.logger.run_log_dir / "commands"
            cmd_log_dir.mkdir(exist_ok=True)
            
            # Save by command type
            cmd_type = command_data.get('command_type', 'unknown')
            cmd_type_file = cmd_log_dir / f"{cmd_type}_commands.jsonl"
            
            with open(cmd_type_file, 'a') as f:
                f.write(json.dumps(command_data) + '\n')
            
            # Save to master commands log
            master_cmd_file = cmd_log_dir / "all_commands.jsonl"
            with open(master_cmd_file, 'a') as f:
                f.write(json.dumps(command_data) + '\n')
                
        except Exception as e:
            print(f"Failed to save command-specific logs: {e}")
    
    def get_captured_commands(self) -> List[Dict[str, Any]]:
        """Get all captured commands"""
        with self._lock:
            return self.captured_commands.copy()
    
    def get_command_summary(self) -> Dict[str, Any]:
        """Get summary of captured commands"""
        with self._lock:
            total_commands = len(self.captured_commands)
            successful_commands = sum(1 for cmd in self.captured_commands if cmd.get('success', False))
            
            command_types = {}
            for cmd in self.captured_commands:
                cmd_type = cmd.get('command_type', 'unknown')
                command_types[cmd_type] = command_types.get(cmd_type, 0) + 1
            
            return {
                "total_commands": total_commands,
                "successful_commands": successful_commands,
                "failed_commands": total_commands - successful_commands,
                "command_types": command_types,
                "interception_active": self.active
            }


# Global interceptor instance
_global_interceptor = None

def get_global_command_interceptor(jira_ticket: str = None) -> ComprehensiveCommandInterceptor:
    """Get or create global command interceptor"""
    global _global_interceptor
    if _global_interceptor is None:
        _global_interceptor = ComprehensiveCommandInterceptor(jira_ticket)
    return _global_interceptor

def activate_comprehensive_command_interception(jira_ticket: str = None):
    """Activate comprehensive command interception globally"""
    interceptor = get_global_command_interceptor(jira_ticket)
    interceptor.activate_interception()
    return interceptor

def deactivate_comprehensive_command_interception():
    """Deactivate comprehensive command interception globally"""
    global _global_interceptor
    if _global_interceptor:
        _global_interceptor.deactivate_interception()
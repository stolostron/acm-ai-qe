#!/usr/bin/env python3
"""
Framework Debug Logger - Comprehensive Logging and Debugging Hook System

Purpose: Track every phase, task, agent activity, data flow, terminal commands,
and validation checkpoints for complete framework observability and debugging.

Author: AI Systems Suite
Version: 1.0.0
"""

import json
import time
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import traceback
import inspect
import sys
import os

@dataclass
class LogEntry:
    """Structured log entry for framework debugging"""
    timestamp: str
    run_id: str
    session_id: str
    log_level: str  # DEBUG, INFO, WARN, ERROR, CRITICAL
    component: str  # PHASE, AGENT, TOOL, VALIDATION, CONTEXT, ENVIRONMENT
    action: str
    details: Dict[str, Any]
    phase: Optional[str] = None
    agent: Optional[str] = None
    execution_context: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    data_snapshot: Optional[Dict[str, Any]] = None

class FrameworkDebugLogger:
    """
    Comprehensive framework debugging and logging system
    
    Provides hooks for:
    - Phase transitions (0-Pre through 5)
    - Agent spawning and coordination (A, B, C, D)
    - Tool executions (Bash, Read, Write, Task, etc.)
    - Context flow in Progressive Context Architecture
    - Validation engine checkpoints
    - Environment interactions
    - AI service executions
    - Performance monitoring
    """
    
    def __init__(self, run_id: str = None, base_log_dir: str = None):
        self.run_id = run_id or self._generate_run_id()
        self.session_id = str(uuid.uuid4())[:8]
        self.base_log_dir = Path(base_log_dir or ".claude/logging")
        
        # Initialize logging infrastructure
        self._initialize_logging_infrastructure()
        
        # State tracking
        self.current_phase = None
        self.active_agents = set()
        self.context_inheritance_chain = []
        self.validation_checkpoints = {}
        self.performance_metrics = {}
        self.tool_execution_stack = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Hook registry
        self.hooks = {
            'phase_transition': [],
            'agent_spawn': [],
            'agent_complete': [],
            'tool_execution': [],
            'context_flow': [],
            'validation_checkpoint': [],
            'environment_interaction': [],
            'ai_service_execution': [],
            'error_detected': [],
            'performance_metric': []
        }
        
        # Initialize comprehensive logging
        self.log_info("FRAMEWORK_START", "Framework Debug Logger initialized", {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "log_directory": str(self.log_dir),
            "timestamp": self._get_timestamp()
        })
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID"""
        return f"DEBUG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    def _get_timestamp(self) -> str:
        """Get ISO timestamp with timezone"""
        return datetime.now(timezone.utc).isoformat()
    
    def _initialize_logging_infrastructure(self):
        """Initialize comprehensive logging directory structure"""
        self.log_dir = self.base_log_dir / self.run_id
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create specialized log directories
        self.directories = {
            'phases': self.log_dir / 'phases',
            'agents': self.log_dir / 'agents', 
            'tools': self.log_dir / 'tools',
            'context': self.log_dir / 'context',
            'validation': self.log_dir / 'validation',
            'environment': self.log_dir / 'environment',
            'performance': self.log_dir / 'performance',
            'errors': self.log_dir / 'errors',
            'raw': self.log_dir / 'raw'
        }
        
        for directory in self.directories.values():
            directory.mkdir(exist_ok=True)
        
        # Initialize log files
        self.log_files = {
            'master': self.log_dir / 'framework_debug_master.jsonl',
            'human_readable': self.log_dir / 'framework_debug_readable.log',
            'summary': self.log_dir / 'execution_summary.json',
            'performance': self.log_dir / 'performance_metrics.json',
            'errors': self.log_dir / 'error_log.jsonl'
        }
        
        # Initialize real-time log streams
        self._initialize_log_streams()
    
    def _initialize_log_streams(self):
        """Initialize real-time log streaming files"""
        # Create empty log files
        for log_file in self.log_files.values():
            log_file.touch()
        
        # Initialize summary structure
        summary = {
            "run_metadata": {
                "run_id": self.run_id,
                "session_id": self.session_id,
                "start_time": self._get_timestamp(),
                "status": "in_progress"
            },
            "execution_timeline": [],
            "agent_summary": {},
            "phase_summary": {},
            "tool_usage": {},
            "context_flow": [],
            "validation_results": {},
            "performance_summary": {},
            "error_summary": {}
        }
        
        with open(self.log_files['summary'], 'w') as f:
            json.dump(summary, f, indent=2)
    
    def log_entry(self, entry: LogEntry):
        """Log structured entry to all appropriate destinations"""
        with self._lock:
            # Convert to dictionary
            entry_dict = asdict(entry)
            
            # Write to master JSONL
            with open(self.log_files['master'], 'a') as f:
                f.write(json.dumps(entry_dict) + '\n')
            
            # Write human-readable format
            human_readable = self._format_human_readable(entry)
            with open(self.log_files['human_readable'], 'a') as f:
                f.write(human_readable + '\n')
            
            # Write to component-specific logs
            self._write_component_specific_logs(entry)
            
            # Update real-time summary
            self._update_execution_summary(entry)
            
            # Trigger hooks
            self._trigger_hooks(entry)
    
    def _format_human_readable(self, entry: LogEntry) -> str:
        """Format log entry for human readability"""
        timestamp = entry.timestamp.split('T')[1][:8]  # HH:MM:SS
        
        # Build main log line
        main_line = f"[{timestamp}] [{entry.log_level:5}] [{entry.component:12}] {entry.action}"
        
        if entry.phase:
            main_line += f" | Phase: {entry.phase}"
        if entry.agent:
            main_line += f" | Agent: {entry.agent}"
        
        # Add details on separate lines if complex
        details_str = ""
        if entry.details and len(entry.details) > 0:
            if len(str(entry.details)) > 100:
                details_str = f"\n    Details: {json.dumps(entry.details, indent=6)}"
            else:
                details_str = f" | Details: {entry.details}"
        
        return main_line + details_str
    
    def _write_component_specific_logs(self, entry: LogEntry):
        """Write entry to component-specific log files"""
        component_map = {
            'PHASE': 'phases',
            'AGENT': 'agents',
            'TOOL': 'tools',
            'CONTEXT': 'context',
            'VALIDATION': 'validation',
            'ENVIRONMENT': 'environment'
        }
        
        if entry.component in component_map:
            component_dir = self.directories[component_map[entry.component]]
            
            # Create component-specific log file
            if entry.phase:
                log_file = component_dir / f"{entry.component.lower()}_{entry.phase}.jsonl"
            elif entry.agent:
                log_file = component_dir / f"{entry.component.lower()}_{entry.agent}.jsonl"
            else:
                log_file = component_dir / f"{entry.component.lower()}_general.jsonl"
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(asdict(entry)) + '\n')
    
    def _update_execution_summary(self, entry: LogEntry):
        """Update real-time execution summary"""
        try:
            with open(self.log_files['summary'], 'r') as f:
                summary = json.load(f)
            
            # Update timeline
            summary['execution_timeline'].append({
                'timestamp': entry.timestamp,
                'component': entry.component,
                'action': entry.action,
                'phase': entry.phase,
                'agent': entry.agent
            })
            
            # Update component summaries
            if entry.component == 'PHASE':
                if entry.phase not in summary['phase_summary']:
                    summary['phase_summary'][entry.phase] = {
                        'start_time': entry.timestamp,
                        'actions': [],
                        'status': 'in_progress'
                    }
                summary['phase_summary'][entry.phase]['actions'].append(entry.action)
                
                if 'complete' in entry.action.lower():
                    summary['phase_summary'][entry.phase]['status'] = 'completed'
                    summary['phase_summary'][entry.phase]['end_time'] = entry.timestamp
            
            if entry.component == 'AGENT':
                if entry.agent not in summary['agent_summary']:
                    summary['agent_summary'][entry.agent] = {
                        'start_time': entry.timestamp,
                        'actions': [],
                        'status': 'active'
                    }
                summary['agent_summary'][entry.agent]['actions'].append(entry.action)
                
                if 'complete' in entry.action.lower():
                    summary['agent_summary'][entry.agent]['status'] = 'completed'
                    summary['agent_summary'][entry.agent]['end_time'] = entry.timestamp
            
            if entry.component == 'TOOL':
                tool_name = entry.details.get('tool_name', 'unknown')
                if tool_name not in summary['tool_usage']:
                    summary['tool_usage'][tool_name] = 0
                summary['tool_usage'][tool_name] += 1
            
            # Update context flow
            if entry.component == 'CONTEXT':
                summary['context_flow'].append({
                    'timestamp': entry.timestamp,
                    'action': entry.action,
                    'details': entry.details
                })
            
            # Update validation results
            if entry.component == 'VALIDATION':
                validation_type = entry.details.get('validation_type', 'unknown')
                summary['validation_results'][validation_type] = {
                    'timestamp': entry.timestamp,
                    'result': entry.details.get('result', 'unknown'),
                    'confidence': entry.details.get('confidence', 0)
                }
            
            # Update performance metrics
            if entry.performance_metrics:
                summary['performance_summary'].update(entry.performance_metrics)
            
            # Update error summary
            if entry.log_level in ['ERROR', 'CRITICAL']:
                if 'error_count' not in summary['error_summary']:
                    summary['error_summary']['error_count'] = 0
                summary['error_summary']['error_count'] += 1
                
                if 'recent_errors' not in summary['error_summary']:
                    summary['error_summary']['recent_errors'] = []
                
                summary['error_summary']['recent_errors'].append({
                    'timestamp': entry.timestamp,
                    'component': entry.component,
                    'action': entry.action,
                    'details': entry.details
                })
                
                # Keep only last 10 errors
                summary['error_summary']['recent_errors'] = summary['error_summary']['recent_errors'][-10:]
            
            # Write updated summary
            with open(self.log_files['summary'], 'w') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            self.log_error("SUMMARY_UPDATE", f"Failed to update execution summary: {e}", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    
    def _trigger_hooks(self, entry: LogEntry):
        """Trigger registered hooks for log entry"""
        try:
            # Determine hook types to trigger
            hook_types = []
            
            if entry.component == 'PHASE':
                hook_types.append('phase_transition')
            elif entry.component == 'AGENT':
                if 'spawn' in entry.action.lower():
                    hook_types.append('agent_spawn')
                elif 'complete' in entry.action.lower():
                    hook_types.append('agent_complete')
            elif entry.component == 'TOOL':
                hook_types.append('tool_execution')
            elif entry.component == 'CONTEXT':
                hook_types.append('context_flow')
            elif entry.component == 'VALIDATION':
                hook_types.append('validation_checkpoint')
            elif entry.component == 'ENVIRONMENT':
                hook_types.append('environment_interaction')
            
            if entry.log_level in ['ERROR', 'CRITICAL']:
                hook_types.append('error_detected')
            
            if entry.performance_metrics:
                hook_types.append('performance_metric')
            
            # Execute hooks
            for hook_type in hook_types:
                for hook_func in self.hooks.get(hook_type, []):
                    try:
                        hook_func(entry)
                    except Exception as hook_error:
                        self.log_error("HOOK_ERROR", f"Hook {hook_func.__name__} failed", {
                            "hook_type": hook_type,
                            "error": str(hook_error),
                            "traceback": traceback.format_exc()
                        })
                        
        except Exception as e:
            # Don't log error here to avoid infinite recursion
            print(f"Hook trigger error: {e}")
    
    # Convenience logging methods
    def log_debug(self, action: str, message: str, details: Dict[str, Any] = None, 
                  phase: str = None, agent: str = None, component: str = "DEBUG",
                  performance_metrics: Dict[str, Any] = None):
        """Log debug message"""
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            run_id=self.run_id,
            session_id=self.session_id,
            log_level="DEBUG",
            component=component,
            action=action,
            details=details or {},
            phase=phase,
            agent=agent,
            performance_metrics=performance_metrics
        )
        self.log_entry(entry)
    
    def log_info(self, action: str, message: str, details: Dict[str, Any] = None,
                 phase: str = None, agent: str = None, component: str = "INFO",
                 performance_metrics: Dict[str, Any] = None):
        """Log info message"""
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            run_id=self.run_id,
            session_id=self.session_id,
            log_level="INFO",
            component=component,
            action=action,
            details=details or {},
            phase=phase,
            agent=agent,
            performance_metrics=performance_metrics
        )
        self.log_entry(entry)
    
    def log_warning(self, action: str, message: str, details: Dict[str, Any] = None,
                   phase: str = None, agent: str = None, component: str = "WARN",
                   performance_metrics: Dict[str, Any] = None):
        """Log warning message"""
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            run_id=self.run_id,
            session_id=self.session_id,
            log_level="WARN",
            component=component,
            action=action,
            details=details or {},
            phase=phase,
            agent=agent,
            performance_metrics=performance_metrics
        )
        self.log_entry(entry)
    
    def log_error(self, action: str, message: str, details: Dict[str, Any] = None,
                  phase: str = None, agent: str = None, component: str = "ERROR",
                  performance_metrics: Dict[str, Any] = None):
        """Log error message"""
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            run_id=self.run_id,
            session_id=self.session_id,
            log_level="ERROR",
            component=component,
            action=action,
            details=details or {},
            phase=phase,
            agent=agent,
            performance_metrics=performance_metrics
        )
        self.log_entry(entry)
        
        # Also write to dedicated error log
        with open(self.log_files['errors'], 'a') as f:
            f.write(json.dumps(asdict(entry)) + '\n')
    
    def log_critical(self, action: str, message: str, details: Dict[str, Any] = None,
                    phase: str = None, agent: str = None, component: str = "CRITICAL",
                    performance_metrics: Dict[str, Any] = None):
        """Log critical message"""
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            run_id=self.run_id,
            session_id=self.session_id,
            log_level="CRITICAL",
            component=component,
            action=action,
            details=details or {},
            phase=phase,
            agent=agent,
            performance_metrics=performance_metrics
        )
        self.log_entry(entry)
        
        # Also write to dedicated error log
        with open(self.log_files['errors'], 'a') as f:
            f.write(json.dumps(asdict(entry)) + '\n')

    # Specialized logging methods for framework components
    def log_phase_transition(self, from_phase: str, to_phase: str, details: Dict[str, Any] = None):
        """Log phase transition"""
        self.current_phase = to_phase
        self.log_info("PHASE_TRANSITION", f"Transitioning from {from_phase} to {to_phase}", {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "transition_details": details or {}
        }, phase=to_phase, component="PHASE")
    
    def log_phase_start(self, phase: str, details: Dict[str, Any] = None):
        """Log phase start"""
        self.current_phase = phase
        self.log_info("PHASE_START", f"Starting phase {phase}", {
            "phase": phase,
            "start_details": details or {}
        }, phase=phase, component="PHASE")
    
    def log_phase_complete(self, phase: str, details: Dict[str, Any] = None, 
                          performance_metrics: Dict[str, Any] = None):
        """Log phase completion"""
        self.log_info("PHASE_COMPLETE", f"Completed phase {phase}", {
            "phase": phase,
            "completion_details": details or {}
        }, phase=phase, component="PHASE", performance_metrics=performance_metrics)
    
    def log_agent_spawn(self, agent: str, task_description: str, details: Dict[str, Any] = None):
        """Log agent spawning"""
        self.active_agents.add(agent)
        self.log_info("AGENT_SPAWN", f"Spawning agent {agent}", {
            "agent": agent,
            "task_description": task_description,
            "spawn_details": details or {}
        }, phase=self.current_phase, agent=agent, component="AGENT")
    
    def log_agent_complete(self, agent: str, result_summary: str, details: Dict[str, Any] = None,
                          performance_metrics: Dict[str, Any] = None):
        """Log agent completion"""
        self.active_agents.discard(agent)
        self.log_info("AGENT_COMPLETE", f"Agent {agent} completed", {
            "agent": agent,
            "result_summary": result_summary,
            "completion_details": details or {}
        }, phase=self.current_phase, agent=agent, component="AGENT", 
        performance_metrics=performance_metrics)
    
    def log_tool_execution(self, tool_name: str, action: str, inputs: Dict[str, Any] = None,
                          outputs: Dict[str, Any] = None, performance_metrics: Dict[str, Any] = None):
        """Log tool execution"""
        execution_id = str(uuid.uuid4())[:8]
        self.tool_execution_stack.append({
            'execution_id': execution_id,
            'tool_name': tool_name,
            'action': action,
            'timestamp': self._get_timestamp()
        })
        
        self.log_debug(action, f"Executing {tool_name}: {action}", {
            "tool_name": tool_name,
            "action": action,
            "execution_id": execution_id,
            "inputs": inputs or {},
            "outputs": outputs or {},
            "stack_depth": len(self.tool_execution_stack)
        }, phase=self.current_phase, component="TOOL", performance_metrics=performance_metrics)
    
    def log_context_flow(self, action: str, context_data: Dict[str, Any] = None,
                        inheritance_chain: List[str] = None):
        """Log Progressive Context Architecture flow"""
        if inheritance_chain:
            self.context_inheritance_chain = inheritance_chain
        
        self.log_debug(action, f"Context flow: {action}", {
            "action": action,
            "context_snapshot": context_data or {},
            "inheritance_chain": self.context_inheritance_chain,
            "context_size": len(str(context_data)) if context_data else 0
        }, phase=self.current_phase, component="CONTEXT")
    
    def log_validation_checkpoint(self, validation_type: str, result: str, confidence: float = None,
                                 details: Dict[str, Any] = None):
        """Log validation checkpoint"""
        self.validation_checkpoints[validation_type] = {
            'result': result,
            'confidence': confidence,
            'timestamp': self._get_timestamp()
        }
        
        self.log_info("VALIDATION_CHECKPOINT", f"Validation {validation_type}: {result}", {
            "validation_type": validation_type,
            "result": result,
            "confidence": confidence,
            "validation_details": details or {}
        }, phase=self.current_phase, component="VALIDATION")
    
    def log_environment_interaction(self, action: str, environment: str = None,
                                   command: str = None, response: Dict[str, Any] = None):
        """Log environment interaction"""
        self.log_debug("ENVIRONMENT_INTERACTION", action, {
            "action": action,
            "environment": environment,
            "command": command,
            "response": response or {}
        }, phase=self.current_phase, component="ENVIRONMENT")
    
    def log_ai_service_execution(self, service_name: str, action: str, 
                                inputs: Dict[str, Any] = None, outputs: Dict[str, Any] = None,
                                performance_metrics: Dict[str, Any] = None):
        """Log AI service execution"""
        self.log_debug("AI_SERVICE_EXECUTION", f"Service {service_name}: {action}", {
            "service_name": service_name,
            "action": action,
            "inputs": inputs or {},
            "outputs": outputs or {},
            "service_performance": performance_metrics or {}
        }, phase=self.current_phase, component="AI_SERVICE", performance_metrics=performance_metrics)
    
    # Hook registration methods
    def register_hook(self, hook_type: str, hook_function):
        """Register a hook function"""
        if hook_type in self.hooks:
            self.hooks[hook_type].append(hook_function)
            self.log_debug("HOOK_REGISTERED", f"Registered {hook_type} hook", {
                "hook_type": hook_type,
                "function_name": hook_function.__name__
            })
        else:
            self.log_warning("HOOK_REGISTRATION_FAILED", f"Unknown hook type: {hook_type}", {
                "hook_type": hook_type,
                "available_types": list(self.hooks.keys())
            })
    
    def unregister_hook(self, hook_type: str, hook_function):
        """Unregister a hook function"""
        if hook_type in self.hooks and hook_function in self.hooks[hook_type]:
            self.hooks[hook_type].remove(hook_function)
            self.log_debug("HOOK_UNREGISTERED", f"Unregistered {hook_type} hook", {
                "hook_type": hook_type,
                "function_name": hook_function.__name__
            })
    
    # Context managers for tracking execution blocks
    @contextmanager
    def track_phase(self, phase: str, details: Dict[str, Any] = None):
        """Context manager for tracking phase execution"""
        start_time = time.time()
        self.log_phase_start(phase, details)
        
        try:
            yield
            
            end_time = time.time()
            performance_metrics = {
                "phase_duration_seconds": end_time - start_time,
                "phase_duration_formatted": f"{end_time - start_time:.2f}s"
            }
            
            self.log_phase_complete(phase, details, performance_metrics)
            
        except Exception as e:
            self.log_error("PHASE_ERROR", f"Phase {phase} failed", {
                "phase": phase,
                "error": str(e),
                "traceback": traceback.format_exc()
            }, phase=phase, component="PHASE")
            raise
    
    @contextmanager
    def track_agent(self, agent: str, task_description: str, details: Dict[str, Any] = None):
        """Context manager for tracking agent execution"""
        start_time = time.time()
        self.log_agent_spawn(agent, task_description, details)
        
        try:
            yield
            
            end_time = time.time()
            performance_metrics = {
                "agent_duration_seconds": end_time - start_time,
                "agent_duration_formatted": f"{end_time - start_time:.2f}s"
            }
            
            self.log_agent_complete(agent, "Task completed successfully", details, performance_metrics)
            
        except Exception as e:
            self.log_error("AGENT_ERROR", f"Agent {agent} failed", {
                "agent": agent,
                "task_description": task_description,
                "error": str(e),
                "traceback": traceback.format_exc()
            }, agent=agent, component="AGENT")
            raise
    
    @contextmanager
    def track_tool(self, tool_name: str, action: str, inputs: Dict[str, Any] = None):
        """Context manager for tracking tool execution"""
        start_time = time.time()
        execution_id = str(uuid.uuid4())[:8]
        
        self.log_tool_execution(tool_name, f"STARTING_{action}", inputs, performance_metrics={
            "execution_id": execution_id,
            "start_time": start_time
        })
        
        try:
            yield execution_id
            
            end_time = time.time()
            performance_metrics = {
                "execution_id": execution_id,
                "tool_duration_seconds": end_time - start_time,
                "tool_duration_formatted": f"{end_time - start_time:.2f}s",
                "status": "SUCCESS"
            }
            
            self.log_tool_execution(tool_name, f"COMPLETED_{action}", inputs, 
                                  outputs={"status": "success"}, performance_metrics=performance_metrics)
            
        except Exception as e:
            end_time = time.time()
            performance_metrics = {
                "execution_id": execution_id,
                "tool_duration_seconds": end_time - start_time,
                "tool_duration_formatted": f"{end_time - start_time:.2f}s",
                "status": "ERROR"
            }
            
            self.log_tool_execution(tool_name, f"FAILED_{action}", inputs,
                                  outputs={"error": str(e)}, performance_metrics=performance_metrics)
            
            self.log_error("TOOL_ERROR", f"Tool {tool_name} failed during {action}", {
                "tool_name": tool_name,
                "action": action,
                "inputs": inputs or {},
                "error": str(e),
                "traceback": traceback.format_exc(),
                "execution_id": execution_id
            }, component="TOOL")
            raise
    
    # Utility methods
    def get_current_state(self) -> Dict[str, Any]:
        """Get current framework state"""
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "current_phase": self.current_phase,
            "active_agents": list(self.active_agents),
            "context_inheritance_chain": self.context_inheritance_chain,
            "validation_checkpoints": self.validation_checkpoints,
            "tool_execution_stack": self.tool_execution_stack,
            "log_directory": str(self.log_dir)
        }
    
    def finalize_logging(self):
        """Finalize logging session"""
        self.log_info("FRAMEWORK_COMPLETE", "Framework execution completed", {
            "final_state": self.get_current_state(),
            "total_log_files": len(list(self.log_dir.rglob("*.jsonl"))) + len(list(self.log_dir.rglob("*.log"))),
            "log_directory_size": sum(f.stat().st_size for f in self.log_dir.rglob("*") if f.is_file())
        })
        
        # Update final summary
        try:
            with open(self.log_files['summary'], 'r') as f:
                summary = json.load(f)
            
            summary['run_metadata']['end_time'] = self._get_timestamp()
            summary['run_metadata']['status'] = 'completed'
            summary['run_metadata']['final_state'] = self.get_current_state()
            
            with open(self.log_files['summary'], 'w') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            self.log_error("FINALIZATION_ERROR", f"Failed to finalize summary: {e}", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })

# Global logger instance
_global_logger: Optional[FrameworkDebugLogger] = None

def get_global_logger() -> Optional[FrameworkDebugLogger]:
    """Get global logger instance"""
    return _global_logger

def initialize_global_logger(run_id: str = None, base_log_dir: str = None) -> FrameworkDebugLogger:
    """Initialize global logger instance"""
    global _global_logger
    _global_logger = FrameworkDebugLogger(run_id, base_log_dir)
    return _global_logger

def finalize_global_logger():
    """Finalize global logger instance"""
    global _global_logger
    if _global_logger:
        _global_logger.finalize_logging()
        _global_logger = None

# Decorator for automatic function logging
def log_function_execution(component: str = "FUNCTION", log_level: str = "DEBUG"):
    """Decorator to automatically log function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_global_logger()
            if logger:
                func_name = func.__name__
                
                # Log function start
                logger.log_debug(f"FUNCTION_START_{func_name}", f"Starting {func_name}", {
                    "function_name": func_name,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }, component=component)
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    
                    end_time = time.time()
                    logger.log_debug(f"FUNCTION_COMPLETE_{func_name}", f"Completed {func_name}", {
                        "function_name": func_name,
                        "execution_time": f"{end_time - start_time:.3f}s",
                        "status": "SUCCESS"
                    }, component=component, performance_metrics={
                        "function_duration_seconds": end_time - start_time
                    })
                    
                    return result
                    
                except Exception as e:
                    end_time = time.time()
                    logger.log_error(f"FUNCTION_ERROR_{func_name}", f"Function {func_name} failed", {
                        "function_name": func_name,
                        "execution_time": f"{end_time - start_time:.3f}s",
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }, component=component)
                    raise
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test the logging system
    logger = FrameworkDebugLogger()
    
    # Test basic logging
    logger.log_info("TEST", "Testing framework debug logger")
    
    # Test phase tracking
    with logger.track_phase("test_phase"):
        logger.log_debug("TEST_ACTION", "Testing phase tracking")
        time.sleep(0.1)  # Simulate work
    
    # Test agent tracking
    with logger.track_agent("test_agent", "Testing agent tracking"):
        logger.log_debug("AGENT_WORK", "Agent doing work")
        time.sleep(0.1)  # Simulate work
    
    # Test tool tracking
    with logger.track_tool("test_tool", "test_action", {"input": "test"}) as execution_id:
        logger.log_debug("TOOL_WORK", f"Tool working with execution_id: {execution_id}")
        time.sleep(0.1)  # Simulate work
    
    logger.finalize_logging()
    print(f"Test logging completed. Logs saved to: {logger.log_dir}")
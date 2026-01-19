#!/usr/bin/env python3
"""
Framework Log Analyzer - Debugging and Investigation Tool

Purpose: Analyze framework logs for debugging, performance analysis, and investigation.
Provides comprehensive tools for understanding framework execution patterns and issues.

Author: AI Systems Suite
Version: 1.0.0
"""

import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
import statistics
import re

class FrameworkLogAnalyzer:
    """
    Comprehensive log analyzer for claude-test-generator framework debugging
    
    Features:
    - Timeline analysis of framework execution
    - Agent coordination pattern analysis
    - Tool usage statistics and performance
    - Context flow visualization
    - Validation checkpoint analysis
    - Error pattern detection
    - Performance bottleneck identification
    - Debug query interface
    """
    
    def __init__(self, log_directory: str):
        self.log_dir = Path(log_directory)
        if not self.log_dir.exists():
            raise FileNotFoundError(f"Log directory not found: {log_directory}")
        
        self.log_files = self._discover_log_files()
        self.logs = self._load_logs()
        self.summary = self._load_summary()
        
        print(f"📊 Log Analyzer initialized")
        print(f"   Log directory: {self.log_dir}")
        print(f"   Log files found: {len(self.log_files)}")
        print(f"   Total log entries: {len(self.logs)}")
    
    def _discover_log_files(self) -> Dict[str, Path]:
        """Discover all log files in the directory"""
        log_files = {}
        
        # Master logs
        master_jsonl = self.log_dir / 'framework_debug_master.jsonl'
        if master_jsonl.exists():
            log_files['master'] = master_jsonl
        
        human_readable = self.log_dir / 'framework_debug_readable.log'
        if human_readable.exists():
            log_files['human_readable'] = human_readable
        
        summary_json = self.log_dir / 'execution_summary.json'
        if summary_json.exists():
            log_files['summary'] = summary_json
        
        error_log = self.log_dir / 'error_log.jsonl'
        if error_log.exists():
            log_files['errors'] = error_log
        
        # Component-specific logs
        for component_dir in ['phases', 'agents', 'tools', 'context', 'validation', 'environment']:
            comp_path = self.log_dir / component_dir
            if comp_path.exists():
                for log_file in comp_path.glob("*.jsonl"):
                    log_files[f"{component_dir}_{log_file.stem}"] = log_file
        
        return log_files
    
    def _load_logs(self) -> List[Dict[str, Any]]:
        """Load all log entries from master log"""
        logs = []
        
        if 'master' in self.log_files:
            with open(self.log_files['master'], 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Failed to parse log line: {e}")
        
        # Sort by timestamp
        logs.sort(key=lambda x: x.get('timestamp', ''))
        return logs
    
    def _load_summary(self) -> Dict[str, Any]:
        """Load execution summary"""
        if 'summary' in self.log_files:
            with open(self.log_files['summary'], 'r') as f:
                return json.load(f)
        return {}
    
    def analyze_execution_timeline(self) -> Dict[str, Any]:
        """Analyze complete execution timeline"""
        print("\n🕒 EXECUTION TIMELINE ANALYSIS")
        print("=" * 50)
        
        if not self.logs:
            print("❌ No logs available for timeline analysis")
            return {}
        
        # Parse timestamps and create timeline
        timeline_events = []
        for log in self.logs:
            try:
                timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                timeline_events.append({
                    'timestamp': timestamp,
                    'component': log.get('component', 'UNKNOWN'),
                    'action': log.get('action', 'UNKNOWN'),
                    'phase': log.get('phase'),
                    'agent': log.get('agent'),
                    'log_level': log.get('log_level', 'INFO')
                })
            except (ValueError, KeyError) as e:
                continue
        
        if not timeline_events:
            print("❌ No valid timestamp data found")
            return {}
        
        # Calculate execution duration
        start_time = timeline_events[0]['timestamp']
        end_time = timeline_events[-1]['timestamp']
        total_duration = end_time - start_time
        
        # Analyze by component
        component_stats = defaultdict(list)
        phase_stats = defaultdict(list)
        agent_stats = defaultdict(list)
        
        for event in timeline_events:
            component_stats[event['component']].append(event)
            if event['phase']:
                phase_stats[event['phase']].append(event)
            if event['agent']:
                agent_stats[event['agent']].append(event)
        
        print(f"📅 Execution Period: {start_time.strftime('%Y-%m-%d %H:%M:%S')} → {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total Duration: {total_duration.total_seconds():.2f} seconds")
        print(f"📊 Total Events: {len(timeline_events)}")
        
        print(f"\n📋 Component Activity:")
        for component, events in sorted(component_stats.items()):
            error_count = sum(1 for e in events if e['log_level'] in ['ERROR', 'CRITICAL'])
            print(f"   {component:15} {len(events):4} events  {error_count:2} errors")
        
        print(f"\n🔄 Phase Activity:")
        for phase, events in sorted(phase_stats.items()):
            if phase:
                duration = self._calculate_phase_duration(events)
                print(f"   {phase:15} {len(events):4} events  {duration}")
        
        print(f"\n🤖 Agent Activity:")
        for agent, events in sorted(agent_stats.items()):
            if agent:
                print(f"   {agent:15} {len(events):4} events")
        
        return {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'total_duration_seconds': total_duration.total_seconds(),
            'total_events': len(timeline_events),
            'component_stats': dict(component_stats),
            'phase_stats': dict(phase_stats),
            'agent_stats': dict(agent_stats)
        }
    
    def _calculate_phase_duration(self, phase_events: List[Dict[str, Any]]) -> str:
        """Calculate duration for a phase"""
        if len(phase_events) < 2:
            return "N/A"
        
        start_time = phase_events[0]['timestamp']
        end_time = phase_events[-1]['timestamp']
        duration = end_time - start_time
        
        return f"{duration.total_seconds():.2f}s"
    
    def analyze_agent_coordination(self) -> Dict[str, Any]:
        """Analyze agent coordination patterns"""
        print("\n🤖 AGENT COORDINATION ANALYSIS")
        print("=" * 50)
        
        agent_events = [log for log in self.logs if log.get('component') == 'AGENT']
        
        if not agent_events:
            print("❌ No agent events found")
            return {}
        
        # Track agent spawning and completion
        agent_lifecycle = defaultdict(list)
        active_agents = {}
        coordination_patterns = []
        
        for event in agent_events:
            agent = event.get('agent')
            action = event.get('action', '')
            timestamp = event.get('timestamp')
            
            if not agent:
                continue
            
            agent_lifecycle[agent].append({
                'action': action,
                'timestamp': timestamp,
                'details': event.get('details', {})
            })
            
            if 'spawn' in action.lower() or 'start' in action.lower():
                active_agents[agent] = timestamp
            elif 'complete' in action.lower() or 'finish' in action.lower():
                if agent in active_agents:
                    start_time = active_agents.pop(agent)
                    coordination_patterns.append({
                        'agent': agent,
                        'start_time': start_time,
                        'end_time': timestamp,
                        'action': action
                    })
        
        # Analyze coordination patterns
        print(f"📊 Agent Summary:")
        print(f"   Total Agents: {len(agent_lifecycle)}")
        print(f"   Active at End: {len(active_agents)}")
        print(f"   Completed Cycles: {len(coordination_patterns)}")
        
        print(f"\n🔄 Agent Lifecycle:")
        for agent, events in agent_lifecycle.items():
            print(f"   {agent:20} {len(events):3} events")
            for event in events[:3]:  # Show first 3 events
                action = event['action'][:30] + "..." if len(event['action']) > 30 else event['action']
                print(f"      └─ {action}")
            if len(events) > 3:
                print(f"      └─ ... and {len(events) - 3} more events")
        
        return {
            'agent_count': len(agent_lifecycle),
            'active_agents': list(active_agents.keys()),
            'completed_cycles': len(coordination_patterns),
            'agent_lifecycle': dict(agent_lifecycle),
            'coordination_patterns': coordination_patterns
        }
    
    def analyze_tool_usage(self) -> Dict[str, Any]:
        """Analyze tool usage patterns and performance"""
        print("\n🔧 TOOL USAGE ANALYSIS")
        print("=" * 50)
        
        tool_events = [log for log in self.logs if log.get('component') == 'TOOL']
        
        if not tool_events:
            print("❌ No tool events found")
            return {}
        
        # Analyze tool usage patterns
        tool_stats = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0,
            'durations': [],
            'errors': 0,
            'actions': Counter()
        })
        
        for event in tool_events:
            details = event.get('details', {})
            tool_name = details.get('tool_name', 'UNKNOWN')
            action = event.get('action', '')
            performance = event.get('performance_metrics') or {}
            
            tool_stats[tool_name]['count'] += 1
            tool_stats[tool_name]['actions'][action] += 1
            
            if event.get('log_level') in ['ERROR', 'CRITICAL']:
                tool_stats[tool_name]['errors'] += 1
            
            # Extract duration if available
            duration = performance.get('tool_duration_seconds')
            if duration:
                tool_stats[tool_name]['total_duration'] += duration
                tool_stats[tool_name]['durations'].append(duration)
        
        # Calculate statistics
        print(f"📊 Tool Usage Summary:")
        print(f"   Total Tool Events: {len(tool_events)}")
        print(f"   Unique Tools Used: {len(tool_stats)}")
        
        print(f"\n🔧 Tool Statistics:")
        for tool_name, stats in sorted(tool_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            avg_duration = statistics.mean(stats['durations']) if stats['durations'] else 0
            error_rate = (stats['errors'] / stats['count']) * 100 if stats['count'] > 0 else 0
            
            print(f"   {tool_name:15} {stats['count']:3} uses  {avg_duration:6.3f}s avg  {error_rate:5.1f}% errors")
            
            # Show top actions
            top_actions = stats['actions'].most_common(2)
            for action, count in top_actions:
                action_display = action[:25] + "..." if len(action) > 25 else action
                print(f"      └─ {action_display:30} ({count} times)")
        
        return {
            'total_tool_events': len(tool_events),
            'unique_tools': len(tool_stats),
            'tool_statistics': dict(tool_stats)
        }
    
    def analyze_context_flow(self) -> Dict[str, Any]:
        """Analyze Progressive Context Architecture flow"""
        print("\n📡 CONTEXT FLOW ANALYSIS")
        print("=" * 50)
        
        context_events = [log for log in self.logs if log.get('component') == 'CONTEXT']
        
        if not context_events:
            print("❌ No context flow events found")
            return {}
        
        # Analyze context inheritance patterns
        inheritance_chain = []
        context_size_trend = []
        
        for event in context_events:
            details = event.get('details', {})
            action = event.get('action', '')
            timestamp = event.get('timestamp')
            
            inheritance_chain.append({
                'timestamp': timestamp,
                'action': action,
                'context_size': details.get('context_size', 0),
                'inheritance_chain': details.get('inheritance_chain', [])
            })
            
            if details.get('context_size'):
                context_size_trend.append(details['context_size'])
        
        print(f"📊 Context Flow Summary:")
        print(f"   Total Context Events: {len(context_events)}")
        print(f"   Context Inheritance Steps: {len(inheritance_chain)}")
        
        if context_size_trend:
            avg_size = statistics.mean(context_size_trend)
            max_size = max(context_size_trend)
            print(f"   Average Context Size: {avg_size:,.0f} chars")
            print(f"   Maximum Context Size: {max_size:,.0f} chars")
        
        print(f"\n📡 Context Inheritance Chain:")
        for i, step in enumerate(inheritance_chain[:10]):  # Show first 10 steps
            chain = " → ".join(step['inheritance_chain']) if step['inheritance_chain'] else "No chain"
            print(f"   {i+1:2}. {step['action']:30} {chain}")
        
        if len(inheritance_chain) > 10:
            print(f"      ... and {len(inheritance_chain) - 10} more steps")
        
        return {
            'total_context_events': len(context_events),
            'inheritance_steps': len(inheritance_chain),
            'inheritance_chain': inheritance_chain,
            'context_size_trend': context_size_trend
        }
    
    def analyze_validation_checkpoints(self) -> Dict[str, Any]:
        """Analyze validation checkpoint results"""
        print("\n🛡️ VALIDATION CHECKPOINT ANALYSIS")
        print("=" * 50)
        
        validation_events = [log for log in self.logs if log.get('component') == 'VALIDATION']
        
        if not validation_events:
            print("❌ No validation events found")
            return {}
        
        # Analyze validation patterns
        validation_stats = defaultdict(lambda: {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'confidence_scores': [],
            'latest_result': None
        })
        
        for event in validation_events:
            details = event.get('details', {})
            validation_type = details.get('validation_type', 'UNKNOWN')
            result = details.get('result', 'UNKNOWN')
            confidence = details.get('confidence')
            
            stats = validation_stats[validation_type]
            stats['total'] += 1
            stats['latest_result'] = result
            
            if result.lower() in ['passed', 'success', 'valid']:
                stats['passed'] += 1
            elif result.lower() in ['failed', 'error', 'invalid']:
                stats['failed'] += 1
            
            if confidence is not None:
                stats['confidence_scores'].append(confidence)
        
        print(f"📊 Validation Summary:")
        print(f"   Total Validation Events: {len(validation_events)}")
        print(f"   Validation Types: {len(validation_stats)}")
        
        print(f"\n🛡️ Validation Results:")
        for val_type, stats in sorted(validation_stats.items()):
            pass_rate = (stats['passed'] / stats['total']) * 100 if stats['total'] > 0 else 0
            avg_confidence = statistics.mean(stats['confidence_scores']) if stats['confidence_scores'] else 0
            
            print(f"   {val_type:25} {stats['total']:3} total  {pass_rate:5.1f}% pass  {avg_confidence:.2f} confidence")
            print(f"      └─ Latest: {stats['latest_result']}")
        
        return {
            'total_validation_events': len(validation_events),
            'validation_types': len(validation_stats),
            'validation_statistics': dict(validation_stats)
        }
    
    def analyze_errors(self) -> Dict[str, Any]:
        """Analyze error patterns and issues"""
        print("\n❌ ERROR ANALYSIS")
        print("=" * 50)
        
        error_events = [log for log in self.logs if log.get('log_level') in ['ERROR', 'CRITICAL']]
        
        if not error_events:
            print("✅ No errors found - clean execution!")
            return {'error_count': 0}
        
        # Analyze error patterns
        error_stats = {
            'by_component': Counter(),
            'by_phase': Counter(),
            'by_agent': Counter(),
            'by_action': Counter(),
            'timeline': []
        }
        
        for event in error_events:
            component = event.get('component', 'UNKNOWN')
            phase = event.get('phase', 'UNKNOWN')
            agent = event.get('agent', 'UNKNOWN')
            action = event.get('action', 'UNKNOWN')
            timestamp = event.get('timestamp')
            
            error_stats['by_component'][component] += 1
            error_stats['by_phase'][phase] += 1
            error_stats['by_agent'][agent] += 1
            error_stats['by_action'][action] += 1
            
            error_stats['timeline'].append({
                'timestamp': timestamp,
                'component': component,
                'phase': phase,
                'agent': agent,
                'action': action,
                'details': event.get('details', {})
            })
        
        print(f"📊 Error Summary:")
        print(f"   Total Errors: {len(error_events)}")
        print(f"   Error Rate: {(len(error_events) / len(self.logs)) * 100:.2f}% of all events")
        
        print(f"\n📊 Errors by Component:")
        for component, count in error_stats['by_component'].most_common():
            if component and component != 'UNKNOWN':
                print(f"   {str(component):15} {count:3} errors")
        
        print(f"\n📊 Errors by Phase:")
        for phase, count in error_stats['by_phase'].most_common():
            if phase and phase != 'UNKNOWN':
                print(f"   {str(phase):15} {count:3} errors")
        
        print(f"\n📊 Recent Errors:")
        for error in error_stats['timeline'][-5:]:  # Show last 5 errors
            component = str(error.get('component', 'UNKNOWN'))[:12]
            action = str(error.get('action', 'UNKNOWN'))[:40]
            print(f"   {component:12} {action}")
        
        return {
            'error_count': len(error_events),
            'error_rate': (len(error_events) / len(self.logs)) * 100 if self.logs else 0,
            'error_statistics': error_stats
        }
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance metrics and bottlenecks"""
        print("\n⚡ PERFORMANCE ANALYSIS")
        print("=" * 50)
        
        # Extract performance metrics
        performance_events = [log for log in self.logs if log.get('performance_metrics')]
        
        if not performance_events:
            print("❌ No performance metrics found")
            return {}
        
        # Analyze performance patterns
        performance_stats = {
            'phase_durations': defaultdict(list),
            'agent_durations': defaultdict(list),
            'tool_durations': defaultdict(list),
            'total_metrics': 0
        }
        
        for event in performance_events:
            metrics = event.get('performance_metrics', {})
            component = event.get('component', 'UNKNOWN')
            phase = event.get('phase')
            agent = event.get('agent')
            
            performance_stats['total_metrics'] += 1
            
            # Phase durations
            if phase and 'phase_duration_seconds' in metrics:
                duration = metrics['phase_duration_seconds']
                performance_stats['phase_durations'][phase].append(duration)
            
            # Agent durations
            if agent and 'agent_duration_seconds' in metrics:
                duration = metrics['agent_duration_seconds']
                performance_stats['agent_durations'][agent].append(duration)
            
            # Tool durations
            if component == 'TOOL' and 'tool_duration_seconds' in metrics:
                tool_name = event.get('details', {}).get('tool_name', 'UNKNOWN')
                duration = metrics['tool_duration_seconds']
                performance_stats['tool_durations'][tool_name].append(duration)
        
        print(f"📊 Performance Summary:")
        print(f"   Total Performance Events: {len(performance_events)}")
        print(f"   Metrics Collected: {performance_stats['total_metrics']}")
        
        # Phase performance
        if performance_stats['phase_durations']:
            print(f"\n⏱️  Phase Performance:")
            for phase, durations in performance_stats['phase_durations'].items():
                avg_duration = statistics.mean(durations)
                max_duration = max(durations)
                print(f"   {phase:15} {avg_duration:6.2f}s avg  {max_duration:6.2f}s max  ({len(durations)} runs)")
        
        # Agent performance
        if performance_stats['agent_durations']:
            print(f"\n🤖 Agent Performance:")
            for agent, durations in performance_stats['agent_durations'].items():
                avg_duration = statistics.mean(durations)
                max_duration = max(durations)
                print(f"   {agent:15} {avg_duration:6.2f}s avg  {max_duration:6.2f}s max  ({len(durations)} runs)")
        
        # Tool performance
        if performance_stats['tool_durations']:
            print(f"\n🔧 Tool Performance (Top 5):")
            tool_avg_durations = {tool: statistics.mean(durations) 
                                for tool, durations in performance_stats['tool_durations'].items()}
            
            for tool, avg_duration in sorted(tool_avg_durations.items(), 
                                           key=lambda x: x[1], reverse=True)[:5]:
                durations = performance_stats['tool_durations'][tool]
                max_duration = max(durations)
                print(f"   {tool:15} {avg_duration:6.3f}s avg  {max_duration:6.3f}s max  ({len(durations)} uses)")
        
        return {
            'total_performance_events': len(performance_events),
            'performance_statistics': performance_stats
        }
    
    def query_logs(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query logs with specified parameters"""
        results = []
        
        for log in self.logs:
            match = True
            
            # Filter by component
            if 'component' in query_params:
                if log.get('component') != query_params['component']:
                    match = False
            
            # Filter by log level
            if 'log_level' in query_params:
                if log.get('log_level') != query_params['log_level']:
                    match = False
            
            # Filter by phase
            if 'phase' in query_params:
                if log.get('phase') != query_params['phase']:
                    match = False
            
            # Filter by agent
            if 'agent' in query_params:
                if log.get('agent') != query_params['agent']:
                    match = False
            
            # Filter by action pattern
            if 'action_contains' in query_params:
                action = log.get('action', '')
                if query_params['action_contains'].lower() not in action.lower():
                    match = False
            
            # Filter by time range
            if 'after' in query_params or 'before' in query_params:
                try:
                    log_time = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
                    
                    if 'after' in query_params:
                        after_time = datetime.fromisoformat(query_params['after'])
                        if log_time < after_time:
                            match = False
                    
                    if 'before' in query_params:
                        before_time = datetime.fromisoformat(query_params['before'])
                        if log_time > before_time:
                            match = False
                            
                except ValueError:
                    match = False
            
            if match:
                results.append(log)
        
        return results
    
    def generate_debug_report(self, output_file: str = None) -> str:
        """Generate comprehensive debug report"""
        print("\n📋 GENERATING COMPREHENSIVE DEBUG REPORT")
        print("=" * 50)
        
        report_lines = []
        report_lines.append("# Framework Debug Report")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Log Directory: {self.log_dir}")
        report_lines.append("")
        
        # Run all analyses
        timeline_analysis = self.analyze_execution_timeline()
        agent_analysis = self.analyze_agent_coordination()
        tool_analysis = self.analyze_tool_usage()
        context_analysis = self.analyze_context_flow()
        validation_analysis = self.analyze_validation_checkpoints()
        error_analysis = self.analyze_errors()
        performance_analysis = self.analyze_performance()
        
        # Compile report
        report_data = {
            'timeline_analysis': timeline_analysis,
            'agent_analysis': agent_analysis,
            'tool_analysis': tool_analysis,
            'context_analysis': context_analysis,
            'validation_analysis': validation_analysis,
            'error_analysis': error_analysis,
            'performance_analysis': performance_analysis,
            'summary': self.summary
        }
        
        # Write JSON report
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"\n📄 Debug report saved to: {output_path}")
        
        return json.dumps(report_data, indent=2, default=str)
    
    def interactive_debug_session(self):
        """Start interactive debugging session"""
        print("\n🔍 INTERACTIVE DEBUG SESSION")
        print("=" * 50)
        print("Available commands:")
        print("  timeline - Show execution timeline")
        print("  agents   - Analyze agent coordination")
        print("  tools    - Analyze tool usage")
        print("  context  - Analyze context flow")
        print("  validate - Analyze validation checkpoints")
        print("  errors   - Analyze errors")
        print("  perf     - Analyze performance")
        print("  query    - Query logs with filters")
        print("  report   - Generate full debug report")
        print("  help     - Show this help")
        print("  exit     - Exit debug session")
        print("")
        
        while True:
            try:
                command = input("debug> ").strip().lower()
                
                if command == 'exit':
                    break
                elif command == 'help':
                    print("Available commands: timeline, agents, tools, context, validate, errors, perf, query, report, help, exit")
                elif command == 'timeline':
                    self.analyze_execution_timeline()
                elif command == 'agents':
                    self.analyze_agent_coordination()
                elif command == 'tools':
                    self.analyze_tool_usage()
                elif command == 'context':
                    self.analyze_context_flow()
                elif command == 'validate':
                    self.analyze_validation_checkpoints()
                elif command == 'errors':
                    self.analyze_errors()
                elif command == 'perf':
                    self.analyze_performance()
                elif command == 'query':
                    self._interactive_query()
                elif command == 'report':
                    report_file = input("Output file (optional): ").strip()
                    if not report_file:
                        report_file = None
                    self.generate_debug_report(report_file)
                elif command:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")
                
            except KeyboardInterrupt:
                print("\nExiting debug session...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def _interactive_query(self):
        """Interactive log query interface"""
        print("\n🔍 Log Query Interface")
        print("Enter query parameters (press Enter to skip):")
        
        query_params = {}
        
        component = input("Component (PHASE/AGENT/TOOL/CONTEXT/VALIDATION/etc.): ").strip()
        if component:
            query_params['component'] = component
        
        log_level = input("Log Level (DEBUG/INFO/WARN/ERROR/CRITICAL): ").strip()
        if log_level:
            query_params['log_level'] = log_level
        
        phase = input("Phase (0-pre/0/1/2/2.5/3/4/5): ").strip()
        if phase:
            query_params['phase'] = phase
        
        agent = input("Agent name: ").strip()
        if agent:
            query_params['agent'] = agent
        
        action_contains = input("Action contains text: ").strip()
        if action_contains:
            query_params['action_contains'] = action_contains
        
        # Execute query
        results = self.query_logs(query_params)
        
        print(f"\n📊 Query Results: {len(results)} entries found")
        
        if results:
            print("\nFirst 10 results:")
            for i, result in enumerate(results[:10]):
                timestamp = result.get('timestamp', 'N/A')[:19]  # Remove timezone
                component = result.get('component', 'N/A')
                action = result.get('action', 'N/A')[:40]
                print(f"  {i+1:2}. [{timestamp}] {component:10} {action}")
            
            if len(results) > 10:
                print(f"     ... and {len(results) - 10} more results")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Framework Log Analyzer")
    parser.add_argument('log_directory', help='Path to log directory')
    parser.add_argument('--analysis', choices=['timeline', 'agents', 'tools', 'context', 'validate', 'errors', 'perf', 'all'],
                       help='Specific analysis to run')
    parser.add_argument('--report', help='Generate debug report to file')
    parser.add_argument('--interactive', action='store_true', help='Start interactive debug session')
    
    args = parser.parse_args()
    
    try:
        analyzer = FrameworkLogAnalyzer(args.log_directory)
        
        if args.interactive:
            analyzer.interactive_debug_session()
        elif args.analysis:
            if args.analysis == 'timeline':
                analyzer.analyze_execution_timeline()
            elif args.analysis == 'agents':
                analyzer.analyze_agent_coordination()
            elif args.analysis == 'tools':
                analyzer.analyze_tool_usage()
            elif args.analysis == 'context':
                analyzer.analyze_context_flow()
            elif args.analysis == 'validate':
                analyzer.analyze_validation_checkpoints()
            elif args.analysis == 'errors':
                analyzer.analyze_errors()
            elif args.analysis == 'perf':
                analyzer.analyze_performance()
            elif args.analysis == 'all':
                analyzer.generate_debug_report(args.report)
        elif args.report:
            analyzer.generate_debug_report(args.report)
        else:
            print("Please specify --analysis, --report, or --interactive option")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
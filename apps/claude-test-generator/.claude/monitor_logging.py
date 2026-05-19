#!/usr/bin/env python3
"""
Real-time Logging Monitor for Claude Test Generator Framework
Shows what the comprehensive logging system captures during execution
"""

import json
import time
from pathlib import Path
from datetime import datetime
import sys

class LogMonitor:
    def __init__(self):
        self.log_base = Path.cwd() / ".claude" / "logging"
        self.current_session_dir = self.log_base / "current-session"
        
    def find_latest_run(self):
        """Find the most recent run directory"""
        run_dirs = [d for d in self.log_base.iterdir() 
                   if d.is_dir() and d.name not in ['current-session', '__pycache__']]
        if run_dirs:
            return max(run_dirs, key=lambda d: d.stat().st_mtime)
        return None
    
    def display_run_summary(self, run_dir):
        """Display comprehensive run summary"""
        print(f"\n📊 RUN SUMMARY: {run_dir.name}")
        print("=" * 80)
        
        # Check execution summary
        summary_file = run_dir / "execution_summary.json"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                
            # Display metadata
            metadata = summary.get("run_metadata", {})
            print(f"🔍 Run ID: {metadata.get('run_id', 'Unknown')}")
            print(f"📅 Start Time: {metadata.get('start_time', 'Unknown')}")
            print(f"📅 End Time: {metadata.get('end_time', 'Not completed')}")
            print(f"📌 Status: {metadata.get('status', 'Unknown')}")
            
            # Display phase summary
            phases = summary.get("phase_summary", {})
            if phases:
                print(f"\n🔄 PHASE PROGRESSION:")
                for phase, info in phases.items():
                    status = info.get('status', 'unknown')
                    symbol = "✅" if status == 'completed' else "🔄"
                    print(f"   {symbol} Phase {phase}: {status}")
            
            # Display agent summary
            agents = summary.get("agent_summary", {})
            if agents:
                print(f"\n🤖 AGENTS SPAWNED:")
                for agent, info in agents.items():
                    status = info.get('status', 'unknown')
                    symbol = "✅" if status == 'completed' else "🔄"
                    print(f"   {symbol} {agent}: {status}")
            
            # Display validation results
            validations = summary.get("validation_results", {})
            if validations:
                print(f"\n✔️  VALIDATION CHECKPOINTS:")
                for check, result in validations.items():
                    status = result.get('result', 'unknown')
                    confidence = result.get('confidence', 0)
                    symbol = "✅" if status == 'passed' else "❌"
                    print(f"   {symbol} {check}: {status} (confidence: {confidence:.2f})")
            
            # Display timeline
            timeline = summary.get("execution_timeline", [])
            if timeline:
                print(f"\n📜 EXECUTION TIMELINE (last 10 events):")
                for event in timeline[-10:]:
                    time_str = event['timestamp'].split('T')[1][:8]
                    component = event['component']
                    action = event['action']
                    phase = event.get('phase', '')
                    agent = event.get('agent', '')
                    
                    line = f"   [{time_str}] {component}: {action}"
                    if phase:
                        line += f" (Phase: {phase})"
                    if agent:
                        line += f" (Agent: {agent})"
                    print(line)
    
    def show_tool_logs(self, run_dir):
        """Show tool execution logs"""
        tools_dir = run_dir / "tools"
        if tools_dir.exists():
            tool_files = list(tools_dir.glob("*.log"))
            if tool_files:
                print(f"\n🔧 TOOL EXECUTIONS:")
                for tool_file in tool_files[:5]:  # Show first 5
                    print(f"   📄 {tool_file.name}")
    
    def show_error_logs(self, run_dir):
        """Show any errors logged"""
        error_file = run_dir / "error_log.jsonl"
        if error_file.exists():
            with open(error_file, 'r') as f:
                errors = [json.loads(line) for line in f]
                if errors:
                    print(f"\n❌ ERRORS DETECTED ({len(errors)} total):")
                    for error in errors[:3]:  # Show first 3
                        print(f"   - {error.get('action', 'Unknown')}: {error.get('details', {}).get('error', 'Unknown error')}")
    
    def monitor_all_runs(self):
        """Display information about all logged runs"""
        print("🔍 COMPREHENSIVE LOGGING SYSTEM MONITOR")
        print("=" * 80)
        
        # Check if logging directory exists
        if not self.log_base.exists():
            print("❌ No logging directory found!")
            return
        
        # Find all run directories
        run_dirs = [d for d in self.log_base.iterdir() 
                   if d.is_dir() and d.name not in ['current-session', '__pycache__']]
        
        if not run_dirs:
            print("📭 No logged runs found yet.")
            print("\n💡 The logging system will create logs when you run the framework.")
            return
        
        # Sort by modification time
        run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        
        print(f"📊 Found {len(run_dirs)} logged runs\n")
        
        # Show recent runs
        print("📅 RECENT RUNS:")
        for run_dir in run_dirs[:5]:  # Show last 5 runs
            mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)
            print(f"   • {run_dir.name} - {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Detail latest run
        latest_run = run_dirs[0]
        self.display_run_summary(latest_run)
        self.show_tool_logs(latest_run)
        self.show_error_logs(latest_run)
        
        # Show logging configuration
        print("\n⚙️  LOGGING CONFIGURATION:")
        config_file = Path.cwd() / ".claude" / "claude_code_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                logging_config = config.get('logging', {})
                hooks_config = config.get('hooks', {})
                
                print("   📝 Logging Settings:")
                for key, value in logging_config.items():
                    print(f"      - {key}: {value}")
                
                active_hooks = hooks_config.get('active_hooks', [])
                print(f"\n   🪝 Active Hooks ({len(active_hooks)}):")
                for hook in active_hooks:
                    mandatory = "🔒" if hook.get('mandatory') else "🔓"
                    print(f"      {mandatory} {hook.get('name')} - {hook.get('description', 'No description')}")

def main():
    monitor = LogMonitor()
    monitor.monitor_all_runs()
    
    print("\n💡 TO IMPROVE LOGGING:")
    print("   1. Ensure comprehensive_logging_hook is active in claude_code_config.json ✅")
    print("   2. Enable execution_verification_hook for anti-simulation ✅")
    print("   3. Run framework with real JIRA tickets for proper organization")
    print("   4. Check .claude/logging/ directory after each run")
    print("   5. Use the framework_debug_logger for custom logging needs")

if __name__ == "__main__":
    main()



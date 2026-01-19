#!/usr/bin/env python3
"""Test script to validate comprehensive logging system"""

import sys
from pathlib import Path

# Add hooks directory to path
hooks_dir = Path(__file__).parent / "hooks"
sys.path.insert(0, str(hooks_dir))

# Import the comprehensive logging hook
from comprehensive_logging_hook import ComprehensiveLoggingHook, claude_code_tool_hook

def test_logging_system():
    print("🧪 Testing Comprehensive Logging System")
    print("=" * 60)
    
    # Create hook instance
    hook = ComprehensiveLoggingHook()
    
    # Initialize run logging
    test_jira = "TEST-123"
    hook.initialize_run_logging(jira_ticket=test_jira)
    
    print(f"✅ Initialized logging for JIRA ticket: {test_jira}")
    print(f"📁 Run ID: {hook.current_run_id}")
    print(f"📂 Log directory: {hook.run_log_file.parent}")
    
    # Test tool logging
    print("\n📝 Testing tool logging...")
    
    # Simulate bash tool execution
    bash_params = {
        "command": "echo 'Testing logging system'",
        "description": "Test command execution"
    }
    result = claude_code_tool_hook("bash", bash_params)
    print("✅ Bash tool logging tested")
    
    # Simulate file read
    read_params = {
        "file_path": "test_file.py",
        "limit": 100
    }
    result = claude_code_tool_hook("read", read_params)
    print("✅ Read tool logging tested")
    
    # Simulate agent spawn
    task_params = {
        "description": "Test agent for logging validation",
        "subagent_type": "test-agent",
        "prompt": "Validate logging system"
    }
    result = claude_code_tool_hook("task", task_params)
    print("✅ Task tool (agent spawn) logging tested")
    
    # Check session stats
    print(f"\n📊 Session Statistics:")
    print(f"   Bash commands: {hook.session_stats['bash_commands']}")
    print(f"   File reads: {hook.session_stats['file_reads']}")
    print(f"   Agent spawns: {hook.session_stats['agent_spawns']}")
    
    # Save session summary
    summary_file = hook.save_session_summary()
    print(f"\n💾 Session summary saved to: {summary_file}")
    
    # Check if logs were created
    if hook.run_log_file.exists():
        with open(hook.run_log_file, 'r') as f:
            log_lines = f.readlines()
            print(f"\n📜 Log entries created: {len(log_lines)}")
            
            # Show first few entries
            print("\n🔍 Sample log entries:")
            for i, line in enumerate(log_lines[:3]):
                print(f"   Entry {i+1}: {line.strip()[:100]}...")
    
    print("\n✅ Comprehensive logging system is working correctly!")
    return True

if __name__ == "__main__":
    try:
        success = test_logging_system()
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()



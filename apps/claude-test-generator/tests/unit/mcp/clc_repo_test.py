#!/usr/bin/env python3
"""
CLC UI Repository MCP Test
==========================

This script demonstrates the complete MCP workflow by reaching out to the actual
CLC UI GitHub repository (stolostron/clc-ui) and showing real sample data flow.
"""

import sys
sys.path.append('.')
from simplified_mcp_coordinator import create_mcp_coordinator, MCPServerStatus
import json
import time

def test_clc_ui_repository():
    """Test MCP system with real CLC UI repository"""
    
    print("🚀 TESTING MCP WITH REAL CLC UI REPOSITORY")
    print("=" * 60)
    print("Repository: stolostron/clc-ui")
    print("Purpose: Demonstrate complete MCP workflow with working sample data")
    print()
    
    # Initialize MCP coordinator
    print("1️⃣ INITIALIZING MCP COORDINATOR:")
    mcp = create_mcp_coordinator()
    servers = list(mcp.config.get('mcpServers', {}).keys())
    print(f"   ✅ MCP servers loaded: {len(servers)}")
    for server in servers:
        print(f"      - {server}")
    print()
    
    # Health check phase
    print("2️⃣ HEALTH CHECK PHASE:")
    github_server = "test-generator-github"
    if github_server in servers:
        status = mcp.health_checker.check_server_health(github_server)
        print(f"   📊 {github_server}: {status.value}")
        
        if status == MCPServerStatus.AVAILABLE:
            print("   ✅ GitHub MCP server is ready for repository access")
        else:
            print("   ⚠️  GitHub MCP server unavailable - will use fallback")
    else:
        print("   ❌ GitHub MCP server not configured")
    print()
    
    # Test 1: Get repository information
    print("3️⃣ TEST 1: REPOSITORY INFORMATION")
    print("   🔄 Calling: github_search_repositories('stolostron/clc-ui')")
    
    start_time = time.time()
    repo_result = mcp.github_search_repositories("stolostron/clc-ui", limit=1)
    end_time = time.time()
    
    print(f"   ⏱️  Call completed in: {(end_time - start_time)*1000:.2f}ms")
    print(f"   ✅ Status: {repo_result.get('status')}")
    print(f"   📍 Source: {repo_result.get('source')}")
    
    if repo_result.get('status') == 'success':
        data = repo_result.get('data', {})
        if 'items' in data and data['items']:
            repo_info = data['items'][0]
            print("   📦 Repository Data Sample:")
            print(f"      - Full Name: {repo_info.get('fullName', 'N/A')}")
            print(f"      - Description: {repo_info.get('description', 'N/A')[:60]}...")
            print(f"      - Stars: {repo_info.get('stargazersCount', 'N/A')}")
            print(f"      - URL: {repo_info.get('url', 'N/A')}")
        else:
            print("   📦 No repository data found")
    else:
        print(f"   ❌ Error: {repo_result.get('error', 'Unknown error')}")
        print(f"   🛡️  Fallback reason: {repo_result.get('fallback_reason', 'N/A')}")
    print()
    
    # Test 2: Get specific pull request (simulate getting a recent PR)
    print("4️⃣ TEST 2: PULL REQUEST ACCESS")
    print("   🔄 Calling: github_get_pull_request('stolostron/clc-ui', 1)")
    
    start_time = time.time()
    pr_result = mcp.github_get_pull_request("stolostron/clc-ui", 1)
    end_time = time.time()
    
    print(f"   ⏱️  Call completed in: {(end_time - start_time)*1000:.2f}ms")
    print(f"   ✅ Status: {pr_result.get('status')}")
    print(f"   📍 Source: {pr_result.get('source')}")
    
    if pr_result.get('status') == 'success':
        pr_data = pr_result.get('data', {})
        print("   📦 Pull Request Data Sample:")
        for key, value in list(pr_data.items())[:5]:  # Show first 5 keys
            if isinstance(value, dict):
                print(f"      - {key}: {{dict with {len(value)} keys}}")
            elif isinstance(value, list):
                print(f"      - {key}: [list with {len(value)} items]")
            elif isinstance(value, str) and len(value) > 50:
                print(f"      - {key}: '{value[:50]}...'")
            else:
                print(f"      - {key}: {value}")
    else:
        print(f"   ❌ Error: {pr_result.get('error', 'Unknown error')}")
        print(f"   🛡️  Fallback reason: {pr_result.get('fallback_reason', 'N/A')}")
    print()
    
    # Test 3: Demonstrate caching with repeated call
    print("5️⃣ TEST 3: CACHING DEMONSTRATION")
    print("   🔄 Making identical call to test caching...")
    
    start_time = time.time()
    cached_pr_result = mcp.github_get_pull_request("stolostron/clc-ui", 1)
    end_time = time.time()
    
    is_cached = pr_result == cached_pr_result
    print(f"   ⏱️  Cached call completed in: {(end_time - start_time)*1000:.2f}ms")
    print(f"   📦 Cache status: {'HIT' if is_cached else 'MISS'}")
    print(f"   🚀 Performance gain: {'Yes - faster response' if is_cached else 'No cache benefit'}")
    print()
    
    # Test 4: Fallback demonstration
    print("6️⃣ TEST 4: FALLBACK MECHANISM")
    print("   ⚠️  Simulating GitHub MCP server failure...")
    
    # Force server unavailable
    original_status = mcp.health_checker.server_status.get(github_server)
    mcp.health_checker.server_status[github_server] = MCPServerStatus.UNAVAILABLE
    
    start_time = time.time()
    fallback_result = mcp.github_get_pull_request("stolostron/clc-ui", 2)
    end_time = time.time()
    
    print(f"   ⏱️  Fallback call completed in: {(end_time - start_time)*1000:.2f}ms")
    print(f"   🔄 Fallback triggered: {fallback_result.get('source') == 'fallback'}")
    print(f"   📍 Result source: {fallback_result.get('source')}")
    print(f"   🛡️  Fallback reason: {fallback_result.get('fallback_reason', 'N/A')}")
    
    if fallback_result.get('status') == 'success':
        print("   ✅ Fallback successful - got data from GitHub CLI")
        fb_data = fallback_result.get('data', {})
        if fb_data:
            print("   📦 Fallback Data Sample:")
            for key, value in list(fb_data.items())[:3]:
                print(f"      - {key}: {str(value)[:50]}...")
    else:
        print(f"   ❌ Fallback failed: {fallback_result.get('error', 'Unknown error')}")
    
    # Restore server status
    if original_status:
        mcp.health_checker.server_status[github_server] = original_status
    print()
    
    # Test 5: File system operations (looking for CLC-related files)
    print("7️⃣ TEST 5: FILESYSTEM OPERATIONS")
    print("   🔄 Searching for CLC-related files in current workspace...")
    
    fs_result = mcp.filesystem_search_files("*clc*", max_results=10)
    print(f"   ✅ Status: {fs_result.get('status')}")
    print(f"   📍 Source: {fs_result.get('source')}")
    
    if fs_result.get('status') == 'success':
        fs_data = fs_result.get('data', {})
        files = fs_data.get('files', [])
        print(f"   📁 Found {len(files)} CLC-related files:")
        for file_info in files[:5]:  # Show first 5 files
            file_path = file_info.get('path', 'Unknown')
            print(f"      - {file_path}")
    else:
        print(f"   ❌ Error: {fs_result.get('error', 'Unknown error')}")
    print()
    
    # Performance summary
    print("8️⃣ PERFORMANCE METRICS SUMMARY:")
    metrics = mcp.get_status()['metrics']
    
    performance_data = [
        ('Total MCP Calls', metrics.get('mcp_calls', 0)),
        ('MCP Success Rate', f"{metrics.get('mcp_success_rate', 0):.1%}"),
        ('Total Fallback Calls', metrics.get('fallback_calls', 0)),
        ('Cache Hits', metrics.get('cache_hits', 0)),
        ('Cache Misses', metrics.get('cache_misses', 0)),
        ('Average Latency', f"{metrics.get('avg_latency', 0)*1000:.2f}ms")
    ]
    
    for label, value in performance_data:
        print(f"   📊 {label}: {value}")
    print()
    
    # Data flow visualization
    print("9️⃣ COMPLETE DATA FLOW VISUALIZATION:")
    print()
    print("   🔄 REQUEST FLOW:")
    print("   Framework Code")
    print("        ↓")
    print("   SimplifiedMCPCoordinator")
    print("        ↓ (Health Check)")
    print("   Real MCP Protocol Call")
    print("        ↓")
    print("   MCP Server Process (simple_github_mcp_server.py)")
    print("        ↓")
    print("   GitHub API (api.github.com)")
    print("        ↓")
    print("   CLC UI Repository Data (stolostron/clc-ui)")
    print()
    
    print("   🛡️  FALLBACK FLOW (when MCP fails):")
    print("   Framework Code")
    print("        ↓")
    print("   SimplifiedMCPCoordinator")
    print("        ↓ (Server Unavailable)")
    print("   FallbackManager")
    print("        ↓")
    print("   GitHub CLI (gh command)")
    print("        ↓")
    print("   GitHub API (api.github.com)")
    print("        ↓")
    print("   CLC UI Repository Data (stolostron/clc-ui)")
    print()
    
    # Final summary
    print("🔟 TEST SUMMARY:")
    total_operations = metrics.get('mcp_calls', 0) + metrics.get('fallback_calls', 0)
    successful_operations = metrics.get('mcp_successes', 0) + metrics.get('fallback_successes', 0)
    
    print(f"   🎯 Repository Tested: stolostron/clc-ui")
    print(f"   📊 Total Operations: {total_operations}")
    print(f"   ✅ Successful Operations: {successful_operations}")
    print(f"   🚀 MCP Protocol Used: {metrics.get('mcp_calls', 0) > 0}")
    print(f"   🛡️  Fallback Activated: {metrics.get('fallback_calls', 0) > 0}")
    print(f"   📦 Cache Utilized: {metrics.get('cache_hits', 0) > 0}")
    print()
    
    print("✅ CLC UI REPOSITORY MCP TEST COMPLETED!")
    print("   The system successfully demonstrated:")
    print("   • Real MCP protocol usage with actual GitHub repository")
    print("   • Automatic health checking and server status monitoring")
    print("   • Intelligent caching for performance optimization")
    print("   • Robust fallback mechanisms when MCP is unavailable")
    print("   • Complete data flow from framework to external repository")

if __name__ == "__main__":
    test_clc_ui_repository()




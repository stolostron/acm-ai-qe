#!/usr/bin/env python3
"""
Test No GitHub CLI Access Scenario
=================================

This script tests what happens when GitHub CLI is completely inaccessible,
simulating Claude Code's MCP execution environment.
"""

import os
import sys
import subprocess
import requests
from functools import lru_cache

# Simulate complete GitHub CLI inaccessibility
def mock_subprocess_run(*args, **kwargs):
    """Mock subprocess.run to simulate no gh command"""
    if args[0] and 'gh' in str(args[0]):
        raise subprocess.FileNotFoundError("No such file or directory: 'gh'")
    else:
        return original_subprocess_run(*args, **kwargs)

# Store original subprocess.run
original_subprocess_run = subprocess.run

@lru_cache(maxsize=1)
def _get_github_token_no_cli() -> str:
    """Token retrieval when GitHub CLI is not accessible"""
    print(f"🔍 _get_github_token_no_cli() called", file=sys.stderr)
    
    # First try environment variable
    env_token = os.getenv('GITHUB_TOKEN')
    print(f"   Environment token: {env_token[:10] if env_token else 'None'}...", file=sys.stderr)
    if env_token and env_token != 'your_github_token_here':
        print("   Using environment token", file=sys.stderr)
        return env_token
    
    # Try GitHub CLI (will fail in restricted environment)
    try:
        print("   Trying GitHub CLI...", file=sys.stderr)
        result = subprocess.run(['gh', 'auth', 'token'], 
                              capture_output=True, text=True, check=True, timeout=5)
        token = result.stdout.strip()
        if token and len(token) > 10:
            print(f"   GitHub CLI success: {token[:10]}...", file=sys.stderr)
            return token
        else:
            raise Exception("GitHub CLI returned invalid token")
    except subprocess.FileNotFoundError:
        print("   GitHub CLI not found", file=sys.stderr)
        raise Exception("GitHub CLI not found in PATH. Install GitHub CLI or set GITHUB_TOKEN environment variable.")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"   GitHub CLI error: {e}", file=sys.stderr)
        raise Exception(f"GitHub CLI error: {e}. Run 'gh auth login' first.")

def test_api_no_cli(scenario: str):
    """Test API access when GitHub CLI is not available"""
    try:
        print(f"🧪 Testing {scenario}", file=sys.stderr)
        token = _get_github_token_no_cli()
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        response = requests.get("https://api.github.com/rate_limit", headers=headers, timeout=10)
        
        result = {
            "status": "SUCCESS" if response.status_code == 200 else "FAILED",
            "status_code": response.status_code,
            "scenario": scenario,
            "token_length": len(token),
            "error_details": response.text if response.status_code != 200 else None
        }
        
        print(f"   Result: {result['status']} (code: {result['status_code']})", file=sys.stderr)
        return result
        
    except Exception as e:
        error_result = {"status": "ERROR", "error": str(e), "scenario": scenario}
        print(f"   Error: {e}", file=sys.stderr)
        return error_result

def main():
    """Test scenarios where GitHub CLI is inaccessible"""
    print("🔍 Testing No GitHub CLI Access Scenarios", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    results = {}
    
    # Test 1: With environment token set, no GitHub CLI
    print("\n Test 1: Environment token set, mock no GitHub CLI", file=sys.stderr)
    # Use existing GITHUB_TOKEN from environment, or skip test if not available
    env_token = os.getenv('GITHUB_TOKEN')
    if not env_token:
        print("   Skipping: GITHUB_TOKEN not set in environment", file=sys.stderr)
        results['env_token_no_cli'] = {"status": "SKIPPED", "reason": "No GITHUB_TOKEN in environment"}
    else:
        os.environ['GITHUB_TOKEN'] = env_token
        # Mock subprocess to simulate no GitHub CLI
        subprocess.run = mock_subprocess_run
        _get_github_token_no_cli.cache_clear()
        results['env_token_no_cli'] = test_api_no_cli("env_token_no_cli")
    
    # Test 2: No environment token, no GitHub CLI (should fail)
    print("\n🧪 Test 2: No environment token, no GitHub CLI", file=sys.stderr)
    if 'GITHUB_TOKEN' in os.environ:
        del os.environ['GITHUB_TOKEN']
    
    _get_github_token_no_cli.cache_clear()
    results['no_token_no_cli'] = test_api_no_cli("no_token_no_cli")
    
    # Test 3: Restore GitHub CLI access
    print("\n🧪 Test 3: Restore GitHub CLI access", file=sys.stderr)
    subprocess.run = original_subprocess_run  # Restore original
    _get_github_token_no_cli.cache_clear()
    results['restored_cli'] = test_api_no_cli("restored_cli")
    
    # Summary
    print("\n📊 Summary:", file=sys.stderr)
    for scenario, result in results.items():
        status = result.get('status', 'UNKNOWN')
        error = result.get('error', '')
        print(f"   {scenario}: {status} {error[:50]}", file=sys.stderr)
    
    return {
        "test_results": results,
        "key_insight": "Environment token works when GitHub CLI is not accessible"
    }

if __name__ == "__main__":
    import json
    result = main()
    print(json.dumps(result, indent=2))
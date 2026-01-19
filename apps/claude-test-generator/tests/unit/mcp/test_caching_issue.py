#!/usr/bin/env python3
"""
Test Authentication Caching Issue
=================================

This script tests the hypothesis that @lru_cache is causing authentication
issues across different execution contexts.
"""

import os
import sys
import subprocess
import requests
from functools import lru_cache

# Simulate the exact caching behavior from OptimizedGitHubMCPIntegration
@lru_cache(maxsize=1)
def _get_github_token() -> str:
    """Cached GitHub token retrieval with enhanced error handling"""
    print(f"🔍 _get_github_token() called - cache miss!", file=sys.stderr)
    
    # First try environment variable
    env_token = os.getenv('GITHUB_TOKEN')
    print(f"   Environment token: {env_token[:10] if env_token else 'None'}...", file=sys.stderr)
    if env_token and env_token != 'your_github_token_here':
        print("   Using environment token", file=sys.stderr)
        return env_token
    
    # Then try GitHub CLI
    try:
        result = subprocess.run(['gh', 'auth', 'token'], 
                              capture_output=True, text=True, check=True, timeout=5)
        token = result.stdout.strip()
        if token and len(token) > 10:  # Basic validation
            print(f"   Using GitHub CLI token: {token[:10]}...", file=sys.stderr)
            return token
        else:
            raise Exception("GitHub CLI returned invalid token")
    except subprocess.FileNotFoundError:
        raise Exception("GitHub CLI not found in PATH. Install GitHub CLI or set GITHUB_TOKEN environment variable.")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        raise Exception(f"GitHub CLI error: {e}. Run 'gh auth login' first.")

def test_api_with_token(token_source: str):
    """Test GitHub API with current token"""
    try:
        token = _get_github_token()
        print(f"🧪 Testing API with token from {token_source}", file=sys.stderr)
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        response = requests.get("https://api.github.com/rate_limit", headers=headers, timeout=10)
        
        result = {
            "status": "SUCCESS" if response.status_code == 200 else "FAILED",
            "status_code": response.status_code,
            "token_source": token_source,
            "token_length": len(token),
            "token_prefix": token[:10],
            "rate_limit": response.json().get('rate', {}).get('remaining') if response.status_code == 200 else None
        }
        
        print(f"   Result: {result['status']} (code: {result['status_code']})", file=sys.stderr)
        return result
        
    except Exception as e:
        error_result = {"status": "ERROR", "error": str(e), "token_source": token_source}
        print(f"   Error: {e}", file=sys.stderr)
        return error_result

def main():
    """Test caching behavior across different scenarios"""
    print("🔍 Testing Authentication Caching Behavior", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    # Test 1: Normal execution (should work)
    print("\n🧪 Test 1: Normal execution", file=sys.stderr)
    result1 = test_api_with_token("normal")
    
    # Test 2: Clear cache and test again (cache miss)
    print("\n🧪 Test 2: After cache clear", file=sys.stderr)
    _get_github_token.cache_clear()
    result2 = test_api_with_token("cache_cleared")
    
    # Test 3: Simulate restricted environment
    print("\n🧪 Test 3: Simulated restricted environment", file=sys.stderr)
    # Temporarily modify environment
    original_github_token = os.environ.get('GITHUB_TOKEN')
    original_path = os.environ.get('PATH')
    
    # Clear environment token
    if 'GITHUB_TOKEN' in os.environ:
        del os.environ['GITHUB_TOKEN']
    
    # Clear cache to force re-evaluation
    _get_github_token.cache_clear()
    result3 = test_api_with_token("restricted_env")
    
    # Test 4: Restore environment and test
    print("\n🧪 Test 4: Restore environment", file=sys.stderr)
    if original_github_token:
        os.environ['GITHUB_TOKEN'] = original_github_token
    if original_path:
        os.environ['PATH'] = original_path
    
    _get_github_token.cache_clear()
    result4 = test_api_with_token("restored")
    
    # Summary
    print("\n📊 Summary:", file=sys.stderr)
    tests = [
        ("Normal", result1),
        ("Cache Cleared", result2), 
        ("Restricted Env", result3),
        ("Restored", result4)
    ]
    
    for name, result in tests:
        status = result.get('status', 'UNKNOWN')
        print(f"   {name}: {status}", file=sys.stderr)
    
    # Return JSON summary
    return {
        "tests": dict(tests),
        "conclusion": "Cache behavior analysis complete"
    }

if __name__ == "__main__":
    import json
    result = main()
    print(json.dumps(result, indent=2))
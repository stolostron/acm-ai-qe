#!/usr/bin/env python3
"""
Optimized GitHub MCP Integration - Performance Enhanced Version

Provides fast GitHub API access with lazy initialization, caching, and
intelligent API call optimization while maintaining comprehensive data.
"""

import json
import subprocess
import requests
import os
import sys
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from functools import lru_cache

class OptimizedGitHubMCPIntegration:
    """Performance-optimized GitHub MCP integration with lazy loading"""
    
    def __init__(self, lazy_init: bool = True):
        self.base_url = "https://api.github.com"
        self.auth_token = None
        self.headers = None
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = time.time() + 3600
        self.session = None
        
        # Performance optimizations
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes cache
        
        if not lazy_init:
            self._initialize()
    
    def _initialize(self):
        """Lazy initialization to avoid startup overhead"""
        if self.auth_token is None:
            try:
                self.auth_token = self._get_github_token()
                print(f"DEBUG: Retrieved token: {self.auth_token[:10]}...{self.auth_token[-4:] if len(self.auth_token) > 10 else 'SHORT'}", file=sys.stderr)
            except Exception as e:
                print(f"DEBUG: Token retrieval failed: {e}", file=sys.stderr)
                raise
            
            self.headers = {
                "Authorization": f"token {self.auth_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            print(f"DEBUG: Headers set: Authorization=token {self.auth_token[:10]}...", file=sys.stderr)
            
            # Use session for connection pooling
            self.session = requests.Session()
            self.session.headers.update(self.headers)
            print("DEBUG: Session initialized", file=sys.stderr)
    
    @lru_cache(maxsize=1)
    def _get_github_token(self) -> str:
        """Cached GitHub token retrieval with enhanced error handling"""
        # First try environment variable
        env_token = os.getenv('GITHUB_TOKEN')
        print(f"DEBUG: GITHUB_TOKEN env var: {env_token[:10] if env_token else 'None'}...", file=sys.stderr)
        if env_token and env_token != 'your_github_token_here':
            print(f"DEBUG: Using environment token", file=sys.stderr)
            return env_token
        
        # Then try GitHub CLI
        try:
            result = subprocess.run(['gh', 'auth', 'token'], 
                                  capture_output=True, text=True, check=True, timeout=5)
            token = result.stdout.strip()
            if token and len(token) > 10:  # Basic validation
                return token
            else:
                raise Exception("GitHub CLI returned invalid token")
        except subprocess.FileNotFoundError:
            raise Exception("GitHub CLI not found in PATH. Install GitHub CLI or set GITHUB_TOKEN environment variable.")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise Exception(f"GitHub CLI error: {e}. Run 'gh auth login' first.")
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.cache:
            return False
        
        entry = self.cache[cache_key]
        return datetime.now() < entry['expires']
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if valid"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        return None
    
    def _store_in_cache(self, cache_key: str, data: Dict):
        """Store data in cache with TTL"""
        self.cache[cache_key] = {
            'data': data,
            'expires': datetime.now() + timedelta(seconds=self.cache_ttl)
        }
    
    def _make_request(self, endpoint: str, params: Dict = None, use_cache: bool = True) -> Dict:
        """Optimized GitHub API request with caching and session reuse"""
        # Ensure initialization
        if self.auth_token is None:
            self._initialize()
        
        # Check cache first
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        if use_cache:
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result
        
        # Rate limiting check (simplified)
        if self.rate_limit_remaining < 10:
            if time.time() < self.rate_limit_reset:
                wait_time = min(self.rate_limit_reset - time.time(), 60)  # Max 60s wait
                print(f"Rate limit approaching, waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
        
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = self.session.get(url, params=params or {}, timeout=30)
            
            # Update rate limit info
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
            self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', time.time() + 3600))
            
            if response.status_code == 200:
                result = response.json()
                if use_cache:
                    self._store_in_cache(cache_key, result)
                return result
            elif response.status_code == 404:
                return {"error": "Not found", "status": 404}
            else:
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            return {"error": "Request timeout", "fallback_to_cli": True}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}", "fallback_to_cli": True}
    
    def get_pull_request(self, repo: str, pr_number: int, 
                        include_commits: bool = True, 
                        include_files: bool = True,
                        lightweight: bool = False) -> Dict:
        """Optimized PR information retrieval with options"""
        try:
            endpoint = f"/repos/{repo}/pulls/{pr_number}"
            
            if lightweight:
                # Fast path: only basic PR info
                pr_data = self._make_request(endpoint)
                if "error" in pr_data:
                    return pr_data
                
                return {
                    "pr_info": pr_data,
                    "meta": {
                        "retrieved_at": datetime.now().isoformat(),
                        "mode": "lightweight",
                        "rate_limit_remaining": self.rate_limit_remaining
                    }
                }
            
            # Full path: all data (with parallel requests where possible)
            results = {}
            
            # Primary PR data
            pr_data = self._make_request(endpoint)
            if "error" in pr_data:
                return pr_data
            results["pr_info"] = pr_data
            
            # Optional additional data
            if include_commits:
                commits = self._make_request(f"{endpoint}/commits")
                results["commits"] = commits if not isinstance(commits, dict) or "error" not in commits else []
            
            if include_files:
                files = self._make_request(f"{endpoint}/files")
                results["files_changed"] = files if not isinstance(files, dict) or "error" not in files else []
            
            results["meta"] = {
                "retrieved_at": datetime.now().isoformat(),
                "mode": "comprehensive",
                "rate_limit_remaining": self.rate_limit_remaining,
                "cached_requests": sum(1 for k in [endpoint, f"{endpoint}/commits", f"{endpoint}/files"] 
                                     if self._is_cache_valid(f"{k}:{{}}"))
            }
            
            return results
            
        except Exception as e:
            return {"error": str(e), "fallback_to_cli": True}
    
    def get_pull_request_batch(self, repo: str, pr_numbers: List[int], 
                              lightweight: bool = True) -> Dict:
        """Optimized batch PR retrieval"""
        results = {}
        
        for pr_number in pr_numbers:
            try:
                result = self.get_pull_request(repo, pr_number, 
                                             include_commits=not lightweight,
                                             include_files=not lightweight,
                                             lightweight=lightweight)
                results[pr_number] = result
                
                # Brief pause to be respectful to API
                if not lightweight:
                    time.sleep(0.1)
                    
            except Exception as e:
                results[pr_number] = {"error": str(e)}
        
        return {
            "batch_results": results,
            "total_processed": len(pr_numbers),
            "successful": len([r for r in results.values() if "error" not in r]),
            "meta": {
                "batch_mode": "lightweight" if lightweight else "comprehensive",
                "processed_at": datetime.now().isoformat()
            }
        }
    
    def search_pull_requests(self, repo: str, query: str = "", 
                           state: str = "all", limit: int = 100,
                           use_cache: bool = True) -> Dict:
        """Optimized PR search with caching"""
        try:
            search_query = f"repo:{repo} type:pr {query}".strip()
            endpoint = "/search/issues"
            params = {
                "q": search_query,
                "state": state,
                "per_page": min(limit, 100),
                "sort": "updated"
            }
            
            result = self._make_request(endpoint, params, use_cache)
            
            if "error" in result:
                return result
            
            return {
                "total_count": result.get("total_count", 0),
                "pull_requests": result.get("items", []),
                "meta": {
                    "query": search_query,
                    "limit": limit,
                    "retrieved_at": datetime.now().isoformat(),
                    "cached": self._is_cache_valid(f"{endpoint}:{json.dumps(params, sort_keys=True)}")
                }
            }
            
        except Exception as e:
            return {"error": str(e), "fallback_to_cli": True}
    
    def analyze_pr_timeline(self, repo: str, pr_numbers: List[int]) -> Dict:
        """Optimized multi-PR timeline analysis"""
        try:
            # Use lightweight mode for timeline analysis
            batch_result = self.get_pull_request_batch(repo, pr_numbers, lightweight=True)
            
            timeline_data = []
            for pr_number, pr_data in batch_result.get("batch_results", {}).items():
                if "error" not in pr_data and "pr_info" in pr_data:
                    pr_info = pr_data["pr_info"]
                    timeline_data.append({
                        "pr_number": pr_number,
                        "created_at": pr_info.get("created_at"),
                        "updated_at": pr_info.get("updated_at"),
                        "merged_at": pr_info.get("merged_at"),
                        "state": pr_info.get("state"),
                        "title": pr_info.get("title", "")[:100]  # Truncate for performance
                    })
            
            # Sort by creation date
            timeline_data.sort(key=lambda x: x.get("created_at", ""))
            
            return {
                "timeline": timeline_data,
                "total_prs": len(pr_numbers),
                "analyzed_prs": len(timeline_data),
                "analysis": {
                    "date_range": {
                        "earliest": timeline_data[0].get("created_at") if timeline_data else None,
                        "latest": timeline_data[-1].get("created_at") if timeline_data else None
                    },
                    "states": {state: sum(1 for pr in timeline_data if pr.get("state") == state) 
                             for state in ["open", "closed", "merged"]},
                },
                "meta": {
                    "analyzed_at": datetime.now().isoformat(),
                    "optimization": "lightweight_batch_mode"
                }
            }
            
        except Exception as e:
            return {"error": str(e), "fallback_available": False}
    
    def test_connection(self) -> Dict:
        """Test connection with performance metrics"""
        try:
            start_time = time.time()
            
            # Lazy initialization test
            if self.auth_token is None:
                init_start = time.time()
                self._initialize()
                init_time = (time.time() - init_start) * 1000
            else:
                init_time = 0
            
            # Quick API test
            api_start = time.time()
            result = self._make_request("/rate_limit")
            api_time = (time.time() - api_start) * 1000
            
            total_time = (time.time() - start_time) * 1000
            
            if "error" not in result:
                return {
                    "status": "connected",
                    "user": result.get("resources", {}).get("core", {}).get("remaining", "unknown"),
                    "rate_limit_remaining": self.rate_limit_remaining,
                    "performance": {
                        "total_time": f"{total_time:.2f}ms",
                        "init_time": f"{init_time:.2f}ms",
                        "api_time": f"{api_time:.2f}ms"
                    },
                    "optimizations": {
                        "lazy_initialization": init_time == 0,
                        "session_pooling": self.session is not None,
                        "caching_enabled": True
                    }
                }
            else:
                return {"status": "error", "error": result["error"]}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def clear_cache(self):
        """Clear performance cache"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        valid_entries = sum(1 for entry in self.cache.values() 
                          if datetime.now() < entry['expires'])
        
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
            "cache_ttl": self.cache_ttl
        }

# Performance testing function
def compare_github_performance():
    """Compare GitHub MCP performance optimizations"""
    import time
    
    print("🏃 GitHub Performance Comparison Test")
    print("=" * 45)
    
    try:
        # Test optimized version
        optimized = OptimizedGitHubMCPIntegration(lazy_init=True)
        
        # Test 1: Initialization overhead
        start = time.time()
        test_result = optimized.test_connection()
        init_time = (time.time() - start) * 1000
        
        print(f"Optimized initialization: {init_time:.2f}ms")
        print(f"Status: {test_result.get('status', 'unknown')}")
        
        # Test 2: Lightweight PR fetch
        start = time.time()
        pr_result = optimized.get_pull_request("stolostron/cluster-curator-controller", 468, lightweight=True)
        lightweight_time = (time.time() - start) * 1000
        
        print(f"Lightweight PR fetch: {lightweight_time:.2f}ms")
        
        # Test 3: Full PR fetch (for comparison)
        start = time.time()
        full_result = optimized.get_pull_request("stolostron/cluster-curator-controller", 468, lightweight=False)
        full_time = (time.time() - start) * 1000
        
        print(f"Full PR fetch: {full_time:.2f}ms")
        print(f"Speedup: {full_time/lightweight_time:.1f}x faster with lightweight mode")
        
        # Test 4: Cache performance
        start = time.time()
        cached_result = optimized.get_pull_request("stolostron/cluster-curator-controller", 468, lightweight=True)
        cached_time = (time.time() - start) * 1000
        
        print(f"Cached PR fetch: {cached_time:.2f}ms")
        print(f"Cache speedup: {lightweight_time/cached_time:.1f}x faster")
        
        cache_stats = optimized.get_cache_stats()
        print(f"Cache stats: {cache_stats}")
        
        if lightweight_time < 500:  # Less than 500ms
            print("✅ Performance optimizations successful")
        else:
            print("⚠️ Performance could be improved further")
            
    except Exception as e:
        print(f"❌ Performance test error: {str(e)[:60]}...")

if __name__ == "__main__":
    compare_github_performance()
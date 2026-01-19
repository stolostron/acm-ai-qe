#!/usr/bin/env python3
"""
Example Integration with Simplified MCP Coordinator
===================================================

This example shows how to integrate the simplified MCP coordinator
into your framework code with proper error handling and monitoring.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# Import the simplified coordinator
from simplified_mcp_coordinator import SimplifiedMCPCoordinator, create_mcp_coordinator
from mcp_config_manager import MCPConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FrameworkMCPService:
    """
    Example service class showing how to integrate MCP into your framework
    
    This demonstrates:
    - Proper initialization
    - Error handling
    - Performance monitoring
    - Caching strategies
    - Fallback handling
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        # Initialize configuration manager
        self.config_manager = MCPConfigManager(config_path)
        
        # Apply environment-specific settings
        self.config_manager.apply_environment_overrides()
        
        # Create MCP coordinator
        self.mcp = create_mcp_coordinator(config_path)
        
        # Track service metrics
        self.operation_count = 0
        self.error_count = 0
        
        logger.info("Framework MCP Service initialized")
        logger.info(f"Environment: {self.config_manager.environment}")
        logger.info(f"Servers: {self.config_manager.list_servers()}")
    
    def analyze_github_pr(self, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Analyze a GitHub pull request with automatic fallback
        
        This shows proper error handling and result processing
        """
        self.operation_count += 1
        
        try:
            # Get PR information via MCP
            logger.info(f"Fetching PR {repo}#{pr_number}")
            result = self.mcp.github_get_pull_request(repo, pr_number)
            
            if result.get("status") == "error":
                self.error_count += 1
                logger.error(f"Failed to fetch PR: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error"),
                    "source": result.get("source", "unknown")
                }
            
            # Process the result
            pr_data = result.get("data", {})
            
            # Example analysis
            analysis = {
                "success": True,
                "pr_number": pr_number,
                "title": pr_data.get("title", "Unknown"),
                "state": pr_data.get("state", "unknown"),
                "author": pr_data.get("author", {}).get("login", "unknown"),
                "source": result.get("source", "mcp"),
                "analysis": {
                    "files_changed": len(pr_data.get("files", [])),
                    "commits": len(pr_data.get("commits", [])),
                    "is_large_pr": len(pr_data.get("files", [])) > 50
                }
            }
            
            return analysis
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Exception analyzing PR: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "exception"
            }
    
    def find_test_files(self, pattern: str = "*test*.py") -> Dict[str, Any]:
        """
        Find test files in the repository
        
        Demonstrates filesystem operations with MCP
        """
        self.operation_count += 1
        
        try:
            # Search for test files
            logger.info(f"Searching for test files: {pattern}")
            result = self.mcp.filesystem_search_files(pattern, max_results=100)
            
            if result.get("status") == "error":
                self.error_count += 1
                logger.error(f"Failed to search files: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error"),
                    "source": result.get("source", "unknown")
                }
            
            # Process results
            files_data = result.get("data", {})
            test_files = files_data.get("files", [])
            
            # Categorize test files
            categorized = {
                "unit_tests": [],
                "integration_tests": [],
                "e2e_tests": [],
                "other_tests": []
            }
            
            for file_info in test_files:
                file_path = file_info.get("path", "")
                if "unit" in file_path:
                    categorized["unit_tests"].append(file_path)
                elif "integration" in file_path:
                    categorized["integration_tests"].append(file_path)
                elif "e2e" in file_path:
                    categorized["e2e_tests"].append(file_path)
                else:
                    categorized["other_tests"].append(file_path)
            
            return {
                "success": True,
                "total_files": files_data.get("count", 0),
                "categorized": categorized,
                "source": result.get("source", "mcp")
            }
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Exception finding test files: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "exception"
            }
    
    def batch_analyze_prs(self, repo: str, pr_numbers: List[int]) -> Dict[str, Any]:
        """
        Analyze multiple PRs efficiently
        
        Demonstrates batch operations and caching benefits
        """
        results = []
        cache_hits = 0
        
        # Get initial cache metrics
        initial_metrics = self.mcp.get_status()["metrics"]
        initial_cache_hits = initial_metrics.get("cache_hits", 0)
        
        # Process each PR
        for pr_number in pr_numbers:
            result = self.analyze_github_pr(repo, pr_number)
            results.append(result)
        
        # Calculate cache performance
        final_metrics = self.mcp.get_status()["metrics"]
        final_cache_hits = final_metrics.get("cache_hits", 0)
        cache_hits = final_cache_hits - initial_cache_hits
        
        return {
            "success": True,
            "analyzed_count": len(results),
            "successful_count": sum(1 for r in results if r.get("success")),
            "cache_hits": cache_hits,
            "cache_hit_rate": cache_hits / len(pr_numbers) if pr_numbers else 0,
            "results": results
        }
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get comprehensive service health information"""
        mcp_status = self.mcp.get_status()
        
        # Calculate service-level metrics
        success_rate = (self.operation_count - self.error_count) / max(self.operation_count, 1)
        
        return {
            "service": "framework_mcp",
            "healthy": success_rate > 0.9,
            "metrics": {
                "operations": self.operation_count,
                "errors": self.error_count,
                "success_rate": success_rate
            },
            "mcp_status": mcp_status,
            "environment": self.config_manager.environment
        }
    
    def demonstrate_error_handling(self):
        """Demonstrate various error scenarios and handling"""
        print("\n🔍 Demonstrating Error Handling...")
        
        # Test 1: Non-existent repository
        result = self.analyze_github_pr("fake-owner/fake-repo", 1)
        print(f"\nNon-existent repo result: {json.dumps(result, indent=2)}")
        
        # Test 2: Invalid pattern
        result = self.find_test_files("***invalid***")
        print(f"\nInvalid pattern result: {json.dumps(result, indent=2)}")
        
        # Test 3: Server health check
        health = self.get_service_health()
        print(f"\nService health: {json.dumps(health, indent=2)}")


def main():
    """Demonstrate the integration"""
    print("🚀 MCP Framework Integration Example\n")
    
    # Initialize service
    service = FrameworkMCPService()
    
    # Example 1: Analyze a real PR
    print("📊 Example 1: Analyzing a GitHub PR")
    result = service.analyze_github_pr("microsoft/vscode", 1)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Example 2: Find test files
    print("\n📁 Example 2: Finding test files")
    result = service.find_test_files("*test*.py")
    print(f"Found {result.get('total_files', 0)} test files")
    for category, files in result.get("categorized", {}).items():
        print(f"  {category}: {len(files)} files")
    
    # Example 3: Batch operations
    print("\n🔄 Example 3: Batch PR analysis")
    result = service.batch_analyze_prs("microsoft/vscode", [1, 2, 3, 4, 5])
    print(f"Analyzed {result['analyzed_count']} PRs")
    print(f"Cache hit rate: {result['cache_hit_rate']:.1%}")
    
    # Example 4: Error handling
    service.demonstrate_error_handling()
    
    # Show final metrics
    print("\n📈 Final Service Metrics:")
    health = service.get_service_health()
    print(json.dumps(health, indent=2))


if __name__ == "__main__":
    main()




#!/usr/bin/env python3
"""
Test Suite for Simplified MCP Implementation
===========================================

Comprehensive tests to ensure the simplified MCP coordinator works correctly
with proper fallback handling, caching, and monitoring.
"""

import json
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from simplified_mcp_coordinator import (
    SimplifiedMCPCoordinator,
    MCPHealthChecker,
    MCPServerStatus,
    PerformanceMonitor,
    FallbackManager
)


class TestMCPHealthChecker(unittest.TestCase):
    """Test the health checking functionality"""
    
    def setUp(self):
        self.health_checker = MCPHealthChecker(check_interval=1)
    
    def test_initial_status_unknown(self):
        """Test that servers start with unknown status"""
        status = self.health_checker.check_server_health("test-server")
        self.assertIn(status, [MCPServerStatus.UNKNOWN, MCPServerStatus.UNAVAILABLE])
    
    def test_status_caching(self):
        """Test that status is cached within interval"""
        # First check
        status1 = self.health_checker.check_server_health("test-server")
        
        # Immediate second check should return cached value
        status2 = self.health_checker.check_server_health("test-server")
        self.assertEqual(status1, status2)
    
    def test_status_refresh_after_interval(self):
        """Test that status refreshes after interval"""
        # First check
        self.health_checker.check_server_health("test-server")
        
        # Wait for interval to pass
        time.sleep(1.1)
        
        # This should trigger a new check
        with patch.object(self.health_checker, '_perform_health_check') as mock_check:
            mock_check.return_value = MCPServerStatus.AVAILABLE
            status = self.health_checker.check_server_health("test-server")
            mock_check.assert_called_once()
            self.assertEqual(status, MCPServerStatus.AVAILABLE)


class TestPerformanceMonitor(unittest.TestCase):
    """Test performance monitoring functionality"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
    
    def test_record_mcp_success(self):
        """Test recording successful MCP calls"""
        self.monitor.record_call("mcp", True, 0.1)
        metrics = self.monitor.get_metrics()
        
        self.assertEqual(metrics["mcp_calls"], 1)
        self.assertEqual(metrics["mcp_successes"], 1)
        self.assertEqual(metrics["mcp_failures"], 0)
        self.assertEqual(metrics["mcp_success_rate"], 1.0)
    
    def test_record_fallback_failure(self):
        """Test recording failed fallback calls"""
        self.monitor.record_call("fallback", False, 0.2)
        metrics = self.monitor.get_metrics()
        
        self.assertEqual(metrics["fallback_calls"], 1)
        self.assertEqual(metrics["fallback_successes"], 0)
        self.assertEqual(metrics["fallback_failures"], 1)
        self.assertEqual(metrics["fallback_success_rate"], 0.0)
    
    def test_average_latency_calculation(self):
        """Test average latency calculation"""
        self.monitor.record_call("mcp", True, 0.1)
        self.monitor.record_call("mcp", True, 0.3)
        self.monitor.record_call("fallback", True, 0.2)
        
        metrics = self.monitor.get_metrics()
        self.assertAlmostEqual(metrics["avg_latency"], 0.2, places=2)


class TestFallbackManager(unittest.TestCase):
    """Test fallback management functionality"""
    
    def setUp(self):
        self.fallback_manager = FallbackManager()
    
    def test_default_strategies_registered(self):
        """Test that default fallback strategies are registered"""
        strategies = self.fallback_manager.fallback_strategies
        
        self.assertIn("github_get_pull_request", strategies)
        self.assertIn("filesystem_search_files", strategies)
        self.assertIn("filesystem_grep_content", strategies)
    
    def test_custom_fallback_registration(self):
        """Test registering custom fallback"""
        def custom_fallback(**kwargs):
            return {"status": "success", "custom": True}
        
        self.fallback_manager.register_fallback("custom_op", custom_fallback)
        result = self.fallback_manager.execute_fallback("custom_op")
        
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["custom"])
        self.assertEqual(result["source"], "fallback")
    
    def test_fallback_error_handling(self):
        """Test fallback error handling"""
        def failing_fallback(**kwargs):
            raise Exception("Fallback failed")
        
        self.fallback_manager.register_fallback("failing_op", failing_fallback)
        result = self.fallback_manager.execute_fallback("failing_op")
        
        self.assertIn("error", result)
        self.assertTrue(result["fallback_failed"])
    
    @patch('subprocess.run')
    def test_github_pr_fallback(self, mock_run):
        """Test GitHub PR fallback with mocked gh CLI"""
        mock_run.return_value = Mock(
            stdout='{"title": "Test PR", "state": "open"}',
            stderr='',
            returncode=0
        )
        
        result = self.fallback_manager._github_pr_cli_fallback("owner/repo", 123)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["title"], "Test PR")
        mock_run.assert_called_once()


class TestSimplifiedMCPCoordinator(unittest.TestCase):
    """Test the main coordinator functionality"""
    
    def setUp(self):
        # Create a test config file
        self.test_config = {
            "mcpServers": {
                "test-server": {
                    "type": "stdio",
                    "command": "python3",
                    "args": ["test_server.py"]
                }
            }
        }
        
        self.config_path = Path("test_mcp_config.json")
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
        
        self.coordinator = SimplifiedMCPCoordinator(self.config_path)
    
    def tearDown(self):
        # Clean up test config
        if self.config_path.exists():
            self.config_path.unlink()
    
    def test_initialization(self):
        """Test coordinator initialization"""
        self.assertIsNotNone(self.coordinator.health_checker)
        self.assertIsNotNone(self.coordinator.performance_monitor)
        self.assertIsNotNone(self.coordinator.fallback_manager)
        self.assertEqual(self.coordinator.config["mcpServers"]["test-server"]["command"], "python3")
    
    def test_cache_functionality(self):
        """Test caching mechanism"""
        # Create cache key
        cache_key = self.coordinator._get_cache_key("server", "tool", {"param": "value"})
        
        # Test cache miss
        result = self.coordinator._check_cache(cache_key)
        self.assertIsNone(result)
        
        # Update cache
        test_data = {"status": "success", "data": "test"}
        self.coordinator._update_cache(cache_key, test_data)
        
        # Test cache hit
        result = self.coordinator._check_cache(cache_key)
        self.assertEqual(result, test_data)
    
    @patch.object(MCPHealthChecker, 'check_server_health')
    @patch.object(SimplifiedMCPCoordinator, '_execute_mcp_call')
    def test_successful_mcp_call(self, mock_execute, mock_health):
        """Test successful MCP call flow"""
        mock_health.return_value = MCPServerStatus.AVAILABLE
        mock_execute.return_value = {"status": "success", "data": "test_result"}
        
        result = self.coordinator.call_mcp_tool("test-server", "test-tool", {"param": "value"})
        
        self.assertEqual(result["status"], "success")
        mock_health.assert_called_once_with("test-server")
        mock_execute.assert_called_once_with("test-server", "test-tool", {"param": "value"})
    
    @patch.object(MCPHealthChecker, 'check_server_health')
    @patch.object(FallbackManager, 'execute_fallback')
    def test_fallback_on_unavailable_server(self, mock_fallback, mock_health):
        """Test fallback when server is unavailable"""
        mock_health.return_value = MCPServerStatus.UNAVAILABLE
        mock_fallback.return_value = {"status": "success", "source": "fallback"}
        
        result = self.coordinator.call_mcp_tool("test-server", "test-tool", {"param": "value"})
        
        self.assertEqual(result["source"], "fallback")
        mock_fallback.assert_called_once()
    
    def test_convenience_methods(self):
        """Test high-level convenience methods"""
        with patch.object(self.coordinator, 'call_mcp_tool') as mock_call:
            mock_call.return_value = {"status": "success"}
            
            # Test GitHub method
            self.coordinator.github_get_pull_request("owner/repo", 123)
            mock_call.assert_called_with(
                "test-generator-github",
                "get_pull_request",
                {"repo": "owner/repo", "pr_number": 123}
            )
            
            # Test filesystem method
            self.coordinator.filesystem_search_files("*.py")
            mock_call.assert_called_with(
                "test-generator-filesystem",
                "search_files",
                {"pattern": "*.py", "max_results": 100}
            )
    
    def test_status_reporting(self):
        """Test status reporting functionality"""
        status = self.coordinator.get_status()
        
        self.assertIn("coordinator", status)
        self.assertIn("servers", status)
        self.assertIn("metrics", status)
        self.assertIn("cache_size", status)
        self.assertIn("fallback_strategies", status)
    
    def test_cache_clearing(self):
        """Test cache clearing functionality"""
        # Add something to cache
        self.coordinator._update_cache("test_key", {"data": "test"})
        self.assertEqual(len(self.coordinator.cache), 1)
        
        # Clear cache
        self.coordinator.clear_cache()
        self.assertEqual(len(self.coordinator.cache), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        self.coordinator = SimplifiedMCPCoordinator()
    
    @patch('subprocess.run')
    def test_end_to_end_with_fallback(self, mock_run):
        """Test end-to-end flow with fallback"""
        # Mock gh CLI response
        mock_run.return_value = Mock(
            stdout='{"title": "Integration Test PR", "state": "open", "author": {"login": "test-user"}}',
            stderr='',
            returncode=0
        )
        
        # Server will be unavailable, triggering fallback
        result = self.coordinator.github_get_pull_request("test/repo", 1)
        
        # Should get result from fallback
        self.assertEqual(result.get("source"), "fallback")
        self.assertEqual(result.get("data", {}).get("title"), "Integration Test PR")
    
    def test_performance_metrics_accumulation(self):
        """Test that performance metrics accumulate correctly"""
        initial_metrics = self.coordinator.get_status()["metrics"]
        
        # Make several calls (will use fallback)
        for i in range(3):
            self.coordinator.filesystem_search_files(f"test{i}.py")
        
        final_metrics = self.coordinator.get_status()["metrics"]
        
        # Metrics should have increased
        self.assertGreater(
            final_metrics["fallback_calls"],
            initial_metrics["fallback_calls"]
        )


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    print("🧪 Running Simplified MCP Coordinator Tests\n")
    run_tests()
    print("\n✅ Testing complete!")




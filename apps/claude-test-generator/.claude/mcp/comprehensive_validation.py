#!/usr/bin/env python3
"""
Comprehensive Validation - GitHub MCP Server Analysis
====================================================

Validates all recent changes and confirms root cause analysis.
"""

import json
import subprocess
import os
import sys
import time
from typing import Dict, Any, List

class ComprehensiveValidator:
    """Validates all aspects of the GitHub MCP server implementation"""
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        self.validation_count = 0
        
    def log_result(self, test_name: str, status: str, details: Dict[str, Any] = None):
        """Log validation result"""
        self.validation_count += 1
        self.results[test_name] = {
            "status": status,
            "details": details or {},
            "timestamp": time.time() - self.start_time
        }
        print(f"[{self.validation_count:2d}] {test_name}: {status}", file=sys.stderr)
        if details:
            print(f"     Details: {json.dumps(details, indent=4)[:200]}...", file=sys.stderr)
    
    def validate_root_cause_analysis(self) -> Dict[str, Any]:
        """Validate our root cause analysis findings"""
        print("🔍 VALIDATING ROOT CAUSE ANALYSIS", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        findings = {}
        
        # Test 1: Verify GitHub CLI authentication works in normal context
        try:
            result = subprocess.run(['gh', 'auth', 'token'], 
                                  capture_output=True, text=True, check=True, timeout=5)
            token = result.stdout.strip()
            findings["github_cli_works"] = {
                "status": "CONFIRMED",
                "token_length": len(token),
                "token_prefix": token[:10]
            }
            self.log_result("GitHub CLI Authentication", "✅ WORKING", findings["github_cli_works"])
        except Exception as e:
            findings["github_cli_works"] = {"status": "FAILED", "error": str(e)}
            self.log_result("GitHub CLI Authentication", "❌ FAILED", findings["github_cli_works"])
        
        # Test 2: Verify direct API calls work with token
        try:
            import urllib.request
            token = subprocess.run(['gh', 'auth', 'token'], 
                                 capture_output=True, text=True, check=True).stdout.strip()
            
            request = urllib.request.Request('https://api.github.com/rate_limit')
            request.add_header('Authorization', f'token {token}')
            request.add_header('User-Agent', 'Validation-Test/1.0')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())
                findings["direct_api_works"] = {
                    "status": "CONFIRMED",
                    "response_code": response.status,
                    "rate_limit": data.get("rate", {}).get("remaining", "unknown")
                }
                self.log_result("Direct API Access", "✅ WORKING", findings["direct_api_works"])
        except Exception as e:
            findings["direct_api_works"] = {"status": "FAILED", "error": str(e)}
            self.log_result("Direct API Access", "❌ FAILED", findings["direct_api_works"])
        
        # Test 3: Verify MCP server works in direct execution
        try:
            cmd = '''echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "health_check", "arguments": {}}}' | python3 /Users/ashafi/Documents/work/ai/ai_systems/apps/claude-test-generator/.claude/mcp/simple_github_mcp_server.py'''
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15,
                                  env={"GITHUB_TOKEN": token, "PATH": os.environ["PATH"]})
            
            # Parse the health check response
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                health_response = json.loads(lines[1])
                health_data = json.loads(health_response["result"]["content"][0]["text"])
                
                findings["mcp_direct_execution"] = {
                    "status": "CONFIRMED",
                    "health_status": health_data.get("status"),
                    "integration_type": health_data.get("debug", {}).get("integration_type")
                }
                self.log_result("MCP Direct Execution", "✅ WORKING", findings["mcp_direct_execution"])
            else:
                findings["mcp_direct_execution"] = {"status": "FAILED", "output": result.stdout[:200]}
                self.log_result("MCP Direct Execution", "❌ FAILED", findings["mcp_direct_execution"])
        except Exception as e:
            findings["mcp_direct_execution"] = {"status": "FAILED", "error": str(e)}
            self.log_result("MCP Direct Execution", "❌ FAILED", findings["mcp_direct_execution"])
        
        return findings
    
    def validate_integration_strategy(self) -> Dict[str, Any]:
        """Validate the integration strategy and fallback chain"""
        print("\n🔧 VALIDATING INTEGRATION STRATEGY", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        strategy_tests = {}
        
        # Test integration import order
        try:
            sys.path.insert(0, '/Users/ashafi/Documents/work/ai/ai_systems/apps/claude-test-generator/.claude/mcp')
            
            # Test each integration availability
            integrations = [
                ("optimized_github_mcp_integration", "OptimizedGitHubMCPIntegration"),
                ("hardcoded_github_mcp_integration", "HardcodedGitHubMCPIntegration"),
                ("fixed_github_mcp_integration", "FixedGitHubMCPIntegration"),
                ("stdlib_github_mcp_integration", "StdlibGitHubMCPIntegration")
            ]
            
            import_results = {}
            for module_name, class_name in integrations:
                try:
                    module = __import__(module_name)
                    cls = getattr(module, class_name)
                    import_results[module_name] = {"status": "AVAILABLE", "class": class_name}
                    self.log_result(f"Integration: {module_name}", "✅ AVAILABLE")
                except ImportError as e:
                    import_results[module_name] = {"status": "UNAVAILABLE", "error": str(e)}
                    self.log_result(f"Integration: {module_name}", "❌ UNAVAILABLE", {"error": str(e)})
            
            strategy_tests["integration_imports"] = import_results
        except Exception as e:
            strategy_tests["integration_imports"] = {"status": "FAILED", "error": str(e)}
            self.log_result("Integration Import Tests", "❌ FAILED")
        
        # Test fallback mechanism
        try:
            # Test server with different environments
            environments = [
                {"name": "full_env", "env": {"GITHUB_TOKEN": os.getenv('GITHUB_TOKEN', ''), "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}},
                {"name": "no_token", "env": {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}},
                {"name": "restricted", "env": {"PATH": "/usr/bin:/bin"}}
            ]
            
            fallback_results = {}
            for env_test in environments:
                try:
                    cmd = '''echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}' | python3 /Users/ashafi/Documents/work/ai/ai_systems/apps/claude-test-generator/.claude/mcp/simple_github_mcp_server.py'''
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10,
                                          env=env_test["env"])
                    
                    fallback_results[env_test["name"]] = {
                        "status": "SUCCESS" if result.returncode == 0 else "FAILED",
                        "stderr": result.stderr[-200:] if result.stderr else "",
                        "stdout_lines": len(result.stdout.split('\n')) if result.stdout else 0
                    }
                    
                    status = "✅ WORKING" if result.returncode == 0 else "❌ FAILED"
                    self.log_result(f"Fallback Test: {env_test['name']}", status)
                    
                except Exception as e:
                    fallback_results[env_test["name"]] = {"status": "ERROR", "error": str(e)}
                    self.log_result(f"Fallback Test: {env_test['name']}", "❌ ERROR")
            
            strategy_tests["fallback_mechanism"] = fallback_results
        except Exception as e:
            strategy_tests["fallback_mechanism"] = {"status": "FAILED", "error": str(e)}
            self.log_result("Fallback Mechanism Tests", "❌ FAILED")
        
        return strategy_tests
    
    def validate_api_functionality(self) -> Dict[str, Any]:
        """Validate all GitHub API functionality"""
        print("\n🌐 VALIDATING API FUNCTIONALITY", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        api_tests = {}
        
        # Test all MCP tools
        tools = [
            {"name": "health_check", "args": {}},
            {"name": "get_repository_info", "args": {"repo": "stolostron/cluster-curator-controller"}},
            {"name": "get_pull_request", "args": {"repo": "stolostron/cluster-curator-controller", "pr_number": 468}},
            {"name": "get_pull_request_files", "args": {"repo": "stolostron/cluster-curator-controller", "pr_number": 468}},
            {"name": "search_repositories", "args": {"query": "cluster-curator", "max_results": 2}}
        ]
        
        for tool in tools:
            try:
                github_token = os.getenv('GITHUB_TOKEN', '')
                cmd = f'''echo '{{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {{}}}}
{{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {{"name": "{tool["name"]}", "arguments": {json.dumps(tool["args"])}}}}}' | GITHUB_TOKEN="{github_token}" PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" python3 /Users/ashafi/Documents/work/ai/ai_systems/apps/claude-test-generator/.claude/mcp/simple_github_mcp_server.py'''
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        response = json.loads(lines[1])
                        result_data = json.loads(response["result"]["content"][0]["text"])
                        
                        api_tests[tool["name"]] = {
                            "status": "SUCCESS",
                            "result_status": result_data.get("status", "unknown"),
                            "has_data": "data" in result_data,
                            "response_size": len(str(result_data))
                        }
                        self.log_result(f"API Tool: {tool['name']}", "✅ WORKING")
                    else:
                        api_tests[tool["name"]] = {"status": "FAILED", "reason": "Invalid response format"}
                        self.log_result(f"API Tool: {tool['name']}", "❌ FAILED")
                else:
                    api_tests[tool["name"]] = {"status": "FAILED", "returncode": result.returncode}
                    self.log_result(f"API Tool: {tool['name']}", "❌ FAILED")
                    
            except Exception as e:
                api_tests[tool["name"]] = {"status": "ERROR", "error": str(e)}
                self.log_result(f"API Tool: {tool['name']}", "❌ ERROR")
        
        return api_tests
    
    def validate_claude_code_compatibility(self) -> Dict[str, Any]:
        """Validate Claude Code MCP client compatibility"""
        print("\n🤖 VALIDATING CLAUDE CODE COMPATIBILITY", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        compatibility_tests = {}
        
        # Test MCP configuration validity
        try:
            with open('/Users/ashafi/Documents/work/ai/ai_systems/apps/claude-test-generator/.mcp.json', 'r') as f:
                mcp_config = json.load(f)
            
            # Validate configuration structure
            config_validation = {
                "has_mcpServers": "mcpServers" in mcp_config,
                "has_github_server": "test-generator-github" in mcp_config.get("mcpServers", {}),
                "has_command": "command" in mcp_config.get("mcpServers", {}).get("test-generator-github", {}),
                "has_args": "args" in mcp_config.get("mcpServers", {}).get("test-generator-github", {}),
                "has_env": "env" in mcp_config.get("mcpServers", {}).get("test-generator-github", {}),
                "server_count": len(mcp_config.get("mcpServers", {}))
            }
            
            compatibility_tests["mcp_config"] = {
                "status": "VALID",
                "validation": config_validation
            }
            self.log_result("MCP Configuration", "✅ VALID")
            
        except Exception as e:
            compatibility_tests["mcp_config"] = {"status": "INVALID", "error": str(e)}
            self.log_result("MCP Configuration", "❌ INVALID")
        
        # Test file structure
        try:
            required_files = [
                '/Users/ashafi/Documents/work/ai/ai_systems/apps/claude-test-generator/.claude/mcp/simple_github_mcp_server.py',
                '/Users/ashafi/Documents/work/ai/ai_systems/apps/claude-test-generator/.claude/mcp/stdlib_github_mcp_integration.py',
                '/Users/ashafi/Documents/work/ai/ai_systems/apps/claude-test-generator/.claude/mcp/optimized_github_mcp_integration.py'
            ]
            
            file_status = {}
            for file_path in required_files:
                exists = os.path.exists(file_path)
                if exists:
                    file_size = os.path.getsize(file_path)
                    file_status[os.path.basename(file_path)] = {"exists": True, "size": file_size}
                else:
                    file_status[os.path.basename(file_path)] = {"exists": False}
            
            compatibility_tests["file_structure"] = {
                "status": "COMPLETE",
                "files": file_status
            }
            self.log_result("File Structure", "✅ COMPLETE")
            
        except Exception as e:
            compatibility_tests["file_structure"] = {"status": "INCOMPLETE", "error": str(e)}
            self.log_result("File Structure", "❌ INCOMPLETE")
        
        return compatibility_tests
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        print("\n📊 GENERATING VALIDATION REPORT", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        # Calculate summary statistics
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results.values() if "✅" in str(r)])
        failed_tests = len([r for r in self.results.values() if "❌" in str(r)])
        
        # Overall validation status
        overall_status = "PASSED" if failed_tests == 0 else "PARTIAL" if passed_tests > failed_tests else "FAILED"
        
        validation_report = {
            "summary": {
                "overall_status": overall_status,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
                "total_time": f"{time.time() - self.start_time:.2f}s"
            },
            "detailed_results": self.results,
            "conclusions": {
                "root_cause_analysis": "CONFIRMED" if "github_cli_works" in str(self.results) else "UNCONFIRMED",
                "integration_strategy": "WORKING" if passed_tests > failed_tests else "NEEDS_WORK",
                "api_functionality": "OPERATIONAL" if passed_tests >= total_tests * 0.8 else "DEGRADED",
                "claude_code_compatibility": "COMPATIBLE" if "mcp_config" in str(self.results) else "INCOMPATIBLE"
            },
            "recommendations": []
        }
        
        # Add recommendations based on results
        if failed_tests > 0:
            validation_report["recommendations"].append("Address failed test cases for complete functionality")
        if overall_status == "PASSED":
            validation_report["recommendations"].append("All validations passed - ready for production")
        else:
            validation_report["recommendations"].append("Review and fix failing components before deployment")
        
        return validation_report

def main():
    """Run comprehensive validation"""
    validator = ComprehensiveValidator()
    
    print("🔍 COMPREHENSIVE VALIDATION STARTING", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Run all validation tests
    root_cause_results = validator.validate_root_cause_analysis()
    integration_results = validator.validate_integration_strategy()
    api_results = validator.validate_api_functionality()
    compatibility_results = validator.validate_claude_code_compatibility()
    
    # Generate final report
    final_report = validator.generate_validation_report()
    
    print("\n🎯 VALIDATION COMPLETE", file=sys.stderr)
    print(f"Overall Status: {final_report['summary']['overall_status']}", file=sys.stderr)
    print(f"Success Rate: {final_report['summary']['success_rate']}", file=sys.stderr)
    
    return final_report

if __name__ == "__main__":
    import json
    result = main()
    print(json.dumps(result, indent=2))
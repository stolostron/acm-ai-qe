#!/usr/bin/env python3
"""
MCP Configuration Manager
=========================

Manages MCP configuration, server registration, and environment-specific settings.
Provides a clean interface for configuration management and validation.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging

logger = logging.getLogger(__name__)


class MCPConfigManager:
    """Manages MCP configuration and server settings"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(".mcp.json")
        self.config = self._load_config()
        self.environment = os.getenv("MCP_ENV", "development")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_path}")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "mcpServers": {},
            "settings": {
                "cache_ttl": 300,
                "health_check_interval": 60,
                "enable_fallback": True,
                "enable_cache": True,
                "log_level": "INFO"
            }
        }
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def register_server(self, name: str, server_config: Dict[str, Any]):
        """Register a new MCP server"""
        self.config.setdefault("mcpServers", {})[name] = server_config
        logger.info(f"Registered MCP server: {name}")
    
    def unregister_server(self, name: str):
        """Remove an MCP server"""
        if name in self.config.get("mcpServers", {}):
            del self.config["mcpServers"][name]
            logger.info(f"Unregistered MCP server: {name}")
    
    def get_server_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific server"""
        return self.config.get("mcpServers", {}).get(name)
    
    def list_servers(self) -> List[str]:
        """List all registered servers"""
        return list(self.config.get("mcpServers", {}).keys())
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting"""
        return self.config.get("settings", {}).get(key, default)
    
    def update_setting(self, key: str, value: Any):
        """Update a configuration setting"""
        self.config.setdefault("settings", {})[key] = value
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate the current configuration"""
        issues = []
        
        # Check servers
        servers = self.config.get("mcpServers", {})
        if not servers:
            issues.append("No MCP servers configured")
        
        for name, server in servers.items():
            if "command" not in server:
                issues.append(f"Server {name} missing 'command' field")
            if "args" not in server:
                issues.append(f"Server {name} missing 'args' field")
        
        # Check settings
        settings = self.config.get("settings", {})
        if settings.get("cache_ttl", 300) < 0:
            issues.append("cache_ttl must be non-negative")
        if settings.get("health_check_interval", 60) < 10:
            issues.append("health_check_interval should be at least 10 seconds")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        env_configs = {
            "development": {
                "log_level": "DEBUG",
                "cache_ttl": 60,
                "enable_cache": False
            },
            "testing": {
                "log_level": "INFO",
                "cache_ttl": 300,
                "enable_cache": True
            },
            "production": {
                "log_level": "WARNING",
                "cache_ttl": 600,
                "enable_cache": True
            }
        }
        
        return env_configs.get(self.environment, env_configs["development"])
    
    def apply_environment_overrides(self):
        """Apply environment-specific overrides to configuration"""
        env_config = self.get_environment_config()
        for key, value in env_config.items():
            self.update_setting(key, value)
        logger.info(f"Applied {self.environment} environment configuration")
    
    def export_config(self, output_path: Optional[Path] = None) -> str:
        """Export configuration as JSON string"""
        config_str = json.dumps(self.config, indent=2)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(config_str)
            logger.info(f"Configuration exported to {output_path}")
        
        return config_str
    
    def import_config(self, config_data: Union[str, Dict[str, Any], Path]):
        """Import configuration from JSON string, dict, or file"""
        if isinstance(config_data, Path):
            with open(config_data) as f:
                self.config = json.load(f)
        elif isinstance(config_data, str):
            self.config = json.loads(config_data)
        elif isinstance(config_data, dict):
            self.config = config_data
        else:
            raise ValueError("config_data must be a Path, string, or dict")
        
        logger.info("Configuration imported successfully")


def create_default_config(output_path: Optional[Path] = None) -> Dict[str, Any]:
    """Create a default MCP configuration file"""
    default_config = {
        "mcpServers": {
            "test-generator-filesystem": {
                "type": "stdio",
                "command": "python3",
                "args": [".claude/mcp/simple_mcp_server.py"],
                "env": {},
                "description": "Filesystem operations MCP server"
            },
            "test-generator-github": {
                "type": "stdio",
                "command": "python3",
                "args": [".claude/mcp/simple_github_mcp_server.py"],
                "env": {},
                "description": "GitHub API MCP server"
            }
        },
        "settings": {
            "cache_ttl": 300,
            "health_check_interval": 60,
            "enable_fallback": True,
            "enable_cache": True,
            "log_level": "INFO",
            "max_retries": 3,
            "retry_delay": 1.0
        }
    }
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        logger.info(f"Created default configuration at {output_path}")
    
    return default_config


# CLI interface for configuration management
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python mcp_config_manager.py <command> [args...]")
        print("Commands:")
        print("  list                - List all registered servers")
        print("  validate            - Validate current configuration")
        print("  export [path]       - Export configuration")
        print("  create-default      - Create default configuration")
        print("  show                - Show current configuration")
        sys.exit(1)
    
    command = sys.argv[1]
    manager = MCPConfigManager()
    
    if command == "list":
        servers = manager.list_servers()
        print("Registered MCP Servers:")
        for server in servers:
            config = manager.get_server_config(server)
            print(f"  - {server}: {config.get('description', 'No description')}")
    
    elif command == "validate":
        result = manager.validate_config()
        if result["valid"]:
            print("✅ Configuration is valid")
        else:
            print("❌ Configuration has issues:")
            for issue in result["issues"]:
                print(f"  - {issue}")
    
    elif command == "export":
        output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        config_str = manager.export_config(output_path)
        if not output_path:
            print(config_str)
    
    elif command == "create-default":
        output_path = Path(".mcp.json")
        create_default_config(output_path)
        print(f"Created default configuration at {output_path}")
    
    elif command == "show":
        print(json.dumps(manager.config, indent=2))
    
    else:
        print(f"Unknown command: {command}")

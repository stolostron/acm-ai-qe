#!/usr/bin/env python3
"""
Setup script for Claude Test Generator
Loads environment variables and validates configuration
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists():
        if env_example.exists():
            print("❌ .env file not found!")
            print("📋 Please copy .env.example to .env and fill in your values:")
            print(f"   cp .env.example .env")
            print(f"   # Then edit .env with your actual tokens")
            return False
        else:
            print("❌ No .env configuration found!")
            return False
    
    # Load .env file
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value
    
    return True

def validate_configuration():
    """Validate that required configuration is present"""
    required_vars = ['GITHUB_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var) or os.environ.get(var) == 'your_github_token_here':
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("📝 Please update your .env file with actual values")
        return False
    
    print("✅ Configuration validated successfully!")
    return True

def main():
    """Main setup function"""
    print("🚀 Claude Test Generator Setup")
    print("=" * 40)
    
    if not load_env_file():
        sys.exit(1)
    
    if not validate_configuration():
        sys.exit(1)
    
    print("🎯 Ready to generate test plans!")
    print("💡 Usage: Generate test plan for ACM-12345")

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Centralized GitHub Credential Provider
======================================

Single source of truth for GitHub token retrieval.
Uses a secure hierarchy: GITHUB_TOKEN -> GH_TOKEN -> gh CLI

SECURITY: No hardcoded tokens - uses environment variables or authenticated CLI.
"""

import os
import subprocess
from functools import lru_cache
from typing import Optional


class GitHubCredentialError(Exception):
    """Raised when no valid GitHub token can be obtained."""
    pass


@lru_cache(maxsize=1)
def get_github_token() -> str:
    """
    Get GitHub token using a secure priority chain:
    1. GITHUB_TOKEN environment variable
    2. GH_TOKEN environment variable
    3. gh CLI auth token

    Returns:
        str: Valid GitHub token

    Raises:
        GitHubCredentialError: If no valid token can be obtained
    """
    # Priority 1: GITHUB_TOKEN environment variable
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token and _is_valid_token(github_token):
        return github_token

    # Priority 2: GH_TOKEN environment variable
    gh_token = os.getenv('GH_TOKEN')
    if gh_token and _is_valid_token(gh_token):
        return gh_token

    # Priority 3: GitHub CLI authentication
    cli_token = _get_token_from_cli()
    if cli_token and _is_valid_token(cli_token):
        return cli_token

    # No valid token found
    raise GitHubCredentialError(
        "No GitHub token found. Options:\n"
        "  1. Set GITHUB_TOKEN environment variable\n"
        "  2. Set GH_TOKEN environment variable\n"
        "  3. Run 'gh auth login' to authenticate GitHub CLI"
    )


def _is_valid_token(token: str) -> bool:
    """
    Validate that a token has the expected format.

    Valid token formats:
    - ghp_* (personal access tokens)
    - gho_* (OAuth tokens)
    - github_pat_* (fine-grained PATs)
    - Classic tokens (40+ character alphanumeric)
    """
    if not token or len(token) < 20:
        return False

    # Check for known token prefixes
    valid_prefixes = ('ghp_', 'gho_', 'github_pat_', 'ghs_')
    if any(token.startswith(prefix) for prefix in valid_prefixes):
        return True

    # Accept classic tokens (40+ alphanumeric characters)
    if len(token) >= 40 and token.isalnum():
        return True

    return False


def _get_token_from_cli() -> Optional[str]:
    """
    Attempt to get token from GitHub CLI.

    Returns:
        Optional[str]: Token if successful, None otherwise
    """
    try:
        result = subprocess.run(
            ['gh', 'auth', 'token'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        token = result.stdout.strip()
        if token:
            return token
    except subprocess.FileNotFoundError:
        # gh CLI not installed
        pass
    except subprocess.CalledProcessError:
        # gh CLI not authenticated
        pass
    except subprocess.TimeoutExpired:
        # gh CLI timed out
        pass
    except Exception:
        # Other unexpected errors
        pass

    return None


def clear_token_cache() -> None:
    """Clear the cached token (useful for testing)."""
    get_github_token.cache_clear()


def get_token_info() -> dict:
    """
    Get information about the current token source.

    Returns:
        dict: Token source information (does not expose token value)
    """
    info = {
        'has_github_token_env': bool(os.getenv('GITHUB_TOKEN')),
        'has_gh_token_env': bool(os.getenv('GH_TOKEN')),
        'gh_cli_available': False,
        'gh_cli_authenticated': False,
        'token_available': False,
        'token_source': None
    }

    # Check GitHub CLI availability
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True, timeout=2)
        info['gh_cli_available'] = result.returncode == 0

        if info['gh_cli_available']:
            auth_result = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True,
                timeout=5
            )
            info['gh_cli_authenticated'] = auth_result.returncode == 0
    except Exception:
        pass

    # Determine token source
    try:
        get_github_token()
        info['token_available'] = True

        if os.getenv('GITHUB_TOKEN') and _is_valid_token(os.getenv('GITHUB_TOKEN')):
            info['token_source'] = 'GITHUB_TOKEN'
        elif os.getenv('GH_TOKEN') and _is_valid_token(os.getenv('GH_TOKEN')):
            info['token_source'] = 'GH_TOKEN'
        elif info['gh_cli_authenticated']:
            info['token_source'] = 'gh_cli'
    except GitHubCredentialError:
        info['token_available'] = False

    return info


if __name__ == "__main__":
    import json
    import sys

    print("GitHub Credential Provider - Status Check", file=sys.stderr)
    print("=" * 45, file=sys.stderr)

    info = get_token_info()
    print(json.dumps(info, indent=2))

    try:
        token = get_github_token()
        print(f"\nToken retrieved successfully (length: {len(token)})", file=sys.stderr)
        print(f"Token prefix: {token[:10]}...", file=sys.stderr)
    except GitHubCredentialError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

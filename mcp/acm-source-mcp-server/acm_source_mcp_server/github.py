"""GitHub API helpers using the gh CLI."""

import asyncio
import json
import base64
from typing import Optional


async def run_gh(args: list[str], timeout: float = 30.0) -> tuple[int, str, str]:
    """Run a gh CLI command and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "gh", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return 1, "", "Command timed out"
    return proc.returncode, stdout.decode(), stderr.decode()


async def fetch_file(owner: str, repo: str, path: str, ref: str) -> Optional[str]:
    """Fetch raw file content from GitHub via the contents API."""
    rc, stdout, stderr = await run_gh([
        "api", "-X", "GET",
        f"repos/{owner}/{repo}/contents/{path}?ref={ref}",
        "-q", ".content",
    ])
    if rc != 0 or not stdout.strip():
        return None
    try:
        return base64.b64decode(stdout.strip()).decode("utf-8", errors="replace")
    except Exception:
        return None


async def search_github_code(query: str, owner: str, repo: str) -> list[str]:
    """Search code in a repo via GitHub search API. Returns list of file paths."""
    import urllib.parse
    full_query = f"{query}+repo:{owner}/{repo}"
    encoded_query = urllib.parse.quote(full_query, safe="+:")
    rc, stdout, stderr = await run_gh([
        "api", "-X", "GET",
        f"search/code?q={encoded_query}&per_page=30",
        "-q", ".items[].path",
    ])
    if rc != 0 or not stdout.strip():
        return []
    return [p for p in stdout.strip().split("\n") if p]


async def list_tree(owner: str, repo: str, ref: str, path_filter: Optional[str] = None) -> list[str]:
    """List files in a repo tree. Optionally filter by path prefix."""
    rc, stdout, stderr = await run_gh([
        "api", "-X", "GET",
        f"repos/{owner}/{repo}/git/trees/{ref}?recursive=1",
        "-q", ".tree[].path",
    ], timeout=60.0)
    if rc != 0 or not stdout.strip():
        return []
    paths = stdout.strip().split("\n")
    if path_filter:
        paths = [p for p in paths if p.startswith(path_filter)]
    return paths


async def run_command(cmd: list[str], timeout: float = 30.0) -> tuple[int, str, str]:
    """Run an arbitrary shell command."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return 1, "", "Command timed out"
    return proc.returncode, stdout.decode(), stderr.decode()

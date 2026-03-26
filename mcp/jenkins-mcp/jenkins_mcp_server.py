"""
Jenkins MCP Server for Cursor IDE.

Forked from: redhat-community-ai-tools/jenkins-mcp
Fixed: auth (Basic), log parsing (text), path handling (nested), trigger params
Added: Pipeline analyzer, downstream tree, test results, pipeline stages, build monitoring
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib3
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import FastMCP

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

JENKINS_CONFIG_PATH = Path.home() / ".jenkins" / "config.json"
JENKINS_TOOLS_DIR = os.environ.get("JENKINS_TOOLS_DIR", "")


def _load_config() -> dict:
    if JENKINS_CONFIG_PATH.exists():
        with open(JENKINS_CONFIG_PATH) as f:
            return json.load(f)
    return {
        "jenkins_url": os.environ.get("JENKINS_URL", ""),
        "jenkins_user": os.environ.get("JENKINS_USER", ""),
        "jenkins_token": os.environ.get("JENKINS_TOKEN", ""),
    }


_cfg = _load_config()
JENKINS_URL = _cfg.get("jenkins_url", "").rstrip("/")
JENKINS_USER = _cfg.get("jenkins_user", "")
JENKINS_TOKEN = _cfg.get("jenkins_token", "")

mcp = FastMCP("jenkins")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def normalize_job_path(job_path: str) -> str:
    """Convert 'folder/sub/job' to Jenkins API format 'job/folder/job/sub/job/job'.
    Paths already containing 'job/' segments are returned as-is.
    """
    if not job_path:
        return job_path
    job_path = job_path.strip("/")
    if job_path.startswith("job/"):
        return job_path
    parts = job_path.split("/")
    return "/".join(f"job/{p}" for p in parts)


def parse_jenkins_url(url: str) -> tuple[str, str, Optional[int]]:
    """Parse a full Jenkins build URL into (base_url, job_api_path, build_number).

    Example:
        https://jenkins.example.com/job/CI/job/main/42/
        -> ("https://jenkins.example.com", "job/CI/job/main", 42)
    """
    parsed = urlparse(url.rstrip("/"))
    path = parsed.path.rstrip("/")

    build_number: Optional[int] = None
    segments = path.split("/")
    if segments and segments[-1].isdigit():
        build_number = int(segments[-1])
        segments = segments[:-1]

    path_str = "/".join(segments)
    match = re.search(r"(/?job/.+)$", path_str)
    job_api_path = match.group(1).lstrip("/") if match else ""

    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return base_url, job_api_path, build_number


async def jenkins_api(
    api_path: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    expect_json: bool = True,
) -> dict[str, Any] | str | None:
    """Authenticated API call using HTTP Basic auth (username:token)."""
    auth = httpx.BasicAuth(JENKINS_USER, JENKINS_TOKEN)
    async with httpx.AsyncClient(verify=False, auth=auth, timeout=60.0) as client:
        url = f"{JENKINS_URL}/{api_path.lstrip('/')}"
        headers = {"Accept": "application/json"} if expect_json else {}

        if method.upper() == "GET":
            resp = await client.request(method, url, headers=headers, params=data)
        else:
            resp = await client.request(method, url, headers=headers, data=data)
        resp.raise_for_status()
        return resp.json() if expect_json else resp.text


def _check_tools_dir() -> Optional[str]:
    """Return error message if JENKINS_TOOLS_DIR is not configured."""
    if not JENKINS_TOOLS_DIR or not Path(JENKINS_TOOLS_DIR).is_dir():
        return (
            "JENKINS_TOOLS_DIR is not configured or does not exist. "
            "Set the JENKINS_TOOLS_DIR environment variable to the path of your "
            "jenkins-tools repository clone."
        )
    return None


def _run_tool(args: list[str], timeout: int = 120) -> str:
    """Run an existing jenkins-tools script as a subprocess."""
    env = os.environ.copy()
    env.update({
        "JENKINS_USER": JENKINS_USER,
        "JENKINS_TOKEN": JENKINS_TOKEN,
        "JENKINS_URL": JENKINS_URL,
        "JENKINS_API_TOKEN": JENKINS_TOKEN,
    })
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
        if proc.returncode != 0:
            return f"Error (exit {proc.returncode}):\n{proc.stderr}\n{proc.stdout}"
        return proc.stdout
    except subprocess.TimeoutExpired:
        return f"Error: timed out after {timeout}s"
    except FileNotFoundError as exc:
        return f"Error: script not found - {exc}"


# ------------------------------------------------------------------
# Core Jenkins API Tools
# ------------------------------------------------------------------

@mcp.tool()
async def get_all_jobs() -> Any:
    """List all Jenkins jobs at the root level with name, URL, and status color."""
    return await jenkins_api("api/json?tree=jobs[name,url,color]")


@mcp.tool()
async def get_job(job_path: str) -> Any:
    """Get details for a Jenkins job.

    Args:
        job_path: Slash-separated path (e.g. 'CI-Jobs/main-pipeline').
    """
    return await jenkins_api(f"{normalize_job_path(job_path)}/api/json")


@mcp.tool()
async def get_build(job_path: str, build_number: Optional[int] = None) -> Any:
    """Get build information for a Jenkins job.

    Args:
        job_path: Slash-separated path.
        build_number: Build number, or omit for last build.
    """
    base = normalize_job_path(job_path)
    suffix = f"/{build_number}" if build_number is not None else "/lastBuild"
    return await jenkins_api(f"{base}{suffix}/api/json")


@mcp.tool()
async def trigger_build(
    job_path: str,
    parameters: Optional[dict[str, str]] = None,
) -> str:
    """Trigger a Jenkins build, optionally with parameters.

    Args:
        job_path: Slash-separated path.
        parameters: Build parameters as key-value pairs.
    """
    base = normalize_job_path(job_path)
    if parameters:
        await jenkins_api(f"{base}/buildWithParameters", method="POST", data=parameters, expect_json=False)
    else:
        await jenkins_api(f"{base}/build", method="POST", expect_json=False)
    return f"Build triggered: {job_path}"


@mcp.tool()
async def get_build_log(
    job_path: str,
    build_number: Optional[int] = None,
    start: int = 0,
    max_lines: int = 500,
) -> str:
    """Get console output for a build (plain text).

    Args:
        job_path: Slash-separated path.
        build_number: Build number, or omit for last build.
        start: Byte offset for pagination.
        max_lines: Max lines to return (default 500, 0 = unlimited).
    """
    base = normalize_job_path(job_path)
    suffix = f"/{build_number}" if build_number is not None else "/lastBuild"
    text = await jenkins_api(
        f"{base}{suffix}/consoleText", data={"start": start}, expect_json=False,
    )
    if not isinstance(text, str):
        return str(text)
    if max_lines > 0:
        lines = text.split("\n")
        if len(lines) > max_lines:
            return (
                "\n".join(lines[-max_lines:])
                + f"\n\n[Truncated: last {max_lines} of {len(lines)} lines]"
            )
    return text


@mcp.tool()
async def get_build_status(build_url: str) -> Any:
    """Quick status check for a running or completed build.

    Args:
        build_url: Full Jenkins build URL.
    """
    _, job_api_path, build_number = parse_jenkins_url(build_url)
    suffix = f"/{build_number}" if build_number else "/lastBuild"
    return await jenkins_api(
        f"{job_api_path}{suffix}/api/json"
        "?tree=result,building,duration,estimatedDuration,displayName,timestamp",
    )


@mcp.tool()
async def get_pipeline_stages(
    job_path: str,
    build_number: Optional[int] = None,
) -> Any:
    """Get pipeline stage details via the Workflow API.
    Returns stage names, statuses, and durations.

    Args:
        job_path: Slash-separated path.
        build_number: Build number, or omit for last build.
    """
    base = normalize_job_path(job_path)
    suffix = f"/{build_number}" if build_number is not None else "/lastBuild"
    return await jenkins_api(f"{base}{suffix}/wfapi/describe")


# ------------------------------------------------------------------
# Specialized Tools (wrap existing jenkins-tools scripts)
# ------------------------------------------------------------------

@mcp.tool()
async def analyze_pipeline(
    build_url: str,
    max_depth: int = 10,
    console_lines: int = 200,
) -> str:
    """Deep failure analysis for a Jenkins pipeline build.
    Identifies root cause, failed stages, and provides fix recommendations.

    Args:
        build_url: Full Jenkins build URL.
        max_depth: Downstream recursion depth (default 10).
        console_lines: Console lines to analyze per job (default 200).
    """
    if err := _check_tools_dir():
        return err
    script = f"{JENKINS_TOOLS_DIR}/skills/jenkins-pipeline-analyzer/scripts/jenkins_pipeline_analyzer.py"
    args = [
        sys.executable, script,
        "--url", build_url,
        "--no-verify-ssl",
        "--format", "markdown",
        "--max-depth", str(max_depth),
        "--console-lines", str(console_lines),
    ]
    return await asyncio.to_thread(_run_tool, args, 180)


@mcp.tool()
async def get_downstream_tree(
    build_url: str,
    max_depth: int = 5,
    output_format: str = "tree",
) -> str:
    """Visualize the downstream job tree for a Jenkins build.

    Args:
        build_url: Full Jenkins build URL.
        max_depth: Recursion depth (default 5).
        output_format: 'tree' (ASCII), 'markdown', or 'json'.
    """
    if err := _check_tools_dir():
        return err
    script = f"{JENKINS_TOOLS_DIR}/skills/jenkins-downstream-tree/scripts/jenkins_downstream_tree.py"
    args = [
        sys.executable, script,
        "--url", build_url,
        "--no-verify-ssl",
        "--format", output_format,
        "--max-depth", str(max_depth),
    ]
    return await asyncio.to_thread(_run_tool, args, 120)


@mcp.tool()
async def get_test_results(
    job_path: str,
    build_number: Optional[int] = None,
    mode: str = "summary",
) -> str:
    """Fetch test results for a Jenkins build.

    Args:
        job_path: Slash-separated path.
        build_number: Build number, or omit for latest.
        mode: 'summary', 'full', or 'failures'.
    """
    if err := _check_tools_dir():
        return err
    script = f"{JENKINS_TOOLS_DIR}/skills/jenkins-result-summary/scripts/fetch_jenkins_results.py"
    args = [
        sys.executable, script,
        "--job", job_path,
        "--mode", mode,
        "--no-verify-ssl",
        "--pretty",
    ]
    if build_number is not None:
        args.extend(["--build", str(build_number)])
    return await asyncio.to_thread(_run_tool, args, 120)


@mcp.tool()
async def analyze_test_results(
    job_path: str,
    build_number: Optional[int] = None,
    failures_only: bool = False,
    output_format: str = "markdown",
) -> str:
    """Fetch and analyze test results grouped by component/squad.

    Args:
        job_path: Slash-separated path.
        build_number: Build number, or omit for latest.
        failures_only: Only show components with failures.
        output_format: 'markdown', 'summary', 'json', or 'slack'.
    """
    if err := _check_tools_dir():
        return err
    fetch_script = f"{JENKINS_TOOLS_DIR}/skills/jenkins-result-summary/scripts/fetch_jenkins_results.py"
    fetch_args = [
        sys.executable, fetch_script,
        "--job", job_path,
        "--mode", "summary",
        "--no-verify-ssl",
        "--pretty",
    ]
    if build_number is not None:
        fetch_args.extend(["--build", str(build_number)])

    fetched = await asyncio.to_thread(_run_tool, fetch_args, 120)
    if fetched.startswith("Error"):
        return fetched

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    try:
        tmp.write(fetched)
        tmp.close()

        analyze_script = f"{JENKINS_TOOLS_DIR}/skills/jenkins-result-summary/scripts/analyze.py"
        analyze_args = [
            sys.executable, analyze_script,
            "--input-file", tmp.name,
            "--format", output_format,
        ]
        if failures_only:
            analyze_args.append("--failures-only")
        return await asyncio.to_thread(_run_tool, analyze_args, 60)
    finally:
        os.unlink(tmp.name)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")

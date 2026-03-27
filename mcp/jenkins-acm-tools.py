#!/usr/bin/env python3
"""
Jenkins MCP Wrapper - Adds ACM-specific analysis tools on top of the upstream server.

The upstream jenkins-mcp server provides 7 generic tools (get_all_jobs, get_job,
get_build, trigger_build, get_build_log, get_build_status, get_pipeline_stages).

This wrapper adds 4 specialized tools that call jenkins-tools analysis scripts
for deeper CI/CD failure investigation specific to ACM pipelines.

Upstream: https://github.com/redhat-community-ai-tools/jenkins-mcp
PR with fixes: https://github.com/redhat-community-ai-tools/jenkins-mcp/pull/13

Usage: python jenkins-acm-tools.py
"""

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

JENKINS_TOOLS_DIR = os.environ.get("JENKINS_TOOLS_DIR", "")

# Import the upstream server's mcp instance and credentials
jenkins_mcp_dir = os.path.join(os.path.dirname(__file__), ".external", "jenkins-mcp")
sys.path.insert(0, jenkins_mcp_dir)

from jenkins_mcp_server import mcp, get_jenkins_context


def _check_tools_dir() -> Optional[str]:
    if not JENKINS_TOOLS_DIR or not Path(JENKINS_TOOLS_DIR).is_dir():
        return (
            "JENKINS_TOOLS_DIR is not configured or does not exist. "
            "Set the JENKINS_TOOLS_DIR environment variable to the path of your "
            "jenkins-tools repository clone."
        )
    return None


def _run_tool(args: list[str], timeout: int = 120) -> str:
    url, user, token = get_jenkins_context()
    env = os.environ.copy()
    env.update({
        "JENKINS_USER": user,
        "JENKINS_TOKEN": token,
        "JENKINS_URL": url,
        "JENKINS_API_TOKEN": token,
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


if __name__ == "__main__":
    print("Jenkins MCP + ACM tools: loading upstream server + 4 ACM analysis tools...", file=sys.stderr)
    mcp.run(transport="stdio")

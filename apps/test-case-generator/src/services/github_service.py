"""GitHub service using gh CLI for PR data retrieval."""

import json
import subprocess
from pathlib import Path
from typing import Optional

from ..models.gather_output import PRData


def _run_gh(args: list[str], timeout: int = 30) -> Optional[str]:
    """Run a gh CLI command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def search_pr_for_jira(jira_id: str, repo: str = "stolostron/console") -> Optional[int]:
    """Search for a PR associated with a JIRA ticket ID."""
    output = _run_gh([
        "search", "prs", jira_id,
        "--repo", repo,
        "--json", "number,title,state",
        "--limit", "5",
    ])
    if not output:
        return None

    try:
        results = json.loads(output)
        if results:
            return results[0]["number"]
    except (json.JSONDecodeError, KeyError, IndexError):
        pass
    return None


def get_pr_metadata(pr_number: int, repo: str = "stolostron/console") -> Optional[PRData]:
    """Fetch PR metadata via gh CLI."""
    output = _run_gh([
        "pr", "view", str(pr_number),
        "--repo", repo,
        "--json", "title,body,files,additions,deletions,mergedAt,state",
    ])
    if not output:
        return None

    try:
        data = json.loads(output)
        files = [f["path"] for f in data.get("files", [])]
        return PRData(
            number=pr_number,
            title=data.get("title", ""),
            repo=repo,
            state=data.get("state", ""),
            body=data.get("body"),
            files=files,
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            merged_at=data.get("mergedAt"),
        )
    except (json.JSONDecodeError, KeyError):
        return None


def get_pr_diff(pr_number: int, repo: str = "stolostron/console", output_path: Optional[Path] = None) -> Optional[str]:
    """Fetch the full PR diff."""
    output = _run_gh([
        "pr", "diff", str(pr_number),
        "--repo", repo,
    ], timeout=60)
    if not output:
        return None

    if output_path:
        output_path.write_text(output, encoding="utf-8")
        return str(output_path)

    return output


def detect_area_from_files(files: list[str]) -> Optional[str]:
    """Detect the console area from PR file paths."""
    area_patterns = {
        "governance": ["Governance", "governance", "policy", "Policy"],
        "rbac": ["rbac", "RBAC", "RoleAssignment", "ClusterPermission", "user-management"],
        "fleet-virt": ["Virtualization", "virtualization", "kubevirt", "fleet-virt"],
        "cclm": ["CCLM", "cclm", "LiveMigration", "live-migration"],
        "mtv": ["MTV", "mtv", "forklift", "migration-toolkit"],
        "clusters": ["Clusters", "clusters", "ClusterSet", "ClusterDeployment", "ClusterPool"],
        "search": ["Search", "search"],
        "applications": ["Applications", "applications", "Subscription", "Channel"],
        "credentials": ["Credentials", "credentials"],
    }

    area_scores: dict[str, int] = {}
    for file_path in files:
        for area, patterns in area_patterns.items():
            for pattern in patterns:
                if pattern in file_path:
                    area_scores[area] = area_scores.get(area, 0) + 1

    if area_scores:
        return max(area_scores, key=area_scores.get)
    return None

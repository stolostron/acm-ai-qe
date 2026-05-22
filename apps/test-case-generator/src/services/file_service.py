"""File service for reading local test cases, conventions, and knowledge."""

import os
from pathlib import Path
from typing import Optional


def get_app_root() -> Path:
    """Get the app root directory."""
    return Path(__file__).resolve().parent.parent.parent


def get_knowledge_dir() -> Path:
    """Get the knowledge database directory."""
    return get_app_root() / "knowledge"


def read_conventions() -> str:
    """Read the test case format conventions."""
    path = get_knowledge_dir() / "conventions" / "test-case-format.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def read_html_templates() -> str:
    """Read the Polarion HTML templates."""
    path = get_knowledge_dir() / "conventions" / "polarion-html-templates.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def read_area_knowledge(area: str) -> Optional[str]:
    """Read domain knowledge for a specific area."""
    path = get_knowledge_dir() / "architecture" / f"{area}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


AREA_TO_COMPONENT_DIRS = {
    "governance": ["grc"],
    "rbac": ["rbac"],
    "fleet-virt": ["virt"],
    "clusters": ["clc", "bm"],
    "search": ["search"],
    "applications": ["alc"],
    "credentials": ["clc"],
    "cclm": ["virt"],
    "mtv": ["mtv"],
}


def find_existing_test_cases(version: str, area: Optional[str] = None, max_count: int = 3) -> list[str]:
    """Find existing test case files for a given ACM version and area.

    Search order:
    1. External automation workspace (area-aware, if it exists)
    2. runs/ directory (previous pipeline runs)
    3. knowledge/examples/ (shipped sample — always available)
    """
    search_paths: list[Path] = []

    # 1. Check external automation workspace (opt-in via env var, no hardcoded default)
    automation_workspace = os.environ.get("ACM_AUTOMATION_WORKSPACE")
    if automation_workspace:
        automation_base = Path(automation_workspace)
        if automation_base.exists():
            component_dirs = AREA_TO_COMPONENT_DIRS.get(area, []) if area else []
            for component_dir in component_dirs:
                tc_path = automation_base / component_dir / "test-cases" / version
                if tc_path.exists():
                    search_paths.append(tc_path)

    # 2. Previous pipeline runs
    search_paths.append(get_app_root() / "runs" / "test-case-generator")

    # 3. Shipped sample test case (always available as fallback)
    search_paths.append(get_knowledge_dir() / "examples")

    results: list[str] = []
    for search_path in search_paths:
        if not search_path.exists():
            continue
        # For runs/ directory, search recursively
        glob_pattern = "**/*.md" if search_path == get_app_root() / "runs" / "test-case-generator" else "*.md"
        for md_file in sorted(search_path.glob(glob_pattern), key=lambda p: p.stat().st_mtime, reverse=True):
            if md_file.name.startswith("RHACM4K-") or md_file.name == "test-case.md" or md_file.name.startswith("sample-"):
                results.append(str(md_file))
                if len(results) >= max_count:
                    return results

    return results



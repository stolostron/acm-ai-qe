"""File service for reading local test cases, conventions, and knowledge."""

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


def find_existing_test_cases(version: str, max_count: int = 3) -> list[str]:
    """Find existing test case files for a given ACM version.

    Searches common locations where test cases may be stored.
    """
    search_paths = [
        get_app_root() / "runs",
    ]

    # Also check the automation workspace if accessible
    automation_tc_path = Path.home() / "Documents" / "work" / "automation" / "documentation" / "acm-components" / "virt" / "test-cases" / version
    if automation_tc_path.exists():
        search_paths.insert(0, automation_tc_path)

    results: list[str] = []
    for search_path in search_paths:
        if not search_path.exists():
            continue
        for md_file in sorted(search_path.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            if md_file.name.startswith("RHACM4K-"):
                results.append(str(md_file))
                if len(results) >= max_count:
                    return results

    return results


def read_naming_patterns() -> str:
    """Read the area naming patterns."""
    path = get_knowledge_dir() / "conventions" / "area-naming-patterns.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

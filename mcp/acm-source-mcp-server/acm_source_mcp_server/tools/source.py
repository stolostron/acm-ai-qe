"""Source code tools: get_component_source, get_component_types, get_routes, get_route_component, get_wizard_steps."""

import re
from acm_source_mcp_server.config import REPOS, get_branch_for_repo, state
from acm_source_mcp_server.github import fetch_file, list_tree


async def get_component_source(path: str, repo: str = "acm") -> str:
    """Fetch raw source code for a file from the currently active branch.

    Args:
        path: File path within the repository (e.g. 'frontend/src/routes/Infrastructure/Clusters/Clusters.tsx').
        repo: Repository key.
    """
    if repo not in REPOS:
        return f"Unknown repo '{repo}'. Valid: {list(REPOS.keys())}"

    info = REPOS[repo]
    branch = get_branch_for_repo(repo, state)
    content = await fetch_file(info["owner"], info["repo"], path, branch)
    if content is None:
        return f"File not found: {path} (branch: {branch}, repo: {info['owner']}/{info['repo']})"

    lines = [
        f"// File: {path}",
        f"// Repo: {info['owner']}/{info['repo']} (branch: {branch})",
        f"// Lines: {len(content.splitlines())}",
        "",
        content,
    ]
    return "\n".join(lines)


async def get_component_types(path: str, repo: str = "acm") -> str:
    """Extract TypeScript type/interface definitions from a source file.

    Args:
        path: File path within the repository.
        repo: Repository key.
    """
    if repo not in REPOS:
        return f"Unknown repo '{repo}'. Valid: {list(REPOS.keys())}"

    info = REPOS[repo]
    branch = get_branch_for_repo(repo, state)
    content = await fetch_file(info["owner"], info["repo"], path, branch)
    if content is None:
        return f"File not found: {path} (branch: {branch})"

    type_pattern = re.compile(
        r"^(export\s+)?(type|interface|enum)\s+\w+.*?(?=\n(?:export\s+)?(?:type|interface|enum|function|const|class|import)\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    matches = type_pattern.findall(content)
    if not matches:
        simple_pattern = re.compile(r"^(export\s+)?(type|interface|enum)\s+.+$", re.MULTILINE)
        simple_matches = simple_pattern.findall(content)
        if not simple_matches:
            return f"No type/interface/enum definitions found in {path}"

    extracted = []
    for match in re.finditer(
        r"^((?:export\s+)?(?:type|interface|enum)\s+\w+[^\n]*(?:\n(?!(?:export\s+)?(?:type|interface|enum|function|const|class|import)\s).*)*)",
        content,
        re.MULTILINE,
    ):
        extracted.append(match.group(0).strip())

    if not extracted:
        return f"No type/interface/enum definitions found in {path}"

    lines = [f"Types from {path} (branch: {branch}):", ""]
    for t in extracted:
        lines.append(t)
        lines.append("")

    return "\n".join(lines)


async def get_routes(repo: str = "acm") -> str:
    """Extract navigation paths and route definitions from the ACM Console or kubevirt-plugin.

    Args:
        repo: Repository key ('acm' or 'kubevirt').
    """
    if repo not in REPOS:
        return f"Unknown repo '{repo}'. Valid: {list(REPOS.keys())}"

    info = REPOS[repo]
    branch = get_branch_for_repo(repo, state)

    route_files = []
    if repo == "acm":
        candidates = [
            "frontend/src/routes/Routes.tsx",
            "frontend/src/routes/index.tsx",
            "frontend/src/NavigationPath.ts",
            "frontend/src/NavigationPath.tsx",
            "frontend/src/lib/NavigationPath.ts",
        ]
    elif repo == "kubevirt":
        candidates = [
            "src/utils/constants/routes.ts",
            "src/routes.tsx",
            "src/views/routes.ts",
        ]
    else:
        return f"Routes extraction not supported for repo '{repo}'."

    for candidate in candidates:
        content = await fetch_file(info["owner"], info["repo"], candidate, branch)
        if content:
            route_files.append((candidate, content))

    if not route_files:
        return f"No route files found in {info['owner']}/{info['repo']} (branch: {branch})"

    lines = [f"Route definitions from {info['owner']}/{info['repo']} (branch: {branch}):", ""]
    for filepath, content in route_files:
        lines.append(f"--- {filepath} ---")
        lines.append(content[:5000])
        if len(content) > 5000:
            lines.append(f"\n... truncated ({len(content)} chars total)")
        lines.append("")

    return "\n".join(lines)


async def get_route_component(route_path: str, repo: str = "acm") -> str:
    """Get the component file that handles a specific route path.

    Args:
        route_path: The URL path segment (e.g. '/multicloud/infrastructure/clusters').
        repo: Repository key.
    """
    if repo not in REPOS:
        return f"Unknown repo '{repo}'. Valid: {list(REPOS.keys())}"

    info = REPOS[repo]
    branch = get_branch_for_repo(repo, state)

    if repo == "acm":
        candidates = [
            "frontend/src/routes/Routes.tsx",
            "frontend/src/routes/index.tsx",
            "frontend/src/NavigationPath.ts",
        ]
    elif repo == "kubevirt":
        candidates = [
            "src/utils/constants/routes.ts",
            "src/routes.tsx",
        ]
    else:
        return f"Route component lookup not supported for repo '{repo}'."

    for candidate in candidates:
        content = await fetch_file(info["owner"], info["repo"], candidate, branch)
        if content and route_path in content:
            context_lines = []
            for i, line in enumerate(content.splitlines()):
                if route_path in line:
                    start = max(0, i - 3)
                    end = min(len(content.splitlines()), i + 10)
                    context_lines.extend(content.splitlines()[start:end])
                    break

            component_match = re.search(
                r"(?:component|element|render).*?[=:]\s*[<{]?\s*(\w+)",
                "\n".join(context_lines),
                re.IGNORECASE,
            )
            component_name = component_match.group(1) if component_match else "unknown"

            lines = [
                f"Route '{route_path}' found in {candidate} (branch: {branch})",
                f"Component: {component_name}",
                "",
                "Context:",
                "\n".join(context_lines),
            ]
            return "\n".join(lines)

    return f"Route '{route_path}' not found in {info['owner']}/{info['repo']} (branch: {branch})"


async def get_wizard_steps(path: str, repo: str = "acm") -> str:
    """Analyze a wizard component file to extract step structure.

    Args:
        path: File path to the wizard component.
        repo: Repository key.
    """
    if repo not in REPOS:
        return f"Unknown repo '{repo}'. Valid: {list(REPOS.keys())}"

    info = REPOS[repo]
    branch = get_branch_for_repo(repo, state)
    content = await fetch_file(info["owner"], info["repo"], path, branch)
    if content is None:
        return f"File not found: {path} (branch: {branch})"

    steps = []

    # PatternFly Wizard patterns
    step_patterns = [
        re.compile(r"<WizardStep\s[^>]*name=[\"']([^\"']+)[\"']", re.MULTILINE),
        re.compile(r"<WizardStep\s[^>]*title=[\"']([^\"']+)[\"']", re.MULTILINE),
        re.compile(r"name:\s*[\"']([^\"']+)[\"']", re.MULTILINE),
        re.compile(r"title:\s*[\"']([^\"']+)[\"'].*?(?:id|key):\s*[\"']([^\"']+)[\"']", re.MULTILINE),
        re.compile(r"\{\s*(?:name|title|label)\s*:\s*(?:t\([\"']([^\"']+)[\"']\)|[\"']([^\"']+)[\"'])", re.MULTILINE),
    ]

    for pattern in step_patterns:
        for match in pattern.finditer(content):
            step_name = match.group(1) or (match.group(2) if match.lastindex >= 2 else None)
            if step_name and step_name not in steps:
                steps.append(step_name)

    if not steps:
        return f"No wizard steps detected in {path}. File may not be a wizard component or uses non-standard patterns."

    lines = [f"Wizard steps from {path} (branch: {branch}):", ""]
    for i, step in enumerate(steps, 1):
        lines.append(f"  Step {i}: {step}")

    return "\n".join(lines)

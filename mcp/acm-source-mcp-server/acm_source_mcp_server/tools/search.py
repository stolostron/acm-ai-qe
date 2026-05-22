"""Search tools: search_code, search_translations."""

import json
from acm_source_mcp_server.config import REPOS, get_branch_for_repo, state
from acm_source_mcp_server.github import search_github_code, list_tree, fetch_file


COMPONENT_DIRS = [
    "frontend/src/routes/",
    "frontend/src/ui-components/",
    "frontend/src/components/",
    "src/views/",
    "src/multicluster/",
]


async def search_code(query: str, repo: str = "acm", scope: str = "all") -> str:
    """Search source code via GitHub code search API.

    Args:
        query: Search query string.
        repo: Repository key (acm, kubevirt, acm-e2e, search-e2e, app-e2e, grc-e2e).
        scope: 'all' for GitHub code search, 'components' to filter to common component directories.
    """
    if repo not in REPOS:
        return f"Unknown repo '{repo}'. Valid: {list(REPOS.keys())}"

    info = REPOS[repo]
    owner, repo_name = info["owner"], info["repo"]
    branch = get_branch_for_repo(repo, state)

    if scope == "components":
        all_paths = []
        for dir_prefix in COMPONENT_DIRS:
            tree_paths = await list_tree(owner, repo_name, branch, path_filter=dir_prefix)
            all_paths.extend(tree_paths)

        query_lower = query.lower()
        matched = [p for p in all_paths if query_lower in p.lower()][:30]

        if not matched:
            return f"No files matching '{query}' in component directories on branch '{branch}'."

        lines = [f"Files matching '{query}' in {owner}/{repo_name} (branch: {branch}, scope: components):", ""]
        for p in matched:
            lines.append(f"  {p}")
        lines.append(f"\n({len(matched)} results)")
        return "\n".join(lines)

    paths = await search_github_code(query, owner, repo_name)
    if not paths:
        return f"No results for '{query}' in {owner}/{repo_name}."

    lines = [f"Search results for '{query}' in {owner}/{repo_name} (branch: {branch}):", ""]
    for p in paths[:30]:
        lines.append(f"  {p}")
    lines.append(f"\n({len(paths)} results, showing max 30)")
    return "\n".join(lines)


async def search_translations(query: str, exact: bool = False) -> str:
    """Search ACM Console translation strings (en.json localization file).

    Args:
        query: Text or key to search for in translations.
        exact: If True, match the exact string; if False, case-insensitive substring match.
    """
    info = REPOS["acm"]
    branch = get_branch_for_repo("acm", state)

    content = await fetch_file(info["owner"], info["repo"], "frontend/public/locales/en/translation.json", branch)
    if not content:
        content = await fetch_file(info["owner"], info["repo"], "frontend/src/lib/nls/en.json", branch)
    if not content:
        return "Could not find translation file on this branch."

    try:
        translations = json.loads(content)
    except json.JSONDecodeError:
        return "Failed to parse translation file."

    matches = []
    query_lower = query.lower()

    for key, value in translations.items():
        if not isinstance(value, str):
            continue
        if exact:
            if query == key or query == value:
                matches.append((key, value))
        else:
            if query_lower in key.lower() or query_lower in value.lower():
                matches.append((key, value))

    if not matches:
        return f"No translation matches for '{query}'."

    lines = [f"Translation matches for '{query}' (branch: {branch}):", ""]
    for key, value in matches[:30]:
        display_value = value[:80] + "..." if len(value) > 80 else value
        lines.append(f"  {key}: \"{display_value}\"")
    if len(matches) > 30:
        lines.append(f"\n... and {len(matches) - 30} more matches")
    lines.append(f"\n({len(matches)} total matches)")
    return "\n".join(lines)

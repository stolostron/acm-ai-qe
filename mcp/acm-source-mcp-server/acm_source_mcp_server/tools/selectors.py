"""Selector tools: get_acm_selectors, get_fleet_virt_selectors, get_patternfly_selectors, find_test_ids."""

import re
from acm_source_mcp_server.config import REPOS, get_branch_for_repo, state
from acm_source_mcp_server.github import fetch_file, list_tree, search_github_code


async def find_test_ids(component_path: str, repo: str = "acm") -> str:
    """Extract data-testid, id, aria-label, and data-test attributes from a source file.

    Args:
        component_path: File path within the repository.
        repo: Repository key.
    """
    if repo not in REPOS:
        return f"Unknown repo '{repo}'. Valid: {list(REPOS.keys())}"

    info = REPOS[repo]
    branch = get_branch_for_repo(repo, state)
    content = await fetch_file(info["owner"], info["repo"], component_path, branch)
    if content is None:
        return f"File not found: {component_path} (branch: {branch})"

    patterns = {
        "data-testid": re.compile(r'data-testid=["\'{]([^"\'}\s]+)', re.MULTILINE),
        "data-test": re.compile(r'data-test=["\'{]([^"\'}\s]+)', re.MULTILINE),
        "id": re.compile(r'\bid=["\'{]([^"\'}\s]+)', re.MULTILINE),
        "aria-label": re.compile(r'aria-label=["\'{]([^"\'}\s]+)', re.MULTILINE),
    }

    results: dict[str, list[str]] = {}
    for attr_name, pattern in patterns.items():
        matches = list(set(pattern.findall(content)))
        if matches:
            results[attr_name] = sorted(matches)

    if not results:
        return f"No test IDs or accessibility attributes found in {component_path}"

    lines = [f"Test attributes from {component_path} (branch: {branch}):", ""]
    for attr_name, values in results.items():
        lines.append(f"  {attr_name} ({len(values)}):")
        for v in values[:20]:
            lines.append(f"    {v}")
        if len(values) > 20:
            lines.append(f"    ... and {len(values) - 20} more")
        lines.append("")

    return "\n".join(lines)


async def get_acm_selectors(source: str = "both", component: str = "all") -> str:
    """Return selectors from QE repos (catalog) and/or ACM Console source code.

    Args:
        source: 'catalog' (QE repos only), 'source' (console source only), or 'both'.
        component: 'all', 'clc', 'search', 'app', 'grc'.
    """
    component_repo_map = {
        "clc": "acm-e2e",
        "search": "search-e2e",
        "app": "app-e2e",
        "grc": "grc-e2e",
    }

    selector_dirs = {
        "acm-e2e": ["cypress/views/", "tests/cypress/views/"],
        "search-e2e": ["cypress/views/", "tests/cypress/views/"],
        "app-e2e": ["cypress/views/", "tests/cypress/views/"],
        "grc-e2e": ["cypress/views/", "tests/cypress/views/"],
    }

    lines = []

    if source in ("catalog", "both"):
        repos_to_check = (
            [component_repo_map[component]] if component in component_repo_map
            else list(component_repo_map.values()) if component == "all"
            else []
        )

        for repo_key in repos_to_check:
            info = REPOS[repo_key]
            branch = get_branch_for_repo(repo_key, state)
            dirs = selector_dirs.get(repo_key, ["cypress/views/"])

            found_files = []
            for d in dirs:
                tree_paths = await list_tree(info["owner"], info["repo"], branch, path_filter=d)
                found_files.extend([p for p in tree_paths if p.endswith((".js", ".ts"))])

            if found_files:
                lines.append(f"\n=== {repo_key} ({info['owner']}/{info['repo']}) selector files ===")
                for f in found_files[:15]:
                    lines.append(f"  {f}")
                if len(found_files) > 15:
                    lines.append(f"  ... and {len(found_files) - 15} more files")

    if source in ("source", "both"):
        if component in ("all", "clc"):
            info = REPOS["acm"]
            branch = get_branch_for_repo("acm", state)
            paths = await search_github_code("data-testid", info["owner"], info["repo"])
            if paths:
                lines.append(f"\n=== ACM Console source files with data-testid (branch: {branch}) ===")
                for p in paths[:15]:
                    lines.append(f"  {p}")
                if len(paths) > 15:
                    lines.append(f"  ... and {len(paths) - 15} more files")

    if not lines:
        return f"No selector data found for component='{component}', source='{source}'."

    header = f"ACM Selectors (source={source}, component={component}):\n"
    return header + "\n".join(lines)


async def get_fleet_virt_selectors() -> str:
    """Return common Fleet Virtualization selectors from kubevirt-plugin cypress/views/ directory."""
    info = REPOS["kubevirt"]
    branch = get_branch_for_repo("kubevirt", state)

    view_dirs = ["cypress/views/", "cypress/support/views/", "tests/views/"]
    found_files = []

    for d in view_dirs:
        paths = await list_tree(info["owner"], info["repo"], branch, path_filter=d)
        found_files.extend([p for p in paths if p.endswith((".ts", ".js"))])

    if not found_files:
        return f"No selector view files found in {info['owner']}/{info['repo']} (branch: {branch})"

    lines = [f"Fleet Virt selector files from {info['owner']}/{info['repo']} (branch: {branch}):", ""]
    for f in found_files[:25]:
        lines.append(f"  {f}")
    if len(found_files) > 25:
        lines.append(f"  ... and {len(found_files) - 25} more files")

    lines.append("\nUse get_component_source(path, repo='kubevirt') to read specific view files.")
    return "\n".join(lines)


async def get_patternfly_selectors(component: str | None = None) -> str:
    """Return common PatternFly v6 CSS selectors used in test automation.

    Args:
        component: Optional PF component name to filter (e.g. 'modal', 'table', 'button').
    """
    catalog = {
        "button": [
            ".pf-v6-c-button",
            ".pf-v6-c-button.pf-m-primary",
            ".pf-v6-c-button.pf-m-secondary",
            ".pf-v6-c-button.pf-m-tertiary",
            ".pf-v6-c-button.pf-m-danger",
            ".pf-v6-c-button.pf-m-link",
            ".pf-v6-c-button.pf-m-plain",
            ".pf-v6-c-button.pf-m-disabled",
        ],
        "modal": [
            ".pf-v6-c-modal-box",
            ".pf-v6-c-modal-box__header",
            ".pf-v6-c-modal-box__title",
            ".pf-v6-c-modal-box__body",
            ".pf-v6-c-modal-box__footer",
            ".pf-v6-c-modal-box__close",
        ],
        "table": [
            ".pf-v6-c-table",
            ".pf-v6-c-table__thead",
            ".pf-v6-c-table__tbody",
            ".pf-v6-c-table__tr",
            ".pf-v6-c-table__th",
            ".pf-v6-c-table__td",
            ".pf-v6-c-table__sort-indicator",
            ".pf-v6-c-table__action",
        ],
        "dropdown": [
            ".pf-v6-c-menu-toggle",
            ".pf-v6-c-menu-toggle__text",
            ".pf-v6-c-menu",
            ".pf-v6-c-menu__list",
            ".pf-v6-c-menu__list-item",
            ".pf-v6-c-menu__item",
            ".pf-v6-c-menu__item-text",
        ],
        "select": [
            ".pf-v6-c-menu-toggle",
            ".pf-v6-c-select__toggle",
            ".pf-v6-c-menu",
            ".pf-v6-c-menu__list-item",
            '[role="option"]',
            '[role="listbox"]',
        ],
        "nav": [
            ".pf-v6-c-nav",
            ".pf-v6-c-nav__list",
            ".pf-v6-c-nav__item",
            ".pf-v6-c-nav__link",
            ".pf-v6-c-nav__link.pf-m-current",
        ],
        "page": [
            ".pf-v6-c-page",
            ".pf-v6-c-page__header",
            ".pf-v6-c-page__sidebar",
            ".pf-v6-c-page__main",
            ".pf-v6-c-page__main-section",
            ".pf-v6-c-page__main-breadcrumb",
        ],
        "alert": [
            ".pf-v6-c-alert",
            ".pf-v6-c-alert.pf-m-success",
            ".pf-v6-c-alert.pf-m-danger",
            ".pf-v6-c-alert.pf-m-warning",
            ".pf-v6-c-alert.pf-m-info",
            ".pf-v6-c-alert__title",
            ".pf-v6-c-alert__description",
        ],
        "form": [
            ".pf-v6-c-form",
            ".pf-v6-c-form__group",
            ".pf-v6-c-form__label",
            ".pf-v6-c-form__control",
            ".pf-v6-c-form__helper-text",
            ".pf-v6-c-form__actions",
        ],
        "input": [
            ".pf-v6-c-form-control",
            'input[type="text"]',
            'input[type="password"]',
            'input[type="search"]',
            ".pf-v6-c-text-input-group",
            ".pf-v6-c-text-input-group__text-input",
        ],
        "chip": [
            ".pf-v6-c-chip",
            ".pf-v6-c-chip__text",
            ".pf-v6-c-chip-group",
            ".pf-v6-c-chip-group__list",
            ".pf-v6-c-chip-group__list-item",
        ],
        "wizard": [
            ".pf-v6-c-wizard",
            ".pf-v6-c-wizard__header",
            ".pf-v6-c-wizard__nav",
            ".pf-v6-c-wizard__nav-item",
            ".pf-v6-c-wizard__nav-link",
            ".pf-v6-c-wizard__main-body",
            ".pf-v6-c-wizard__footer",
        ],
        "tabs": [
            ".pf-v6-c-tabs",
            ".pf-v6-c-tabs__list",
            ".pf-v6-c-tabs__item",
            ".pf-v6-c-tabs__link",
            ".pf-v6-c-tabs__item.pf-m-current",
        ],
        "toolbar": [
            ".pf-v6-c-toolbar",
            ".pf-v6-c-toolbar__content",
            ".pf-v6-c-toolbar__group",
            ".pf-v6-c-toolbar__item",
            ".pf-v6-c-toolbar__filter",
        ],
        "card": [
            ".pf-v6-c-card",
            ".pf-v6-c-card__header",
            ".pf-v6-c-card__title",
            ".pf-v6-c-card__body",
            ".pf-v6-c-card__footer",
        ],
        "empty_state": [
            ".pf-v6-c-empty-state",
            ".pf-v6-c-empty-state__icon",
            ".pf-v6-c-empty-state__title",
            ".pf-v6-c-empty-state__body",
            ".pf-v6-c-empty-state__actions",
        ],
        "label": [
            ".pf-v6-c-label",
            ".pf-v6-c-label__content",
            ".pf-v6-c-label.pf-m-blue",
            ".pf-v6-c-label.pf-m-green",
            ".pf-v6-c-label.pf-m-red",
            ".pf-v6-c-label-group",
        ],
        "popover": [
            ".pf-v6-c-popover",
            ".pf-v6-c-popover__content",
            ".pf-v6-c-popover__body",
            ".pf-v6-c-tooltip",
            ".pf-v6-c-tooltip__content",
        ],
        "switch": [
            ".pf-v6-c-switch",
            ".pf-v6-c-switch__input",
            ".pf-v6-c-switch__toggle",
            ".pf-v6-c-switch__label",
        ],
        "pagination": [
            ".pf-v6-c-pagination",
            ".pf-v6-c-pagination__nav",
            ".pf-v6-c-options-menu__toggle",
        ],
        "breadcrumb": [
            ".pf-v6-c-breadcrumb",
            ".pf-v6-c-breadcrumb__list",
            ".pf-v6-c-breadcrumb__item",
            ".pf-v6-c-breadcrumb__link",
        ],
    }

    if component:
        key = component.lower().replace("-", "_").replace(" ", "_")
        if key not in catalog:
            return f"Unknown PF component '{component}'. Available: {', '.join(sorted(catalog.keys()))}"
        lines = [f"PatternFly v6 selectors for '{component}':", ""]
        for sel in catalog[key]:
            lines.append(f"  {sel}")
        return "\n".join(lines)

    lines = ["PatternFly v6 CSS Selectors Catalog:", ""]
    for comp_name, selectors in sorted(catalog.items()):
        lines.append(f"  {comp_name}:")
        for sel in selectors:
            lines.append(f"    {sel}")
        lines.append("")

    return "\n".join(lines)

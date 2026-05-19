"""Entry point for acm-source-mcp-server."""

from fastmcp import FastMCP

from acm_source_mcp_server.tools.version import (
    list_repos,
    list_versions,
    set_acm_version,
    set_cnv_version,
    get_current_version,
)
from acm_source_mcp_server.tools.search import search_code, search_translations
from acm_source_mcp_server.tools.source import (
    get_component_source,
    get_component_types,
    get_routes,
    get_route_component,
    get_wizard_steps,
)
from acm_source_mcp_server.tools.selectors import (
    get_acm_selectors,
    get_fleet_virt_selectors,
    get_patternfly_selectors,
    find_test_ids,
)
from acm_source_mcp_server.tools.cluster import detect_cnv_version, get_cluster_virt_info

mcp = FastMCP(
    "acm-source-mcp-server",
    instructions="Source code discovery for ACM Console and Fleet Virtualization UI repos",
)

mcp.tool()(list_repos)
mcp.tool()(list_versions)
mcp.tool()(set_acm_version)
mcp.tool()(set_cnv_version)
mcp.tool()(get_current_version)
mcp.tool()(search_code)
mcp.tool()(search_translations)
mcp.tool()(get_component_source)
mcp.tool()(get_component_types)
mcp.tool()(get_routes)
mcp.tool()(get_route_component)
mcp.tool()(get_wizard_steps)
mcp.tool()(get_acm_selectors)
mcp.tool()(get_fleet_virt_selectors)
mcp.tool()(get_patternfly_selectors)
mcp.tool()(find_test_ids)
mcp.tool()(detect_cnv_version)
mcp.tool()(get_cluster_virt_info)


def main():
    mcp.run()


if __name__ == "__main__":
    main()

Run a knowledge-building session against the current cluster. Instead of
checking health, focus on discovering and documenting what's deployed.

For every component found on the cluster:
1. Check if it exists in the static knowledge (knowledge/component-registry.md)
2. If not, or if details differ, investigate it:
   - Collect detailed info from the cluster (oc describe, labels, owner refs)
   - Reverse-engineer dependencies from cluster metadata (owner refs, OLM
     labels, CSV metadata, env vars, webhooks, ConsolePlugins, APIServices)
   - Cross-reference with neo4j-rhacm MCP for broader dependency coverage
   - Search docs/rhacm-docs/ for documentation
   - Use acm-ui MCP to search source code
3. Write findings to knowledge/learned/

This is a proactive knowledge refresh -- use it after upgrading ACM or when
you want to ensure the knowledge base matches the current cluster state.

If a specific area to learn about is provided: $ARGUMENTS

# Fleet Virtualization Area Knowledge

## Overview

Fleet Virtualization in ACM Console provides centralized management of virtual machines across managed clusters running OpenShift Virtualization (CNV/KubeVirt).

## Key Features
- Tree view of VMs organized by cluster, namespace, and status
- VM lifecycle actions (start, stop, restart, pause, migrate)
- Saved searches for VM filtering
- Status aggregation across clusters
- VM creation via templates

## Key Components
- Tree View with toggle button for list/tree display
- VM Actions menu (kebab menu per VM row)
- Saved Searches sidebar
- Status cards with compliance/health indicators

## Navigation Routes
- Fleet Virtualization pages are part of the Infrastructure section
- Uses kubevirt-plugin for VM-specific components

## Testing Considerations
- Requires CNV installed on at least one spoke cluster
- Set both `set_acm_version()` AND `set_cnv_version()` in acm-ui MCP
- VM actions depend on VM state (running vs stopped)
- Tree view toggle persists across page navigations

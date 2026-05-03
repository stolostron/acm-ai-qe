# Flux Operator

Discovered: 2026-04-09
Source: Cluster diagnostic Stage 1.5

## Overview
- CSV: flux.v2.3.0
- Namespace: flux-system (primary), replicated across 108 namespaces via OLM
- Phase: Succeeded
- Owned CRDs: alerts.notification.toolkit.fluxcd.io, buckets.source.toolkit.fluxcd.io, gitrepositories.source.toolkit.fluxcd.io, helmcharts.source.toolkit.fluxcd.io, helmreleases.helm.toolkit.fluxcd.io, kustomizations.kustomize.toolkit.fluxcd.io
- Managed Deployments: helm-controller, image-automation-controller, image-reflector-controller, kustomize-controller, notification-controller, source-controller

## ACM Integration
None detected. No ConsolePlugin, no addon, no deployments in ACM namespaces.

## Dependencies
Likely installed as an AAP (Ansible Automation Platform) dependency. Present in the same set of 108 namespaces as the AAP operator.

## Classification Impact
No direct impact on ACM test failure classification. Flux health does not affect ACM features. Safe to ignore during ACM-focused cluster diagnostics.

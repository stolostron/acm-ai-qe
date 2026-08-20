---
type: architecture
subsystem: virtualization
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - architecture/virtualization/architecture.md
---

# Virtualization -- Dev Build CI Integration

## Purpose

Install CNV and MTV from dev catalogs (Brew IIB / Konflux FBC) instead of the GA addon path during CI pipeline runs. Used when testing against pre-release operator versions.

---

## Pipeline Parameters

| Parameter | Type | Description |
|---|---|---|
| `USE_DEV_BUILDS` | boolean | Enable dev CatalogSource installation (default: false) |
| `CNV_DEV_IIB` | string | Brew IIB build ID integer (e.g., `1181905`) |
| `MTV_DEV_CATALOG` | string | 40-char Konflux git SHA (e.g., `cda94ea88db7024c4681f3dc249fd40f823e7ff3`) |
| `MTV_OCP_VERSION` | string | OCP version suffix for FBC repo (default: `v422`) |

---

## Confirmed Working Values (as of Aug 2026)

| Parameter | Value | Version Installed | Platform |
|---|---|---|---|
| `CNV_DEV_IIB` | `1181905` | CNV 4.23.0 (v4.23.0.rhel9-24, Konflux build, smoke-tested) | OCP 4.22.4 + ACM 5.0.0 |
| `MTV_DEV_CATALOG` | `cda94ea88db7024c4681f3dc249fd40f823e7ff3` | MTV 2.12.3 (on-push stable, July 22 2026) | OCP 4.22.4 + ACM 5.0.0 |

---

## How to Find New Values

### CNV_DEV_IIB -- CNV Version Explorer API

```bash
curl -s 'https://cnv-version-explorer.apps.cnv2.engineering.redhat.com/GetSuccessfulBuildsByVersion?version=4.23.0&max_entries=5' | jq '.[0].iib'
```

Returns an integer. Only use IIBs where `smoke_test_status: "Passed"`.

Registry image: `brew.registry.redhat.io/rh-osbs/iib:<IIB_ID>`

### MTV_DEV_CATALOG -- Quay Tag Listing

```bash
curl -s 'https://quay.io/api/v1/repository/redhat-user-workloads/rh-mtv-1-tenant/forklift-fbc-prod-v422/tag/?limit=10' \
  | jq '[.tags[] | select(.name | startswith("on-push-")) | {name, last_modified}] | sort_by(.last_modified) | reverse | .[0]'
```

Tag format: `on-push-<40-char-commit-hash>`. Pass **only the hash** (without `on-push-` prefix).

Registry image: `quay.io/redhat-user-workloads/rh-mtv-1-tenant/forklift-fbc-prod-v<OCP_VERSION>:<hash>`

**Important:** The `vXXX` suffix must match target OCP version:
- OCP 4.21 → `forklift-fbc-prod-v421`
- OCP 4.22 → `forklift-fbc-prod-v422`
- OCP 4.23 → `forklift-fbc-prod-v423`

### Tag Stability

- `on-push-` tags = stable builds (preferred for CI)
- `on-pr-` tags = ephemeral, can be garbage-collected (avoid in pipelines)

---

## Pipeline Flow

1. `console_virt_tests` (top-level) passes `USE_DEV_BUILDS`, `CNV_DEV_IIB`, `MTV_DEV_CATALOG` downstream
2. `virt_cclm_tests` receives params, exports to `run_cclm_pipeline.sh`
3. `run_cclm_pipeline.sh` Phase 0.5 runs `setup_dev_builds.sh` on hub and spokes
4. `setup_dev_builds.sh` handles: GA operator detection/uninstall, MCH addon disablement, pull-secret patching, IDMS, CatalogSource/Subscription/CR creation, health verification
5. On failure: automatic fallback to GA addon path (re-enables MCH component)

---

## Script Location

`ci/scripts/setup/cclm/setup_dev_builds.sh` in `stolostron/acmqe-autotest`

---

## Pull Secret Requirements

- `brew.registry.redhat.io` -- auth copied from `registry.redhat.io` (automatic)
- `quay.io/openshift-virtualization` -- requires `KONFLUX_PULL_SECRET` env var with base64-encoded Quay auth (for MTV Konflux builds)

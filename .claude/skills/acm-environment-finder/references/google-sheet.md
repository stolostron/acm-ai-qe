# CI Environment Inventory Google Sheet

## Identity

| Field | Value |
|-------|-------|
| Spreadsheet ID | `1yg75xNpeO1i_K39D43FZmMauQe2d2OuJ1UjunX7jz3A` |
| Access | Optional: any Sheets API or host integration (e.g. `read_sheet_values` if your agent has Google Workspace tools). **No sheet access is required** — skip sheet and use `inventory.json` + Jenkins only. |
| Typical range | `A1:J200` (expand if sheet grows) |

## Header row (observed)

**Column drift:** Before mapping columns, confirm the header row still matches the table below (or the sheet’s current layout). Owners sometimes insert columns or rename headers. If headers do not match, **do not guess** — treat the sheet as unreliable for this session and continue with `inventory.json` + Jenkins only (see the main skill’s Mode 1).

Row 2 (1-based) is often the column header for data blocks:

| Col | Header |
|-----|--------|
| A | Provider |
| B | Cluster Name |
| C | OpenShift |
| D | ACM version |
| E | Status |
| F | kubeadmin password |
| G | OpenShift console |
| H | ACM console |
| I | API |
| J | Notes |

## Parsing rules

1. **Skip** rows where column B (Cluster Name) is empty and column A is not a known provider label.
2. **Section headers** appear as single cells (e.g. `ACM 2.9`, `E2E automation Clusters`) -- treat as context, not data rows.
3. **Status** (column E): prefer rows with `Running` for find-mode unless user asks otherwise.
4. **API URL** may appear in column G or H (console URLs) or I; derive API server from console URL when I is empty: replace `console-openshift-console.apps.` with `api.` and path suffix `6443` where applicable, or use embedded `https://api.` links in multi-line cells.
5. **ACM version** text is free-form (DOWNSTREAM tags, `latest-2.17`, multi-line MCE/ACM). Normalize by substring match against user request (e.g. `2.17`, `2.15.2`).
6. Sheet can be **stale** -- always validate with Jenkins + optional health check.

## User identity (when using Google tools)

If the host passes a `user_google_email` (or equivalent) into Sheet reads, use the authenticated Google account for your organization. This repository does not ship OAuth tokens.

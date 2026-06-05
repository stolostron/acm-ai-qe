# Depth Router

## Depth Selection Rules

| Trigger Phrases | Depth | Phases | Duration |
|----------------|-------|--------|----------|
| "is my hub alive", "quick check", "sanity", "pulse" | Quick | Phase 1 only | ~30s |
| "health check", "how's my hub", "check my cluster", "hub status" | Standard | Phases 1-4 | ~2-3 min |
| "deep check", "thorough", "full diagnostic", "deep audit", "comprehensive" | Deep | All 6 phases | ~5-10 min |
| "why are clusters Unknown", "investigate search", "what's wrong with governance" | Targeted | Full depth on specific area | ~3-5 min |

Default: **Standard** when intent is unclear.

## Phase Coverage by Depth

| Phase | Quick | Standard | Deep | Targeted |
|-------|-------|----------|------|----------|
| 1: Discover | Yes | Yes | Yes | Yes |
| 2: Learn | - | Yes | Yes | Yes (area-specific) |
| 3: Check | - | Yes | Yes | Yes (focused) |
| 4: Pattern Match | - | Yes | Yes | Yes |
| 5: Correlate | - | - | Yes | Yes |
| 6: Deep Investigate | - | - | Yes | Yes |

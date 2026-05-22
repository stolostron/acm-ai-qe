# Classification Decision Routing

## Quick Reference

| Evidence Pattern | Classification | Confidence |
|---|---|---|
| Selector not in official source + no recent product change | AUTOMATION_BUG | 0.90+ |
| Selector not in official source + intentional product rename | AUTOMATION_BUG | 0.95 |
| Selector not in official source + unintentional product removal | PRODUCT_BUG | 0.85 |
| Subsystem critical + test depends on that subsystem | INFRASTRUCTURE | 0.85-0.95 |
| Subsystem healthy + wrong data returned | PRODUCT_BUG | 0.85+ |
| After-all hook cascade | NO_BUG | 0.95+ |
| Feature intentionally disabled | NO_BUG | 0.90+ |
| Multiple independent root causes | MIXED | per-cause |
| Inconsistent reproduction | FLAKY | 0.70-0.80 |
| Insufficient evidence | UNKNOWN | < 0.70 |

## Routing Flow

```
Test Failure
    |
    v
PR-1: Blank page? ──yes──> Check console-api + auth
    |no
    v
PR-2: After-all hook? ──yes──> NO_BUG
    |no
    v
A4: Dead selector (3+)? ──yes──> AUTOMATION_BUG
    |no
    v
A4: Group by strict criteria
    |
    v
Phase B: 12-layer investigation
    |
    v
PR-6: Backend health? ──unhealthy──> INFRASTRUCTURE hypothesis
    |healthy
    v
D0: Route by evidence:
    Path A: selector mismatch ──> AUTOMATION_BUG
    Path B1: timeout + infra ──> INFRASTRUCTURE
    Path B2: complex ──> full analysis
    |
    v
D-V5: Counterfactual verification
    |
    v
D4b: Causal link check
    |
    v
D5: Counter-bias check
    |
    v
Final Classification
```

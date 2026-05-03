# Governance Data Flow

How policies move from creation on the hub to enforcement on spoke clusters.

---

## Policy Lifecycle

```
User creates Policy via console UI or oc apply
  -> Policy CR created in hub namespace
  -> grc-policy-propagator watches for new/changed policies
    -> evaluates PlacementBinding + PlacementRule
    -> determines target managed clusters
    -> creates replicated Policy in each target cluster's namespace
  -> governance-policy-framework addon on spoke
    -> detects replicated Policy
    -> instantiates policy template (ConfigurationPolicy, CertificatePolicy, etc.)
    -> controller evaluates compliance
  -> compliance status flows back to hub
    -> spoke addon updates Policy status
    -> propagator aggregates compliance across clusters
  -> console UI displays compliance status in policy table
```

## Compliance Reporting Flow

```
Spoke cluster
  config-policy-controller evaluates ConfigurationPolicy
    -> compares desired state vs actual state
    -> sets compliance status (Compliant / NonCompliant)
  governance-policy-framework reports status to hub
    -> updates replicated Policy status in cluster namespace

Hub cluster
  grc-policy-propagator
    -> reads compliance from all cluster namespaces
    -> aggregates into root Policy status
    -> status appears in console UI policy table
```

## Failure Points

| Point | What breaks | Symptom |
|-------|------------|---------|
| propagator down | Policies not distributed to spokes | New policies created but never enforced |
| propagator cert corrupted | Webhook fails TLS | Policy creation/modification returns 500 |
| spoke addon missing | No compliance reporting from that spoke | Policy shows "no status" for that cluster |
| ResourceQuota blocks propagator restart | Propagator stays down after crash | Policies stale, no new distribution |
| PlacementBinding wrong | Policy targets wrong clusters | Compliance reports don't match expectations |

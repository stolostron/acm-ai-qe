# JQL Query Patterns for ACM Project

## Syntax Notes
- String values must be quoted: `fixVersion = "ACM 2.17.0"`
- `~` is "contains" (fuzzy text search): `summary ~ "keyword"`
- `=` is exact match: `component = "Governance"`
- Multiple conditions: `AND`, `OR`, `NOT`
- Order results: `ORDER BY created DESC`

## Finding Related Tickets

### QE tracking ticket for a story
```
summary ~ "[QE] --- ACM-XXXXX"
```

### Sub-tasks of a ticket
```
parent = ACM-XXXXX
```

### Tickets in the same epic
```
project = ACM AND fixVersion = "ACM 2.17.0" AND component = "COMPONENT" AND summary ~ "keyword"
```

### Bugs filed against a feature
```
project = ACM AND summary ~ "keyword" AND type = Bug AND status != Closed
```

### QE tasks for a release
```
project = ACM AND labels = "QE" AND fixVersion = "ACM 2.17.0"
```

## Finding Tickets by Area

### Governance
```
project = ACM AND component = "Governance" AND fixVersion = "ACM 2.17.0"
```

### RBAC / Fleet Virt / CCLM / MTV
```
project = ACM AND component = "Virtualization" AND fixVersion = "ACM 2.17.0"
```

### Clusters / Credentials
```
project = ACM AND component = "Cluster Lifecycle" AND fixVersion = "ACM 2.17.0"
```

### Search
```
project = ACM AND component = "Search" AND fixVersion = "ACM 2.17.0"
```

### Applications
```
project = ACM AND component = "Application Lifecycle" AND fixVersion = "ACM 2.17.0"
```

## Advanced Patterns

### Recently updated bugs
```
project = ACM AND type = Bug AND updated >= -7d ORDER BY updated DESC
```

### Tickets with specific labels
```
project = ACM AND labels in ("QE", "dev-complete") AND fixVersion = "ACM 2.17.0"
```

### Tickets by assignee
```
project = ACM AND assignee = "username" AND status != Closed
```

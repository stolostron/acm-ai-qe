# Polarion Query Guide

## Lucene Query Syntax (NOT JQL)

Polarion uses Apache Lucene query syntax. This is different from JIRA's JQL.

### Field Queries
```
type:testcase                           -- by work item type
title:"governance labels"               -- by title (quoted for phrase match)
status:"proposed"                       -- by status
casecomponent:"console"                 -- by component
caseautomation:"notautomated"           -- by automation status
```

### Combining
```
type:testcase AND title:"RBAC"
type:testcase AND status:"proposed" AND caseautomation:"notautomated"
type:testcase AND title:"governance" AND NOT title:"deprecated"
```

### Wildcards
```
title:govern*                           -- prefix match
title:*labels*                          -- contains match
```

## Project ID

Always use `RHACM4K` for ACM test cases:
```
get_polarion_work_items(project_id="RHACM4K", query='...')
```

## Common Queries

### Find test cases for a feature
```
type:testcase AND title:"labels on policy details"
```

### Find test cases by area
```
type:testcase AND title:"governance"
type:testcase AND title:"RBAC"
type:testcase AND title:"fleet virt"
```

### Find approved test cases
```
type:testcase AND status:"proposed"
```

### Find unautomated test cases
```
type:testcase AND caseautomation:"notautomated" AND status:"proposed"
```

## Tool Usage Patterns

### Quick coverage check
```
get_polarion_work_items(project_id="RHACM4K", query='type:testcase AND title:"feature keyword"')
```

### Read full test case
```
get_polarion_work_item(project_id="RHACM4K", work_item_id="RHACM4K-63381", fields="@all")
```

### Compare with generated test case
```
get_polarion_test_case_summary(project_id="RHACM4K", work_item_id="RHACM4K-63381")
get_polarion_test_steps(project_id="RHACM4K", work_item_id="RHACM4K-63381")
```

# Ansible Automation Area Knowledge Base

Domain knowledge for writing Ansible Automation automation tests.

---

## Test Area

| Directory | Specs |
|-----------|-------|
| `cypress/tests/automation/` | 2 specs (automation actions, upgrade) |

---

## Key Files

| File | Purpose |
|------|---------|
| `cypress/views/automation/automation.js` | Automation page object |
| `cypress/views/actions/automation.js` | Automation state setup/teardown |
| `cypress/apis/automation.js` | Automation API wrappers |

---

## Navigation

- Path: `constants.automationPath` = `/multicloud/infrastructure/automations`

---

## API Resources

- Ansible Tower/AAP job templates: `constants.jobtemplate_api_path`
- Ansible Tower/AAP inventories: `constants.inventory_api_path`

---

## Tags

`@CLC`, `@e2e`

---

## Key Patterns

- Requires Ansible Automation Platform (AAP) credential configured
- Tests create/edit/delete automation templates linked to cluster lifecycle hooks
- Cluster lifecycle hooks: pre-install, post-install, pre-upgrade, post-upgrade, pre-destroy

# Jira Create Command

Create a new Jira issue interactively using `AskUserQuestion` to collect all required and optional fields.

## Instructions

Follow these steps in order. Use `AskUserQuestion` for each step. Do NOT skip steps or guess values.

### Step 1: Issue Type

Use `AskUserQuestion` to ask the user what type of issue to create:

- **Story** — User-facing functionality with acceptance criteria
- **Bug** — Defect report with reproduction steps
- **Task** — Internal technical work, non-user-facing
- **Spike** — Research, investigation, or proof-of-concept
- **Feature** — Significant customer-facing capability
- **Epic** — Large body of work spanning multiple sprints
- **Sub-task** — Child task under an existing issue

### Step 2: Delegate to Specialist Agent

Based on the issue type selected, launch the appropriate specialist agent to help craft the content. The agent should help formulate the summary, description, and any type-specific fields:

| Issue Type | Agent | Purpose |
|------------|-------|---------|
| Story | `story-specialist` | Craft user story format, acceptance criteria, definition of done |
| Bug | `bug-specialist` | Structure reproduction steps, expected vs actual behavior, severity |
| Task | `task-specialist` | Technical breakdown, implementation details |
| Spike | `spike-specialist` | Research questions, success criteria, time-box |
| Feature | `feature-specialist` | Feature strategy, user impact, rollout plan |
| Epic | `epic-specialist` | Epic scope, child story breakdown, cross-team coordination |
| Sub-task | `task-specialist` | Scoped sub-task breakdown |

The agent should return a proposed **summary** and **description**. Present them to the user for approval or editing via `AskUserQuestion`.

### Step 3: Collect Core Fields

Use `AskUserQuestion` to collect the remaining fields. Group questions logically (up to 4 questions per call). You may batch related fields together.

**Priority** (default: Normal):
- Blocker
- Critical
- Major
- Normal (Recommended)
- Minor
- Trivial

**Work Type** (submit as ID number):
- None = -1
- Associate Wellness & Development = 10604
- BU Features = 10605
- Future Sustainability = 10606
- Incidents & Support = 10607
- Quality / Stability / Reliability = 10608
- Security & Compliance = 10609
- Product / Portfolio Work = 10610

**Original Estimate** (e.g., '2h', '1d', '30m')

**Story Points** (default: 1) — MUST always be prompted for via `AskUserQuestion`. If the user does not provide a value, use 1.

### Step 4: Collect Categorization Fields

Use `AskUserQuestion` to collect:

**Component** — Present the top relevant components from the ACM project. Suggest based on keywords in the summary/description. Common components include:
- Search
- Console
- GRC
- Cluster Lifecycle
- Observability
- HyperShift
- Installer
- Server Foundation
- Application Lifecycle
- Infrastructure Operator
- DevOps
- Global Hub
- Multicluster Networking
- Business Continuity
- Container Native Virtualization
- Edge
- Documentation

**Labels** — Ask if they want to add any labels (free text, comma-separated).

**Target Version** — Ask for the target version (e.g., "ACM 2.16.0").

### Step 5: Parent / Linking

Use `AskUserQuestion` to ask if there is a parent or related issue.

- If **Sub-task**: Ask for the parent issue key (required). Set the `parent` field on `create_issue`.
- If **any other type** and a parent is provided: Create the issue first, then use `link_issue` to link it to the parent with an appropriate link type (e.g., "Blocks", "Depend", "Related", "Incorporates"). Ask the user which link type to use.
- If **Epic**: Ask for an `epic_name` (required for Epics).

### Step 6: Confirm and Create

Before calling `create_issue`, display a summary of ALL fields to the user and ask for confirmation.

Always set:
- `project_key`: "ACM"
- `security_level`: "Red Hat Employee"
- `assignee`: "jpacker@redhat.com"

Call `create_issue` with all collected fields.

After creation, if linking is needed (non-sub-task with a parent), call `link_issue`.

### Step 7: Post-Creation

After successful creation:
1. Display the created issue key and link
2. If this is an Epic, ask if the user wants to create child stories/tasks now
3. If this is a Feature, ask if the user wants to create related epics or stories

## Error Handling

- Validate date formats (YYYY-MM-DD)
- Validate time estimates use Jira format (e.g., '1h 30m', '2d')
- If `create_issue` fails, show the error and ask the user what to fix
- Never retry creation without user confirmation

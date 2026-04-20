# Learned Patterns

This directory stores patterns learned from successful test case generation runs. The test-case-generator agent writes here after producing validated test cases.

No patterns have been written yet. Files will accumulate as runs complete successfully.

## Planned Contents

Files are added over time as the agent discovers new patterns:

- Component field orders (description list column sequences)
- System label filtering rules by context
- Common edge cases by area
- Translation key mappings

## Rules

- Only the test-case-generator agent writes to this directory
- Files are JSON format: `<area>-patterns.json`
- Each file has a `last_updated` timestamp
- Patterns are additive -- never delete existing entries, only add or update

# Learned Patterns

This directory contains patterns learned from successful test case generation runs. Files here are written by the agent after producing validated test cases.

## Contents

Files are added over time as the agent discovers new patterns:

- Component field orders (description list column sequences)
- System label filtering rules by context
- Common edge cases by area
- Translation key mappings

## Rules

- Only the test-case-generator agent writes to this directory
- Files are JSON format for easy parsing
- Each file has a `last_updated` timestamp
- Patterns are additive -- never delete existing entries, only add or update

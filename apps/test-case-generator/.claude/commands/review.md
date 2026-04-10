# /review -- Review an existing test case

Usage: `/review <PATH_TO_TEST_CASE> [--version <VERSION>] [--area <AREA>]`

## Arguments

- `PATH_TO_TEST_CASE` (required): Path to the test case markdown file
- `--version`: ACM version (default: extracted from test case Release field)
- `--area`: Console area (default: extracted from test case title tag)

## Process

1. Read the test case file
2. Launch the quality-reviewer agent with the file path, version, and area
3. Display the review results (blocking issues, warnings, suggestions, verdict)
4. If NEEDS_FIXES: offer to fix the identified issues

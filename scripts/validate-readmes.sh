#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

echo "=== Validate skills/README.md ==="

if [ ! -f skills/README.md ]; then
  echo "FAIL: skills/README.md does not exist"
  exit 1
fi

while IFS= read -r skill_md; do
  dir=$(dirname "$skill_md")
  skill_name=$(basename "$dir")

  if ! grep -q "$skill_name" skills/README.md; then
    echo "FAIL: $skill_name not listed in skills/README.md"
    ERRORS=$((ERRORS + 1))
  fi

done < <(find skills/ -name 'SKILL.md' -type f 2>/dev/null)

echo "=== Validate commands/README.md ==="

if [ -f commands/README.md ]; then
  while IFS= read -r cmd_md; do
    cmd_name=$(basename "$cmd_md" .md)
    if [ "$cmd_name" = "README" ]; then continue; fi

    if ! grep -q "$cmd_name" commands/README.md; then
      echo "FAIL: $cmd_name not listed in commands/README.md"
      ERRORS=$((ERRORS + 1))
    fi
  done < <(find commands/ -name '*.md' -type f 2>/dev/null)
fi

if [ "$ERRORS" -gt 0 ]; then
  echo "FAILED: $ERRORS error(s)"
  exit 1
fi

echo "PASSED"

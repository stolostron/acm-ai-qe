#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

echo "=== Skill Frontmatter Lint ==="

while IFS= read -r skill_md; do
  dir=$(dirname "$skill_md")
  skill_name=$(basename "$dir")

  # Check name: field
  if ! head -20 "$skill_md" | grep -q '^name:'; then
    echo "FAIL: $skill_md — missing 'name:' in frontmatter"
    ERRORS=$((ERRORS + 1))
  fi

  # Check description: field
  if ! head -20 "$skill_md" | grep -q '^description:'; then
    echo "FAIL: $skill_md — missing 'description:' in frontmatter"
    ERRORS=$((ERRORS + 1))
  fi

  # Check for hardcoded credentials
  if grep -qiE '(password|token|secret|api[_-]?key)\s*[:=]\s*["\x27][^"\x27]+["\x27]' "$skill_md" 2>/dev/null; then
    echo "FAIL: $skill_md — possible hardcoded credential"
    ERRORS=$((ERRORS + 1))
  fi

done < <(find skills/ -name 'SKILL.md' -type f 2>/dev/null)

SKILL_COUNT=$(find skills/ -name 'SKILL.md' -type f 2>/dev/null | wc -l | tr -d ' ')
echo "Checked $SKILL_COUNT skills"

if [ "$ERRORS" -gt 0 ]; then
  echo "FAILED: $ERRORS error(s)"
  exit 1
fi

echo "PASSED"

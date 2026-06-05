#!/usr/bin/env bash
set -euo pipefail

ERRORS=0
CHECKED=0

echo "=== Skill Path Integrity Test ==="

for skill_md in $(find skills/ -name 'SKILL.md' -type f 2>/dev/null); do
  dir=$(dirname "$skill_md")

  # Check knowledge path references: ../../../.claude/knowledge/
  for ref in $(grep -oE '\.\./\.\./\.\./\.claude/knowledge/[A-Za-z0-9_./-]+' "$skill_md" 2>/dev/null || true); do
    resolved="$dir/$ref"
    resolved=$(echo "$resolved" | sed 's/[)>`].*$//')
    if [ ! -e "$resolved" ] && [ ! -d "$resolved" ]; then
      echo "BROKEN: $skill_md -> $ref"
      ERRORS=$((ERRORS + 1))
    fi
    CHECKED=$((CHECKED + 1))
  done

  # Check sibling skill references: ../acm-*/SKILL.md
  for ref in $(grep -oE '\.\./acm-[A-Za-z0-9_-]+/SKILL\.md' "$skill_md" 2>/dev/null || true); do
    resolved="$dir/$ref"
    if [ ! -f "$resolved" ]; then
      echo "BROKEN: $skill_md -> $ref"
      ERRORS=$((ERRORS + 1))
    fi
    CHECKED=$((CHECKED + 1))
  done

  # Check cross-category skill references: ../../<category>/acm-*/SKILL.md
  for ref in $(grep -oE '\.\./\.\./[A-Za-z0-9_-]+/acm-[A-Za-z0-9_-]+/SKILL\.md' "$skill_md" 2>/dev/null || true); do
    resolved="$dir/$ref"
    if [ ! -f "$resolved" ]; then
      echo "BROKEN: $skill_md -> $ref"
      ERRORS=$((ERRORS + 1))
    fi
    CHECKED=$((CHECKED + 1))
  done
done

# Also check reference files
for ref_md in $(find skills/ -path '*/references/*.md' -type f 2>/dev/null); do
  dir=$(dirname "$ref_md")

  # Check knowledge path references in reference files (one extra ../ level)
  for ref in $(grep -oE '\.\./\.\./\.\./\.\./\.claude/knowledge/[A-Za-z0-9_./-]+' "$ref_md" 2>/dev/null || true); do
    resolved="$dir/$ref"
    resolved=$(echo "$resolved" | sed 's/[)>`].*$//')
    if [ ! -e "$resolved" ] && [ ! -d "$resolved" ]; then
      echo "BROKEN: $ref_md -> $ref"
      ERRORS=$((ERRORS + 1))
    fi
    CHECKED=$((CHECKED + 1))
  done
done

echo "Checked $CHECKED path references"

if [ "$ERRORS" -gt 0 ]; then
  echo "FAILED: $ERRORS broken path(s)"
  exit 1
fi

echo "PASSED"

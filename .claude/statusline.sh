#!/bin/bash
# Status line for Claude Code — shows model, branch, context %, cost, duration
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name // "unknown"')
BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
PCT=${PCT:-0}
COST=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
DURATION_MS=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')

# Color coding: green <70%, yellow 70-89%, red 90%+
RESET='\033[0m'
if [ "$PCT" -ge 90 ]; then COLOR='\033[31m'
elif [ "$PCT" -ge 70 ]; then COLOR='\033[33m'
else COLOR='\033[32m'; fi

MINS=$((DURATION_MS / 60000))
SECS=$(((DURATION_MS % 60000) / 1000))
COST_FMT=$(printf '$%.2f' "$COST")

echo -e "[$MODEL] $BRANCH | ${COLOR}ctx ${PCT}%${RESET} | ${COST_FMT} | ${MINS}m${SECS}s"

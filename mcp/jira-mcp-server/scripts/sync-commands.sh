#!/bin/bash

# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file was developed with AI assistance.

# Script to synchronize command files between .cursor, .claude, and .gemini directories
# Usage: ./sync-commands.sh

set -e

# Define directory paths
CURSOR_DIR="./.cursor/commands"
CLAUDE_DIR="./.claude/commands"
GEMINI_DIR="./.gemini/commands"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[SYNC]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Create directories if they don't exist
create_directories() {
    log "Creating directories if they don't exist..."
    mkdir -p "$CURSOR_DIR" "$CLAUDE_DIR" "$GEMINI_DIR"
}

# Check if git is available and we're in a git repo
check_git() {
    if ! command -v git &> /dev/null; then
        error "Git is not available. Please install git."
        exit 1
    fi

    if ! git rev-parse --git-dir &> /dev/null; then
        error "Not in a git repository."
        exit 1
    fi
}

# Get list of changed files using git
get_changed_files() {
    local status_output
    status_output=$(git status --porcelain 2>/dev/null || echo "")

    # Get modified and new files
    echo "$status_output" | grep -E "^[AM?].*\.(cursor|claude|gemini)/commands/.*\.(md|toml)$" | awk '{print $2}' || true
}

# Extract content from markdown file (excluding potential headers)
extract_md_content() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        return 1
    fi

    # For now, we'll take the entire content
    # In the future, we could add logic to skip specific headers
    cat "$file"
}

# Extract content from TOML file (excluding headers)
extract_toml_content() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        return 1
    fi

    # Skip TOML headers and extract description/content
    # This is a simplified approach - you may need to adjust based on actual Gemini TOML format
    grep -v "^#" "$file" 2>/dev/null || cat "$file"
}

# Convert markdown content to TOML format
md_to_toml() {
    local md_content="$1"
    local command_name="$2"

    # Basic TOML structure for Gemini commands
    # You may need to adjust this format based on actual Gemini requirements
    cat << EOF
# Gemini command configuration
[command]
name = "$command_name"
description = """
$md_content
"""
EOF
}

# Convert TOML content to markdown format
toml_to_md() {
    local toml_content="$1"

    # Extract description from TOML and convert to markdown
    # This is a simplified approach - you may need more sophisticated parsing
    echo "$toml_content" | grep -A 1000 'description = """' | sed '1d' | sed '/"""$/,$d'
}

# Add Claude-specific headers if needed
add_claude_headers() {
    local content="$1"
    local command_name="$2"

    # For now, Claude uses the same format as Cursor
    # You can add Claude-specific headers here if needed
    echo "$content"
}

# Add Gemini-specific headers
add_gemini_headers() {
    local content="$1"
    local command_name="$2"

    # Add Gemini TOML headers
    cat << EOF
# Auto-generated from command synchronization
# Last updated: $(date)

$content
EOF
}

# Sync a single command across all platforms
sync_command() {
    local source_file="$1"
    local command_name

    # Extract command name from file path
    command_name=$(basename "$source_file" | sed 's/\.[^.]*$//')

    log "Syncing command: $command_name"

    # Determine source format and extract content
    local content
    if [[ "$source_file" == *.md ]]; then
        content=$(extract_md_content "$source_file")
    elif [[ "$source_file" == *.toml ]]; then
        content=$(toml_to_md "$(extract_toml_content "$source_file")")
    else
        warn "Unknown file format for $source_file"
        return 1
    fi

    # Sync to Cursor (markdown)
    local cursor_file="$CURSOR_DIR/${command_name}.md"
    if [[ "$source_file" != *".cursor"* ]]; then
        log "  → Updating Cursor: $cursor_file"
        echo "$content" > "$cursor_file"
    fi

    # Sync to Claude (markdown with potential headers)
    local claude_file="$CLAUDE_DIR/${command_name}.md"
    if [[ "$source_file" != *".claude"* ]]; then
        log "  → Updating Claude: $claude_file"
        add_claude_headers "$content" "$command_name" > "$claude_file"
    fi

    # Sync to Gemini (TOML)
    local gemini_file="$GEMINI_DIR/${command_name}.toml"
    if [[ "$source_file" != *".gemini"* ]]; then
        log "  → Updating Gemini: $gemini_file"
        add_gemini_headers "$(md_to_toml "$content" "$command_name")" "$command_name" > "$gemini_file"
    fi
}

# Get all command files from all directories
get_all_command_files() {
    find "$CURSOR_DIR" "$CLAUDE_DIR" "$GEMINI_DIR" -name "*.md" -o -name "*.toml" 2>/dev/null | sort -u
}

# Main synchronization logic
main() {
    log "Starting command synchronization..."

    check_git
    create_directories

    # Get changed files from git
    local changed_files
    changed_files=$(get_changed_files)

    if [[ -z "$changed_files" ]]; then
        log "No changed command files detected. Checking for missing files..."

        # Check if any command exists in one location but not others
        local all_commands=()
        local need_sync=false

        # Collect all unique command names
        for dir in "$CURSOR_DIR" "$CLAUDE_DIR" "$GEMINI_DIR"; do
            if [[ -d "$dir" ]]; then
                while IFS= read -r -d '' file; do
                    local cmd_name
                    cmd_name=$(basename "$file" | sed 's/\.[^.]*$//')
                    all_commands+=("$cmd_name")
                done < <(find "$dir" -name "*.md" -o -name "*.toml" -print0 2>/dev/null)
            fi
        done

        # Remove duplicates
        local unique_commands
        IFS=$'\n' unique_commands=($(printf '%s\n' "${all_commands[@]}" | sort -u))

        # Check if all commands exist in all locations
        for cmd in "${unique_commands[@]}"; do
            local cursor_exists=false
            local claude_exists=false
            local gemini_exists=false

            [[ -f "$CURSOR_DIR/${cmd}.md" ]] && cursor_exists=true
            [[ -f "$CLAUDE_DIR/${cmd}.md" ]] && claude_exists=true
            [[ -f "$GEMINI_DIR/${cmd}.toml" ]] && gemini_exists=true

            if ! ($cursor_exists && $claude_exists && $gemini_exists); then
                need_sync=true
                log "Command '$cmd' is missing in some locations"

                # Find source file for syncing
                local source_file=""
                if $cursor_exists; then
                    source_file="$CURSOR_DIR/${cmd}.md"
                elif $claude_exists; then
                    source_file="$CLAUDE_DIR/${cmd}.md"
                elif $gemini_exists; then
                    source_file="$GEMINI_DIR/${cmd}.toml"
                fi

                if [[ -n "$source_file" ]]; then
                    sync_command "$source_file"
                fi
            fi
        done

        if ! $need_sync; then
            success "All command files are already synchronized."
        fi
    else
        log "Found changed files:"
        echo "$changed_files" | while read -r file; do
            log "  - $file"
        done

        # Sync each changed file
        echo "$changed_files" | while read -r file; do
            if [[ -f "$file" ]]; then
                sync_command "$file"
            fi
        done
    fi

    success "Command synchronization completed!"
}

# Help function
show_help() {
    cat << EOF
Command File Synchronization Script

This script synchronizes command files between .cursor, .claude, and .gemini directories.

Usage:
  $0 [options]

Options:
  -h, --help    Show this help message
  --dry-run     Show what would be synchronized without making changes
  --force       Force synchronization of all files regardless of git status

The script:
1. Uses git to detect changed command files
2. Preserves platform-specific headers for Claude and Gemini
3. Converts between markdown (.md) and TOML (.toml) formats as needed
4. Ensures all three platforms have synchronized command definitions

File formats:
- Cursor: .cursor/commands/*.md (markdown)
- Claude: .claude/commands/*.md (markdown with potential headers)
- Gemini: .gemini/commands/*.toml (TOML configuration)
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --dry-run)
            warn "Dry run mode not implemented yet"
            exit 0
            ;;
        --force)
            warn "Force mode not implemented yet"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main
#!/bin/bash
# review-prompts.sh — Display all prompts in the centralized database
#
# Usage:
#   ./review-prompts.sh           # Summary of all prompts
#   ./review-prompts.sh agent     # Show specific agent prompt
#   ./review-prompts.sh --full    # Full content of all prompts
#   ./review-prompts.sh --diff    # Show git changes since last commit

set -euo pipefail

PROMPTS_DIR="$HOME/clawd/prompts"
REGISTRY="$PROMPTS_DIR/registry.yaml"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

header() { echo -e "\n${BOLD}${BLUE}═══ $1 ═══${NC}"; }
subheader() { echo -e "${CYAN}--- $1 ---${NC}"; }

if [ "${1:-}" = "--diff" ]; then
    header "Prompt Changes (git diff)"
    cd "$PROMPTS_DIR"
    git diff --stat 2>/dev/null || echo "Not in a git repo or no changes"
    git diff --name-only 2>/dev/null
    exit 0
fi

if [ "${1:-}" = "--full" ]; then
    header "Full Prompt Contents"
    for f in "$PROMPTS_DIR/agents/"*.md; do
        agent=$(basename "$f" .md)
        subheader "Agent: $agent"
        cat "$f"
        echo ""
    done
    for f in "$PROMPTS_DIR/tasks/"*/*.md; do
        task=$(echo "$f" | sed "s|$PROMPTS_DIR/tasks/||")
        subheader "Task: $task"
        cat "$f"
        echo ""
    done
    exit 0
fi

if [ $# -gt 0 ] && [ "$1" != "--full" ] && [ "$1" != "--diff" ]; then
    # Show specific agent/task prompt
    target="$1"
    if [ -f "$PROMPTS_DIR/agents/${target}.md" ]; then
        header "Agent Prompt: $target"
        cat "$PROMPTS_DIR/agents/${target}.md"
    elif [ -f "$PROMPTS_DIR/tasks/${target}.md" ]; then
        header "Task Prompt: $target"
        cat "$PROMPTS_DIR/tasks/${target}.md"
    else
        echo "Prompt not found: $target"
        echo "Available agents: $(ls "$PROMPTS_DIR/agents/" | sed 's/.md//' | tr '\n' ' ')"
    fi
    exit 0
fi

# Default: summary view
header "Prompt Database Summary"
echo -e "${GREEN}Location:${NC} $PROMPTS_DIR"
echo -e "${GREEN}Registry:${NC} $REGISTRY"
echo ""

# Count files
agent_count=$(ls "$PROMPTS_DIR/agents/"*.md 2>/dev/null | wc -l | tr -d ' ')
task_count=$(find "$PROMPTS_DIR/tasks" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
component_count=$(find "$PROMPTS_DIR/components" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

echo -e "${BOLD}Totals:${NC} $agent_count agents | $task_count tasks | $component_count components"
echo ""

subheader "Agent Prompts"
printf "%-15s %-10s %-8s %s\n" "AGENT" "LINES" "SIZE" "FIRST LINE"
printf "%-15s %-10s %-8s %s\n" "───────" "─────" "────" "──────────"
for f in "$PROMPTS_DIR/agents/"*.md; do
    agent=$(basename "$f" .md)
    lines=$(wc -l < "$f" | tr -d ' ')
    size=$(wc -c < "$f" | tr -d ' ')
    first=$(head -1 "$f" | sed 's/^# //')
    printf "%-15s %-10s %-8s %s\n" "$agent" "${lines}L" "${size}B" "$first"
done

echo ""
subheader "Task Prompts"
printf "%-35s %-10s %-8s\n" "TASK" "LINES" "SIZE"
printf "%-35s %-10s %-8s\n" "───────────────────" "─────" "────"
find "$PROMPTS_DIR/tasks" -name "*.md" | sort | while read f; do
    task=$(echo "$f" | sed "s|$PROMPTS_DIR/tasks/||")
    lines=$(wc -l < "$f" | tr -d ' ')
    size=$(wc -c < "$f" | tr -d ' ')
    printf "%-35s %-10s %-8s\n" "$task" "${lines}L" "${size}B"
done

echo ""
subheader "Reusable Components"
printf "%-45s %-10s %-8s\n" "COMPONENT" "LINES" "SIZE"
printf "%-45s %-10s %-8s\n" "──────────────────────────" "─────" "────"
find "$PROMPTS_DIR/components" -name "*.md" | sort | while read f; do
    comp=$(echo "$f" | sed "s|$PROMPTS_DIR/components/||")
    lines=$(wc -l < "$f" | tr -d ' ')
    size=$(wc -c < "$f" | tr -d ' ')
    printf "%-45s %-10s %-8s\n" "$comp" "${lines}L" "${size}B"
done

echo ""
echo -e "${GREEN}Commands:${NC}"
echo "  review-prompts.sh <agent>  — View specific prompt"
echo "  review-prompts.sh --full   — View all prompts"
echo "  review-prompts.sh --diff   — View git changes"
echo "  assemble-prompts.sh        — Deploy prompts to agents"

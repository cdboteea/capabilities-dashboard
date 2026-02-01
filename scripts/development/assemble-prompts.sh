#!/bin/bash
# assemble-prompts.sh — Assembles agent AGENTS.md files from the centralized prompt database
# Usage: ./assemble-prompts.sh [agent_name]
# If no agent specified, assembles all agents.

set -euo pipefail

PROMPTS_DIR="$HOME/clawd/prompts"
AGENTS_BASE="$HOME/.clawdbot/agents"
REGISTRY="$PROMPTS_DIR/registry.yaml"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[assemble]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
err() { echo -e "${RED}[error]${NC} $1"; }

assemble_agent() {
    local agent_id="$1"
    local prompt_file="$PROMPTS_DIR/agents/${agent_id}.md"
    local target_dir="$AGENTS_BASE/${agent_id}/agent"
    local target_file="$target_dir/AGENTS.md"
    
    if [ ! -f "$prompt_file" ]; then
        warn "No prompt file for agent '$agent_id' at $prompt_file — skipping"
        return 0
    fi
    
    # Ensure target directory exists
    mkdir -p "$target_dir"
    
    # Build the assembled prompt
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    cat > "$target_file" << HEADER
<!-- ═══════════════════════════════════════════════════════════ -->
<!-- AUTO-GENERATED from prompt database. Do not edit directly. -->
<!-- Source: prompts/agents/${agent_id}.md                      -->
<!-- Assembled: ${timestamp}                                    -->
<!-- Edit the source file and run: scripts/assemble-prompts.sh  -->
<!-- ═══════════════════════════════════════════════════════════ -->

HEADER
    
    # Append the main prompt
    cat "$prompt_file" >> "$target_file"
    
    # Check for and append relevant component files based on agent
    local components_appended=0
    
    # Research agents get tool guides and quality standards
    if [[ "$agent_id" == "research" || "$agent_id" == "synthesizer" ]]; then
        if [ -f "$PROMPTS_DIR/components/quality/source-evaluation.md" ]; then
            echo "" >> "$target_file"
            echo "---" >> "$target_file"
            echo "" >> "$target_file"
            cat "$PROMPTS_DIR/components/quality/source-evaluation.md" >> "$target_file"
            components_appended=$((components_appended + 1))
        fi
    fi
    
    if [[ "$agent_id" == "research" ]]; then
        # Research-specific output format
        if [ -f "$PROMPTS_DIR/components/output-formats/research-report.md" ]; then
            echo "" >> "$target_file"
            echo "---" >> "$target_file"
            echo "" >> "$target_file"
            cat "$PROMPTS_DIR/components/output-formats/research-report.md" >> "$target_file"
            components_appended=$((components_appended + 1))
        fi
    fi
    
    log "Assembled ${agent_id} → ${target_file} (+${components_appended} components)"
}

# Main
if [ $# -gt 0 ]; then
    # Assemble specific agent
    assemble_agent "$1"
else
    # Assemble all agents that have prompt files
    log "Assembling all agent prompts from $PROMPTS_DIR/agents/"
    for prompt_file in "$PROMPTS_DIR/agents/"*.md; do
        agent_id=$(basename "$prompt_file" .md)
        assemble_agent "$agent_id"
    done
    log "Done! All prompts assembled."
fi

echo ""
log "Tip: Review assembled prompts with: cat ~/.clawdbot/agents/<agent>/agent/AGENTS.md"

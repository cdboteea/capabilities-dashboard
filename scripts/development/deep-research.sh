#!/bin/bash
# deep-research.sh — Orchestrates multi-agent deep research
# 
# Usage: 
#   ./deep-research.sh "research topic" [depth]
#   depth: 1=quick, 2=standard, 3=deep, 4=comprehensive (default: 2)
#
# Architecture:
#   1. Planner agent decomposes topic into sub-questions
#   2. Parallel searcher agents investigate each sub-question
#   3. Evaluator assesses findings and identifies gaps
#   4. (Optional) Gap-filling iteration
#   5. Synthesizer produces final report
#
# Output: ~/clawd/research-outputs/YYYY-MM-DD-topic-slug/report.md

set -euo pipefail

# ═══════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════
CLAWD_DIR="$HOME/clawd"
PROMPTS_DIR="$CLAWD_DIR/prompts"
OUTPUT_BASE="$CLAWD_DIR/research-outputs"
MAX_PARALLEL=6  # Max concurrent searcher agents
POLL_INTERVAL=10  # Seconds between status checks
PLANNER_TIMEOUT=120  # 2 min for planning
SEARCHER_TIMEOUT=180  # 3 min per searcher
EVALUATOR_TIMEOUT=120
SYNTHESIZER_TIMEOUT=300  # 5 min for synthesis

# Models by role
PLANNER_MODEL=""  # Empty = use agent default (Sonnet)
SEARCHER_MODEL=""
EVALUATOR_MODEL=""
SYNTHESIZER_MODEL=""

# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[research]${NC} $1"; }
info() { echo -e "${BLUE}[info]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
err() { echo -e "${RED}[error]${NC} $1" >&2; }

slugify() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//' | cut -c1-50
}

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# ═══════════════════════════════════════════
# Parse arguments
# ═══════════════════════════════════════════
if [ $# -lt 1 ]; then
    echo "Usage: $0 \"research topic\" [depth 1-4]"
    echo "  depth 1: Quick Scan (2-3 questions, ~2 min)"
    echo "  depth 2: Standard (3-5 questions, ~5 min) [default]"
    echo "  depth 3: Deep Dive (5-7 questions, ~15 min)"
    echo "  depth 4: Comprehensive (7-10 questions, ~30 min)"
    exit 1
fi

TOPIC="$1"
DEPTH="${2:-2}"
SLUG=$(slugify "$TOPIC")
DATE=$(date +"%Y-%m-%d")
OUTPUT_DIR="$OUTPUT_BASE/${DATE}-${SLUG}"
START_TIME=$(date +%s)

mkdir -p "$OUTPUT_DIR"

log "═══════════════════════════════════════════"
log "Deep Research: $TOPIC"
log "Depth: $DEPTH | Output: $OUTPUT_DIR"
log "Started: $(date)"
log "═══════════════════════════════════════════"

# ═══════════════════════════════════════════
# Phase 1: Planning
# ═══════════════════════════════════════════
log ""
log "📋 Phase 1: Planning — decomposing topic into sub-questions..."

PLANNER_PROMPT=$(cat "$PROMPTS_DIR/tasks/deep-research/planner.md")

# Write the planning task
cat > "$OUTPUT_DIR/planner-task.txt" << TASK
$PLANNER_PROMPT

---

## Your Assignment

**Topic:** $TOPIC
**Depth Level:** $DEPTH

Please analyze this topic and produce a research plan. Save the plan as YAML to: $OUTPUT_DIR/plan.yaml

Remember:
- Depth $DEPTH means $([ "$DEPTH" = "1" ] && echo "2-3" || [ "$DEPTH" = "2" ] && echo "3-5" || [ "$DEPTH" = "3" ] && echo "5-7" || echo "7-10") sub-questions
- Sub-questions should be independent and searchable
- Include at least one about criticisms/limitations
- Include at least one about recent developments
TASK

# Note: In production, this would use clawdbot's sessions_spawn API
# For now, we output the task file for the main agent to orchestrate
log "Planner task written to: $OUTPUT_DIR/planner-task.txt"

# ═══════════════════════════════════════════
# Phase 2: Search (parallel)
# ═══════════════════════════════════════════
# This phase is orchestrated by the main agent using sessions_spawn
# The script prepares the searcher task templates

SEARCHER_PROMPT=$(cat "$PROMPTS_DIR/tasks/deep-research/searcher.md")

cat > "$OUTPUT_DIR/searcher-template.txt" << TASK
$SEARCHER_PROMPT

---

## Your Assignment

**Broader Topic:** $TOPIC
**Sub-question:** {SUB_QUESTION}
**Sub-question ID:** {SQ_ID}
**Search Strategies:** {STRATEGIES}

Execute your research and save findings as YAML to: $OUTPUT_DIR/findings-{SQ_ID}.yaml
TASK

log "Searcher template written to: $OUTPUT_DIR/searcher-template.txt"

# ═══════════════════════════════════════════
# Phase 3: Evaluation
# ═══════════════════════════════════════════
EVALUATOR_PROMPT=$(cat "$PROMPTS_DIR/tasks/deep-research/evaluator.md")

cat > "$OUTPUT_DIR/evaluator-task-template.txt" << TASK
$EVALUATOR_PROMPT

---

## Your Assignment

**Topic:** $TOPIC
**Research Plan:** (contents of plan.yaml)
**Findings:** (contents of all findings-*.yaml files)

Review all findings and produce your evaluation. Save to: $OUTPUT_DIR/evaluation.yaml
TASK

log "Evaluator task template written to: $OUTPUT_DIR/evaluator-task-template.txt"

# ═══════════════════════════════════════════
# Phase 4: Synthesis
# ═══════════════════════════════════════════
SYNTHESIZER_PROMPT=$(cat "$PROMPTS_DIR/tasks/deep-research/synthesizer.md")

cat > "$OUTPUT_DIR/synthesizer-task-template.txt" << TASK
$SYNTHESIZER_PROMPT

---

## Your Assignment

**Topic:** $TOPIC
**Research Plan:** (contents of plan.yaml)
**Evaluation:** (contents of evaluation.yaml)
**All Findings:** (contents of all findings-*.yaml files)

Produce the final research report. Save to: $OUTPUT_DIR/report.md
TASK

log "Synthesizer task template written to: $OUTPUT_DIR/synthesizer-task-template.txt"

# ═══════════════════════════════════════════
# Metadata
# ═══════════════════════════════════════════
cat > "$OUTPUT_DIR/metadata.yaml" << META
topic: "$TOPIC"
depth: $DEPTH
started: "$(timestamp)"
output_dir: "$OUTPUT_DIR"
status: "planning"
phases:
  planning: { status: "pending" }
  searching: { status: "pending", agents: 0 }
  evaluating: { status: "pending" }
  synthesizing: { status: "pending" }
META

log ""
log "═══════════════════════════════════════════"
log "Preparation complete!"
log "Output directory: $OUTPUT_DIR"
log ""
log "Files created:"
log "  - planner-task.txt (ready to spawn planner agent)"
log "  - searcher-template.txt (template for each searcher)"
log "  - evaluator-task-template.txt (template for evaluator)"
log "  - synthesizer-task-template.txt (template for synthesizer)"
log "  - metadata.yaml (tracking state)"
log ""
log "Next step: Main agent reads planner-task.txt and spawns the planner."
log "═══════════════════════════════════════════"

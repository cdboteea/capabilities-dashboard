#!/bin/bash
# evaluate-research.sh — Evaluate a research output using the LLM judge
# 
# Usage: ./evaluate-research.sh <research_report.md> <original_question> [output_file]
#
# Uses Claude to score the research on 7 quality dimensions.
# Results saved as YAML.

set -euo pipefail

PROMPTS_DIR="$HOME/clawd/prompts"
JUDGE_PROMPT="$PROMPTS_DIR/tasks/evaluation/llm-judge.md"

GREEN='\033[0;32m'
NC='\033[0m'
log() { echo -e "${GREEN}[evaluate]${NC} $1"; }

if [ $# -lt 2 ]; then
    echo "Usage: $0 <research_report.md> \"original question\" [output.yaml]"
    exit 1
fi

REPORT_FILE="$1"
QUESTION="$2"
OUTPUT_FILE="${3:-${REPORT_FILE%.md}-evaluation.yaml}"

if [ ! -f "$REPORT_FILE" ]; then
    echo "Error: Report file not found: $REPORT_FILE"
    exit 1
fi

REPORT_CONTENT=$(cat "$REPORT_FILE")
JUDGE_CONTENT=$(cat "$JUDGE_PROMPT")

log "Evaluating: $REPORT_FILE"
log "Question: $QUESTION"
log "Output: $OUTPUT_FILE"

# Build the evaluation prompt
cat > /tmp/eval-prompt.txt << EVAL
$JUDGE_CONTENT

---

## Research to Evaluate

**ORIGINAL QUESTION:** $QUESTION

**RESEARCH OUTPUT:**

$REPORT_CONTENT
EVAL

log "Evaluation prompt prepared ($(wc -c < /tmp/eval-prompt.txt) bytes)"
log "To run: spawn a sub-agent with this prompt, or use the main agent's LLM judge"
log "Prompt saved to: /tmp/eval-prompt.txt"

# Note: Actual LLM call would be done by the main agent via sessions_spawn
# This script prepares the evaluation prompt for orchestration

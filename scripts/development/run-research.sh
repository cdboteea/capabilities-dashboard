#!/bin/bash
# run-research.sh — Full automated research pipeline
#
# Usage: ./run-research.sh "topic" [depth]
#
# Runs the complete pipeline:
#   1. Prepare task files (deep-research.sh)
#   2. Output instructions for main agent to execute
#
# The main agent reads this output and spawns agents accordingly.

set -euo pipefail

TOPIC="${1:?Usage: $0 \"topic\" [depth]}"
DEPTH="${2:-1}"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

# Step 1: Prepare all task files
echo -e "${GREEN}[1/2]${NC} Preparing research task files..."
"$SCRIPTS_DIR/deep-research.sh" "$TOPIC" "$DEPTH"

# Find the output directory (most recently created)
OUTPUT_DIR=$(ls -td ~/clawd/research-outputs/*/ 2>/dev/null | head -1)

if [ -z "$OUTPUT_DIR" ]; then
    echo "Error: No output directory created"
    exit 1
fi

echo ""
echo -e "${GREEN}[2/2]${NC} Research prepared. Output directory: $OUTPUT_DIR"
echo ""
echo "═══════════════════════════════════════════════════════"
echo -e "${BOLD}AGENT ORCHESTRATION INSTRUCTIONS${NC}"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Step 1: Spawn planner"
echo "  agentId: research"
echo "  task: Read ${OUTPUT_DIR}planner-task.txt and follow instructions"
echo "  label: dr-planner"
echo ""
echo "Step 2: Read plan.yaml, spawn parallel searchers"
echo "  For each sub_question in ${OUTPUT_DIR}plan.yaml:"
echo "    agentId: research"
echo "    task: [searcher prompt] + sub-question + save to findings-sqN.yaml"
echo "    label: dr-searcher-sqN"
echo ""
echo "Step 3: After all searchers complete, spawn synthesizer"
echo "  agentId: synthesizer"
echo "  task: Read all findings files + synthesize to report.md"
echo "  label: dr-synthesizer"
echo ""
echo "Step 4: (Optional) Spawn evaluator"
echo "  agentId: research"
echo "  task: Score report.md + save evaluation.yaml"
echo "  label: dr-evaluator"
echo ""
echo "Task files: ${OUTPUT_DIR}"
echo "═══════════════════════════════════════════════════════"

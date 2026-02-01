#!/bin/bash
# ab-test-prompt.sh — Run A/B test on two prompt variants
#
# Usage: ./ab-test-prompt.sh <benchmark_id> <prompt_a.md> <prompt_b.md>
#
# Runs the same benchmark query with both prompts, then evaluates both outputs
# using the LLM judge. Reports comparison.

set -euo pipefail

PROMPTS_DIR="$HOME/clawd/prompts"
BENCHMARKS="$PROMPTS_DIR/tasks/evaluation/benchmarks.yaml"
RESULTS_DIR="$HOME/clawd/prompts/evaluations"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

log() { echo -e "${GREEN}[ab-test]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }

if [ $# -lt 3 ]; then
    echo "Usage: $0 <benchmark_id> <prompt_a.md> <prompt_b.md>"
    echo ""
    echo "Available benchmarks:"
    grep "id:" "$BENCHMARKS" | sed 's/.*id: /  /'
    exit 1
fi

BENCHMARK_ID="$1"
PROMPT_A="$2"
PROMPT_B="$3"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
TEST_DIR="$RESULTS_DIR/ab-${TIMESTAMP}-${BENCHMARK_ID}"

mkdir -p "$TEST_DIR"

# Extract benchmark question
QUESTION=$(python3 -c "
import yaml, sys
with open('$BENCHMARKS') as f:
    data = yaml.safe_load(f)
for bm in data['benchmarks']:
    if bm['id'] == '$BENCHMARK_ID':
        print(bm['question'])
        sys.exit(0)
print('BENCHMARK_NOT_FOUND')
sys.exit(1)
" 2>/dev/null || echo "BENCHMARK_NOT_FOUND")

if [ "$QUESTION" = "BENCHMARK_NOT_FOUND" ]; then
    echo "Error: Benchmark '$BENCHMARK_ID' not found"
    exit 1
fi

log "═══════════════════════════════════════════"
log "A/B Test: $BENCHMARK_ID"
log "Question: $QUESTION"
log "Variant A: $PROMPT_A"
log "Variant B: $PROMPT_B"
log "Output: $TEST_DIR"
log "═══════════════════════════════════════════"

# Save test metadata
cat > "$TEST_DIR/metadata.yaml" << META
test_id: "ab-${TIMESTAMP}-${BENCHMARK_ID}"
benchmark_id: "$BENCHMARK_ID"
question: "$QUESTION"
variant_a: "$PROMPT_A"
variant_b: "$PROMPT_B"
started: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
status: "prepared"
META

# Prepare variant A task
cat > "$TEST_DIR/task-a.txt" << TASK
$(cat "$PROMPT_A")

---

Research this topic and produce a structured report:

**Topic:** $QUESTION

Save your report to: $TEST_DIR/output-a.md
TASK

# Prepare variant B task
cat > "$TEST_DIR/task-b.txt" << TASK
$(cat "$PROMPT_B")

---

Research this topic and produce a structured report:

**Topic:** $QUESTION

Save your report to: $TEST_DIR/output-b.md
TASK

log ""
log "Test prepared! Files:"
log "  $TEST_DIR/task-a.txt — Spawn with variant A prompt"
log "  $TEST_DIR/task-b.txt — Spawn with variant B prompt"
log ""
log "Next steps:"
log "  1. Spawn two research agents with task-a.txt and task-b.txt"
log "  2. Wait for both to complete"
log "  3. Run evaluate-research.sh on both outputs"
log "  4. Compare scores"
log ""
log "Decision threshold: Adopt new variant only if avg score improves ≥1.0"

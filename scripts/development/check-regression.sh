#!/bin/bash
# check-regression.sh — Prevent regression when updating prompts
#
# Usage: ./check-regression.sh <prompt_id> <new_prompt_file>
#
# Checks new prompt against known insights and regression rules

set -euo pipefail

PROMPT_ID="${1:?Usage: $0 <prompt_id> <new_prompt_file>}"
NEW_PROMPT="${2:?Usage: $0 <prompt_id> <new_prompt_file>}"

INSIGHTS_DB="$HOME/clawd/knowledge/agent-insights.yaml"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

warn() { echo -e "${YELLOW}[regression-check]${NC} $1"; }
error() { echo -e "${RED}[regression-check]${NC} $1"; }
log() { echo -e "${GREEN}[regression-check]${NC} $1"; }

if [ ! -f "$NEW_PROMPT" ]; then
    error "Prompt file not found: $NEW_PROMPT"
    exit 1
fi

if [ ! -f "$INSIGHTS_DB" ]; then
    error "Insights database not found: $INSIGHTS_DB"
    exit 1
fi

log "Checking prompt '$PROMPT_ID' for potential regressions..."

# Extract regression rules for this prompt
REGRESSION_RULES=$(python3 -c "
import yaml
with open('$INSIGHTS_DB') as f:
    data = yaml.safe_load(f)

rules = data.get('regression_prevention', [])
agent_rules = [r for r in rules if '$PROMPT_ID' in r.get('affected_agents', [])]

for rule in agent_rules:
    print(f\"RULE: {rule['rule']}\")
    print(f\"REASON: {rule['reason']}\")
    print('---')
" 2>/dev/null || echo "Could not parse regression rules")

if [ -z "$REGRESSION_RULES" ]; then
    log "No specific regression rules found for '$PROMPT_ID'"
else
    echo "$REGRESSION_RULES"
fi

# Check for specific patterns that indicate regression
log "Performing automated checks..."

PROMPT_CONTENT=$(cat "$NEW_PROMPT")
ISSUES_FOUND=0

# Check 1: Source evaluation framework (for research agents)
if [[ "$PROMPT_ID" =~ (research|synthesizer) ]]; then
    if ! echo "$PROMPT_CONTENT" | grep -iq "source.*credibility\|credibility.*source\|tier.*credible"; then
        error "❌ Missing source evaluation framework"
        echo "   Regression rule: 'Never remove source evaluation framework from research agents'"
        echo "   Reason: Citations are critical for research credibility"
        ((ISSUES_FOUND++))
    else
        log "✅ Source evaluation framework present"
    fi
fi

# Check 2: Structured output format examples
if echo "$PROMPT_CONTENT" | grep -iq "yaml\|json\|structured\|format"; then
    if ! echo "$PROMPT_CONTENT" | grep -E "\`\`\`(yaml|json)" >/dev/null; then
        warn "⚠️  Mentions structured output but no format examples found"
        echo "   Consider adding concrete YAML/JSON examples"
        echo "   Rule: 'Always include structured output format examples in prompts'"
    else
        log "✅ Structured output format examples present"
    fi
fi

# Check 3: Error handling instructions
if [[ "$PROMPT_ID" =~ (personal|operator) ]]; then
    if ! echo "$PROMPT_CONTENT" | grep -iq "error\|fail\|graceful\|fallback"; then
        warn "⚠️  No error handling instructions found"
        echo "   Rule: 'Include error handling and graceful degradation instructions'"
        echo "   Reason: Agent confusion leads to incomplete tasks"
        ((ISSUES_FOUND++))
    else
        log "✅ Error handling instructions present"
    fi
fi

# Check 4: Known agent-specific issues
AGENT_ISSUES=$(python3 -c "
import yaml
with open('$INSIGHTS_DB') as f:
    data = yaml.safe_load(f)

agents = data.get('agents', {})
if '$PROMPT_ID' in agents:
    issues = agents['$PROMPT_ID'].get('known_issues', [])
    for issue in issues:
        if 'fix' not in issue:
            print(f\"UNRESOLVED: {issue['issue']}\")
            print(f\"PRIORITY: {issue.get('priority', 'unknown')}\")
            print('---')
" 2>/dev/null || echo "")

if [ -n "$AGENT_ISSUES" ]; then
    warn "Unresolved known issues for '$PROMPT_ID':"
    echo "$AGENT_ISSUES"
fi

# Summary
echo ""
if [ $ISSUES_FOUND -eq 0 ]; then
    log "✅ No regressions detected. Prompt appears safe to deploy."
    echo ""
    echo "Next steps:"
    echo "1. Test the updated prompt manually"
    echo "2. Run A/B test if evaluation system exists"
    echo "3. Update insights database if new learnings emerge"
    exit 0
else
    error "❌ $ISSUES_FOUND potential regression(s) found."
    echo ""
    echo "Recommended actions:"
    echo "1. Review and fix the issues above"
    echo "2. Consult $INSIGHTS_DB for detailed context"
    echo "3. Consider A/B testing before full deployment"
    exit 1
fi
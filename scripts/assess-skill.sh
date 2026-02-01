#!/bin/bash
# assess-skill.sh — Evaluate a skill's readiness for promotion to stable/production
# Usage: ./assess-skill.sh <skill-name>

set -euo pipefail

SKILL_NAME="${1:-}"
DEV_ROOT="$HOME/projects"

if [ -z "$SKILL_NAME" ]; then
    echo "Usage: $0 <skill-name>"
    echo ""
    echo "Available development skills:"
    ls -1 "$DEV_ROOT/skills/development/" 2>/dev/null | sed 's/^/  /' || echo "  (none)"
    exit 1
fi

SKILL_PATH="$DEV_ROOT/skills/development/$SKILL_NAME"

if [ ! -d "$SKILL_PATH" ]; then
    echo "❌ Skill '$SKILL_NAME' not found in development"
    exit 1
fi

echo "🔍 Assessing skill: $SKILL_NAME"
echo "📁 Path: $SKILL_PATH"
echo ""

# Initialize scoring
TOTAL_SCORE=0
MAX_SCORE=0

score_check() {
    local description="$1"
    local result="$2"
    local weight="${3:-1}"
    
    MAX_SCORE=$((MAX_SCORE + weight))
    
    if [ "$result" = "pass" ]; then
        TOTAL_SCORE=$((TOTAL_SCORE + weight))
        echo "✅ $description"
    elif [ "$result" = "partial" ]; then
        TOTAL_SCORE=$((TOTAL_SCORE + weight / 2))
        echo "🟡 $description (partial)"
    else
        echo "❌ $description"
    fi
}

echo "📋 FUNCTIONALITY ASSESSMENT"
echo "─────────────────────────────"

# Check if SKILL.md exists
if [ -f "$SKILL_PATH/SKILL.md" ]; then
    score_check "Has SKILL.md documentation" "pass" 2
    
    # Check documentation quality
    word_count=$(wc -w < "$SKILL_PATH/SKILL.md")
    if [ $word_count -gt 200 ]; then
        score_check "Documentation is comprehensive (${word_count} words)" "pass" 1
    elif [ $word_count -gt 50 ]; then
        score_check "Documentation is basic (${word_count} words)" "partial" 1  
    else
        score_check "Documentation is too brief (${word_count} words)" "fail" 1
    fi
    
    # Check for usage examples
    if grep -q -i "example\|usage" "$SKILL_PATH/SKILL.md" || grep -q '```' "$SKILL_PATH/SKILL.md"; then
        score_check "Contains usage examples" "pass" 1
    else
        score_check "Contains usage examples" "fail" 1
    fi
    
else
    score_check "Has SKILL.md documentation" "fail" 2
    score_check "Documentation is comprehensive" "fail" 1
    score_check "Contains usage examples" "fail" 1
fi

echo ""
echo "🔧 TECHNICAL ASSESSMENT"
echo "─────────────────────────"

# Check for additional files (scripts, dependencies)
file_count=$(find "$SKILL_PATH" -type f | wc -l | tr -d ' ')
if [ $file_count -gt 1 ]; then
    score_check "Has supporting files ($file_count total)" "pass" 1
    
    # Check for common script types
    if find "$SKILL_PATH" -name "*.js" -o -name "*.py" -o -name "*.sh" | grep -q .; then
        score_check "Has executable scripts" "pass" 1
    else
        score_check "Has executable scripts" "partial" 1
    fi
else
    score_check "Has supporting files (only SKILL.md)" "partial" 1
    score_check "Has executable scripts" "fail" 1
fi

# Check for dependency declarations
if [ -f "$SKILL_PATH/SKILL.md" ] && grep -q -i "requirement\|dependency\|install\|setup" "$SKILL_PATH/SKILL.md"; then
    score_check "Documents dependencies" "pass" 1
else
    score_check "Documents dependencies" "fail" 1
fi

echo ""
echo "📊 ASSESSMENT SUMMARY"
echo "════════════════════════"

PERCENTAGE=$((TOTAL_SCORE * 100 / MAX_SCORE))
echo "Score: $TOTAL_SCORE/$MAX_SCORE ($PERCENTAGE%)"

if [ $PERCENTAGE -ge 80 ]; then
    echo "🎉 Status: READY FOR PROMOTION TO STABLE"
    echo ""
    echo "Next steps:"
    echo "1. Run final manual tests"
    echo "2. mv ~/projects/skills/development/$SKILL_NAME ~/projects/skills/stable/"
    echo "3. git commit -m \"promote: $SKILL_NAME to stable\""
elif [ $PERCENTAGE -ge 60 ]; then
    echo "🟡 Status: NEEDS MINOR IMPROVEMENTS"
    echo ""
    echo "Address the ❌ items above before promotion"
elif [ $PERCENTAGE -ge 40 ]; then
    echo "🔶 Status: NEEDS SIGNIFICANT WORK"
    echo ""
    echo "Major improvements needed before promotion"
else
    echo "❌ Status: NOT READY - NEEDS MAJOR DEVELOPMENT"
    echo ""
    echo "Substantial work required"
fi
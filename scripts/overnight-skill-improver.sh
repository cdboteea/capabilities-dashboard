#!/bin/bash
# overnight-skill-improver.sh — Automatically improve development skills during overnight hours
# Assesses skills needing work and delegates improvement tasks to sub-agents

set -euo pipefail

DEV_ROOT="$HOME/projects"
LOGFILE="$HOME/clawd/logs/overnight-skill-improvement-$(date +%Y%m%d).log"
PROMOTION_THRESHOLD=80

log() {
    local msg="$(date '+%Y-%m-%d %H:%M:%S') [OVERNIGHT-DEV] $*"
    echo "$msg"
    echo "$msg" >> "$LOGFILE"
}

mkdir -p "$(dirname "$LOGFILE")"

log "🌙 Starting overnight skill improvement cycle"

# Get list of development skills
DEVELOPMENT_SKILLS=($(ls -1 "$DEV_ROOT/skills/development/" 2>/dev/null || true))

if [ ${#DEVELOPMENT_SKILLS[@]} -eq 0 ]; then
    log "✅ No development skills found - all promoted!"
    exit 0
fi

log "🔍 Found ${#DEVELOPMENT_SKILLS[@]} development skills: ${DEVELOPMENT_SKILLS[*]}"

# Assess each skill and identify improvement needs
for skill in "${DEVELOPMENT_SKILLS[@]}"; do
    log "📋 Assessing skill: $skill"
    
    # Run assessment and extract score
    assessment_output=$("$DEV_ROOT/scripts/assess-skill.sh" "$skill" 2>/dev/null || echo "Assessment failed")
    score_line=$(echo "$assessment_output" | grep "Score:" || echo "Score: 0/0 (0%)")
    percentage=$(echo "$score_line" | grep -o '[0-9]\+%' | tr -d '%' || echo "0")
    
    log "📊 $skill: ${percentage}% ready"
    
    if [ "$percentage" -lt "$PROMOTION_THRESHOLD" ]; then
        log "🔧 $skill needs improvement (${percentage}% < ${PROMOTION_THRESHOLD}%)"
        
        # Create improvement task description
        improvement_task="OVERNIGHT SKILL IMPROVEMENT

**Skill**: $skill  
**Current Score**: ${percentage}%
**Target**: 80%+ for promotion to production

**Mission**: Improve ~/projects/skills/development/$skill to meet production standards.

**Process**:
1. Run: ~/projects/scripts/assess-skill.sh $skill
2. Fix all ❌ failing criteria:
   - Enhance SKILL.md documentation (examples, dependencies, troubleshooting)
   - Improve code quality (error handling, structure)  
   - Document all requirements and setup steps
   - Add working usage examples
   - Ensure security compliance
3. Re-assess until score >= 80%
4. Commit improvements with clear message

**Success**: Skill ready for promotion (score >= 80%)
**Time Limit**: 2 hours max

Work only in ~/projects/skills/development/$skill/ - don't modify production code."

        log "🤖 Ready to spawn sub-agent for $skill improvement"
        echo "SPAWN_TASK:$skill:$improvement_task" >> "$LOGFILE"
        
    else
        log "🎉 $skill ready for promotion (${percentage}% >= ${PROMOTION_THRESHOLD}%)"
        echo "READY_FOR_PROMOTION:$skill" >> "$LOGFILE"
    fi
done

log "🌙 Overnight skill assessment complete"
log "📝 Full assessment log: $LOGFILE"
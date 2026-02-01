#!/bin/bash
# spawn-skill-improvers.sh — Spawn sub-agents to improve development skills overnight

set -euo pipefail

DEV_ROOT="$HOME/projects"

# Get development skills needing work
DEVELOPMENT_SKILLS=($(ls -1 "$DEV_ROOT/skills/development/" 2>/dev/null || true))

if [ ${#DEVELOPMENT_SKILLS[@]} -eq 0 ]; then
    echo "✅ No development skills found - all promoted!"
    exit 0
fi

echo "🌙 **OVERNIGHT SKILL IMPROVEMENT INITIATED**"
echo ""
echo "📊 Assessing ${#DEVELOPMENT_SKILLS[@]} development skills for improvement opportunities..."
echo ""

SPAWN_COMMANDS=()

# Assess each skill
for skill in "${DEVELOPMENT_SKILLS[@]}"; do
    # Run assessment
    assessment_output=$("$DEV_ROOT/scripts/assess-skill.sh" "$skill" 2>/dev/null || echo "Assessment failed")
    score_line=$(echo "$assessment_output" | grep "Score:" || echo "Score: 0/0 (0%)")
    percentage=$(echo "$score_line" | grep -o '[0-9]\+%' | tr -d '%' || echo "0")
    
    if [ "$percentage" -lt 80 ]; then
        echo "🔧 **$skill**: ${percentage}% (needs improvement)"
        SPAWN_COMMANDS+=("$skill:$percentage")
    else
        echo "🎉 **$skill**: ${percentage}% (ready for promotion!)"
    fi
done

echo ""

# Generate spawn commands if needed
if [ ${#SPAWN_COMMANDS[@]} -gt 0 ]; then
    echo "🚀 **Spawning ${#SPAWN_COMMANDS[@]} overnight improvement agents:**"
    echo ""
    
    for skill_info in "${SPAWN_COMMANDS[@]}"; do
        IFS=':' read -r skill_name current_score <<< "$skill_info"
        
        echo "**🤖 Spawning agent for: $skill_name**"
        echo "\`sessions_spawn(agentId='coder', task='OVERNIGHT SKILL IMPROVEMENT: $skill_name - Improve from ${current_score}% to 80%+ for production readiness. Fix all assessment failures in ~/projects/skills/development/$skill_name/ - enhance documentation, add examples, improve code quality, document dependencies. Re-assess until promotion ready.', timeoutSeconds=7200, cleanup='keep', label='overnight-$skill_name')\`"
        echo ""
    done
    
    echo "🌙 **Overnight skill development work started. Check results tomorrow morning!**"
else
    echo "✨ **All development skills are ready for promotion! No overnight work needed.**"
fi
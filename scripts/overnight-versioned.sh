#!/bin/bash
# overnight-versioned.sh — Versioned overnight improvement with copy-on-promotion

set -euo pipefail

DEV_ROOT="$HOME/projects"
VERSION_MANAGER="$DEV_ROOT/scripts/version-manager.sh"

log() {
    echo "$(date '+%H:%M:%S') [VERSIONED] $*"
}

assess_skill() {
    local skill_name="$1"
    
    if [ -x "$DEV_ROOT/scripts/assess-skill.sh" ]; then
        local assessment_output
        assessment_output=$("$DEV_ROOT/scripts/assess-skill.sh" "$skill_name" 2>/dev/null || echo "Assessment failed")
        local score_line=$(echo "$assessment_output" | grep "Score:" || echo "Score: 0/0 (0%)")
        echo "$score_line" | grep -o '[0-9]\+' | head -1 || echo "0"
    else
        echo "0"
    fi
}

process_skill() {
    local skill_name="$1"
    local skill_dir="$DEV_ROOT/skills/development/$skill_name"
    
    log "📋 Processing $skill_name"
    
    # Convert to versioned if needed
    "$VERSION_MANAGER" convert "$skill_name" >/dev/null 2>&1
    
    # Check current score
    local score=$(assess_skill "$skill_name")
    log "📊 $skill_name: ${score}%"
    
    # Check if ready for initial production deployment
    local prod_version=$(jq -r '.productionVersion' "$skill_dir/versions.json" 2>/dev/null || echo "null")
    
    if [ "$prod_version" = "null" ] && [ "$score" -ge 80 ]; then
        log "🚀 $skill_name ready for initial production deployment"
        "$VERSION_MANAGER" promote "$skill_name"
        # Continue development after promotion
    fi
    
    # Launch improvement session
    local improvement_prompt="VERSIONED SKILL IMPROVEMENT: $skill_name

**Current Score**: ${score}%
**Workspace**: ~/projects/skills/development/$skill_name/current/

## Mission
Improve this skill systematically. Work on the CURRENT DEVELOPMENT VERSION.

## Process
1. Assess: ~/projects/scripts/assess-skill.sh $skill_name
2. Fix failing criteria systematically
3. Enhance documentation and examples
4. Add error handling and validation
5. Improve code quality and structure

## Target Areas by Score:
- **0-79%**: Basic functionality, documentation, dependencies
- **80-89%**: Enhanced quality, comprehensive docs, optimization
- **90%+**: Excellence, best practices, advanced features

Work in ~/projects/skills/development/$skill_name/current/ to improve assessment score."

    log "🚀 Launching Claude Code session for $skill_name"
    if cd "$DEV_ROOT" && claude --remote "$improvement_prompt" >/dev/null 2>&1; then
        log "✅ Session launched"
        return 0
    else
        log "❌ Failed to launch session"
        return 1
    fi
}

main() {
    log "🌙 Starting versioned overnight development"
    
    if ! command -v claude &> /dev/null; then
        log "❌ Claude Code not found"
        exit 1
    fi
    
    local skills=($(ls -1 "$DEV_ROOT/skills/development/" 2>/dev/null || true))
    
    if [ ${#skills[@]} -eq 0 ]; then
        echo "✨ No development skills found"
        exit 0
    fi
    
    log "🔍 Found ${#skills[@]} skills: ${skills[*]}"
    
    local sessions_launched=0
    
    for skill in "${skills[@]}"; do
        if process_skill "$skill"; then
            sessions_launched=$((sessions_launched + 1))
            sleep 2
        fi
    done
    
    log "✅ Complete: $sessions_launched sessions launched"
    
    echo ""
    echo "🌙 **VERSIONED OVERNIGHT DEVELOPMENT STARTED**"
    echo ""
    echo "🚀 **$sessions_launched Claude Code sessions** launched for versioned improvement"
    echo ""
    echo "📊 **Features Active:**"
    echo "• **Version Control**: Each skill has proper version tracking"
    echo "• **Copy-on-Promotion**: Production deployment keeps development copy"
    echo "• **Continuous Improvement**: Development never stops after deployment"
    echo "• **Smart Deployment**: Production updated when significantly improved"
    echo ""
    echo "🌐 **Monitor**: https://claude.ai/code"
    echo "🔍 **Check Versions**: \`~/projects/scripts/version-manager.sh list\`"
    echo ""
    echo "**Professional versioned development active!** 🎯"
}

main "$@"
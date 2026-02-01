#!/bin/bash
# overnight-claude-code.sh — Overnight skill improvement using Claude Code remote sessions
# Replaces custom sub-agents with professional Claude Code workflow

set -euo pipefail

DEV_ROOT="$HOME/projects"
LOGFILE="$HOME/clawd/logs/overnight-claude-code-$(date +%Y%m%d).log"
PROMOTION_THRESHOLD=80

log() {
    local msg="$(date '+%Y-%m-%d %H:%M:%S') [CLAUDE-CODE] $*"
    echo "$msg"
    echo "$msg" >> "$LOGFILE"
}

check_claude_code() {
    if ! command -v claude &> /dev/null; then
        log "❌ Claude Code not found. Install: curl -fsSL https://claude.ai/install.sh | bash"
        exit 1
    fi
    
    log "✅ Claude Code available: $(claude --version 2>/dev/null | head -1 || echo 'version check failed')"
}

launch_skill_improvement() {
    local skill_name="$1"
    local current_score="$2"
    
    log "🚀 Launching Claude Code remote session for $skill_name"
    
    # Create detailed improvement prompt for Claude Code
    local improvement_prompt="OVERNIGHT SKILL IMPROVEMENT: $skill_name

**Current Assessment Score**: ${current_score}%
**Target**: 80%+ for production promotion
**Workspace**: ~/projects/skills/development/$skill_name/

## Mission
Transform this development skill into production-ready quality by systematically fixing all assessment failures.

## Process
1. **Initial Assessment**: Run ~/projects/scripts/assess-skill.sh $skill_name to see current state
2. **Fix Documentation**: Enhance SKILL.md with:
   - Clear description and usage examples
   - Complete dependency documentation  
   - Installation/setup instructions
   - Troubleshooting guidance
   - Working code examples with expected outputs
3. **Improve Code Quality**: Add:
   - Error handling and input validation
   - Proper file structure and organization
   - Executable permissions for scripts
   - Security compliance (no hardcoded secrets)
4. **Validate Changes**: 
   - Test all examples in documentation
   - Verify dependencies are correctly documented
   - Ensure security boundaries are respected
5. **Final Assessment**: Re-run assessment until score >= 80%
6. **Commit**: Create clear commit message documenting improvements

## Success Criteria
- Assessment score >= 80% (promotion ready)
- All examples in SKILL.md work correctly
- Dependencies clearly documented and testable
- Code follows security best practices
- Ready for immediate production deployment

Begin by assessing current state and systematically addressing each failing criteria."

    # Launch remote Claude Code session in background
    local session_output
    session_output=$(cd "$DEV_ROOT" && claude --remote "$improvement_prompt" 2>&1) || {
        log "❌ Failed to launch Claude Code session for $skill_name"
        log "Error: $session_output"
        return 1
    }
    
    # Extract session info
    local session_info=$(echo "$session_output" | grep -i "session\|id" | head -1 || echo "Session launched")
    log "📋 $skill_name session: $session_info"
    
    echo "SKILL:$skill_name:$(date '+%Y-%m-%d %H:%M:%S'):$session_info" >> "$LOGFILE"
    return 0
}

main() {
    mkdir -p "$(dirname "$LOGFILE")"
    log "🌙 Starting overnight Claude Code skill improvement"
    
    check_claude_code
    
    # Get development skills
    local skills=($(ls -1 "$DEV_ROOT/skills/development/" 2>/dev/null || true))
    
    if [ ${#skills[@]} -eq 0 ]; then
        log "✅ No development skills found - all promoted!"
        echo "✨ All skills have been promoted to production! No overnight work needed."
        exit 0
    fi
    
    log "🔍 Found ${#skills[@]} development skills: ${skills[*]}"
    
    local sessions_launched=0
    local skills_ready_for_promotion=()
    
    # Assess each skill and launch Claude Code sessions as needed
    for skill in "${skills[@]}"; do
        log "📋 Assessing skill: $skill"
        
        # Run assessment
        local assessment_output
        assessment_output=$("$DEV_ROOT/scripts/assess-skill.sh" "$skill" 2>/dev/null || echo "Assessment failed")
        local score_line=$(echo "$assessment_output" | grep "Score:" || echo "Score: 0/0 (0%)")
        local percentage=$(echo "$score_line" | grep -o '[0-9]\+%' | tr -d '%' || echo "0")
        
        log "📊 $skill: ${percentage}% ready"
        
        if [ "$percentage" -lt "$PROMOTION_THRESHOLD" ]; then
            log "🔧 $skill needs improvement (${percentage}% < ${PROMOTION_THRESHOLD}%)"
            
            # Launch Claude Code remote session
            if launch_skill_improvement "$skill" "$percentage"; then
                sessions_launched=$((sessions_launched + 1))
                log "✅ Claude Code session launched for $skill"
            else
                log "❌ Failed to launch session for $skill"
            fi
            
        else
            log "🎉 $skill ready for promotion (${percentage}% >= ${PROMOTION_THRESHOLD}%)"
            skills_ready_for_promotion+=("$skill")
        fi
        
        sleep 2
    done
    
    # Summary
    log "🌙 Overnight Claude Code automation complete"
    log "📊 Summary:"
    log "   • Skills assessed: ${#skills[@]}"
    log "   • Claude Code sessions launched: $sessions_launched"  
    log "   • Skills ready for promotion: ${#skills_ready_for_promotion[@]}"
    
    if [ $sessions_launched -gt 0 ]; then
        echo ""
        echo "🌙 **OVERNIGHT CLAUDE CODE DEVELOPMENT STARTED**"
        echo ""
        echo "🚀 **$sessions_launched Claude Code remote sessions launched** for skill improvement"
        echo ""
        echo "📊 **Monitor Progress:**"
        echo "• **Web Interface**: https://claude.ai/code"
        echo "• **CLI**: \`claude /tasks\` or \`claude --remote-list\`" 
        echo "• **Desktop App**: Download from claude.ai/desktop"
        echo ""
        echo "🌅 **Morning Review Commands:**"
        echo "\`\`\`bash"
        echo "# Check completed sessions"
        echo "claude --remote-list --filter completed"
        echo ""
        echo "# Resume any session for review"
        echo "claude --teleport --interactive"
        echo ""
        echo "# Monitor session status"
        echo "~/projects/scripts/monitor-claude-sessions.sh"
        echo "\`\`\`"
        echo ""
        echo "**Professional development workflow active! Check claude.ai/code for real-time progress.** 🚀"
    fi
    
    if [ ${#skills_ready_for_promotion[@]} -gt 0 ]; then
        echo ""
        echo "🎉 **Skills Ready for Promotion:**"
        for skill in "${skills_ready_for_promotion[@]}"; do
            echo "• **$skill** - Ready for stable → production"
        done
    fi
    
    log "📝 Full log: $LOGFILE"
}
#!/bin/bash
# monitor-claude-sessions.sh — Monitor Claude Code sessions for overnight development

set -euo pipefail

check_claude_code() {
    if ! command -v claude &> /dev/null; then
        echo "❌ Claude Code not found. Install: curl -fsSL https://claude.ai/install.sh | bash"
        exit 1
    fi
}

show_session_status() {
    echo "📊 **Claude Code Session Status** ($(date '+%H:%M:%S'))"
    echo ""
    
    # Try to get task list
    local tasks_output
    if tasks_output=$(claude --print "/tasks" 2>/dev/null); then
        if [[ "$tasks_output" =~ "No active sessions" ]] || [[ -z "$tasks_output" ]]; then
            echo "✅ **No active sessions** - All overnight work completed or not started"
        else
            echo "🔄 **Active Sessions:**"
            echo "$tasks_output"
        fi
    else
        echo "⚠️ **Unable to fetch session list** (may need authentication)"
        echo "   Run: \`claude setup-token\` if needed"
        echo "   Check web interface: https://claude.ai/code"
    fi
    
    echo ""
    echo "🌐 **Web Interface**: https://claude.ai/code"
    echo "🖥️ **Desktop App**: https://claude.ai/desktop"
}

assess_overnight_results() {
    echo "🌅 **Overnight Development Results Assessment**"
    echo ""
    
    local dev_root="$HOME/projects"
    local skills=($(ls -1 "$dev_root/skills/development/" 2>/dev/null || true))
    
    if [ ${#skills[@]} -eq 0 ]; then
        echo "🎉 **SUCCESS**: All skills promoted - no development work remaining!"
        return 0
    fi
    
    echo "📋 **Re-assessing ${#skills[@]} skills after overnight work:**"
    echo ""
    
    local ready_for_promotion=()
    
    for skill in "${skills[@]}"; do
        if [ -x "$dev_root/scripts/assess-skill.sh" ]; then
            local assessment_output
            assessment_output=$("$dev_root/scripts/assess-skill.sh" "$skill" 2>/dev/null || echo "Assessment failed")
            local score_line=$(echo "$assessment_output" | grep "Score:" || echo "Score: 0/0 (0%)")
            local percentage=$(echo "$score_line" | grep -o '[0-9]\+%' | tr -d '%' || echo "0")
            
            if [ "$percentage" -ge 80 ]; then
                echo "🎉 **$skill**: ${percentage}% - Ready for promotion!"
                ready_for_promotion+=("$skill")
            elif [ "$percentage" -ge 70 ]; then
                echo "🔶 **$skill**: ${percentage}% - Improved but needs more work"
            else
                echo "🔧 **$skill**: ${percentage}% - Still needs significant work"
            fi
        else
            echo "⚠️ **$skill**: Unable to assess"
        fi
    done
    
    echo ""
    echo "📊 **Summary**: ${#ready_for_promotion[@]} skills ready for promotion"
    
    if [ ${#ready_for_promotion[@]} -gt 0 ]; then
        echo ""
        echo "🚀 **Promotion Commands:**"
        for skill in "${ready_for_promotion[@]}"; do
            echo "   mv ~/projects/skills/development/$skill ~/projects/skills/stable/"
            echo "   ~/projects/scripts/deploy.sh skill $skill"
        done
    fi
}

main() {
    check_claude_code
    
    case "${1:-summary}" in
        "--assess"|"-a")
            assess_overnight_results
            ;;
        "--help"|"-h")
            echo "📖 **Claude Code Monitoring Guide**"
            echo ""
            echo "🌐 **Web Interface**: https://claude.ai/code"
            echo "🖥️ **Desktop App**: https://claude.ai/desktop" 
            echo "⌨️ **CLI Commands**:"
            echo "   \`claude /tasks\`              - List active sessions"
            echo "   \`claude --teleport\`          - Resume session locally"
            echo "   \`$0 --assess\`               - Check overnight results"
            ;;
        *)
            show_session_status
            ;;
    esac
}

main "$@"
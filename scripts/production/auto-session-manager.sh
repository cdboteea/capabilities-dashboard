#!/bin/bash
# auto-session-manager.sh — Automated session management with sub-agent delegation
# Monitors context usage and automatically archives sessions at 75% usage

set -euo pipefail

SESSIONS_JSON="$HOME/.openclaw/agents/main/sessions/sessions.json"
ARCHIVE_SCRIPT="$HOME/clawd/scripts/archive-session.sh"
ARCHIVE_THRESHOLD=75    # Archive at 75% context usage
CRITICAL_THRESHOLD=85   # Emergency archive at 85%

log() {
    echo "$(date '+%H:%M:%S') [AUTO-MGR] $*"
}

check_context_usage() {
    if [ ! -f "$SESSIONS_JSON" ]; then
        log "❌ No sessions.json found"
        return 1
    fi

    python3 - "$SESSIONS_JSON" "$ARCHIVE_THRESHOLD" "$CRITICAL_THRESHOLD" << 'PYEOF'
import json, sys

sessions_file = sys.argv[1]
archive_threshold = int(sys.argv[2])
critical_threshold = int(sys.argv[3])

with open(sessions_file, 'r') as f:
    sessions = json.load(f)

main_session = sessions.get("agent:main:main")
if not main_session:
    print("NO_SESSION")
    sys.exit(0)

total_tokens = main_session.get("totalTokens", 0)
context_tokens = main_session.get("contextTokens", 200000)
usage_pct = (total_tokens / context_tokens) * 100 if context_tokens > 0 else 0

print(f"{usage_pct:.1f}")

# Print session details for logging
session_id = main_session.get("sessionId", "unknown")
model = main_session.get("model", "unknown")
print(f"DETAILS|{session_id}|{total_tokens:,}|{context_tokens:,}|{model}", file=sys.stderr)
PYEOF
}

delegate_to_subagent() {
    local task_type="$1"
    local description="$2"
    
    log "🤖 Delegating $task_type to sub-agent: $description"
    
    # Determine best agent for task type
    local agent_id="main"  # Default fallback
    case "$task_type" in
        "coding"|"development"|"code")
            agent_id="coder"
            ;;
        "research"|"search"|"analysis")
            agent_id="research"
            ;;
        "writing"|"documentation"|"content")
            agent_id="writer"
            ;;
        "browser"|"automation"|"ui")
            agent_id="operator"
            ;;
        "data"|"analysis"|"processing")
            agent_id="data"
            ;;
        *)
            agent_id="main"
            ;;
    esac
    
    log "📋 Recommended agent: $agent_id"
    echo "DELEGATE_TO:$agent_id"
}

main() {
    log "🔍 Checking context usage..."
    
    # Get context usage percentage
    local usage_info
    usage_info=$(check_context_usage 2>/dev/null)
    local usage_pct="${usage_info%%$'\n'*}"
    
    if [ "$usage_pct" = "NO_SESSION" ]; then
        log "ℹ️ No active session found"
        return 0
    fi
    
    # Extract session details from stderr
    local details
    details=$(check_context_usage 2>&1 >/dev/null | grep "DETAILS" || true)
    if [ -n "$details" ]; then
        IFS='|' read -r _ session_id tokens limit model <<< "$details"
        log "📊 Session $session_id: $tokens/$limit tokens ($usage_pct% used, $model)"
    else
        log "📊 Context usage: $usage_pct%"
    fi
    
    # Take action based on usage
    if (( $(echo "$usage_pct >= $CRITICAL_THRESHOLD" | bc -l) )); then
        log "🔴 CRITICAL: $usage_pct% usage - EMERGENCY ARCHIVE!"
        echo "🚨 EMERGENCY: Session at $usage_pct% capacity - archiving immediately to prevent crash!"
        if [ -x "$ARCHIVE_SCRIPT" ]; then
            "$ARCHIVE_SCRIPT"
            echo "✅ Session archived. Recommend restarting conversation or using sub-agents for heavy tasks."
        else
            echo "❌ Archive script not found at $ARCHIVE_SCRIPT"
        fi
        
    elif (( $(echo "$usage_pct >= $ARCHIVE_THRESHOLD" | bc -l) )); then
        log "🟡 WARNING: $usage_pct% usage - archiving recommended"
        echo "⚠️  Session approaching capacity ($usage_pct% used). Consider:"
        echo "• Archive current session: ~/clawd/scripts/archive-session.sh"
        echo "• Use sub-agents for complex tasks: sessions_spawn(agentId='research', task='...')"
        echo "• Break up remaining work into smaller pieces"
        
    else
        log "🟢 OK: $usage_pct% usage - normal operation"
    fi
    
    # Provide task delegation guidance based on current usage
    if (( $(echo "$usage_pct >= 50" | bc -l) )); then
        echo ""
        echo "💡 Heavy task guidance (current usage: $usage_pct%):"
        echo "• Research/Analysis → sessions_spawn(agentId='research', task='...')"
        echo "• Coding/Development → sessions_spawn(agentId='coder', task='...')"
        echo "• Browser Automation → sessions_spawn(agentId='operator', task='...')"
        echo "• Writing/Docs → sessions_spawn(agentId='writer', task='...')"
        echo "• Data Processing → sessions_spawn(agentId='data', task='...')"
    fi
}

# Allow script to be sourced for individual functions
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
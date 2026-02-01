#!/bin/bash
# check-context.sh — Monitor session context usage and warn before overflow
# Usage: ./check-context.sh [warn-threshold-percent] [critical-threshold-percent]

set -euo pipefail

WARN_THRESHOLD=${1:-75}    # Warn at 75% of context limit
CRITICAL_THRESHOLD=${2:-90} # Critical at 90% of context limit

# Get current session info
SESSIONS_JSON="$HOME/.clawdbot/agents/main/sessions/sessions.json"

if [ ! -f "$SESSIONS_JSON" ]; then
    echo "❌ No sessions.json found"
    exit 1
fi

# Extract current main session info using Python
python3 - "$SESSIONS_JSON" "$WARN_THRESHOLD" "$CRITICAL_THRESHOLD" << 'PYEOF'
import json, sys

sessions_file = sys.argv[1]
warn_threshold = int(sys.argv[2])
critical_threshold = int(sys.argv[3])

with open(sessions_file, 'r') as f:
    sessions = json.load(f)

main_session = sessions.get("agent:main:main")
if not main_session:
    print("❌ No main session found")
    sys.exit(1)

session_id = main_session.get("sessionId", "unknown")
total_tokens = main_session.get("totalTokens", 0)
context_tokens = main_session.get("contextTokens", 200000)  # Default to 200k
input_tokens = main_session.get("inputTokens", 0)
output_tokens = main_session.get("outputTokens", 0)
model = main_session.get("model", "unknown")

# Calculate usage percentages
total_usage_pct = (total_tokens / context_tokens) * 100 if context_tokens > 0 else 0

print(f"📊 Session Context Status")
print(f"Session ID: {session_id}")
print(f"Model: {model}")
print(f"Context Limit: {context_tokens:,} tokens")
print(f"Total Used: {total_tokens:,} tokens ({total_usage_pct:.1f}%)")
print(f"  ├─ Input: {input_tokens:,} tokens")
print(f"  └─ Output: {output_tokens:,} tokens")
print()

# Status indicators
if total_usage_pct >= critical_threshold:
    print(f"🔴 CRITICAL: {total_usage_pct:.1f}% used - archive session immediately!")
    print("Run: ~/clawd/scripts/archive-session.sh")
elif total_usage_pct >= warn_threshold:
    print(f"🟡 WARNING: {total_usage_pct:.1f}% used - consider archiving soon")
    print("Consider breaking up large tasks or using sub-agents")
else:
    print(f"🟢 OK: {total_usage_pct:.1f}% used - plenty of context remaining")

# Recommendations based on usage
remaining = context_tokens - total_tokens
print(f"Remaining: {remaining:,} tokens (~{remaining//1000}k)")

if remaining < 50000:  # Less than 50k tokens left
    print()
    print("💡 Recommendations:")
    print("• Archive current session: ~/clawd/scripts/archive-session.sh")
    print("• Use sub-agents for large tasks: sessions_spawn()")
    print("• Switch to local models for heavy development work")
PYEOF
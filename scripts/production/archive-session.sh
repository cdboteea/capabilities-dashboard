#!/bin/bash
# archive-session.sh — Convert Clawdbot session .jsonl to searchable .md
# Usage: ./archive-session.sh [jsonl-file] [output-dir]
# If no args, archives the latest main session to memory/sessions/

set -euo pipefail

SESSIONS_DIR="${HOME}/.clawdbot/agents/main/sessions"
OUTPUT_DIR="${2:-${HOME}/clawd/memory/sessions}"
mkdir -p "$OUTPUT_DIR"

# Find the latest (largest) .jsonl that isn't a probe or lock file
if [ -n "${1:-}" ]; then
    JSONL_FILE="$1"
else
    JSONL_FILE=$(ls -S "$SESSIONS_DIR"/*.jsonl 2>/dev/null | grep -v probe | grep -v lock | head -1)
fi

if [ -z "$JSONL_FILE" ] || [ ! -f "$JSONL_FILE" ]; then
    echo "No session file found"
    exit 1
fi

SESSION_ID=$(basename "$JSONL_FILE" .jsonl)
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/${TIMESTAMP}.md"

echo "Archiving session $SESSION_ID → $OUTPUT_FILE"

# Convert jsonl to readable markdown
python3 - "$JSONL_FILE" "$OUTPUT_FILE" "$SESSION_ID" "$TIMESTAMP" << 'PYEOF'
import json, sys, os
from datetime import datetime

jsonl_file = sys.argv[1]
output_file = sys.argv[2]
session_id = sys.argv[3]
timestamp = sys.argv[4]

lines = []
with open(jsonl_file, 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:
            continue

# Filter to messages only (skip toolResult for brevity, keep user + assistant)
messages = []
for entry in lines:
    if entry.get('type') != 'message':
        continue
    msg = entry.get('message', {})
    role = msg.get('role', '')
    if role not in ('user', 'assistant'):
        continue
    
    ts = entry.get('timestamp', '')
    content_parts = msg.get('content', '')
    
    # Extract text content
    if isinstance(content_parts, list):
        texts = []
        for part in content_parts:
            if isinstance(part, dict):
                if part.get('type') == 'text':
                    texts.append(part.get('text', ''))
                elif part.get('type') == 'tool_use':
                    tool_name = part.get('name', 'unknown')
                    tool_input = json.dumps(part.get('input', {}))
                    if len(tool_input) > 200:
                        tool_input = tool_input[:200] + '...'
                    texts.append(f'[Tool: {tool_name}({tool_input})]')
            elif isinstance(part, str):
                texts.append(part)
        content = '\n'.join(texts)
    elif isinstance(content_parts, str):
        content = content_parts
    else:
        content = str(content_parts)
    
    if not content.strip():
        continue
    
    # Skip heartbeat noise
    if content.strip() in ('HEARTBEAT_OK', 'NO_REPLY'):
        continue
    if 'Read HEARTBEAT.md if it exists' in content and role == 'user':
        continue
    if 'Pre-compaction memory flush' in content and role == 'user':
        continue
    
    messages.append({
        'role': role,
        'ts': ts,
        'content': content.strip()
    })

# Write markdown
with open(output_file, 'w') as f:
    f.write(f'# Session Archive — {timestamp}\n')
    f.write(f'Session ID: `{session_id}`\n\n')
    if messages:
        first_ts = messages[0].get('ts', 'unknown')
        last_ts = messages[-1].get('ts', 'unknown')
        f.write(f'**Period:** {first_ts} → {last_ts}\n')
    f.write(f'**Messages:** {len(messages)} (heartbeats/flushes filtered)\n\n')
    f.write('---\n\n')
    
    for msg in messages:
        role_label = '👤 **Matias**' if msg['role'] == 'user' else '🤖 **Assistant**'
        ts_short = msg['ts'][11:19] if len(msg['ts']) > 19 else msg['ts']
        f.write(f'### {role_label} ({ts_short})\n\n')
        f.write(msg['content'] + '\n\n')

print(f"Archived {len(messages)} messages to {output_file}")
PYEOF

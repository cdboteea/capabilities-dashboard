#!/bin/bash
# log-research-session.sh — Log a new research session
# Usage: ./log-research-session.sh "topic" "prompt_id" "status" [duration] [notes]

set -euo pipefail

TOPIC="$1"
PROMPT_ID="$2"
STATUS="$3"  # in_progress, completed, failed, partial
DURATION="${4:-0}"
NOTES="${5:-}"

DB_FILE="$HOME/clawd/comparative-research/database/sessions.yaml"
SESSION_ID="session-$(date +%Y%m%d-%H%M%S)"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
OUTPUT_DIR="$(date +%Y-%m-%d-%H%M%S)"

echo "📊 Logging research session..."
echo "Topic: $TOPIC"
echo "Session ID: $SESSION_ID"
echo "Status: $STATUS"

# Extract prompt from prompts database
PROMPT_TEXT=$(python3 -c "
import yaml, sys
with open('$HOME/clawd/comparative-research/database/prompts.yaml', 'r') as f:
    data = yaml.safe_load(f)
    for prompt in data['prompts']:
        if prompt['id'] == '$PROMPT_ID':
            print(prompt['generated_prompt'])
            break
    else:
        print('Prompt not found')
")

# Determine topic category from prompt database
TOPIC_CATEGORY=$(python3 -c "
import yaml, sys
with open('$HOME/clawd/comparative-research/database/prompts.yaml', 'r') as f:
    data = yaml.safe_load(f)
    for prompt in data['prompts']:
        if prompt['id'] == '$PROMPT_ID':
            print(prompt.get('topic_category', 'general'))
            break
    else:
        print('general')
")

# Create backup
cp "$DB_FILE" "$DB_FILE.backup"

# Create session entry
TEMP_FILE=$(mktemp)
cat >> "$TEMP_FILE" << EOF

# Session logged $(date)
- id: "$SESSION_ID"
  created_at: "$TIMESTAMP"
  topic: "$TOPIC"
  topic_category: "$TOPIC_CATEGORY"
  prompt_id: "$PROMPT_ID"
  research_prompt: |
    $PROMPT_TEXT
  status: "$STATUS"
  total_duration_minutes: $DURATION
  completion_summary: ""
  outputs_directory: "$OUTPUT_DIR"
  platforms_attempted: []
  platforms_successful: []
  notes: "$NOTES"
EOF

# Add to sessions database
if grep -q "sessions: \[\]" "$DB_FILE"; then
    # First session - replace empty array
    sed '/sessions: \[\]/r '"$TEMP_FILE" "$DB_FILE" | sed 's/sessions: \[\]/sessions:/' > "$DB_FILE.tmp"
else
    # Append to existing sessions
    sed '/^sessions:/r '"$TEMP_FILE" "$DB_FILE" > "$DB_FILE.tmp"
fi

mv "$DB_FILE.tmp" "$DB_FILE"
rm "$TEMP_FILE"

# Create output directory
mkdir -p "$HOME/clawd/comparative-research/outputs/$OUTPUT_DIR"

echo "✅ Session logged successfully!"
echo "Session ID: $SESSION_ID"
echo "Output Directory: $OUTPUT_DIR"
echo "Database: $DB_FILE"
echo ""
echo "To update this session:"
echo "  ./update-session.sh $SESSION_ID status completed"
echo "  ./update-session.sh $SESSION_ID platforms_successful '[\"chatgpt\", \"claude\"]'"
echo ""
echo "To add platform results:"
echo "  ./log-platform-result.sh $SESSION_ID chatgpt completed 15 chatgpt-response.md"
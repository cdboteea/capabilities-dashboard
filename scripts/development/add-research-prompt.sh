#!/bin/bash
# add-research-prompt.sh — Add a new research prompt to the database
# Usage: ./add-research-prompt.sh "topic" "category" "prompt_text" [effectiveness_rating]

set -euo pipefail

TOPIC="$1"
CATEGORY="$2"
PROMPT_TEXT="$3"
EFFECTIVENESS="${4:-0}"  # Default to 0 (unrated)

DB_FILE="$HOME/clawd/comparative-research/database/prompts.yaml"
PROMPT_ID="prompt-$(date +%Y%m%d-%H%M%S)"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "📝 Adding research prompt to database..."
echo "Topic: $TOPIC"
echo "Category: $CATEGORY"
echo "ID: $PROMPT_ID"

# Create backup
cp "$DB_FILE" "$DB_FILE.backup"

# Create new prompt entry
TEMP_FILE=$(mktemp)
cat >> "$TEMP_FILE" << EOF

# Added $(date)
- id: "$PROMPT_ID"
  created_at: "$TIMESTAMP"
  topic: "$TOPIC"
  topic_category: "$CATEGORY"
  generated_prompt: |
    $PROMPT_TEXT
  prompt_generator: "manual"
  effectiveness_rating: $EFFECTIVENESS
  usage_count: 0
  successful_sessions: 0
  platform_success_rates:
    chatgpt: 0.0
    gemini: 0.0
    claude: 0.0
  avg_output_quality: 0.0
  notes: ""
  keywords: []
EOF

# Add to prompts database (before the closing of prompts array)
if grep -q "prompts: \[\]" "$DB_FILE"; then
    # First prompt - replace empty array
    sed '/prompts: \[\]/r '"$TEMP_FILE" "$DB_FILE" | sed 's/prompts: \[\]/prompts:/' > "$DB_FILE.tmp"
else
    # Append to existing prompts
    sed '/^prompts:/r '"$TEMP_FILE" "$DB_FILE" > "$DB_FILE.tmp"
fi

mv "$DB_FILE.tmp" "$DB_FILE"
rm "$TEMP_FILE"

echo "✅ Prompt added successfully!"
echo "ID: $PROMPT_ID"
echo "Database: $DB_FILE"
echo ""
echo "To use this prompt in research:"
echo "  ./query-prompts.sh --id $PROMPT_ID"
echo ""
echo "To update effectiveness after use:"
echo "  ./update-prompt-effectiveness.sh $PROMPT_ID [1-10]"
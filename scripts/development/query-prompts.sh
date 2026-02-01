#!/bin/bash
# query-prompts.sh — Query research prompts database
# Usage: ./query-prompts.sh [--topic "text"] [--category "cat"] [--min-rating N] [--id "id"]

set -euo pipefail

DB_FILE="$HOME/clawd/comparative-research/database/prompts.yaml"
TOPIC_FILTER=""
CATEGORY_FILTER=""
MIN_RATING=0
PROMPT_ID=""
LIST_ALL=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --topic)
            TOPIC_FILTER="$2"
            LIST_ALL=false
            shift 2
            ;;
        --category)
            CATEGORY_FILTER="$2"
            LIST_ALL=false
            shift 2
            ;;
        --min-rating)
            MIN_RATING="$2"
            LIST_ALL=false
            shift 2
            ;;
        --id)
            PROMPT_ID="$2"
            LIST_ALL=false
            shift 2
            ;;
        *)
            echo "Unknown option $1"
            echo "Usage: $0 [--topic TEXT] [--category CAT] [--min-rating N] [--id ID]"
            exit 1
            ;;
    esac
done

if [ ! -f "$DB_FILE" ]; then
    echo "❌ Prompts database not found: $DB_FILE"
    echo "Run ./init-research-database.sh first"
    exit 1
fi

echo "🔍 Querying research prompts database..."
echo ""

# Python script to query the database
python3 - << EOF
import yaml
import sys
from datetime import datetime

with open('$DB_FILE', 'r') as f:
    data = yaml.safe_load(f)

prompts = data.get('prompts', [])
if not prompts:
    print("📝 No prompts found in database")
    sys.exit(0)

filtered_prompts = []

for prompt in prompts:
    # Apply filters
    include = True
    
    if '$TOPIC_FILTER' and '$TOPIC_FILTER'.lower() not in prompt.get('topic', '').lower():
        include = False
    
    if '$CATEGORY_FILTER' and prompt.get('topic_category', '').lower() != '$CATEGORY_FILTER'.lower():
        include = False
    
    if prompt.get('effectiveness_rating', 0) < $MIN_RATING:
        include = False
        
    if '$PROMPT_ID' and prompt.get('id', '') != '$PROMPT_ID':
        include = False
    
    if include:
        filtered_prompts.append(prompt)

if not filtered_prompts:
    print("❌ No prompts match the specified criteria")
    sys.exit(0)

print(f"📋 Found {len(filtered_prompts)} matching prompt(s):")
print("")

for i, prompt in enumerate(filtered_prompts, 1):
    prompt_id = prompt.get('id', 'unknown')
    topic = prompt.get('topic', 'No topic')
    category = prompt.get('topic_category', 'general')
    rating = prompt.get('effectiveness_rating', 0)
    usage = prompt.get('usage_count', 0)
    created = prompt.get('created_at', 'unknown')
    
    # Success rates
    success_rates = prompt.get('platform_success_rates', {})
    chatgpt_success = success_rates.get('chatgpt', 0)
    gemini_success = success_rates.get('gemini', 0) 
    claude_success = success_rates.get('claude', 0)
    
    print(f"📝 {i}. {topic}")
    print(f"   ID: {prompt_id}")
    print(f"   Category: {category}")
    print(f"   Effectiveness: {rating}/10")
    print(f"   Usage Count: {usage}")
    print(f"   Success Rates: ChatGPT {chatgpt_success:.1%} | Gemini {gemini_success:.1%} | Claude {claude_success:.1%}")
    print(f"   Created: {created}")
    
    if '$PROMPT_ID' or len(filtered_prompts) == 1:
        # Show full prompt for specific queries
        prompt_text = prompt.get('generated_prompt', 'No prompt text')
        print(f"   Prompt:")
        for line in prompt_text.split('\n'):
            print(f"      {line}")
    
    notes = prompt.get('notes', '')
    if notes:
        print(f"   Notes: {notes}")
    
    print("")

if '$LIST_ALL' == 'true' and len(prompts) > 10:
    print(f"📊 Database Summary:")
    print(f"   Total Prompts: {len(prompts)}")
    
    # Category breakdown
    categories = {}
    ratings = []
    for prompt in prompts:
        cat = prompt.get('topic_category', 'general')
        categories[cat] = categories.get(cat, 0) + 1
        rating = prompt.get('effectiveness_rating', 0)
        if rating > 0:
            ratings.append(rating)
    
    print(f"   Categories: {dict(categories)}")
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        print(f"   Average Rating: {avg_rating:.1f}/10 ({len(ratings)} rated)")
    
    print("")
    print("Use filters to narrow results:")
    print("  --topic 'AI' --min-rating 7")
    print("  --category 'technology'")
    print("  --id 'prompt-20260201-143022'")
EOF
#!/bin/bash
# monitor-claude-usage.sh — Monitor Claude Pro subscription usage
# Usage: ./monitor-claude-usage.sh [warn-threshold-dollars]

set -euo pipefail

WARN_THRESHOLD="${1:-50}"  # Default warning at $50/day equivalent
LOG_FILE="$HOME/clawd/logs/claude-usage.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$(dirname "$LOG_FILE")"

echo "📊 Claude Pro Subscription Usage Monitor"
echo "========================================"
echo "Date: $TIMESTAMP"
echo ""

# Get current usage statistics
echo "📈 Current Usage (Last 7 days):"
USAGE_7D=$(openclaw gateway usage-cost --days 7)
echo "$USAGE_7D"

echo ""
echo "📈 Current Usage (Last 30 days):" 
USAGE_30D=$(openclaw gateway usage-cost --days 30)
echo "$USAGE_30D"

echo ""
echo "📈 Today's Usage:"
USAGE_TODAY=$(openclaw gateway usage-cost --days 1)
echo "$USAGE_TODAY"

# Extract today's cost and tokens
TODAY_COST=$(echo "$USAGE_TODAY" | grep "Latest day" | sed 's/.*\$//g' | sed 's/ ·.*//g')
TODAY_TOKENS=$(echo "$USAGE_TODAY" | grep "Latest day" | sed 's/.*· //g' | sed 's/ tokens//g')

echo ""
echo "💰 Cost Analysis:"
echo "Today's equivalent cost: \$${TODAY_COST}"
echo "Today's tokens: ${TODAY_TOKENS}"

# Log the data
echo "$TIMESTAMP,\$${TODAY_COST},${TODAY_TOKENS}" >> "$LOG_FILE"

# Check if we should warn
if (( $(echo "$TODAY_COST > $WARN_THRESHOLD" | bc -l) )); then
    echo ""
    echo "⚠️  HIGH USAGE ALERT!"
    echo "Today's usage (\$${TODAY_COST}) exceeds threshold (\$${WARN_THRESHOLD})"
    echo "Consider moderating usage to preserve subscription limits"
fi

echo ""
echo "🔍 Claude Pro Subscription Notes:"
echo "• Pro subscription has usage limits (not unlimited)"
echo "• Limits reset monthly on billing date"
echo "• Heavy usage may trigger rate limiting"
echo "• Monitor via: https://platform.claude.com/"

echo ""
echo "📊 Usage Trends (Last 7 entries):"
if [ -f "$LOG_FILE" ]; then
    echo "Date,Cost,Tokens"
    tail -7 "$LOG_FILE" | while IFS=, read -r date cost tokens; do
        echo "$date,$cost,$tokens"
    done
else
    echo "No historical data yet"
fi

echo ""
echo "📁 Usage log: $LOG_FILE"
echo "🔄 Run this script daily to track trends"
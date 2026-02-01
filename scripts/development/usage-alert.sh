#!/bin/bash
# usage-alert.sh — Alert system for Claude usage monitoring
# Usage: ./usage-alert.sh [daily-limit] [monthly-limit]

set -euo pipefail

DAILY_LIMIT="${1:-100}"    # $100/day equivalent warning
MONTHLY_LIMIT="${2:-1000}" # $1000/month equivalent warning

echo "🚨 Claude Usage Alert System"
echo "Daily limit: \$${DAILY_LIMIT}"
echo "Monthly limit: \$${MONTHLY_LIMIT}"
echo ""

# Get current usage
TODAY_USAGE=$(openclaw gateway usage-cost --days 1)
MONTHLY_USAGE=$(openclaw gateway usage-cost --days 30)

# Extract costs
TODAY_COST=$(echo "$TODAY_USAGE" | grep "Total:" | sed 's/.*\$//g' | sed 's/ ·.*//g')
MONTHLY_COST=$(echo "$MONTHLY_USAGE" | grep "Total:" | sed 's/.*\$//g' | sed 's/ ·.*//g')

echo "Today's usage: \$${TODAY_COST}"
echo "Monthly usage: \$${MONTHLY_COST}"

# Check thresholds
ALERT_NEEDED=false

if (( $(echo "$TODAY_COST > $DAILY_LIMIT" | bc -l) )); then
    echo ""
    echo "🚨 DAILY LIMIT EXCEEDED!"
    echo "Usage: \$${TODAY_COST} > Limit: \$${DAILY_LIMIT}"
    ALERT_NEEDED=true
fi

if (( $(echo "$MONTHLY_COST > $MONTHLY_LIMIT" | bc -l) )); then
    echo ""
    echo "🚨 MONTHLY LIMIT EXCEEDED!"
    echo "Usage: \$${MONTHLY_COST} > Limit: \$${MONTHLY_LIMIT}"
    ALERT_NEEDED=true
fi

if [ "$ALERT_NEEDED" = true ]; then
    echo ""
    echo "📱 Sending WhatsApp alert to Matias..."
    
    ALERT_MSG="🚨 Claude Usage Alert

Today: \$${TODAY_COST} (limit: \$${DAILY_LIMIT})
Month: \$${MONTHLY_COST} (limit: \$${MONTHLY_LIMIT})

Consider moderating usage to preserve Claude Pro subscription limits.

Time: $(date)"

    # Send alert via OpenClaw message tool
    # Note: This will only work if WhatsApp is configured and working
    echo "Alert message prepared (WhatsApp sending would go here)"
    echo "Message: $ALERT_MSG"
else
    echo ""
    echo "✅ Usage within limits"
fi
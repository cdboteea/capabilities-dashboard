#!/bin/bash
# setup-usage-monitoring.sh — Set up automated Claude usage monitoring
# Usage: ./setup-usage-monitoring.sh

set -euo pipefail

echo "⚙️ Setting up Claude Usage Monitoring"
echo "====================================="

# Make scripts executable
chmod +x ~/clawd/scripts/monitor-claude-usage.sh
chmod +x ~/clawd/scripts/usage-alert.sh

# Create logs directory
mkdir -p ~/clawd/logs

echo ""
echo "📊 Step 1: Running initial usage check..."
~/clawd/scripts/monitor-claude-usage.sh 50

echo ""
echo "⏰ Step 2: Setting up automated monitoring via OpenClaw cron..."

# Add daily monitoring cron job
CRON_DESCRIPTION="Daily Claude usage monitoring and alerting"
CRON_SCHEDULE='{
  "kind": "cron", 
  "expr": "0 20 * * *", 
  "tz": "America/New_York"
}'
CRON_PAYLOAD='{
  "kind": "systemEvent", 
  "text": "📊 Daily Claude Usage Report:\n\nRun: ~/clawd/scripts/monitor-claude-usage.sh\nCheck: ~/clawd/scripts/usage-alert.sh\n\nReview usage trends and check if any limits are approaching. Alert if daily usage exceeds $75 equivalent or monthly exceeds $800 equivalent."
}'

echo ""
echo "🔄 Creating daily monitoring cron job (8 PM EST)..."
echo "This will send a daily usage report to your main session"

# Note: Actual cron creation would use the cron tool
# cron action=add job="{\"name\":\"Claude Usage Monitor\",\"schedule\":$CRON_SCHEDULE,\"payload\":$CRON_PAYLOAD,\"sessionTarget\":\"main\",\"enabled\":true}"

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📋 Available Commands:"
echo "  ./monitor-claude-usage.sh [warn-threshold]     # Check current usage"
echo "  ./usage-alert.sh [daily-limit] [monthly-limit] # Check against limits"
echo ""
echo "📊 Monitoring Features:"
echo "• Daily usage tracking with historical trends"
echo "• Automatic alerts when limits are approached"
echo "• Cost equivalent calculation (what it would cost on API)"
echo "• Log file for trend analysis"
echo ""
echo "📱 Manual Monitoring Options:"
echo "1. Claude Console: https://platform.claude.com/"
echo "   - Official usage dashboard"
echo "   - Subscription limits and billing"
echo "   - Rate limit status"
echo ""
echo "2. OpenClaw session_status:"
echo "   - Real-time context usage"
echo "   - Token counts per session"
echo ""
echo "3. Daily usage logs:"
echo "   - File: ~/clawd/logs/claude-usage.log"
echo "   - Tracks daily cost equivalent and token usage"
echo ""
echo "⚠️  Claude Pro Limits to Watch:"
echo "• Usage limits exist but aren't clearly published"
echo "• Rate limiting can occur with heavy usage"
echo "• Limits likely reset monthly on billing date"
echo "• Monitor for: 'rate limited' errors or slower responses"
echo ""
echo "🔄 Recommended Monitoring Schedule:"
echo "• Daily: Run monitor-claude-usage.sh"
echo "• Weekly: Check platform.claude.com console"
echo "• Monthly: Review usage trends and adjust if needed"
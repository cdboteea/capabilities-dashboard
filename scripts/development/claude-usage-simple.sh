#!/bin/bash
# claude-usage-simple.sh — Simple Claude usage monitoring
# Usage: ./claude-usage-simple.sh

echo "📊 Claude Pro Usage Summary"
echo "=========================="
echo "Date: $(date)"
echo ""

echo "📈 Usage Statistics:"
openclaw gateway usage-cost --days 1 | head -3
echo ""
openclaw gateway usage-cost --days 7 | head -3  
echo ""
openclaw gateway usage-cost --days 30 | head -3

echo ""
echo "📱 Quick Usage Check:"
USAGE_7D=$(openclaw gateway usage-cost --days 7 --json 2>/dev/null || echo '{"totalCost": "unknown"}')
echo "7-day usage: $(echo "$USAGE_7D" | grep -o '\$[0-9.]*' | head -1 || echo 'Data not available')"

echo ""
echo "🔍 How to Monitor Claude Pro Limits:"
echo ""
echo "1. 📊 OpenClaw Built-in:"
echo "   session_status           # Real-time context usage"
echo "   openclaw gateway usage-cost --days 7    # Weekly usage"
echo ""
echo "2. 🌐 Claude Console (Official):"
echo "   https://platform.claude.com/"
echo "   - Login with your Claude account"
echo "   - View subscription usage and limits"
echo "   - Check billing and rate limit status"
echo ""
echo "3. 🚨 Warning Signs to Watch:"
echo "   - 'Rate limited' error messages"
echo "   - Slower response times"
echo "   - 'Usage limit exceeded' notifications"
echo "   - Daily equivalent cost > $100"
echo ""
echo "4. ⚠️  Claude Pro Subscription Notes:"
echo "   - Pro has usage limits (not truly unlimited)"
echo "   - Limits reset monthly on billing cycle"
echo "   - Heavy usage triggers rate limiting"
echo "   - Exact limits not publicly disclosed"
echo ""
echo "💡 Recommendations:"
echo "• Check usage daily during heavy work periods"
echo "• Use local models for non-critical tasks when possible"
echo "• Monitor via Claude console weekly"
echo "• Set up usage tracking routine"

# Create simple usage log entry
echo "$(date '+%Y-%m-%d %H:%M:%S') - Usage check completed" >> ~/clawd/logs/claude-usage-simple.log
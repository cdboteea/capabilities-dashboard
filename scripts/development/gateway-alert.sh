#!/bin/bash
# gateway-alert.sh — Send alerts when gateway monitoring fails
#
# Usage: ./gateway-alert.sh "alert message"

set -euo pipefail

ALERT_MSG="${1:?Usage: $0 \"alert message\"}"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S EST")

# Try multiple notification channels since gateway may be down

# Method 1: Try WhatsApp via gateway (may fail if gateway is down)
try_whatsapp() {
    curl -s -X POST "http://127.0.0.1:18789/api/message/send" \
        -H "Content-Type: application/json" \
        -d '{
            "channel": "whatsapp",
            "to": "+16468532660",
            "message": "🚨 GATEWAY ALERT\n\n'"$ALERT_MSG"'\n\nTime: '"$TIMESTAMP"'"
        }' >/dev/null 2>&1 && return 0 || return 1
}

# Method 2: Try system notification  
try_notification() {
    osascript -e "display notification \"$ALERT_MSG\" with title \"OpenClaw Gateway Alert\" sound name \"Basso\"" 2>/dev/null && return 0 || return 1
}

# Method 3: Log to file
log_alert() {
    echo "[$TIMESTAMP] GATEWAY ALERT: $ALERT_MSG" >> ~/clawd/logs/gateway-alerts.log
}

# Method 4: Send email via Himalaya (if configured)
try_email() {
    if command -v himalaya >/dev/null 2>&1; then
        echo "Gateway Alert: $ALERT_MSG (Time: $TIMESTAMP)" | \
        himalaya message send --account gmail \
            --to "mirvoism@gmail.com" \
            --subject "🚨 OpenClaw Gateway Alert" 2>/dev/null && return 0 || return 1
    else
        return 1
    fi
}

# Try notification methods in order
main() {
    # Ensure log directory exists
    mkdir -p ~/clawd/logs
    
    # Always log the alert
    log_alert
    
    # Try WhatsApp first (primary channel)
    if try_whatsapp; then
        echo "✅ WhatsApp alert sent"
        return 0
    fi
    
    # Try system notification
    if try_notification; then
        echo "✅ System notification sent"
    fi
    
    # Try email backup
    if try_email; then
        echo "✅ Email alert sent"
    fi
    
    echo "⚠️  Alert logged to ~/clawd/logs/gateway-alerts.log"
}

main
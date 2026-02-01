#!/bin/bash
# monitor-and-restart.sh — Automated gateway monitoring with restart and alerts
#
# Run via cron every 5 minutes to ensure gateway stays healthy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$HOME/clawd/logs/gateway-monitor.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log "Starting automated gateway monitoring..."

# Run monitoring with auto-restart
if "$SCRIPT_DIR/monitor-gateway.sh" --restart-if-down >>"$LOG_FILE" 2>&1; then
    log "✅ Gateway monitoring: All systems healthy"
else
    log "❌ Gateway monitoring: Issues detected and restart attempted"
    
    # Send alert about the restart
    "$SCRIPT_DIR/gateway-alert.sh" "Gateway monitoring detected issues and performed automatic restart. Check logs at ~/clawd/logs/gateway-monitor.log for details."
    
    # Wait and verify restart worked
    sleep 10
    if "$SCRIPT_DIR/monitor-gateway.sh" >>"$LOG_FILE" 2>&1; then
        log "✅ Gateway restart successful - system recovered"
        "$SCRIPT_DIR/gateway-alert.sh" "Gateway restart successful - system recovered and healthy"
    else
        log "❌ Gateway restart failed - manual intervention required"
        "$SCRIPT_DIR/gateway-alert.sh" "🚨 CRITICAL: Gateway restart FAILED - manual intervention required. System may be down."
    fi
fi

log "Automated monitoring complete"
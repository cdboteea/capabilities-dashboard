#!/bin/bash
# monitor-gateway.sh — Gateway health monitoring and auto-restart
#
# Usage: ./monitor-gateway.sh [--restart-if-down]
# 
# Checks:
# 1. Gateway HTTP endpoint responds
# 2. WhatsApp connectivity  
# 3. No duplicate processes
# 4. Gateway process is healthy

set -euo pipefail

GATEWAY_URL="http://127.0.0.1:18789"
RESTART_FLAG="${1:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[monitor]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
error() { echo -e "${RED}[error]${NC} $1"; }

# Check 1: Gateway HTTP health
check_http() {
    if curl -s -f "$GATEWAY_URL/health" >/dev/null 2>&1; then
        log "✅ Gateway HTTP responding"
        return 0
    else
        error "❌ Gateway HTTP not responding"
        return 1
    fi
}

# Check 2: Gateway processes
check_processes() {
    local processes
    processes=$(ps aux | grep -E "(clawdbot.*gateway|openclaw-gateway)" | grep -v grep || true)
    local count
    count=$(echo "$processes" | grep -c . || true)
    
    if [ "$count" -eq 0 ]; then
        error "❌ No gateway processes running"
        return 1
    elif [ "$count" -eq 1 ]; then
        log "✅ Single gateway process running"
        echo "$processes" | while read -r line; do
            log "   $line"
        done
        return 0
    else
        warn "⚠️  Multiple gateway processes detected ($count):"
        echo "$processes" | while read -r line; do
            warn "   $line"
        done
        return 1
    fi
}

# Check 3: WhatsApp connectivity (requires successful HTTP first)
check_whatsapp() {
    # This would need to call a gateway API endpoint that shows WhatsApp status
    # For now, we'll just check if gateway is responding
    if curl -s -f "$GATEWAY_URL" >/dev/null 2>&1; then
        log "✅ Gateway control panel accessible"
        return 0
    else
        error "❌ Gateway control panel not accessible"
        return 1
    fi
}

# Restart gateway if requested and checks failed
restart_gateway() {
    warn "Attempting gateway restart..."
    
    # Kill any existing gateway processes
    pkill -f "clawdbot.*gateway" 2>/dev/null || true
    pkill -f "openclaw-gateway" 2>/dev/null || true
    
    sleep 3
    
    # Start fresh gateway
    log "Starting new gateway process..."
    nohup clawdbot gateway &
    
    sleep 5
    
    if check_http; then
        log "✅ Gateway restart successful"
        return 0
    else
        error "❌ Gateway restart failed"
        return 1
    fi
}

# Main monitoring logic
main() {
    log "Starting gateway health check..."
    
    local http_ok=0
    local processes_ok=0
    local whatsapp_ok=0
    
    check_http && http_ok=1
    check_processes && processes_ok=1
    check_whatsapp && whatsapp_ok=1
    
    local total_checks=$((http_ok + processes_ok + whatsapp_ok))
    
    if [ $total_checks -eq 3 ]; then
        log "✅ All checks passed (3/3)"
        exit 0
    else
        warn "❌ Failed checks ($((3 - total_checks))/3)"
        
        if [ "$RESTART_FLAG" = "--restart-if-down" ]; then
            restart_gateway
        else
            error "Use --restart-if-down to automatically restart failed gateway"
            exit 1
        fi
    fi
}

main
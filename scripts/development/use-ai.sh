#!/bin/bash
# use-ai.sh — Simple natural language AI platform dispatcher
# Usage: ./use-ai.sh "chatgpt analyze this code"
#        ./use-ai.sh "gemini research market trends"  
#        ./use-ai.sh "claude app help with architecture"

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "🤖 AI Platform Dispatcher"
    echo "========================"
    echo ""
    echo "Usage: $0 \"[platform] [task]\""
    echo ""
    echo "Examples:"
    echo "  $0 \"chatgpt write a Python script for data processing\""
    echo "  $0 \"gemini research the future of renewable energy\""
    echo "  $0 \"claude app analyze this system architecture\""
    echo ""
    echo "Supported platforms:"
    echo "  🤖 chatgpt, chat-gpt, gpt"
    echo "  🧠 claude-app, claude app"  
    echo "  🔍 gemini, google-gemini"
    echo ""
    echo "Auto-detection (when no platform specified):"
    echo "  📊 research/analysis tasks → gemini"
    echo "  💻 code/technical tasks → claude app"
    echo "  ✨ creative/writing tasks → chatgpt"
    exit 1
fi

# This would be the OpenClaw tool call - for now it's a demo
REQUEST="$*"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "🚀 AI Platform Request: $REQUEST"
echo "📅 Time: $(date)"
echo ""

# In a real implementation, this would use the sessions_spawn OpenClaw tool
echo "🔧 This would execute:"
echo "sessions_spawn(agentId='main', task='AI Platform Router: $REQUEST', label='ai-platform-$TIMESTAMP')"

# For now, just run the router script
~/clawd/scripts/ai-platform-router.sh "$REQUEST"
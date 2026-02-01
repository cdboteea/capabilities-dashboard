#!/bin/bash
# ai-platform-router.sh — Route AI platform requests to appropriate agents
# Usage: ./ai-platform-router.sh "use chatgpt to analyze this code"

set -euo pipefail

REQUEST="$1"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "🤖 AI Platform Router"
echo "Request: $REQUEST"
echo "Time: $(date)"
echo ""

# Convert to lowercase for matching
REQUEST_LOWER=$(echo "$REQUEST" | tr '[:upper:]' '[:lower:]')

# Determine platform and task type
PLATFORM=""
TASK_TYPE=""
CLEAN_REQUEST=""

# Platform detection
if echo "$REQUEST_LOWER" | grep -E "(chatgpt|chat gpt|gpt)" >/dev/null; then
    PLATFORM="chatgpt"
elif echo "$REQUEST_LOWER" | grep -E "(claude app|claude desktop)" >/dev/null; then
    PLATFORM="claude-app"
elif echo "$REQUEST_LOWER" | grep -E "(gemini|google gemini|bard)" >/dev/null; then
    PLATFORM="gemini"
else
    # Default platform logic based on task type
    if echo "$REQUEST_LOWER" | grep -E "(research|analyze|study|investigate|market|trends)" >/dev/null; then
        PLATFORM="gemini"
        echo "🔍 Auto-selected Gemini for research task"
    elif echo "$REQUEST_LOWER" | grep -E "(code|programming|debug|algorithm|technical)" >/dev/null; then
        PLATFORM="claude-app"
        echo "💻 Auto-selected Claude App for technical task"
    elif echo "$REQUEST_LOWER" | grep -E "(write|create|image|creative|story)" >/dev/null; then
        PLATFORM="chatgpt"
        echo "✨ Auto-selected ChatGPT for creative task"
    else
        echo "❓ No platform specified and couldn't auto-detect. Please specify:"
        echo "   use chatgpt to..."
        echo "   use claude app to..."
        echo "   use gemini to..."
        exit 1
    fi
fi

# Clean the request (remove platform prefixes)
CLEAN_REQUEST=$(echo "$REQUEST" | sed -E 's/^(use |ask |)?(chatgpt|claude app|claude desktop|gemini|google gemini|bard)( to| about| help with| research| )?//i' | sed 's/^ *//')

# Detect if this is a research task for Gemini
if [ "$PLATFORM" = "gemini" ] && echo "$REQUEST_LOWER" | grep -E "(research|analyze|study|investigate)" >/dev/null; then
    TASK_TYPE="research"
else
    TASK_TYPE="standard"
fi

echo "🎯 Platform: $PLATFORM"
echo "📋 Task Type: $TASK_TYPE" 
echo "📝 Clean Request: $CLEAN_REQUEST"
echo ""

# Create output directory
OUTPUT_DIR="$HOME/clawd/media/${PLATFORM}-agent/${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"
echo "$CLEAN_REQUEST" > "$OUTPUT_DIR/request.txt"

# Generate platform-specific agent task
case "$PLATFORM" in
    "chatgpt")
        echo "🚀 Launching ChatGPT App Agent..."
        AGENT_TASK="You are the ChatGPT App automation agent.

Task: $CLEAN_REQUEST

Instructions:
1. Launch/focus ChatGPT app: open -a ChatGPT && sleep 3
2. Take screenshot: peekaboo image --path $OUTPUT_DIR/chatgpt-before.png --app ChatGPT
3. Start new conversation: peekaboo key 'cmd+n' && sleep 1
4. Submit request: peekaboo type '$CLEAN_REQUEST' && peekaboo key Return
5. Wait for response: sleep 90 (adjust based on complexity)
6. Take progress screenshot: peekaboo image --path $OUTPUT_DIR/chatgpt-progress.png --app ChatGPT  
7. Capture response: peekaboo click 'Copy' && pbpaste > $OUTPUT_DIR/response.md
8. Final screenshot: peekaboo image --path $OUTPUT_DIR/chatgpt-after.png --app ChatGPT

Handle errors gracefully. If ChatGPT is busy or rate limited, document the timing.
Report back with: ChatGPT's response, timing info, any issues encountered.

Original request: $REQUEST"
        ;;
        
    "claude-app")
        echo "🚀 Launching Claude App Agent..."
        AGENT_TASK="You are the Claude App automation agent.

Task: $CLEAN_REQUEST

Instructions:
1. Launch/focus Claude app: open -a Claude && sleep 3
2. Take screenshot: peekaboo image --path $OUTPUT_DIR/claude-before.png --app Claude
3. Start new conversation: peekaboo key 'cmd+n' && sleep 1
4. Submit request: peekaboo type '$CLEAN_REQUEST' && peekaboo key Return
5. Wait for response: sleep 90 (adjust based on complexity)
6. Take progress screenshot: peekaboo image --path $OUTPUT_DIR/claude-progress.png --app Claude
7. Capture response: peekaboo click 'Copy' && pbpaste > $OUTPUT_DIR/response.md
8. Final screenshot: peekaboo image --path $OUTPUT_DIR/claude-after.png --app Claude

Handle errors gracefully. If Claude app has issues, try restarting.
Report back with: Claude's response, timing info, any issues encountered.

Original request: $REQUEST"
        ;;
        
    "gemini")
        if [ "$TASK_TYPE" = "research" ]; then
            echo "🔬 Launching Gemini Research Agent..."
            AGENT_TASK="You are the Gemini Research automation agent.

Task: $CLEAN_REQUEST

Instructions:
1. Open Gemini: browser action=open targetUrl='https://gemini.google.com' profile=openclaw
2. Take screenshot: browser action=screenshot
3. Select Research tool: browser action=act request='{\"kind\": \"click\", \"ref\": \"Research\"}'
4. Submit research request: browser action=act request='{\"kind\": \"type\", \"text\": \"$CLEAN_REQUEST\"}'
5. Start research: browser action=act request='{\"kind\": \"key\", \"key\": \"Enter\"}'
6. Wait for research plan: browser action=act request='{\"kind\": \"wait\", \"timeMs\": 45000}'
7. Take plan screenshot: browser action=screenshot
8. Launch research: browser action=act request='{\"kind\": \"click\", \"ref\": \"Launch\"}'
9. Monitor progress (check every 2 minutes): browser action=screenshot
10. Wait for completion (up to 20 minutes): browser action=act request='{\"kind\": \"wait\", \"timeMs\": 1200000}'
11. Capture final research report and save to: $OUTPUT_DIR/response.md
12. Final screenshot: browser action=screenshot

Save screenshots to: $OUTPUT_DIR/gemini-*.png
This is a deep research task - expect 10-20 minutes for completion.
Report back with: Research findings, sources, timing info.

Original request: $REQUEST"
        else
            echo "🚀 Launching Gemini Chat Agent..."
            AGENT_TASK="You are the Gemini Chat automation agent.

Task: $CLEAN_REQUEST

Instructions:
1. Open Gemini: browser action=open targetUrl='https://gemini.google.com' profile=openclaw  
2. Take screenshot: browser action=screenshot
3. Submit request: browser action=act request='{\"kind\": \"type\", \"text\": \"$CLEAN_REQUEST\", \"ref\": \"textbox\"}'
4. Send request: browser action=act request='{\"kind\": \"key\", \"key\": \"Enter\"}'
5. Wait for response: browser action=act request='{\"kind\": \"wait\", \"timeMs\": 60000}'
6. Take progress screenshot: browser action=screenshot
7. Capture response and save to: $OUTPUT_DIR/response.md
8. Final screenshot: browser action=screenshot

Save screenshots to: $OUTPUT_DIR/gemini-*.png
Report back with: Gemini's response, timing info, any issues.

Original request: $REQUEST"
        fi
        ;;
esac

# Spawn the appropriate agent
echo "⏳ Spawning $PLATFORM agent..."

# Create metadata file
cat > "$OUTPUT_DIR/metadata.yaml" << EOF
request: "$REQUEST"
clean_request: "$CLEAN_REQUEST"
platform: "$PLATFORM"
task_type: "$TASK_TYPE"
timestamp: "$TIMESTAMP"
started_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
output_dir: "$OUTPUT_DIR"
status: "started"
EOF

echo "📁 Output directory: $OUTPUT_DIR"
echo "🤖 Agent task prepared"
echo ""
echo "Note: This is a demo script. In production, this would call:"
echo "sessions_spawn agentId='main' task='[AGENT_TASK]' cleanup='keep' label='${PLATFORM}-${TIMESTAMP}'"
echo ""
echo "The actual agent task:"
echo "----------------------------------------"
echo "$AGENT_TASK"
echo "----------------------------------------"
echo ""
echo "✅ Ready to deploy! Replace this echo with actual sessions_spawn call."
#!/bin/bash
# test-comparative-e2e.sh — End-to-end test of comparative research workflow
# Usage: ./test-comparative-e2e.sh "research topic"

set -euo pipefail

TOPIC="${1:-Current AI coding assistants trends 2024-2026}"
TEST_DIR="e2e-test-$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$TEST_DIR/test.log"

echo "🧪 End-to-End Comparative Research Test"
echo "Topic: $TOPIC"
echo "Test Directory: $TEST_DIR"
echo ""

mkdir -p "$TEST_DIR"/{outputs,screenshots,logs}
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

# Phase 1: Pre-flight checks
echo "🔍 Phase 1: Pre-flight Checks"
echo "=============================="

echo "📱 Checking required applications..."
APPS_OK=true
for app in "ChatGPT" "Claude"; do
    if [ -d "/Applications/${app}.app" ]; then
        echo "✅ $app.app found"
    else
        echo "❌ $app.app missing"
        APPS_OK=false
    fi
done

echo ""
echo "🔑 Checking permissions..."
PERMS=$(peekaboo permissions)
echo "$PERMS"

echo ""
echo "🌐 Checking Gemini access..."
GEMINI_TEST=$(web_fetch "https://gemini.google.com" --maxChars 200 || echo "FAILED")
if echo "$GEMINI_TEST" | grep -q "Gemini"; then
    echo "✅ Gemini accessible"
else
    echo "⚠️  Gemini access issue"
fi

if [ "$APPS_OK" = false ]; then
    echo "❌ Required apps missing. Cannot proceed."
    exit 1
fi

# Phase 2: Test Agent Spawning
echo ""
echo "🤖 Phase 2: Agent Spawn Test"
echo "============================="

echo "Testing comparative-research agent spawn..."
sessions_spawn \
    agentId="main" \
    task="You are acting as the comparative-research agent. 

Test task: Create a simple research prompt for topic: '$TOPIC'

Requirements:
- Create a 200-word research prompt
- Save to: $TEST_DIR/outputs/test-prompt.md
- Include request for executive summary, key findings, sources
- Report completion status

This is a test - keep it simple but functional." \
    cleanup="keep" \
    label="test-agent-spawn" &

SPAWN_PID=$!
echo "Agent spawned (PID: $SPAWN_PID)"

# Wait for agent completion (max 2 minutes)
echo "⏳ Waiting for agent completion..."
sleep 5

# Check if prompt was created
WAIT_COUNT=0
while [ ! -f "$TEST_DIR/outputs/test-prompt.md" ] && [ $WAIT_COUNT -lt 24 ]; do
    echo "   Waiting for test prompt... ($((WAIT_COUNT * 5))s)"
    sleep 5
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ -f "$TEST_DIR/outputs/test-prompt.md" ]; then
    echo "✅ Test prompt created successfully"
    echo "Preview:"
    head -5 "$TEST_DIR/outputs/test-prompt.md"
else
    echo "❌ Test prompt creation failed"
    echo "Checking session status..."
    sessions_list --limit 5
    exit 1
fi

# Phase 3: Individual Platform Tests
echo ""
echo "🤖 Phase 3: Platform Automation Tests"
echo "======================================"

echo "Testing ChatGPT app automation..."
sessions_spawn \
    agentId="main" \
    task="You are acting as the operator agent for ChatGPT app testing.

Test task: Use ChatGPT app to test basic automation

Instructions:
1. Launch ChatGPT app (if not running)
2. Take a screenshot and save to: $TEST_DIR/screenshots/chatgpt-test.png
3. Create a simple test by typing: 'Hello, this is a test message'
4. Take another screenshot after typing
5. Save any response to: $TEST_DIR/outputs/chatgpt-test.md
6. Report success/failure with details

Use Peekaboo commands:
- peekaboo app launch ChatGPT
- peekaboo image --path $TEST_DIR/screenshots/chatgpt-before.png
- peekaboo type 'Hello, this is a test message'
- peekaboo key Return
- peekaboo image --path $TEST_DIR/screenshots/chatgpt-after.png

If you encounter errors, document them clearly." \
    cleanup="keep" \
    label="test-chatgpt" &

echo "Testing Claude app automation..."
sessions_spawn \
    agentId="main" \
    task="You are acting as the operator agent for Claude app testing.

Test task: Use Claude app to test basic automation

Instructions:
1. Launch Claude app (if not running)  
2. Take a screenshot and save to: $TEST_DIR/screenshots/claude-test.png
3. Create a simple test by typing: 'Hello, this is a test message'
4. Take another screenshot after typing
5. Save any response to: $TEST_DIR/outputs/claude-test.md
6. Report success/failure with details

Use similar Peekaboo commands as ChatGPT test.

If you encounter errors, document them clearly." \
    cleanup="keep" \
    label="test-claude" &

echo "Testing Gemini web automation..."
sessions_spawn \
    agentId="main" \
    task="You are acting as the operator agent for Gemini web testing.

Test task: Test Gemini web interface access

Instructions:
1. Use browser tool to open https://gemini.google.com
2. Take a screenshot
3. Check if sign-in is required
4. Document the current state
5. Save findings to: $TEST_DIR/outputs/gemini-test.md

Use browser commands:
- browser action=open targetUrl='https://gemini.google.com'
- browser action=screenshot
- Document what you observe

This is just a connectivity/UI test - don't try to sign in yet." \
    cleanup="keep" \
    label="test-gemini" &

# Phase 4: Wait and Collect Results
echo ""
echo "⏳ Phase 4: Waiting for Test Completion"
echo "======================================="

echo "Waiting up to 3 minutes for all tests to complete..."
sleep 180

# Phase 5: Results Analysis
echo ""
echo "📊 Phase 5: Results Analysis"
echo "============================"

echo "Test Files Created:"
find "$TEST_DIR" -type f | sort

echo ""
echo "File Sizes:"
find "$TEST_DIR" -type f -exec ls -lh {} \;

echo ""
echo "Active Sessions:"
sessions_list --limit 10

echo ""
echo "Test Summary:"
echo "============="

# Check each test result
TESTS=("test-prompt.md" "chatgpt-test.md" "claude-test.md" "gemini-test.md")
for test in "${TESTS[@]}"; do
    if [ -f "$TEST_DIR/outputs/$test" ]; then
        SIZE=$(stat -f%z "$TEST_DIR/outputs/$test" 2>/dev/null || echo "0")
        if [ "$SIZE" -gt 10 ]; then
            echo "✅ $test - Success ($SIZE bytes)"
        else
            echo "⚠️  $test - Created but small ($SIZE bytes)"
        fi
    else
        echo "❌ $test - Missing"
    fi
done

echo ""
echo "Screenshots:"
if ls "$TEST_DIR/screenshots/"*.png >/dev/null 2>&1; then
    for screenshot in "$TEST_DIR/screenshots/"*.png; do
        echo "📸 $(basename "$screenshot")"
    done
else
    echo "❌ No screenshots found"
fi

echo ""
echo "🎯 Identified Fail Points:"
echo "=========================="

# Analyze for common failure patterns
if ! find "$TEST_DIR/outputs" -name "*.md" -exec grep -l "error\|failed\|timeout" {} \; | head -1; then
    echo "✅ No obvious error patterns in outputs"
else
    echo "⚠️  Errors detected in outputs:"
    find "$TEST_DIR/outputs" -name "*.md" -exec grep -l "error\|failed\|timeout" {} \; | while read -r file; do
        echo "   $file:"
        grep -i "error\|failed\|timeout" "$file" | head -3 | sed 's/^/      /'
    done
fi

echo ""
echo "📁 Full test results saved to: $TEST_DIR/"
echo "📝 Test log: $LOG_FILE"
echo ""
echo "Next steps based on results:"
echo "1. Fix any identified fail points"
echo "2. Grant missing permissions if needed" 
echo "3. Test authentication flows manually"
echo "4. Run full comparative research workflow"
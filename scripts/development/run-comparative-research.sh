#!/bin/bash
# run-comparative-research.sh — Execute complete comparative research workflow with database tracking
# Usage: ./run-comparative-research.sh "research topic" [category]

set -euo pipefail

RESEARCH_TOPIC="$1"
TOPIC_CATEGORY="${2:-general}"

echo "🔬 Starting Comparative Deep Research"
echo "Topic: $RESEARCH_TOPIC"
echo "Category: $TOPIC_CATEGORY"
echo "Timestamp: $(date)"
echo ""

# Validate database exists
DB_DIR="$HOME/clawd/comparative-research/database"
if [ ! -d "$DB_DIR" ]; then
    echo "❌ Research database not initialized"
    echo "Run: ~/clawd/scripts/init-research-database.sh"
    exit 1
fi

# Step 1: Log session start
echo "📊 Step 1: Initializing session..."
SESSION_OUTPUT=$(~/clawd/scripts/log-research-session.sh "$RESEARCH_TOPIC" "manual-prompt" "in_progress" 0 "Automated comparative research")
SESSION_ID=$(echo "$SESSION_OUTPUT" | grep "Session ID:" | cut -d' ' -f3)
OUTPUT_DIR=$(echo "$SESSION_OUTPUT" | grep "Output Directory:" | cut -d' ' -f3)

echo "Session ID: $SESSION_ID"
echo "Output Directory: $OUTPUT_DIR"

# Step 2: Execute research via sessions_spawn with comprehensive task
echo ""
echo "🤖 Step 2: Launching comparative research agent..."

# Create the comprehensive research task
RESEARCH_TASK="You are the comparative deep research coordinator. Execute complete workflow:

## RESEARCH TOPIC: $RESEARCH_TOPIC
## SESSION ID: $SESSION_ID
## OUTPUT DIRECTORY: comparative-research/outputs/$OUTPUT_DIR

### PHASE 1: PROMPT GENERATION (2 minutes)
1. Use ChatGPT to generate comprehensive research prompt
2. No length restrictions - request thorough analysis
3. Save prompt to: ~/clawd/comparative-research/outputs/$OUTPUT_DIR/research-prompt.md
4. Add prompt to database: ~/clawd/scripts/add-research-prompt.sh

### PHASE 2: PLATFORM DEEP RESEARCH LAUNCH (2 minutes)
5. ChatGPT Deep Research:
   - Focus app: peekaboo app focus ChatGPT
   - New chat: peekaboo key 'cmd+n'
   - Submit research prompt with deep research triggers
   - Take screenshots: before, submitted, minimize
   
6. Gemini Research Tool (Two-Step Process):
   - Open: browser action=open targetUrl='https://gemini.google.com'
   - Select Research tool
   - Submit prompt and wait for research plan
   - Click 'Launch Research' button
   - Take screenshots: plan, launched, minimize

### PHASE 3: MONITORING & COLLECTION (10-20 minutes)
7. Monitor both platforms every 2 minutes:
   - Focus each app individually
   - Take progress screenshots
   - Check for completion indicators
   - When complete: capture full response
   
8. Save results to:
   - ~/clawd/comparative-research/outputs/$OUTPUT_DIR/chatgpt-response.md
   - ~/clawd/comparative-research/outputs/$OUTPUT_DIR/gemini-response.md

### PHASE 4: COMPARATIVE ANALYSIS (5 minutes)
9. Generate detailed ChatGPT vs Gemini comparative analysis:
   - Content depth comparison
   - Source quality assessment  
   - Unique insights identification
   - Factual consistency analysis
   - Platform-specific strengths
   - Use case recommendations (when to use ChatGPT vs Gemini)
    
10. Save analysis to: ~/clawd/comparative-research/outputs/$OUTPUT_DIR/comparative-analysis.md

### DATABASE UPDATES:
11. Update session status and metrics
12. Log platform results and performance  
13. Update prompt effectiveness ratings

### ERROR HANDLING:
- Document all authentication issues
- Screenshot any errors or timeouts  
- Gracefully handle platform failures
- Update database with partial results if needed

### SUCCESS CRITERIA:
✅ Research prompt generated and saved
✅ Both platforms (ChatGPT + Gemini) successfully submit research
✅ Comprehensive reports collected from both platforms
✅ Head-to-head comparative analysis completed
✅ Database updated with results and metrics
✅ All outputs saved to designated directory

IMPORTANT: Use explicit focus control and minimize windows between checks to avoid automation interference. Take screenshots at every major step for debugging.

Expected total time: 12-20 minutes for ChatGPT vs Gemini comparison."

# Launch the research session
SPAWN_RESULT=$(sessions_spawn agentId="main" task="$RESEARCH_TASK" cleanup="keep" label="comparative-research-$SESSION_ID")

echo "✅ Research agent launched!"
echo ""
echo "🔍 Monitor progress with:"
echo "  sessions_list --limit 5"
echo ""
echo "📁 Outputs will be saved to:"
echo "  ~/clawd/comparative-research/outputs/$OUTPUT_DIR/"
echo ""  
echo "📊 Session tracking:"
echo "  Session ID: $SESSION_ID"
echo "  Database: ~/clawd/comparative-research/database/sessions.yaml"
echo ""
echo "⏱️  Expected completion: 12-20 minutes"
echo "📱 You'll be notified when research is complete"

# Set up completion monitoring (runs in background)
(
    sleep 30  # Give initial setup time
    
    while true; do
        sleep 300  # Check every 5 minutes
        
        # Check if outputs exist
        OUTPUT_PATH="$HOME/clawd/comparative-research/outputs/$OUTPUT_DIR"
        
        if [ -f "$OUTPUT_PATH/comparative-analysis.md" ]; then
            # Research complete!
            ~/clawd/scripts/update-session.sh "$SESSION_ID" "status" "completed"
            
            # Count completed platforms
            PLATFORMS_DONE=0
            [ -f "$OUTPUT_PATH/chatgpt-response.md" ] && PLATFORMS_DONE=$((PLATFORMS_DONE + 1))
            [ -f "$OUTPUT_PATH/gemini-response.md" ] && PLATFORMS_DONE=$((PLATFORMS_DONE + 1))
            
            # Send completion notification
            echo "🎉 ChatGPT vs Gemini comparative research completed!"
            echo "Topic: $RESEARCH_TOPIC" 
            echo "Platforms completed: $PLATFORMS_DONE/2"
            echo "Results: ~/clawd/comparative-research/outputs/$OUTPUT_DIR/"
            
            exit 0
        fi
        
        # Check for timeout (45 minutes)
        SESSION_AGE=$(( $(date +%s) - $(date -d "$(echo $SESSION_OUTPUT | grep 'Session logged' | cut -d' ' -f3-)" +%s 2>/dev/null || echo 0) ))
        if [ $SESSION_AGE -gt 2700 ]; then  # 45 minutes
            ~/clawd/scripts/update-session.sh "$SESSION_ID" "status" "timeout"
            echo "⚠️ Research session timed out after 45 minutes"
            echo "Check: ~/clawd/comparative-research/outputs/$OUTPUT_DIR/"
            exit 1
        fi
    done
) &

echo "🔄 Background monitoring started (PID: $!)"
echo ""
echo "Use Ctrl+C to cancel monitoring (research will continue)"
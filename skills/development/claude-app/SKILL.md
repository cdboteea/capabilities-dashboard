# Claude App Skill

**Trigger:** "use claude app to..." | "ask claude app about..." | "claude app help with..."

Control the Claude macOS desktop app via dedicated agent for any task.

## Purpose

Natural language access to Claude app with agent automation:
- **"use claude app to analyze this data structure"**
- **"ask claude app about machine learning best practices"**
- **"claude app help with debugging this algorithm"**
- **"get claude's perspective on this architecture design"**

## How It Works

1. **Natural invocation** - Say "use claude app to [task]"
2. **Agent spawning** - Dedicated Claude agent handles the work
3. **App automation** - Agent controls Claude app via Peekaboo
4. **Result delivery** - Agent reports back with response
5. **Continued chat** - You can keep working while agent runs

## Agent Automation Pattern

When triggered, spawns a dedicated agent with this task:
```
You are the Claude App automation agent.

Task: [USER_REQUEST]

Instructions:
1. Launch/focus Claude app: open -a Claude && sleep 3
2. Start new conversation: peekaboo key "cmd+n" && sleep 1  
3. Submit user's request: peekaboo type "[USER_REQUEST]" && peekaboo key Return
4. Wait for response: sleep 60-120 (depending on complexity)
5. Capture response: peekaboo click "Copy" && pbpaste > response.md
6. Take screenshots for verification
7. Report back with Claude's response

Handle errors gracefully and document any issues.
Save outputs to: ~/clawd/media/claude-agent/[timestamp]/
```

## Usage Examples

### Technical Analysis
**You:** "use claude app to explain the security implications of this API design"
**System:** *Spawns agent, sends design to Claude app, returns with security analysis*

### Code Generation
**You:** "claude app help with writing a Python script for data validation"
**System:** *Agent handles the coding task and returns implementation*

### Problem Solving
**You:** "ask claude app to break down this complex algorithm step by step"  
**System:** *Agent gets detailed explanation from Claude and reports back*

### Alternative Perspective
**You:** "get claude app's take on this architectural decision"
**System:** *Agent submits question and returns different viewpoint*

## Technical Implementation

### Agent Spawning Command
```bash
sessions_spawn \
    agentId="main" \
    task="Claude App Agent: [USER_REQUEST]" \
    cleanup="keep" \
    label="claude-app-[short-description]"
```

### Peekaboo Commands Used
```bash
# App control
open -a Claude
peekaboo app focus Claude

# Navigation  
peekaboo key "cmd+n"        # New conversation
peekaboo key "cmd+shift+backspace"  # Clear conversation (if needed)

# Input
peekaboo type "text here"
peekaboo key Return

# Output capture
peekaboo click "Copy"
pbpaste > output.md

# Screenshots
peekaboo image --path screenshot.png --app Claude
```

### Error Handling
- App not responding → Restart app
- UI elements missing → Take debug screenshot  
- Rate limiting → Document timing and retry
- Authentication required → Request manual intervention

## File Organization

Outputs saved to: `~/clawd/media/claude-agent/YYYY-MM-DD-HHMMSS/`
```
├── request.txt          # Original user request
├── response.md          # Claude's response
├── claude-before.png    # Screenshot before submission  
├── claude-after.png     # Screenshot of response
└── metadata.yaml        # Timing and status info
```

## Integration with Main Chat

The skill allows seamless integration:
1. **You continue chatting** with main assistant (Claude Sonnet)
2. **Agent works in background** automating Claude app  
3. **Agent reports back** when complete
4. **No interruption** to your main conversation

## Advantages of Claude App vs Main Assistant

- **Different Claude model** - App may use different version/capabilities
- **App-specific features** - Claude app's unique interfaces and tools
- **Subscription optimization** - Use Claude Pro features efficiently  
- **Model comparison** - Compare Sonnet (main) vs app model responses
- **Parallel processing** - Claude app works while you chat with main Claude

## Model Differences

**Main Assistant (You):**
- Claude Sonnet 4.0
- Full tool access
- OpenClaw integration
- Context continuity

**Claude App:**
- Latest Claude model (may be different version)
- App-specific features
- Standard Claude interface
- Fresh conversation context

## Requirements

- Claude app installed and logged in
- Peekaboo automation permissions granted
- Agent spawning capability available

## Usage Strategy

Use Claude app for:
- **Different perspective** on same problem
- **App-specific features** not available in main chat
- **Fresh context** when main chat context is full
- **Model comparison** between versions
- **Parallel work** while main conversation continues

This skill gives you access to multiple Claude models and interfaces simultaneously, allowing for comparative analysis and expanded capabilities.
# ChatGPT App Skill

**Trigger:** "use chatgpt to..." | "ask chatgpt about..." | "chatgpt help with..."

Control the ChatGPT macOS desktop app via dedicated agent for any task.

## Purpose

Natural language access to ChatGPT app with agent automation:
- **"use chatgpt to analyze this data"**
- **"ask chatgpt about the latest AI trends"**  
- **"chatgpt help with writing a business plan"**
- **"get a second opinion from chatgpt on this code"**

## How It Works

1. **Natural invocation** - Say "use chatgpt to [task]"
2. **Agent spawning** - Dedicated ChatGPT agent handles the work
3. **App automation** - Agent controls ChatGPT app via Peekaboo
4. **Result delivery** - Agent reports back with response
5. **Continued chat** - You can keep working while agent runs

## Agent Automation Pattern

When triggered, spawns a dedicated agent with this task:
```
You are the ChatGPT App automation agent.

Task: [USER_REQUEST]

Instructions:
1. Launch/focus ChatGPT app: open -a ChatGPT && sleep 3
2. Start new conversation: peekaboo key "cmd+n" && sleep 1
3. Submit user's request: peekaboo type "[USER_REQUEST]" && peekaboo key Return
4. Wait for response: sleep 60-120 (depending on complexity)
5. Capture response: peekaboo click "Copy" && pbpaste > response.md
6. Take screenshots for verification
7. Report back with ChatGPT's response

Handle errors gracefully and document any issues.
Save outputs to: ~/clawd/media/chatgpt-agent/[timestamp]/
```

## Usage Examples

### Code Review
**You:** "use chatgpt to review this Python function for optimization"
**System:** *Spawns agent, sends code to ChatGPT app, returns with optimization suggestions*

### Writing Assistance  
**You:** "ask chatgpt to help rewrite this email to sound more professional"
**System:** *Agent handles the rewriting task and returns polished version*

### Research Questions
**You:** "chatgpt help with understanding quantum computing basics"
**System:** *Agent gets comprehensive explanation from ChatGPT and reports back*

### Comparative Analysis
**You:** "get chatgpt's opinion on the pros and cons of React vs Vue"
**System:** *Agent submits question and returns detailed comparison*

## Technical Implementation

### Agent Spawning Command
```bash
sessions_spawn \
    agentId="main" \
    task="ChatGPT App Agent: [USER_REQUEST]" \
    cleanup="keep" \
    label="chatgpt-[short-description]"
```

### Peekaboo Commands Used
```bash
# App control
open -a ChatGPT
peekaboo app focus ChatGPT

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
peekaboo image --path screenshot.png --app ChatGPT
```

### Error Handling
- App not responding → Restart app
- UI elements missing → Take debug screenshot
- Rate limiting → Document timing and retry
- Authentication required → Request manual intervention

## File Organization

Outputs saved to: `~/clawd/media/chatgpt-agent/YYYY-MM-DD-HHMMSS/`
```
├── request.txt          # Original user request
├── response.md          # ChatGPT's response  
├── chatgpt-before.png   # Screenshot before submission
├── chatgpt-after.png    # Screenshot of response
└── metadata.yaml        # Timing and status info
```

## Integration with Main Chat

The skill allows seamless integration:
1. **You continue chatting** with main assistant
2. **Agent works in background** automating ChatGPT app
3. **Agent reports back** when complete
4. **No interruption** to your main conversation

## Advantages Over Direct ChatGPT

- **Compare perspectives** - Get both Claude (main) and ChatGPT opinions
- **Leverage ChatGPT features** - Browse, DALL-E, Canvas, Memory
- **Subscription optimization** - Use ChatGPT Plus features without API costs
- **Parallel processing** - ChatGPT works while you chat with Claude

## Requirements

- ChatGPT app installed and logged in
- Peekaboo automation permissions granted
- Agent spawning capability available

This skill transforms ChatGPT from a separate app into an integrated tool accessible via natural language within your main conversation.
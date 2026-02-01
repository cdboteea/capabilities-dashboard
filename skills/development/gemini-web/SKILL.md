# Gemini Web Skill

**Trigger:** "use gemini to..." | "ask gemini about..." | "gemini help with..." | "gemini research..."

Control Gemini via web browser through dedicated agent for any task.

## Purpose

Natural language access to Gemini web interface with agent automation:
- **"use gemini to research latest AI developments"**
- **"ask gemini about quantum computing applications"**
- **"gemini help with market analysis for electric vehicles"**
- **"gemini research the impact of climate change on agriculture"**

## How It Works

1. **Natural invocation** - Say "use gemini to [task]"
2. **Agent spawning** - Dedicated Gemini agent handles the work
3. **Browser automation** - Agent controls Gemini web via browser tools
4. **Research tool access** - Can use Gemini's Research tool for deep analysis
5. **Result delivery** - Agent reports back with response
6. **Continued chat** - You can keep working while agent runs

## Agent Automation Pattern

When triggered, spawns a dedicated agent with this task:
```
You are the Gemini Web automation agent.

Task: [USER_REQUEST]

Instructions:
1. Open Gemini: browser action=open targetUrl="https://gemini.google.com" profile=openclaw
2. Verify authentication (should be logged in as cdboteea@gmail.com)
3. Choose appropriate approach:
   - Standard chat for general questions
   - Research tool for deep research tasks
4. Submit user's request and wait for response
5. Capture complete response
6. Take screenshots for verification
7. Report back with Gemini's response

For research tasks:
- Click "Research" tool before submitting
- Wait for research plan generation
- Click "Launch Research" to execute
- Monitor progress and capture final report

Save outputs to: ~/clawd/media/gemini-agent/[timestamp]/
```

## Usage Examples

### Research Tasks (Deep Analysis)
**You:** "gemini research the current state of renewable energy adoption globally"
**System:** *Agent uses Research tool, conducts multi-source analysis, returns comprehensive report*

### Technical Questions
**You:** "ask gemini about the differences between GraphQL and REST APIs"
**System:** *Agent submits question to standard chat and returns comparison*

### Market Analysis
**You:** "use gemini to analyze emerging trends in fintech for 2026"
**System:** *Agent leverages Research tool for detailed market analysis*

### Creative Tasks
**You:** "gemini help with brainstorming innovative solutions for urban transportation"
**System:** *Agent facilitates brainstorming session and returns ideas*

## Technical Implementation

### Agent Spawning Command
```bash
sessions_spawn \
    agentId="main" \
    task="Gemini Web Agent: [USER_REQUEST]" \
    cleanup="keep" \
    label="gemini-[short-description]"
```

### Browser Automation Commands
```bash
# Access Gemini
browser action=open targetUrl="https://gemini.google.com" profile=openclaw
browser action=screenshot

# Standard Chat
browser action=act request='{"kind": "type", "text": "[USER_REQUEST]", "ref": "textbox"}'
browser action=act request='{"kind": "key", "key": "Enter"}'

# Research Tool Usage
browser action=act request='{"kind": "click", "ref": "Research"}'
browser action=act request='{"kind": "type", "text": "[USER_REQUEST]"}'
browser action=act request='{"kind": "key", "key": "Enter"}'
# Wait for plan generation
browser action=act request='{"kind": "wait", "timeMs": 45000}'
browser action=act request='{"kind": "click", "ref": "Launch Research"}'

# Response Capture
browser action=act request='{"kind": "wait", "timeMs": 120000}'  # Wait for completion
browser action=screenshot
# Copy response text (method varies by UI)
```

### Smart Tool Selection

The agent intelligently chooses between:

**Standard Chat** for:
- Quick questions
- Conversational requests  
- Creative tasks
- Code help

**Research Tool** for:
- "research" keyword in request
- Market analysis
- Comprehensive studies
- Multi-source investigations
- Complex analysis tasks

## File Organization

Outputs saved to: `~/clawd/media/gemini-agent/YYYY-MM-DD-HHMMSS/`
```
├── request.txt          # Original user request
├── response.md          # Gemini's response
├── gemini-before.png    # Screenshot before submission
├── gemini-progress.png  # Research progress (if applicable)
├── gemini-after.png     # Screenshot of final response
├── research-plan.txt    # Research plan (if Research tool used)
└── metadata.yaml        # Tool used, timing, status info
```

## Integration with Main Chat

The skill allows seamless integration:
1. **You continue chatting** with main assistant (Claude)
2. **Agent works in background** using Gemini web interface
3. **Agent reports back** when complete
4. **No interruption** to your main conversation

## Advantages of Gemini

- **Research Tool** - Deep, multi-source research capabilities
- **Real-time data** - Access to current information
- **Google integration** - Leverages Google's search and knowledge
- **Different perspective** - Alternative AI viewpoint to Claude
- **Specialized research** - Designed for comprehensive analysis

## Authentication & Persistence

- **Pre-authenticated** - Already logged in as cdboteea@gmail.com
- **Persistent session** - Login maintained across automations
- **Reliable access** - No re-authentication needed
- **Isolated profile** - Separate from personal Google account

## Use Case Guidelines

### Use Gemini for:
- **Research tasks** requiring multiple sources
- **Market analysis** and business intelligence  
- **Current events** and real-time information
- **Comparative perspective** to Claude's analysis
- **Google-centric** information needs

### Use Research Tool when:
- Request contains "research" keyword
- Need comprehensive multi-source analysis
- Require detailed citations and sources
- Want structured research report format
- Need current data and trends

### Use Standard Chat when:
- Quick questions or clarifications
- Creative or conversational requests
- Technical explanations
- Code-related help
- General knowledge queries

## Error Handling

- Authentication issues → Verify login status
- Research tool unavailable → Fall back to standard chat
- Timeout on research → Document and retry with shorter scope
- UI changes → Take screenshots and adapt automation
- Network issues → Retry with exponential backoff

## Requirements

- Browser automation capabilities
- Gemini access via openclaw profile (pre-authenticated)
- Agent spawning capability available

## Performance Notes

- **Research tool** typically takes 5-15 minutes for comprehensive analysis
- **Standard chat** responds in 30-60 seconds
- **Agent monitors progress** and provides updates
- **Timeout handling** prevents infinite waits

This skill transforms Gemini from a separate web service into an integrated research assistant accessible via natural language within your main conversation, with particular strength in deep research and analysis tasks.
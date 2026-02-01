# AI Platforms Skill

**Trigger:** "use [platform] to..." | "ask [platform] about..." | "[platform] help with..."

Universal dispatcher for ChatGPT, Claude App, and Gemini automation.

## Purpose

Natural language routing to any AI platform via dedicated agents:
- **"use chatgpt to analyze this code"** → ChatGPT app agent
- **"ask gemini about current market trends"** → Gemini web agent  
- **"claude app help with architecture design"** → Claude app agent
- **"gemini research renewable energy adoption"** → Gemini research tool

## Supported Platforms

### 1. ChatGPT App
**Keywords:** `chatgpt`, `chat gpt`, `gpt`
**Capabilities:**
- Conversational AI with GPT-4/5
- DALL-E image generation
- Canvas collaborative workspace
- Memory and personalization
- Browse capability

**Best for:**
- Code review and generation
- Creative writing
- Image generation requests
- Conversational tasks

### 2. Claude App  
**Keywords:** `claude app`, `claude desktop`
**Capabilities:**
- Latest Claude model (may differ from main chat)
- App-specific features
- Fresh conversation context
- Claude Pro subscription features

**Best for:**
- Technical analysis
- Alternative perspective on complex problems
- Model comparison tasks
- App-specific workflows

### 3. Gemini Web
**Keywords:** `gemini`, `google gemini`, `bard`
**Capabilities:**
- Research tool for deep analysis
- Real-time web information
- Multi-source research
- Google knowledge integration

**Best for:**
- Research tasks requiring multiple sources
- Current events and market analysis  
- Comprehensive studies
- Google-centric information

## Usage Patterns

### Direct Platform Requests
```
"use chatgpt to write a Python script for data processing"
"ask gemini about the latest developments in quantum computing"
"claude app help with debugging this algorithm"
"gemini research the impact of AI on healthcare"
```

### Automatic Platform Selection

The system can intelligently route based on task type:

**Research Tasks** → Gemini Research Tool
- "research the future of renewable energy"
- "analyze market trends in electric vehicles"
- "study the impact of climate change on agriculture"

**Creative/Conversational** → ChatGPT App
- "write a business plan for a startup"
- "create an image of a futuristic city"
- "help with creative writing"

**Technical Analysis** → Claude App
- "analyze this system architecture"
- "review this code for security issues"  
- "explain complex algorithms"

## Implementation

### Agent Spawning Logic

When a request is received, the system:

1. **Parse platform keyword** from natural language
2. **Determine appropriate agent** based on platform
3. **Spawn dedicated agent** with platform-specific task
4. **Route request** to correct automation (app vs web)
5. **Monitor execution** and handle responses

### Routing Examples

```bash
# ChatGPT requests
"use chatgpt to..." → sessions_spawn task="ChatGPT App Agent: [request]"

# Claude App requests  
"claude app help with..." → sessions_spawn task="Claude App Agent: [request]"

# Gemini requests
"gemini research..." → sessions_spawn task="Gemini Web Agent: [request]"
"ask gemini about..." → sessions_spawn task="Gemini Web Agent: [request]"
```

## Smart Features

### Context Awareness
- **Research keywords** → Automatically use Gemini Research tool
- **Image requests** → Route to ChatGPT for DALL-E
- **Code analysis** → Prefer Claude app for technical depth
- **Current events** → Route to Gemini for real-time data

### Parallel Execution
- **Multiple platforms** can work simultaneously
- **Main chat continues** uninterrupted  
- **Agents report back** when complete
- **No blocking** on long research tasks

### Error Handling & Fallbacks
- **Platform unavailable** → Suggest alternative or manual intervention
- **Authentication issues** → Document and request setup
- **App crashes** → Restart and retry
- **Rate limiting** → Queue request for later

## Output Management

### Unified Response Format
Each agent returns structured output:
```
🤖 [Platform] Response for: [Original Request]

[Platform's Response]

📁 Files saved to: ~/clawd/media/[platform]-agent/[timestamp]/
📸 Screenshots: [before/after/progress]
⏱️ Duration: [time taken]
✅ Status: [Success/Partial/Failed]
```

### File Organization
```
~/clawd/media/
├── chatgpt-agent/
│   └── YYYY-MM-DD-HHMMSS/
├── claude-agent/  
│   └── YYYY-MM-DD-HHMMSS/
└── gemini-agent/
    └── YYYY-MM-DD-HHMMSS/
```

## Advanced Usage

### Comparative Analysis
```
"use chatgpt to analyze this business model"
"ask gemini to research the same business model"  
"claude app help with evaluating both perspectives"
```

### Specialized Workflows
```
"gemini research current AI safety regulations"
"use chatgpt to create a compliance presentation based on that research"
"claude app help with technical implementation strategies"
```

### Sequential Tasks
```
"gemini research market opportunities in fintech"
"use that research to have chatgpt write a business proposal"
"claude app help with technical architecture for the proposal"
```

## Integration Benefits

### For Users
- **Natural language** access to all AI platforms
- **No app switching** required
- **Parallel execution** saves time
- **Unified interface** for all AI tools

### For Workflows  
- **Platform strengths** leveraged appropriately
- **Seamless automation** with minimal setup
- **Comprehensive coverage** of AI capabilities
- **Reduced cognitive load** in platform selection

## Requirements

### Technical
- ChatGPT app installed and authenticated
- Claude app installed and authenticated  
- Gemini web access via openclaw browser profile
- Peekaboo automation permissions
- Agent spawning capabilities

### Setup
- All three platform skills installed
- Authentication verified for all platforms
- Browser profile configured for Gemini
- File organization structure created

## Usage Examples in Practice

### Research Project
**You:** "gemini research the current state of quantum computing"
**System:** *Spawns Gemini agent, uses Research tool, returns comprehensive analysis*
**You:** "use chatgpt to explain quantum computing concepts in simple terms"
**System:** *Spawns ChatGPT agent, returns accessible explanation*
**You:** "claude app help with potential business applications"
**System:** *Spawns Claude agent, returns business analysis*

### Code Development
**You:** "claude app help with designing a microservices architecture"
**System:** *Returns architectural recommendations*
**You:** "use chatgpt to generate starter code for the user service"
**System:** *Returns implementation code*
**You:** "ask gemini about deployment best practices for microservices"
**System:** *Returns deployment guidance*

This skill transforms the three AI platforms from separate tools into an integrated ecosystem accessible through natural conversation.
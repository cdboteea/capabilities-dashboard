# Working Comparative Research Workflow

Based on our fail point analysis, here's the corrected approach:

## Usage

From the main OpenClaw session, run:
```
/research-compare "Your research topic here"
```

This will trigger the workflow below using the OpenClaw agent system.

## Implementation

### Step 1: Prompt Generation
```
sessions_spawn agentId="main" task="
Generate a comprehensive deep research prompt for topic: {TOPIC}

Requirements:
- Target 4000-6000 word output length
- Request executive summary, key findings, detailed analysis  
- Demand citations and numbered references
- Ask for multiple perspectives and current developments
- Include methodology section

Save the prompt to: ~/clawd/media/comparative-research/research-prompt-{timestamp}.txt

Format as a single, complete prompt ready to paste into any AI interface.
" cleanup="keep" label="prompt-gen"
```

### Step 2: ChatGPT App Automation  
```
sessions_spawn agentId="main" task="
Use Peekaboo to automate ChatGPT app for research task.

Instructions:
1. Launch ChatGPT app: open -a ChatGPT && sleep 3
2. Screenshot before: peekaboo image --path ~/clawd/media/comparative-research/chatgpt-before.png
3. Start new chat: peekaboo key 'cmd+n' && sleep 1  
4. Paste prompt from: ~/clawd/media/comparative-research/research-prompt-{timestamp}.txt
5. Submit: peekaboo key Return
6. Wait 90 seconds for response (research tasks take time)
7. Screenshot response: peekaboo image --path ~/clawd/media/comparative-research/chatgpt-response.png
8. Copy response: peekaboo click 'Copy' or use keyboard shortcut
9. Save to: ~/clawd/media/comparative-research/chatgpt-response-{timestamp}.md

Handle errors gracefully and document any issues encountered.
" cleanup="keep" label="chatgpt-automation"
```

### Step 3: Claude App Automation
```
sessions_spawn agentId="main" task="
Use Peekaboo to automate Claude app for research task.

Instructions:
1. Launch Claude app: open -a Claude && sleep 3
2. Screenshot before: peekaboo image --path ~/clawd/media/comparative-research/claude-before.png  
3. Start new chat: peekaboo key 'cmd+n' && sleep 1
4. Paste prompt from: ~/clawd/media/comparative-research/research-prompt-{timestamp}.txt
5. Submit: peekaboo key Return
6. Wait 90 seconds for response
7. Screenshot response: peekaboo image --path ~/clawd/media/comparative-research/claude-response.png
8. Copy response: peekaboo click 'Copy' 
9. Save to: ~/clawd/media/comparative-research/claude-response-{timestamp}.md

Document any authentication or permission issues.
" cleanup="keep" label="claude-automation"
```

### Step 4: Gemini Web Automation
```
sessions_spawn agentId="main" task="
Use browser automation for Gemini web interface research.

Instructions:
1. Open Gemini: browser action=open targetUrl='https://gemini.google.com' profile=openclaw
2. Screenshot: browser action=screenshot  
3. Check if sign-in needed - if so, sign in with cdboteea@gmail.com
4. Paste research prompt from: ~/clawd/media/comparative-research/research-prompt-{timestamp}.txt
5. Submit and wait for response (up to 120 seconds)
6. Screenshot final response: browser action=screenshot
7. Copy response text and save to: ~/clawd/media/comparative-research/gemini-response-{timestamp}.md

Document authentication steps and any rate limiting encountered.
" cleanup="keep" label="gemini-automation"  
```

### Step 5: Comparative Analysis
```
sessions_spawn agentId="main" task="
Analyze and compare the research outputs from all three AI platforms.

Input files:
- ChatGPT: ~/clawd/media/comparative-research/chatgpt-response-{timestamp}.md
- Claude: ~/clawd/media/comparative-research/claude-response-{timestamp}.md  
- Gemini: ~/clawd/media/comparative-research/gemini-response-{timestamp}.md

Analysis required:
1. Content depth and comprehensiveness comparison
2. Source quality and citation practices assessment
3. Unique insights identified per platform
4. Factual accuracy evaluation (cross-reference claims)
5. Structure and readability analysis
6. Platform-specific strengths and weaknesses
7. Use case recommendations (when to use which)

Generate detailed comparison report and save to:
~/clawd/media/comparative-research/comparison-analysis-{timestamp}.md

Include executive summary with key findings.
" cleanup="keep" label="comparison-analysis"
```

## Coordination Script

Create a simple coordinator that spawns these tasks in sequence:

```bash
# ~/clawd/scripts/run-comparative-research.sh
#!/bin/bash
TOPIC="$1"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "🔬 Starting comparative research: $TOPIC"
echo "Timestamp: $TIMESTAMP"

# Create output directory
mkdir -p ~/clawd/media/comparative-research

# Step 1: Generate prompt
echo "📝 Step 1: Generating research prompt..."
# sessions_spawn call for prompt generation

# Step 2: Wait and then spawn automation tasks
echo "🤖 Step 2: Starting platform automation..."  
# sessions_spawn calls for each platform

# Step 3: Analysis
echo "📊 Step 3: Generating analysis..."
# sessions_spawn call for comparison

echo "✅ Comparative research initiated. Monitor with: sessions_list"
```

## Key Improvements

1. **Uses sessions_spawn correctly** - No shell command issues
2. **Task-focused agents** - Each spawn handles one specific automation  
3. **Proper file management** - Consistent paths and naming
4. **Error handling** - Each task documents issues gracefully
5. **Incremental testing** - Can test each step independently

## Testing Approach

Test each step individually:
1. Test prompt generation first
2. Test ChatGPT automation with simple prompt
3. Test Claude automation with simple prompt  
4. Test Gemini web access and authentication
5. Test comparison analysis with sample outputs
6. Integrate into full workflow

This approach avoids the shell script pitfalls and leverages OpenClaw's agent system correctly.
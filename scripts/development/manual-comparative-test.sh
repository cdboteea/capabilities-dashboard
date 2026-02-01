#!/bin/bash
# manual-comparative-test.sh — Manual test of comparative research workflow
# Run this to test each component individually

set -euo pipefail

TOPIC="Current trends in AI coding assistants 2024-2026"
TEST_DIR="manual-test-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$TEST_DIR"

echo "🧪 Manual Comparative Research Test"
echo "Topic: $TOPIC"
echo "Directory: $TEST_DIR"
echo ""

# Create the research prompt first
echo "📝 Creating research prompt..."
cat > "$TEST_DIR/research-prompt.txt" << 'EOF'
Please conduct a comprehensive research analysis on: Current trends in AI coding assistants (2024-2026)

Provide a detailed report including:

**Executive Summary**
- 2-3 paragraph overview of current state and key developments

**Key Findings** (10 numbered points covering):
- Market leaders and adoption rates  
- Performance improvements and new capabilities
- Developer productivity impact data
- Integration patterns with IDEs and workflows
- Emerging trends and future directions
- Business impact and ROI metrics
- User satisfaction and pain points
- Technical limitations and breakthrough solutions
- Competitive landscape changes
- Regulatory and ethical considerations

**Detailed Analysis**
- Technology evolution from GitHub Copilot to current state
- Comparison of major platforms (Copilot, Cursor, Claude Dev, etc.)
- Performance benchmarks and productivity studies
- Integration ecosystem and developer adoption patterns
- Market size and growth projections

**Sources and Methodology**
- Include numbered citations [1], [2], etc.
- Assess source credibility
- Note any limitations in available data
- Explain research approach

Target: 4000-6000 words with comprehensive citations
Focus: 2024-2026 developments with relevant historical context
EOF

echo "✅ Research prompt created"

# Test ChatGPT app automation (with Peekaboo)
echo ""
echo "🤖 Testing ChatGPT App (manual steps):"
echo "1. Open ChatGPT app"
echo "2. Start new conversation" 
echo "3. Paste prompt from: $TEST_DIR/research-prompt.txt"
echo "4. Copy response to: $TEST_DIR/chatgpt-response.md"
echo ""
read -p "Press Enter after completing ChatGPT test..."

# Test Gemini web interface
echo ""
echo "🌟 Testing Gemini Web Interface (manual steps):"
echo "1. Open https://gemini.google.com in browser"
echo "2. Sign in with cdboteea@gmail.com if needed"
echo "3. Paste prompt from: $TEST_DIR/research-prompt.txt"  
echo "4. Copy response to: $TEST_DIR/gemini-response.md"
echo ""
read -p "Press Enter after completing Gemini test..."

# Test Claude app
echo ""
echo "🧠 Testing Claude App (manual steps):"
echo "1. Open Claude app"
echo "2. Start new conversation"
echo "3. Paste prompt from: $TEST_DIR/research-prompt.txt"
echo "4. Copy response to: $TEST_DIR/claude-response.md"
echo ""
read -p "Press Enter after completing Claude test..."

# Analysis
echo ""
echo "📊 Analysis Phase"
echo "Once you have all three responses, I can analyze them for comparison."

if [ -f "$TEST_DIR/chatgpt-response.md" ] || [ -f "$TEST_DIR/gemini-response.md" ] || [ -f "$TEST_DIR/claude-response.md" ]; then
    echo ""
    echo "Found response files! Generating comparison..."
    
    COMPARISON_PROMPT="Analyze and compare these AI research reports on '$TOPIC':

Files available:"
    
    if [ -f "$TEST_DIR/chatgpt-response.md" ]; then
        COMPARISON_PROMPT="$COMPARISON_PROMPT
- ChatGPT response: $(wc -w < "$TEST_DIR/chatgpt-response.md") words"
    fi
    
    if [ -f "$TEST_DIR/gemini-response.md" ]; then
        COMPARISON_PROMPT="$COMPARISON_PROMPT  
- Gemini response: $(wc -w < "$TEST_DIR/gemini-response.md") words"
    fi
    
    if [ -f "$TEST_DIR/claude-response.md" ]; then
        COMPARISON_PROMPT="$COMPARISON_PROMPT
- Claude response: $(wc -w < "$TEST_DIR/claude-response.md") words"
    fi
    
    COMPARISON_PROMPT="$COMPARISON_PROMPT

Please provide a detailed comparison covering:
1. Content depth and comprehensiveness
2. Source quality and citation practices  
3. Unique insights from each model
4. Accuracy and factual reliability
5. Structure and readability
6. Strengths and weaknesses
7. Overall recommendations for this type of research

Save this comparison analysis for review."
    
    echo "$COMPARISON_PROMPT" > "$TEST_DIR/comparison-prompt.txt"
    echo "✅ Comparison prompt created: $TEST_DIR/comparison-prompt.txt"
    echo ""
    echo "Run this prompt through your preferred model to get the final analysis."
else
    echo "⏳ No response files found yet. Complete the manual tests above first."
fi

echo ""
echo "📁 All files saved to: $TEST_DIR/"
echo "📋 Summary of test components:"
ls -la "$TEST_DIR/"
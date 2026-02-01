#!/bin/bash
# test-comparative-research.sh — Test the comparative research workflow with a simple topic

set -euo pipefail

echo "🧪 Testing Comparative Research Workflow"
echo "Topic: 'Current trends in AI coding assistants'"
echo ""

# Create test output directory
TEST_DIR="test-research-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$TEST_DIR"
echo "📁 Test directory: $TEST_DIR"

# Test 1: Verify ChatGPT app is available
echo ""
echo "🔍 Test 1: ChatGPT App Availability"
if [ -d "/Applications/ChatGPT.app" ]; then
    echo "✅ ChatGPT.app found"
else
    echo "❌ ChatGPT.app not found"
fi

# Test 2: Verify Claude app is available  
echo ""
echo "🔍 Test 2: Claude App Availability"
if [ -d "/Applications/Claude.app" ]; then
    echo "✅ Claude.app found"
else
    echo "❌ Claude.app not found"
fi

# Test 3: Check Peekaboo permissions
echo ""
echo "🔍 Test 3: Peekaboo Permissions"
PERMISSIONS=$(peekaboo permissions)
echo "$PERMISSIONS"

if echo "$PERMISSIONS" | grep -q "Screen Recording.*Granted"; then
    echo "✅ Screen recording permission granted"
else
    echo "⚠️  Screen recording permission needed for UI automation"
    echo "   Please grant in: System Settings > Privacy & Security > Screen Recording"
fi

if echo "$PERMISSIONS" | grep -q "Accessibility.*Granted"; then
    echo "✅ Accessibility permission granted"
else
    echo "❌ Accessibility permission needed"
fi

# Test 4: Browser access to Gemini
echo ""
echo "🔍 Test 4: Gemini Web Access"
GEMINI_TEST=$(web_fetch "https://gemini.google.com" | head -20 2>/dev/null || echo "Failed to fetch")
if echo "$GEMINI_TEST" | grep -q "Gemini"; then
    echo "✅ Gemini web interface accessible"
else
    echo "⚠️  Gemini web interface may need authentication"
fi

# Test 5: Create sample prompt generation
echo ""
echo "🔍 Test 5: Sample Prompt Generation"
cat > "$TEST_DIR/sample-prompt.md" << 'EOF'
# Deep Research Prompt: Current Trends in AI Coding Assistants

Please conduct a comprehensive analysis of the current trends in AI coding assistants. Provide:

## Executive Summary
A 2-3 paragraph overview of the current state and key developments.

## Key Findings
10 numbered key findings covering:
- Market leaders and adoption rates
- Performance improvements and capabilities
- Developer productivity impacts
- Integration patterns and workflows
- Emerging trends and future directions

## Detailed Analysis
In-depth examination of:
- Technology evolution (from Copilot to current state)
- Business impact and ROI data
- User satisfaction and pain points
- Competitive landscape analysis
- Technical limitations and solutions

## Sources and Citations
Please provide numbered citations for all major claims and include:
- Publication dates
- Source credibility assessment
- Direct quotes where relevant

## Methodology
Describe your research approach and any limitations.

Target length: 4000-6000 words
Focus on 2024-2026 developments with historical context where relevant.
EOF

echo "✅ Sample prompt created: $TEST_DIR/sample-prompt.md"

# Test 6: Agent availability
echo ""
echo "🔍 Test 6: Required Agents"
AVAILABLE_AGENTS=$(agents_list 2>/dev/null || echo "Error getting agents")
if echo "$AVAILABLE_AGENTS" | grep -q "operator"; then
    echo "✅ Operator agent available"
else
    echo "❌ Operator agent not available"
fi

if echo "$AVAILABLE_AGENTS" | grep -q "research"; then
    echo "✅ Research agent available"
else
    echo "❌ Research agent not available"
fi

# Summary
echo ""
echo "📋 Test Summary"
echo "==============="
echo "✅ = Ready to use"
echo "⚠️  = Needs setup"
echo "❌ = Missing requirement"
echo ""
echo "Next steps:"
echo "1. Grant screen recording permission to enable UI automation"
echo "2. Test manual authentication to Gemini web interface"
echo "3. Run full comparative research workflow"
echo ""
echo "Test files saved to: $TEST_DIR/"
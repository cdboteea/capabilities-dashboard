#!/bin/bash
# setup-comparative-research.sh — Complete setup for comparative research system
# Usage: ./setup-comparative-research.sh

set -euo pipefail

echo "🚀 Setting up Comparative Deep Research System"
echo "=============================================="
echo ""

# Step 1: Initialize database
echo "📊 Step 1: Initializing research database..."
~/clawd/scripts/init-research-database.sh

echo ""
echo "🔍 Step 2: Verifying system requirements..."

# Check required applications
MISSING_APPS=()
for app in "ChatGPT"; do
    if [ ! -d "/Applications/${app}.app" ]; then
        MISSING_APPS+=("$app")
    fi
done

if [ ${#MISSING_APPS[@]} -gt 0 ]; then
    echo "⚠️  Missing applications:"
    for app in "${MISSING_APPS[@]}"; do
        echo "   - $app.app"
    done
    echo ""
    echo "Please install missing applications before using the system."
else
    echo "✅ Required applications found"
fi

# Check Peekaboo permissions
echo ""
echo "🔑 Checking Peekaboo permissions..."
PERMS=$(peekaboo permissions)
echo "$PERMS"

if echo "$PERMS" | grep -q "Screen Recording.*Granted"; then
    echo "✅ Screen recording permission granted"
else
    echo "⚠️  Screen recording permission required"
    echo "   Grant in: System Settings > Privacy & Security > Screen Recording"
fi

# Check web access
echo ""
echo "🌐 Checking web access..."
if web_fetch "https://gemini.google.com" >/dev/null 2>&1; then
    echo "✅ Web access working"
else
    echo "⚠️  Web access issues detected"
fi

echo ""
echo "📝 Step 3: Creating sample research prompt..."

# Add a sample prompt to the database
~/clawd/scripts/add-research-prompt.sh \
    "AI Coding Assistants Trends 2024-2026" \
    "technology" \
    "Conduct comprehensive deep research analysis on current trends in AI coding assistants (2024-2026).

Research Requirements:
- Multi-source analysis: academic papers, industry reports, developer surveys, expert opinions
- Current market leaders and adoption patterns analysis
- Performance improvements and capability evolution
- Developer productivity impact assessment
- Integration ecosystem and workflow changes
- Business impact and ROI metrics
- Future trends and technology roadmap
- Challenges, limitations, and emerging solutions

Output Structure:
- Executive Summary (key findings and market overview)
- Market Analysis (leaders, adoption, growth metrics)
- Technology Evolution (capability improvements and innovations)  
- Developer Impact (productivity, satisfaction, workflow changes)
- Business Impact (ROI, cost savings, efficiency gains)
- Integration Ecosystem (IDE support, tool compatibility)
- Future Outlook (trends, predictions, roadmap)
- Challenges & Solutions (current limitations and fixes)
- Sources & References (comprehensive citations)

Provide extensive analysis with detailed citations and data. No length restrictions." \
    8

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📁 System Structure:"
echo "   Database: ~/clawd/comparative-research/database/"
echo "   Outputs:  ~/clawd/comparative-research/outputs/"
echo "   Templates: ~/clawd/comparative-research/templates/"
echo ""
echo "📋 Available Commands:"
echo "   ./run-comparative-research.sh \"topic\" [category]    # Run full research"
echo "   ./query-prompts.sh --topic \"AI\"                     # Find prompts"
echo "   ./add-research-prompt.sh \"topic\" \"cat\" \"prompt\"   # Add prompt"
echo ""
echo "🧪 Test the system:"
echo "   ./run-comparative-research.sh \"Current AI trends\" \"technology\""
echo ""
echo "📊 View existing prompts:"
echo "   ./query-prompts.sh"
echo ""
echo "⚠️  Requirements for full automation:"
echo "   - Grant screen recording permission if needed"
echo "   - Sign in to Gemini (cdboteea@gmail.com) in isolated browser"
echo "   - Ensure ChatGPT app is signed in"
echo ""
echo "✅ System ready for comparative deep research!"
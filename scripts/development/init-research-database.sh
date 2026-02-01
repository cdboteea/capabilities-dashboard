#!/bin/bash
# init-research-database.sh — Initialize comparative research database structure
# Usage: ./init-research-database.sh

set -euo pipefail

DB_DIR="$HOME/clawd/comparative-research/database"
OUTPUTS_DIR="$HOME/clawd/comparative-research/outputs"
TEMPLATES_DIR="$HOME/clawd/comparative-research/templates"

echo "🗃️ Initializing Comparative Research Database..."

# Create directory structure
mkdir -p "$DB_DIR"
mkdir -p "$OUTPUTS_DIR"
mkdir -p "$TEMPLATES_DIR"
mkdir -p "$HOME/clawd/comparative-research/documentation"

# Initialize database files
echo "📊 Creating database files..."

# Research Sessions Database
cat > "$DB_DIR/sessions.yaml" << 'EOF'
# Comparative Research Sessions Database
# Format: YAML for human readability and easy editing

sessions: []
# Example entry:
# - id: "session-20260201-143022"
#   created_at: "2026-02-01T14:30:22Z"
#   topic: "AI coding assistants trends 2024-2026"
#   topic_category: "technology"
#   research_prompt: "Comprehensive analysis of..."
#   status: "completed"  # in_progress, completed, failed, partial
#   total_duration_minutes: 18
#   completion_summary: "All platforms completed successfully"
#   outputs_directory: "2026-02-01-143022"
#   platforms_attempted: ["chatgpt", "gemini"]
#   platforms_successful: ["chatgpt", "gemini"] 
#   notes: "Both platforms completed successfully"
EOF

# Research Prompts Database
cat > "$DB_DIR/prompts.yaml" << 'EOF'
# Research Prompts Database
# Track generated prompts for reuse and effectiveness analysis

prompts: []
# Example entry:
# - id: "prompt-20260201-143022"
#   created_at: "2026-02-01T14:30:22Z"
#   topic: "AI coding assistants trends"
#   topic_category: "technology"
#   generated_prompt: |
#     Conduct comprehensive research analysis...
#   prompt_generator: "chatgpt"  # chatgpt, manual, claude, gemini
#   effectiveness_rating: 8  # 1-10 scale
#   usage_count: 3
#   successful_sessions: 2
#   platform_success_rates:
#     chatgpt: 1.0
#     gemini: 0.85
#   avg_output_quality: 8.5
#   notes: "Excellent for technology topics"
#   keywords: ["AI", "coding", "assistants", "trends"]
EOF

# Platform Metrics Database  
cat > "$DB_DIR/metrics.yaml" << 'EOF'
# Platform Performance Metrics Database
# Track detailed performance across platforms

platform_results: []
# Example entry:
# - id: "result-20260201-143022-chatgpt"
#   session_id: "session-20260201-143022"
#   platform: "chatgpt"
#   status: "completed"
#   submitted_at: "2026-02-01T14:32:15Z"
#   completed_at: "2026-02-01T14:47:33Z"
#   duration_minutes: 15
#   output_file_path: "2026-02-01-143022/chatgpt-response.md"
#   output_word_count: 7850
#   citation_count: 23
#   unique_insights_count: 8
#   response_quality_score: 9  # 1-10
#   factual_accuracy_score: 8  # 1-10
#   structure_quality_score: 9  # 1-10
#   error_notes: ""
#   screenshots: ["chatgpt-before.png", "chatgpt-progress-1435.png", "chatgpt-complete.png"]

summary_stats:
  total_sessions: 0
  total_prompts: 0
  platform_averages:
    chatgpt:
      avg_duration_minutes: 0
      avg_quality_score: 0
      success_rate: 0
    gemini:
      avg_duration_minutes: 0
      avg_quality_score: 0
      success_rate: 0
EOF

# Create prompt templates
cat > "$TEMPLATES_DIR/prompt-templates.md" << 'EOF'
# Research Prompt Templates

## Technology Topics
```
Conduct comprehensive deep research analysis on: {TOPIC}

Research Requirements:
- Multi-source analysis: academic papers, industry reports, expert opinions, recent developments
- Current state assessment and future trends identification
- Technical implementation details and practical applications
- Market analysis and adoption patterns
- Challenges, limitations, and breakthrough solutions
- Competitive landscape and key players

Output Structure:
- Executive Summary (key findings and implications)
- Current State Analysis (comprehensive overview)
- Technical Deep Dive (implementation details)
- Market & Adoption Analysis (trends and data)
- Future Outlook (predictions and roadmap)
- Challenges & Solutions (problems and emerging fixes)
- Sources & References (comprehensive citations)

Provide extensive analysis with detailed citations. No length restrictions.
```

## Business/Economic Topics
```
Conduct thorough business research analysis on: {TOPIC}

Research Scope:
- Market analysis and size assessment
- Key players and competitive dynamics
- Financial performance and business models
- Regulatory environment and policy impacts
- Consumer behavior and adoption trends
- Risk factors and opportunities
- Industry forecasts and growth projections

Analysis Framework:
- Market Overview (size, growth, segments)
- Competitive Analysis (key players, market share)
- Business Model Analysis (revenue streams, profitability)
- Regulatory Impact Assessment (current and pending)
- Consumer Insights (behavior, preferences, trends)
- Risk Assessment (challenges and mitigation)
- Future Outlook (predictions and scenarios)

Provide comprehensive analysis with financial data and market intelligence.
```

## Healthcare/Science Topics
```
Conduct scientific research analysis on: {TOPIC}

Research Parameters:
- Peer-reviewed academic sources and clinical studies
- Current scientific consensus and emerging research
- Methodology analysis and evidence quality assessment
- Clinical applications and real-world outcomes
- Regulatory status and approval processes
- Ethical considerations and societal implications
- Future research directions and potential breakthroughs

Scientific Framework:
- Current Scientific Understanding (established knowledge)
- Recent Research Developments (latest studies and findings)
- Clinical Evidence Assessment (trials, outcomes, efficacy)
- Methodology & Evidence Quality (study design analysis)
- Regulatory & Approval Status (FDA, international agencies)
- Ethical & Social Implications (broader impact assessment)
- Research Gaps & Future Directions (what's needed next)

Emphasize evidence-based analysis with rigorous source evaluation.
```
EOF

# Create analysis templates
cat > "$TEMPLATES_DIR/analysis-templates.md" << 'EOF'
# Comparative Analysis Templates

## Standard Comparative Analysis
```
# Comparative Deep Research Analysis: {TOPIC}

## Executive Summary
[2-3 paragraph synthesis of key findings across all platforms]

## Platform Performance Comparison

### Content Depth & Comprehensiveness
| Platform | Depth Score | Coverage Areas | Unique Insights |
|----------|-------------|----------------|-----------------|
| ChatGPT  | X/10        | [areas]        | [insights]      |
| Gemini   | X/10        | [areas]        | [insights]      |

### Source Quality & Citations
| Platform | Citation Count | Source Quality | Methodology |
|----------|----------------|----------------|-------------|
| ChatGPT  | X citations    | [assessment]   | [approach]  |
| Gemini   | X citations    | [assessment]   | [approach]  |

### Factual Consistency Analysis
- **Consistent Claims:** [claims verified across platforms]
- **Conflicting Information:** [discrepancies and analysis]
- **Platform-Specific Data:** [unique claims requiring verification]

### Structural Quality Assessment
- **Organization:** [how well each platform structured the response]
- **Readability:** [clarity and accessibility comparison]
- **Completeness:** [topic coverage gaps and strengths]

## Platform-Specific Strengths

### ChatGPT Strengths
- [specific areas where ChatGPT excelled]

### Gemini Research Tool Strengths  
- [specific areas where Gemini excelled]

## Use Case Recommendations
- **For [specific need]:** Use [platform] because [rationale]
- **For [specific need]:** Use [platform] because [rationale]

## Overall Assessment
[Summary of which platform provided the best overall research for this topic]
```
EOF

echo "✅ Database structure initialized!"
echo ""
echo "📁 Created directories:"
echo "   - $DB_DIR (database files)"
echo "   - $OUTPUTS_DIR (research outputs)"
echo "   - $TEMPLATES_DIR (prompt templates)"
echo ""
echo "📊 Database files created:"
echo "   - sessions.yaml (research sessions)"
echo "   - prompts.yaml (prompt database)"  
echo "   - metrics.yaml (platform metrics)"
echo ""
echo "📝 Template files created:"
echo "   - prompt-templates.md (research prompt templates)"
echo "   - analysis-templates.md (comparative analysis templates)"
echo ""
echo "🚀 Ready to start tracking comparative research!"
echo ""
echo "Next steps:"
echo "1. Run your first research session"
echo "2. Use add-research-prompt.sh to log prompts"
echo "3. Use update-session.sh to track results"
echo "4. Use query-database.sh to analyze patterns"
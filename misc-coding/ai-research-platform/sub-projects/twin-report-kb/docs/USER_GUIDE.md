# Twin-Report KB - User Guide

> Generate comprehensive research reports using multiple AI models for complete coverage

## Overview

The Twin-Report Knowledge Base is a dual AI research system that creates comprehensive reports on any topic using multiple models simultaneously. By comparing outputs from different AI models (like DeepSeek R1 and QwQ-32B), the system identifies gaps, overlaps, and contradictions to ensure thorough research coverage.

## Core Concept

```
Topic Creation → Twin Report Generation → Gap Analysis → Quality Control → Knowledge Base
```

### Why "Twin Reports"?

1. **Comprehensive Coverage**: Different models have different strengths and knowledge bases
2. **Gap Detection**: What one model misses, another might cover
3. **Quality Assurance**: Contradictions between models highlight areas needing verification
4. **Bias Reduction**: Multiple perspectives reduce single-model bias

## Getting Started

### 1. System Requirements

- Docker and Docker Compose
- Access to Mac Studio LLM endpoint
- 8GB+ RAM for basic operation
- PostgreSQL with pgvector extension

### 2. Start the Services

```bash
# From AI Research Platform root
cd sub-projects/twin-report-kb
docker-compose up -d

# Verify services are running
curl http://localhost:8100/health
```

### 3. Create Your First Research Topic

```bash
curl -X POST http://localhost:8100/topics \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Artificial Intelligence Ethics",
    "description": "Comprehensive analysis of ethical considerations in AI development, deployment, and governance",
    "generation_method": "local"
  }'
```

## Web Interface

The Twin-Report KB now includes a modern web interface accessible at `http://localhost:3000`.

### Dashboard Features

#### Service Health Monitoring
- **Real-time Status**: Live health indicators for all 4 backend services
- **Service Cards**: Visual status display with color-coded indicators
- **Quick Diagnostics**: Instant overview of system health

#### Document Upload
- **Drag & Drop Interface**: Modern file upload with visual feedback
- **Multiple Input Methods**: 
  - File upload (PDF, DOCX, XLSX, PPTX, TXT, HTML, MD)
  - Web URL processing
  - Google Docs integration
- **Real-time Validation**: File type and size checking (up to 100MB)
- **Progress Tracking**: Step-by-step processing indicators

#### Statistics Dashboard
- **Processing Metrics**: Document counts, success rates, average processing time
- **Recent Activity**: Last processed documents and their status
- **System Overview**: Quick access to all major functions

#### Interactive Features
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Toast Notifications**: Real-time feedback for all operations
- **Background Processing**: Non-blocking document upload and processing
- **Queue Management**: Visual indication of processing queue status

### Using the Web Interface

#### 1. Access the Dashboard
```bash
# Start the frontend service
cd sub-projects/twin-report-kb
docker-compose up frontend -d

# Open in browser
open http://localhost:3000
```

#### 2. Upload Documents
1. Navigate to the Upload page or use dashboard quick actions
2. Choose upload method:
   - **Drag & Drop**: Drop files onto the upload zone
   - **File Picker**: Click to browse and select files
   - **URL Input**: Enter web page or document URL
   - **Google Docs**: Provide Google Docs sharing URL

#### 3. Monitor Processing
- Watch real-time progress indicators
- View step-by-step processing status
- Get notifications when processing completes

#### 4. Check Service Health
- Dashboard displays live status for all services
- Click service cards for detailed health information
- Monitor system performance and connectivity

### Web vs API Access

| Feature | Web Interface | API Access |
|---------|---------------|------------|
| **Ease of Use** | Point & click, visual feedback | Command-line, scriptable |
| **File Upload** | Drag & drop, progress tracking | Programmatic upload |
| **Monitoring** | Real-time dashboard | JSON responses |
| **Best For** | Interactive use, demos | Automation, integration |

### 3. Create Your First Research Topic

```bash
curl -X POST http://localhost:8100/topics \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Artificial Intelligence Ethics",
    "description": "Comprehensive analysis of ethical considerations in AI development, deployment, and governance",
    "generation_method": "local"
  }'
```

## Research Workflows

### Basic Research Workflow

#### 1. Create a Topic
```bash
POST /topics
{
  "title": "Climate Change Adaptation Strategies",
  "description": "Analysis of adaptation methods for climate change impacts across different sectors",
  "generation_method": "local",
  "metadata": {
    "domain": "environmental",
    "priority": "high",
    "target_audience": "policy_makers"
  }
}
```

#### 2. Generate Twin Reports
```bash
POST /topics/{topic_id}/generate-twin-reports
{
  "models": ["deepseek-r1", "qwq-32b"],
  "max_words": 8000,
  "include_citations": true,
  "research_depth": "comprehensive"
}
```

#### 3. Monitor Progress
```bash
# Check report generation status
GET /topics/{topic_id}/articles

# View specific report
GET /articles/{article_id}
```

#### 4. Analyze Differences
```bash
# Get gap analysis between twin reports
GET /topics/{topic_id}/diff-analysis
```

### Advanced Research Workflow

#### Multi-Model Research
```bash
# Generate reports with multiple specialized models
POST /topics/{topic_id}/generate-twin-reports
{
  "models": ["deepseek-r1", "llama4-scout", "qwq-32b"],
  "max_words": 12000,
  "include_citations": true,
  "research_depth": "expert",
  "custom_instructions": "Focus on recent developments and practical applications"
}
```

#### Iterative Research
```bash
# Create follow-up topics based on gaps
POST /topics
{
  "title": "AI Ethics - Privacy Considerations",
  "description": "Deep dive into privacy aspects identified in main AI Ethics report",
  "parent_topic_id": "{parent_id}",
  "generation_method": "local"
}
```

## Available Models

### Primary Models

| Model | Best For | Parameters | Response Time |
|-------|----------|------------|---------------|
| **DeepSeek R1** | Complex reasoning, analysis | 671B | 60-120s |
| **QwQ-32B** | Quick insights, summaries | 32B | 15-30s |
| **Llama 4 Scout** | Domain expertise | 70B+ | 30-60s |
| **Llama 4 Maverick** | Creative research | 70B+ | 30-60s |

### Model Selection Guide

#### For Academic Research
- Primary: **DeepSeek R1** (thorough analysis)
- Secondary: **Llama 4 Scout** (domain expertise)

#### For Business Analysis
- Primary: **QwQ-32B** (efficient insights)
- Secondary: **DeepSeek R1** (complex strategy)

#### For Creative Projects
- Primary: **Llama 4 Maverick** (creative approach)
- Secondary: **DeepSeek R1** (analytical balance)

## Research Examples

### Example 1: Technology Analysis

```bash
# Topic: "Quantum Computing Applications"
curl -X POST http://localhost:8100/topics \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Quantum Computing Applications in Finance",
    "description": "Comprehensive analysis of current and potential quantum computing applications in financial services",
    "generation_method": "local",
    "metadata": {
      "domain": "technology",
      "sector": "finance",
      "timeframe": "2024-2030"
    }
  }'

# Generate specialized twin reports
curl -X POST http://localhost:8100/topics/1/generate-twin-reports \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["deepseek-r1", "llama4-scout"],
    "max_words": 10000,
    "include_citations": true,
    "custom_instructions": "Focus on practical applications, implementation challenges, and timeline predictions"
  }'
```

### Example 2: Policy Research

```bash
# Topic: "Renewable Energy Policy"
curl -X POST http://localhost:8100/topics \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Global Renewable Energy Policy Effectiveness",
    "description": "Comparative analysis of renewable energy policies across different countries and their effectiveness",
    "generation_method": "local",
    "metadata": {
      "domain": "policy",
      "geographic_scope": "global",
      "analysis_type": "comparative"
    }
  }'

# Generate comprehensive policy analysis
curl -X POST http://localhost:8100/topics/2/generate-twin-reports \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["deepseek-r1", "qwq-32b"],
    "max_words": 15000,
    "include_citations": true,
    "research_depth": "expert",
    "custom_instructions": "Include policy mechanisms, implementation outcomes, and recommendations for improvement"
  }'
```

## Understanding Results

### Report Structure

Each generated report includes:
- **Executive Summary**: Key findings and recommendations
- **Main Content**: Detailed analysis with sections
- **Citations**: Source references and evidence
- **Metadata**: Generation parameters and model information

### Gap Analysis

The system automatically identifies:
- **Coverage Gaps**: Topics covered by one model but not another
- **Depth Differences**: Areas where one model provides more detail
- **Contradictions**: Conflicting information between models
- **Unique Insights**: Novel perspectives from specific models

### Quality Indicators

- **Citation Density**: Number of references per section
- **Factual Accuracy**: Cross-model fact consistency
- **Completeness**: Coverage of topic dimensions
- **Coherence**: Logical flow and structure

## API Reference

### Core Endpoints

#### Topics Management
```http
GET    /topics                 # List all topics
POST   /topics                 # Create new topic
GET    /topics/{id}            # Get topic details
PUT    /topics/{id}            # Update topic
DELETE /topics/{id}            # Delete topic
```

#### Report Generation
```http
POST   /topics/{id}/generate-twin-reports    # Generate reports
GET    /topics/{id}/articles                 # Get topic articles
GET    /articles/{id}                        # Get specific article
```

#### Analysis
```http
GET    /topics/{id}/diff-analysis            # Get gap analysis
GET    /articles/{id}/quality                # Get quality metrics
```

### Request Examples

#### Create Topic with Metadata
```json
{
  "title": "AI in Healthcare",
  "description": "Comprehensive analysis of AI applications in healthcare delivery",
  "generation_method": "local",
  "metadata": {
    "domain": "healthcare",
    "priority": "high",
    "target_audience": "medical_professionals",
    "research_timeline": "6_months"
  }
}
```

#### Generate Reports with Custom Parameters
```json
{
  "models": ["deepseek-r1", "qwq-32b"],
  "max_words": 8000,
  "include_citations": true,
  "research_depth": "comprehensive",
  "custom_instructions": "Focus on clinical applications and regulatory considerations",
  "output_format": "academic",
  "language": "en"
}
```

## Tips and Best Practices

### Topic Creation
1. **Be Specific**: Narrow, well-defined topics produce better results
2. **Include Context**: Add relevant metadata for better model understanding
3. **Set Expectations**: Use description to guide model focus

### Model Selection
1. **Start Small**: Begin with QwQ-32B for quick insights
2. **Scale Up**: Use DeepSeek R1 for comprehensive analysis
3. **Combine Strengths**: Mix reasoning and domain models

### Report Review
1. **Read Both Reports**: Don't rely on a single model's output
2. **Check Contradictions**: Investigate conflicting information
3. **Verify Citations**: Confirm important facts independently

### System Optimization
1. **Monitor Resources**: Watch Mac Studio performance during generation
2. **Batch Requests**: Avoid overwhelming the system with simultaneous reports
3. **Regular Cleanup**: Archive old topics to maintain performance

## Troubleshooting

### Common Issues

#### Model Timeouts
- **Cause**: Large reports on resource-constrained system
- **Solution**: Reduce `max_words` or use smaller models

#### Missing Citations
- **Cause**: Model configuration or prompt issues
- **Solution**: Ensure `include_citations: true` and check model capabilities

#### Poor Gap Analysis
- **Cause**: Similar models producing similar outputs
- **Solution**: Use models with different architectures (e.g., DeepSeek R1 + Llama 4)

### Health Checks
```bash
# Check service health
curl http://localhost:8100/health

# Check database connectivity
curl http://localhost:8100/topics

# Check model availability
curl https://matiass-mac-studio.tail174e9b.ts.net/v1/models
```

## Advanced Features

### Custom Research Templates
Create reusable research templates for specific domains:

```json
{
  "template_name": "technology_analysis",
  "default_models": ["deepseek-r1", "llama4-scout"],
  "default_params": {
    "max_words": 8000,
    "include_citations": true,
    "custom_instructions": "Include technical specifications, market analysis, and future trends"
  }
}
```

### Batch Processing
Process multiple related topics:

```bash
# Create parent topic
POST /topics (parent_topic)

# Create subtopics
POST /topics (subtopic_1, parent_id)
POST /topics (subtopic_2, parent_id)

# Generate all reports
POST /topics/{parent_id}/generate-batch-reports
```

### Export and Integration
Export reports in various formats:

```bash
# Export as PDF
GET /articles/{id}/export?format=pdf

# Export as Markdown
GET /articles/{id}/export?format=markdown

# Export gap analysis
GET /topics/{id}/diff-analysis/export?format=json
```

---

**Need Help?** Check the [Technical Specs](../../docs/TECHNICAL_SPECS.md) for detailed API documentation and infrastructure details. 
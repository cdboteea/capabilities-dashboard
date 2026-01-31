# AI Research Platform - Evaluation Criteria & Assessment Metrics

> Comprehensive documentation of all quality scoring, assessment metrics, and evaluation criteria used across the platform

## Table of Contents

1. [Overview](#overview)
2. [Twin-Report KB Metrics](#twin-report-kb-metrics)
3. [Idea Database Metrics](#idea-database-metrics)
4. [Real-Time Intel Metrics](#real-time-intel-metrics)
5. [AI Browser Agent Metrics](#ai-browser-agent-metrics)
6. [Cross-Platform Metrics](#cross-platform-metrics)
7. [Configuration & Updates](#configuration--updates)
8. [Validation & Testing](#validation--testing)

---

## Overview

### Assessment Philosophy
All evaluation metrics in the AI Research Platform follow these principles:
- **Transparency**: Clear criteria and calculation methods
- **Configurability**: Adjustable thresholds and weights
- **Auditability**: Complete scoring history and rationale
- **Actionability**: Metrics drive specific improvement recommendations

### Scoring Standards
- **Scale**: 0.0 to 1.0 (decimal precision to 3 places)
- **Thresholds**: Documented minimum acceptable scores
- **Weights**: Configurable component weightings
- **Confidence**: All scores include confidence intervals where applicable

---

## Twin-Report KB Metrics

### 1. Diff Analysis Quality Scoring

**Location**: `sub-projects/twin-report-kb/docker/diff_worker/src/quality_scorer.py`

#### Overall Quality Score Formula
```
Overall Score = (Completeness × 0.30) + (Accuracy × 0.25) + (Usefulness × 0.25) + (Coherence × 0.20)
```

#### Component Metrics

##### 1.1 Completeness Score (Weight: 30%)
**Purpose**: Measures presence and depth of required analysis components

**Criteria**:
- **Required Components** (40% of completeness):
  - `summary` field present and non-empty
  - `gaps` array present
  - `overlaps` array present  
  - `contradictions` array present
  - `confidence_score` field present
  - Score: `(present_components / 5) × 0.4`

- **Summary Quality** (30% of completeness):
  - Basic summary (>50 chars): +0.2
  - Detailed summary (>150 chars): +0.1
  - Score cap: 0.3

- **Gap Analysis Depth** (30% of completeness):
  - Gaps identified: +0.2
  - Multiple gaps (>2): +0.1
  - Score cap: 0.3

**Thresholds**:
- Excellent: ≥0.9
- Good: ≥0.7
- Needs Improvement: <0.7

##### 1.2 Accuracy Score (Weight: 25%)
**Purpose**: Validates correctness of analysis using AI validation

**Criteria**:
- **Confidence Correlation** (60%): Uses diff result's confidence_score
- **AI Validation** (40%): Mac Studio LLM validates analysis quality
- **Combined Score**: `(confidence × 0.6) + (ai_validation × 0.4)`

**AI Validation Prompt**:
```
Evaluate the accuracy and quality of this diff analysis:
- Logical consistency of findings
- Appropriateness of confidence level  
- Quality of gap/overlap identification
- Overall analytical rigor
Rate 0-1 scale.
```

##### 1.3 Usefulness Score (Weight: 25%)
**Purpose**: Measures actionability and practical value of analysis

**Criteria**:
- **Actionable Gaps** (30%): Gaps with >20 characters of detail
- **Quality Overlaps** (20%): Overlaps with similarity metrics
- **Detailed Contradictions** (20%): Contradictions with >50 characters
- **Summary Insights** (30%): Presence of insight indicators
  - Keywords: "identified", "analysis", "shows", "reveals", "indicates"

##### 1.4 Coherence Score (Weight: 20%)
**Purpose**: Evaluates logical consistency and narrative flow

**Criteria**:
- **Summary-Findings Alignment** (70%):
  - Summary mentions gaps when gaps found: +0.3
  - Summary mentions overlaps when overlaps found: +0.2
  - Summary mentions contradictions when found: +0.2
- **Confidence-Findings Correlation** (20%):
  - High confidence (>0.8) + substantial findings (>2): +0.2
  - Low confidence (<0.4) + few findings (<2): +0.1
- **Metadata Consistency** (10%): Metadata field present: +0.1

#### Quality Levels
```yaml
excellent: ≥0.90
very_good: ≥0.80
good: ≥0.70
satisfactory: ≥0.60
needs_improvement: ≥0.50
poor: <0.50
```

### 2. Gap Analysis Priority Scoring

**Location**: `sub-projects/twin-report-kb/docker/diff_worker/src/gap_detector.py`

#### Priority Score Formula
```
Priority Score = Base Severity Score + Context Modifiers
```

**Severity Mapping**:
```yaml
high: 0.90
medium: 0.60
low: 0.30
```

**Context Modifiers** (Future Enhancement):
- Topic importance: ±0.1
- Research urgency: ±0.1
- Resource availability: ±0.05

### 3. Article Quality Scoring

**Location**: `sub-projects/twin-report-kb/docker/diff_worker/src/quality_scorer.py`

#### Overall Article Quality Formula
```
Article Quality = (Content × 0.30) + (Structure × 0.20) + (Citations × 0.25) + (Depth × 0.25)
```

##### 3.1 Content Quality (Weight: 30%)
**Criteria**:
- **Length Appropriateness** (30%):
  - Optimal (1,000-10,000 words): +0.3
  - Substantial (>500 words): +0.2
- **Sentence Variety** (20%):
  - Average sentence length 10-25 words: +0.2
- **Examples Present** (20%):
  - Keywords: "example", "instance", "case", "specifically", "such as"
  - Score: `min(example_count / 10, 0.2)`
- **Technical Depth** (30%):
  - Keywords: "analysis", "research", "study", "data", "evidence"
  - Score: `min(technical_count / 20, 0.3)`

##### 3.2 Structure Quality (Weight: 20%)
**Criteria**:
- **Header Organization** (40%):
  - ≥3 headers: +0.4
  - ≥1 header: +0.2
- **Paragraph Structure** (30%):
  - ≥5 paragraphs: +0.3
  - ≥3 paragraphs: +0.2
- **Logical Flow** (30%):
  - Transition words: "however", "therefore", "furthermore", "moreover", "consequently"
  - Score: `min(transition_count / 10, 0.3)`

##### 3.3 Citation Quality (Weight: 25%)
**Criteria**:
- **Citation Count** (40%):
  - ≥10 citations: +0.4
  - ≥5 citations: +0.3
  - ≥2 citations: +0.2
- **Source Diversity** (30%):
  - URLs + academic indicators: +0.3
  - Either URLs or academic: +0.2
- **In-text Integration** (30%):
  - Properly integrated citations: +0.3

##### 3.4 Depth Quality (Weight: 25%)
**Criteria**:
- **Analytical Language** (30%): "analyze", "examine", "investigate", "explore", "evaluate", "assess"
- **Evidence Usage** (30%): "evidence", "data", "research", "findings", "results", "shows"
- **Critical Thinking** (20%): "however", "although", "despite", "nevertheless", "on the other hand"
- **Explanations** (20%): "because", "since", "due to", "as a result", "therefore"

---

## Idea Database Metrics

### 1. Content Categorization Confidence

**Location**: `sub-projects/idea-database/services/email_processor/src/email_parser.py`

#### Category Scoring Algorithm
```python
# Keyword-based scoring
for category, keywords in CATEGORY_KEYWORDS.items():
    score = 0
    for keyword in keywords:
        score += content.count(keyword.lower())
        if keyword.lower() in subject.lower():
            score += 2  # Subject line bonus
    category_scores[category] = score

# Selection criteria
best_category = max(category_scores, key=category_scores.get)
confidence = min(category_scores[best_category] / 10, 1.0)  # Normalize to 0-1
```

**Categories & Keywords**:
```yaml
business_ideas:
  - startup, business, entrepreneur, market, revenue, product, service
dev_tools:
  - github, python, javascript, framework, library, api, development
research_papers:
  - paper, study, research, analysis, findings, methodology, academic
ai_implementations:
  - ai, machine learning, neural, model, algorithm, automation
industry_news:
  - news, announcement, company, industry, market, update, trend
reference_materials:
  - tutorial, guide, documentation, how-to, reference, manual
```

**Confidence Thresholds**:
```yaml
high_confidence: ≥0.70
medium_confidence: 0.40-0.69
low_confidence: <0.40
manual_review_required: <0.70
```

### 2. Entity Extraction Confidence

**Location**: Database schema and LLM processing

#### Entity Confidence Scoring
- **Exact Match**: 0.95-1.0
- **Fuzzy Match**: 0.70-0.94
- **Context-based**: 0.50-0.69
- **Uncertain**: <0.50

**Entity Types & Validation**:
```yaml
technology: Cross-reference with known tech databases
person: Validate against public profiles
company: Check against business registries
paper: Verify DOI/publication databases
repository: Validate GitHub/GitLab existence
concept: Context-based confidence only
```

### 3. Priority Scoring

**Location**: Database schema `priority_score` field

#### Priority Calculation
```python
priority_score = (
    category_relevance * 0.4 +
    content_quality * 0.3 +
    timeliness * 0.2 +
    source_credibility * 0.1
)
```

**Component Definitions**:
- **Category Relevance**: Alignment with user interests (0-1)
- **Content Quality**: Length, structure, information density (0-1)
- **Timeliness**: Recency and trending topics (0-1)
- **Source Credibility**: Sender reputation and domain authority (0-1)

---

## Real-Time Intel Metrics

### 1. Source Quality Evaluation

**Location**: `Original Specs/real_time_intel_spec.md`

#### Source Evaluation Schema
```json
{
  "accuracy_score": 0.85,        // 0-1 scale based on fact-checking
  "relevance_score": 0.92,       // 0-1 scale for financial content
  "timeliness_score": 0.78,      // Speed of breaking news coverage
  "geographic_coverage": ["US", "EU", "ASIA"],
  "update_frequency": "hourly",
  "source_type": "news|macro|research|regulatory"
}
```

#### Evaluation Criteria

##### 1.1 Accuracy Score
**Method**: LLM-based fact-checking against authoritative sources
**Calculation**:
- Cross-reference claims with verified databases
- Historical accuracy tracking
- Correction frequency analysis
- **Threshold**: Sources <0.60 flagged for retirement

##### 1.2 Relevance Score  
**Method**: Content alignment with financial/macro topics
**Factors**:
- Topic coverage percentage
- Keyword density analysis
- User engagement metrics
- **Threshold**: Sources <0.50 deprioritized

##### 1.3 Timeliness Score
**Method**: Breaking news speed comparison
**Metrics**:
- Time-to-publish vs. competitors
- Update frequency consistency
- Market hours coverage
- **Threshold**: Sources <0.40 marked as delayed

### 2. Sentiment Analysis Metrics

**Location**: `sub-projects/real-time-intel/docker/sentiment_analyzer/`

#### 2.1 Overall Sentiment Calculation

**Formula**:
```
Overall Sentiment = Base Model Score + Financial Context Adjustment
Final Score = Clamp(Overall Sentiment, -1.0, 1.0)
```

**Base Model Processing**:
```python
# MLX FinBERT Forward Pass
logits = finbert_model(input_ids, attention_mask)
probabilities = softmax(logits)  # [P(neg), P(neu), P(pos)]
sentiment_score = (probabilities[2] - probabilities[0])  # -1 to +1
confidence = max(probabilities) - (1/3)  # Above random chance
```

**Financial Context Adjustment**:
```python
# Financial lexicon weighting
positive_terms = ["profit", "growth", "bullish", "outperform", "beat estimates"]
negative_terms = ["loss", "decline", "bearish", "underperform", "miss estimates"]

financial_boost = (positive_count * 0.15) - (negative_count * 0.15)
financial_boost = clamp(financial_boost, -0.3, 0.3)
adjusted_sentiment = base_sentiment + financial_boost
```

**Quality Thresholds**:
```yaml
sentiment_confidence:
  high_confidence: ≥0.80
  medium_confidence: ≥0.60
  low_confidence: ≥0.40
  unreliable: <0.40

sentiment_strength:
  strong_positive: ≥0.60
  moderate_positive: 0.10 to 0.59
  neutral: -0.10 to 0.10
  moderate_negative: -0.59 to -0.10
  strong_negative: ≤-0.60
```

#### 2.2 Financial Sentiment Calculation

**Market-Specific Formula**:
```
Financial Sentiment = Base Financial Score × Market Context Multiplier
```

**Market Context Multipliers**:
```yaml
trading_hours:
  market_open: 1.0      # Normal impact
  pre_post_market: 0.8  # Reduced impact
  market_closed: 0.6    # Minimal impact

volatility_adjustment:
  vix_low: 1.0          # VIX < 15
  vix_moderate: 1.1     # VIX 15-25
  vix_high: 1.2         # VIX 25-35
  vix_extreme: 1.3      # VIX > 35
```

**Financial Sentiment Scale**:
```yaml
bullish: 0.7 to 1.0     # Price positive, growth expected
neutral: -0.7 to 0.7    # No clear direction, mixed signals
bearish: -1.0 to -0.7   # Price negative, decline expected
```

#### 2.3 Emotion Detection Metrics

**Multi-Emotion Classification**:
```python
emotion_scores = {
    'fear': calculate_emotion_score(content, fear_keywords, fear_model),
    'greed': calculate_emotion_score(content, greed_keywords, greed_model),
    'uncertainty': calculate_emotion_score(content, uncertainty_keywords, uncertainty_model),
    'confidence': calculate_emotion_score(content, confidence_keywords, confidence_model),
    'excitement': calculate_emotion_score(content, excitement_keywords, excitement_model),
    'anxiety': calculate_emotion_score(content, anxiety_keywords, anxiety_model)
}
```

**Emotion Keyword Patterns**:
```yaml
fear_indicators:
  - ["crash", "collapse", "panic", "plunge", "disaster"]
  - ["crisis", "risk", "danger", "threat", "concern"]
  - ["worry", "afraid", "scared", "terrified"]

greed_indicators:
  - ["boom", "surge", "skyrocket", "euphoria", "bubble"]
  - ["frenzy", "rush", "gold rush", "easy money"]
  - ["get rich", "opportunity", "windfall"]

uncertainty_indicators:
  - ["unclear", "uncertain", "unknown", "unpredictable"]
  - ["volatile", "mixed signals", "conflicting"]
  - ["ambiguous", "confused", "unsure"]
```

**Emotion Scoring Formula**:
```python
def calculate_emotion_score(content, keywords, model):
    # Keyword-based scoring (30%)
    keyword_score = count_emotion_keywords(content, keywords) / max(1, len(content.split()) / 100)
    
    # Model-based scoring (70%)
    model_score = emotion_model.predict(content, emotion_type)
    
    # Combined score
    combined_score = (keyword_score * 0.3) + (model_score * 0.7)
    
    # Context adjustment
    context_adjusted = apply_emotion_context(combined_score, emotion_type, content)
    
    return clamp(context_adjusted, 0.0, 1.0)
```

#### 2.4 Entity-Specific Sentiment

**Targeted Sentiment Extraction**:
```python
def calculate_entity_sentiment(content, entity):
    # Find entity mentions
    mentions = find_entity_mentions(content, entity)
    
    # Extract context windows (±50 words)
    context_windows = []
    for mention in mentions:
        start = max(0, mention.start - 250)  # ~50 words
        end = min(len(content), mention.end + 250)
        context_windows.append(content[start:end])
    
    # Calculate sentiment for each context
    context_sentiments = [calculate_base_sentiment(ctx) for ctx in context_windows]
    
    # Weighted average (recent mentions weighted higher)
    weights = [1.0 / (i + 1) for i in range(len(context_sentiments))]
    weighted_sentiment = sum(s * w for s, w in zip(context_sentiments, weights)) / sum(weights)
    
    # Calculate confidence (agreement between contexts)
    variance = calculate_variance([s for s in context_sentiments])
    confidence = max(0.1, 1.0 - variance)
    
    return EntitySentiment(
        entity_id=entity.id,
        score=weighted_sentiment,
        confidence=confidence,
        mention_count=len(mentions)
    )
```

#### 2.5 Temporal Sentiment Aggregation

**Time-Weighted Sentiment Trends**:
```python
def calculate_sentiment_trends(entity_id, time_window_hours=24):
    historical_sentiments = get_historical_sentiments(entity_id, time_window_hours)
    
    # Apply exponential decay weighting
    current_time = datetime.now()
    weighted_sentiments = []
    
    for record in historical_sentiments:
        age_hours = (current_time - record.timestamp).total_seconds() / 3600
        # Exponential decay: weight = e^(-age/half_life)
        half_life_hours = 6  # Sentiment half-life of 6 hours
        weight = math.exp(-age_hours / half_life_hours)
        weighted_sentiments.append({'sentiment': record.score, 'weight': weight})
    
    # Calculate weighted average
    total_weight = sum(item['weight'] for item in weighted_sentiments)
    current_sentiment = sum(item['sentiment'] * item['weight'] for item in weighted_sentiments) / total_weight
    
    # Calculate trend direction
    recent_avg = calculate_recent_average(weighted_sentiments, hours=2)
    older_avg = calculate_recent_average(weighted_sentiments, hours=12)
    
    trend_direction = "improving" if recent_avg > older_avg + 0.1 else \
                     "declining" if recent_avg < older_avg - 0.1 else "stable"
    
    return SentimentTrend(
        current_sentiment=current_sentiment,
        trend_direction=trend_direction,
        trend_strength=abs(recent_avg - older_avg),
        confidence=min(1.0, len(historical_sentiments) / 10)
    )
```

#### 2.6 Confidence Scoring

**Multi-Factor Confidence Calculation**:
```python
def calculate_sentiment_confidence(
    base_confidence: float,
    content_length: int,
    entity_mentions: int,
    source_quality: float,
    model_agreement: float
) -> float:
    # Content length factor (optimal 500-2000 words)
    length_factor = min(1.0, content_length / 1000) if content_length < 1000 else \
                   max(0.7, 1.0 - (content_length - 2000) / 5000)
    
    # Entity mention factor (optimal ~3 mentions)
    mention_factor = min(1.0, entity_mentions / 3)
    
    # Weighted combination
    confidence_factors = [
        (base_confidence, 0.4),      # 40% base model confidence
        (length_factor, 0.15),       # 15% content length
        (mention_factor, 0.15),      # 15% entity mentions
        (source_quality, 0.2),       # 20% source quality
        (model_agreement, 0.1)       # 10% model agreement
    ]
    
    final_confidence = sum(factor * weight for factor, weight in confidence_factors)
    return clamp(final_confidence, 0.1, 1.0)
```

#### 2.7 Performance Metrics

**Processing Performance**:
```yaml
sentiment_processing:
  speed_target: <100ms_per_article
  throughput_target: >1000_articles_per_minute
  accuracy_target: >85%_financial_content
  availability_target: 99.9%_uptime

model_performance:
  finbert_accuracy: >90%_financial_sentiment
  emotion_detection_accuracy: >80%_multi_emotion
  entity_sentiment_accuracy: >85%_targeted_analysis
  confidence_correlation: >0.8_predicted_vs_actual
```

**Quality Thresholds**:
```yaml
sentiment_quality_gates:
  excellent: ≥0.90
  good: ≥0.75
  acceptable: ≥0.60
  needs_review: ≥0.40
  poor: <0.40

processing_alerts:
  low_confidence_threshold: <0.5
  high_variance_threshold: >0.3
  processing_delay_threshold: >200ms
  model_disagreement_threshold: >0.4
```

### 3. Content Processing Quality

#### Alert Generation Metrics
```yaml
alert_quality:
  relevance_accuracy: manual_review_sample
  false_positive_rate: <10%
  response_time: alert_to_decision_tracking
  portfolio_impact_correlation: alert_severity_vs_price_movement
  sentiment_alert_accuracy: sentiment_change_vs_price_movement
```

#### Performance Targets
```yaml
source_availability: >95%
content_processing_speed: >events_per_minute
alert_generation_rate: alerts_per_hour_by_severity
sentiment_analysis_accuracy: confidence_score_distributions
entity_sentiment_tracking: sentiment_trends_by_company
emotion_detection_rate: emotions_detected_per_article
```

---

## AI Browser Agent Metrics

### 1. Response Quality Validation

**Location**: `Original Specs/ai_browser_agent_spec.md`

#### Quality Assessment Framework
```python
quality_checks = {
    'completeness': check_response_completeness(response, prompt),
    'relevance': check_relevance_score(response, prompt),
    'coherence': check_response_coherence(response),
    'error_indicators': detect_error_messages(response),
    'truncation': check_for_truncation(response)
}

overall_score = calculate_quality_score(quality_checks)
# Threshold: overall_score < 0.7 triggers error recovery
```

#### Component Metrics

##### 1.1 Completeness Score
- **Full Response**: All requested elements present
- **Partial Response**: Some elements missing
- **Incomplete**: Major components missing

##### 1.2 Relevance Score
- **Highly Relevant**: Direct answer to prompt
- **Somewhat Relevant**: Related but not precise
- **Irrelevant**: Off-topic or generic

##### 1.3 Coherence Score
- **Coherent**: Logical flow and consistency
- **Partially Coherent**: Some logical issues
- **Incoherent**: Contradictory or nonsensical

### 2. Automation Accuracy Metrics

#### Success Rate Tracking
```yaml
session_success_rate: successful_completions / total_attempts
provider_reliability: uptime_percentage_by_provider
prompt_effectiveness: success_rate_by_prompt_type
error_recovery_rate: successful_recoveries / total_errors
```

---

## Cross-Platform Metrics

### 1. LLM Performance Metrics

#### Response Quality Standards
```yaml
citation_accuracy: >95%
response_latency: <3_seconds
token_generation_speed: tokens_per_second
error_rate: <5%
confidence_correlation: predicted_vs_actual_quality
```

#### Model-Specific Thresholds
```yaml
deepseek_r1:
  reasoning_accuracy: >90%
  response_time: <5s
  confidence_threshold: >0.8

qwen_3_72b:
  multilingual_accuracy: >85%
  response_time: <3s
  confidence_threshold: >0.75

llama_4_scout:
  domain_expertise: >95%
  response_time: <4s
  confidence_threshold: >0.85
```

### 2. System Health Metrics

#### Infrastructure Performance
```yaml
database_performance:
  query_response_time: <100ms
  connection_pool_utilization: <80%
  transaction_success_rate: >99%

vector_database:
  search_latency: <200ms
  similarity_accuracy: >90%
  index_freshness: <1_hour

storage_systems:
  minio_availability: >99.9%
  chroma_response_time: <500ms
  postgres_uptime: >99.5%
```

---

## Configuration & Updates

### 1. Metric Configuration Files

#### Primary Configuration
```yaml
# config/evaluation_criteria.yml
diff_analysis:
  weights:
    completeness: 0.30
    accuracy: 0.25
    usefulness: 0.25
    coherence: 0.20
  thresholds:
    excellent: 0.90
    good: 0.70
    needs_improvement: 0.50

article_quality:
  weights:
    content: 0.30
    structure: 0.20
    citations: 0.25
    depth: 0.25
  word_count_optimal: [1000, 10000]
  citation_count_minimum: 2

idea_database:
  confidence_thresholds:
    high: 0.70
    medium: 0.40
    manual_review: 0.70
  category_keywords:
    business_ideas: [startup, business, entrepreneur]
    # ... full keyword lists
```

#### Environment-Specific Overrides
```yaml
# config/evaluation_criteria.dev.yml
diff_analysis:
  thresholds:
    excellent: 0.80  # Lower bar for development
    good: 0.60
    needs_improvement: 0.40
```

### 2. Update Procedures

#### 2.1 Metric Weight Adjustments
```bash
# 1. Update configuration file
vim config/evaluation_criteria.yml

# 2. Validate configuration
python scripts/validate_config.py

# 3. Deploy with gradual rollout
docker-compose restart diff_worker

# 4. Monitor impact
python scripts/monitor_metric_changes.py --days 7
```

#### 2.2 Threshold Modifications
```python
# scripts/update_thresholds.py
def update_quality_thresholds(component, new_thresholds):
    """
    Update quality thresholds with validation and rollback capability
    """
    # Validate new thresholds
    validate_threshold_logic(new_thresholds)
    
    # Backup current configuration
    backup_config()
    
    # Apply changes
    update_config_file(component, new_thresholds)
    
    # Test with sample data
    test_results = run_threshold_tests()
    
    if test_results.success_rate < 0.95:
        rollback_config()
        raise ThresholdUpdateError("New thresholds failed validation")
    
    # Deploy to production
    deploy_config_changes()
```

#### 2.3 New Metric Addition
```python
# Example: Adding semantic similarity metric
def add_semantic_similarity_metric():
    """
    Add new semantic similarity metric to diff analysis
    """
    # 1. Define metric calculation
    def calculate_semantic_similarity(text1, text2):
        # Implementation here
        return similarity_score
    
    # 2. Update quality scorer
    # Add to QualityScorer class
    
    # 3. Update configuration
    # Add weights and thresholds
    
    # 4. Update database schema if needed
    # Add new fields for storing metric
    
    # 5. Update documentation
    # Document new metric in this file
```

### 3. A/B Testing Framework

#### Metric Comparison Testing
```python
# scripts/ab_test_metrics.py
class MetricABTest:
    def __init__(self, metric_name, control_config, test_config):
        self.metric_name = metric_name
        self.control_config = control_config
        self.test_config = test_config
    
    def run_test(self, sample_size=1000, duration_days=7):
        """
        Run A/B test comparing metric configurations
        """
        # Split traffic between control and test
        # Measure outcomes
        # Statistical significance testing
        # Generate recommendation report
```

---

## Validation & Testing

### 1. Metric Validation Pipeline

#### Automated Testing
```python
# tests/test_evaluation_metrics.py
class TestEvaluationMetrics:
    def test_diff_quality_scoring(self):
        """Test diff quality scoring with known good/bad examples"""
        
    def test_article_quality_bounds(self):
        """Ensure all quality scores are within 0-1 bounds"""
        
    def test_confidence_correlation(self):
        """Validate confidence scores correlate with manual assessment"""
        
    def test_threshold_consistency(self):
        """Ensure thresholds are logically consistent"""
```

#### Manual Validation Process
```yaml
validation_schedule:
  weekly: sample_validation_50_items
  monthly: comprehensive_review_200_items
  quarterly: full_metric_audit_external_review

validation_criteria:
  inter_rater_reliability: >0.80
  metric_human_correlation: >0.75
  false_positive_rate: <15%
  false_negative_rate: <10%
```

### 2. Performance Monitoring

#### Metric Drift Detection
```python
# scripts/monitor_metric_drift.py
def detect_metric_drift(metric_name, window_days=30):
    """
    Detect significant changes in metric distributions
    """
    # Calculate rolling statistics
    # Compare to historical baselines
    # Alert on significant deviations
    # Generate drift analysis report
```

#### Quality Regression Testing
```bash
# Daily regression test
python scripts/quality_regression_test.py \
  --metrics all \
  --sample-size 100 \
  --baseline-period 30d \
  --alert-threshold 0.05
```

### 3. Continuous Improvement

#### Feedback Integration
```python
# User feedback on quality assessments
class QualityFeedback:
    def collect_user_feedback(self, assessment_id, user_rating, comments):
        """Collect user feedback on quality assessments"""
        
    def analyze_feedback_patterns(self):
        """Identify systematic issues in quality scoring"""
        
    def recommend_metric_adjustments(self):
        """Suggest metric improvements based on feedback"""
```

#### Metric Evolution Tracking
```yaml
# Track metric performance over time
metric_history:
  version: 1.0
  introduced: 2025-01-22
  performance_baseline: 0.85
  improvement_targets:
    - increase_accuracy_to_0.90_by_2025-03-01
    - reduce_false_positives_to_5%_by_2025-02-15
  deprecation_criteria:
    - accuracy_below_0.70_for_30_days
    - user_satisfaction_below_0.60
```

---

## Summary

This documentation provides:

1. **Complete Coverage**: All assessment metrics across all platform components
2. **Clear Criteria**: Specific calculation methods and thresholds
3. **Update Procedures**: Safe methods for modifying evaluation criteria
4. **Validation Framework**: Testing and monitoring for metric quality
5. **Configuration Management**: Centralized configuration with environment overrides

### Key Principles for Metric Management

1. **Document Everything**: All metrics must be documented here
2. **Test Changes**: Never deploy metric changes without validation
3. **Monitor Impact**: Track metric performance after changes
4. **User Feedback**: Incorporate user assessment of metric quality
5. **Continuous Improvement**: Regular review and refinement of criteria

### Next Steps

1. Implement centralized configuration system
2. Build A/B testing framework for metric changes
3. Create automated validation pipeline
4. Establish regular metric review schedule
5. Integrate user feedback collection system 
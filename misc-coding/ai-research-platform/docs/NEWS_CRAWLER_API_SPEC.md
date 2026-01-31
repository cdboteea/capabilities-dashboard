# Real-Time Intel News Crawler - Enhanced API Specification
## Web Actions AI Agent Compatible Design

> **Purpose**: Enterprise-grade API enabling seamless swapping between crawling implementations  
> **Current**: Browser-Use + Playwright (Sprint 0)  
> **Future**: Web Actions AI Agent with ADK Orchestrator integration  
> **Architecture**: Production-ready with job management, real-time monitoring, and quality scoring

---

## 🏗️ Enhanced Architecture Integration

### Web Actions AI Agent Integration
```
Real-Time Intel → News Crawler API → Web Actions AI Agent
                                   ↓
                              ADK Orchestrator (9011)
                                   ↓
                              Mac Studio LLM (Qwen-3-72B)
                                   ↓
                              MCP Bridge (9020)
                                   ↓
                              Chrome Automation
```

### Multi-Implementation Architecture
```
┌─────────────────────────────────────────────┐
│         Real-Time Intel Platform            │
├─────────────────────────────────────────────┤
│         Enhanced News Crawler API           │
├─────────────────────────────────────────────┤
│  Implementation Layer (Hot-Swappable)       │
│  ├── Browser-Use + Playwright              │
│  ├── Web Actions AI Agent                  │
│  ├── Traditional Scrapy                    │
│  └── Hybrid AI-Enhanced Crawler            │
└─────────────────────────────────────────────┘
```

## 📋 Enhanced API Specification

### Base URL Structure
```
Production:  http://news-crawler:8300/v1
Development: http://localhost:8300/v1
Docker:      http://news-crawler:8300/v1
```

### Authentication & Headers
```http
Authorization: Bearer {crawler_api_key}
X-API-Version: 1.0
X-Implementation: web_actions_ai|browser_use|scrapy|custom
Content-Type: application/json
```

## 🔌 Core API Endpoints

### 1. Enhanced Job Management

#### **Submit Crawl Job**
```http
POST /v1/crawl/jobs
```

**Request Body:**
```json
{
  "job_id": "optional-uuid",
  "source_config": {
    "type": "news_site|search_query|rss_feed|financial_source",
    "target": "https://reuters.com/finance|Apple earnings Q4|feed_url",
    "parameters": {
      "max_articles": 50,
      "date_range": {
        "start": "2025-01-22T00:00:00Z",
        "end": "2025-01-27T23:59:59Z"
      },
      "categories": ["earnings", "mergers", "market_news"],
      "languages": ["en"],
      "financial_focus": true,
      "include_sentiment": true,
      "entity_extraction": true,
      "full_text": true
    }
  },
  "crawl_config": {
    "implementation": "web_actions_ai|browser_use|scrapy",
    "priority": "low|normal|high|urgent",
    "retry_policy": {
      "max_retries": 3,
      "backoff_factor": 1.5,
      "timeout": 60
    },
    "extraction_rules": {
      "title": "h1, .headline, [data-title]",
      "content": ".article-body, .content, main",
      "author": ".author, .byline, [data-author]",
      "date": ".date, .published, time[datetime]",
      "tags": ".tags, .categories, .keywords"
    },
    "ai_enhancement": {
      "content_analysis": true,
      "entity_extraction": true,
      "sentiment_scoring": true,
      "financial_metrics": true
    }
  },
  "callback_config": {
    "webhook_url": "http://event-processor:8303/events/webhook",
    "real_time_updates": true,
    "quality_threshold": 0.8
  }
}
```

**Response:**
```json
{
  "job_id": "crawl_20250122_reuters_finance",
  "status": "submitted",
  "estimated_duration": "00:08:30",
  "estimated_articles": 45,
  "created_at": "2025-01-22T10:30:00Z",
  "implementation": "web_actions_ai",
  "tracking_url": "/v1/crawl/jobs/crawl_20250122_reuters_finance/status",
  "websocket_url": "ws://news-crawler:8300/v1/crawl/jobs/crawl_20250122_reuters_finance/stream"
}
```

#### **Get Job Status**
```http
GET /v1/crawl/jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "crawl_20250122_reuters_finance",
  "status": "running|completed|failed|cancelled",
  "progress": {
    "articles_found": 34,
    "articles_extracted": 28,
    "articles_processed": 25,
    "percentage_complete": 73.5,
    "current_step": "ai_content_analysis",
    "estimated_remaining": "00:02:15",
    "current_url": "https://reuters.com/finance/page-3"
  },
  "execution_details": {
    "implementation": "web_actions_ai",
    "start_time": "2025-01-22T10:30:00Z",
    "duration": "00:06:15",
    "pages_visited": 15,
    "ai_tasks_completed": 12,
    "errors_encountered": 1,
    "retry_attempts": 1,
    "adk_orchestrator_status": "healthy"
  },
  "quality_metrics": {
    "average_quality_score": 89.3,
    "content_extraction_success": 92.8,
    "entity_extraction_accuracy": 94.5,
    "sentiment_confidence": 87.2
  }
}
```

#### **Get Job Results**
```http
GET /v1/crawl/jobs/{job_id}/results
```

**Query Parameters:**
```
?format=json|csv
&include=metadata|content|sentiment|entities
&page=1&limit=50
&sort_by=date|quality_score|relevance
&filter_by=category,sentiment,quality_threshold
```

**Response:**
```json
{
  "job_id": "crawl_20250122_reuters_finance",
  "total_articles": 34,
  "page": 1,
  "limit": 50,
  "articles": [
    {
      "article_id": "art_reuters_001",
      "url": "https://reuters.com/finance/apple-earnings-q4",
      "title": "Apple Reports Record Q4 Earnings, Beats Estimates",
      "content": "Apple Inc (AAPL.O) reported record fourth-quarter earnings...",
      "summary": "AI-generated: Apple exceeded Q4 expectations with strong iPhone sales and services revenue growth.",
      "metadata": {
        "author": "John Smith",
        "published_date": "2025-01-22T09:15:00Z",
        "category": "earnings",
        "language": "en",
        "word_count": 1247,
        "reading_time": 5,
        "source_reliability": 0.95
      },
      "extraction_info": {
        "quality_score": 94.5,
        "confidence": 0.98,
        "extraction_method": "ai_enhanced",
        "validation_status": "verified",
        "extracted_at": "2025-01-22T10:35:12Z",
        "ai_processing_time": 2.3
      },
      "financial_analysis": {
        "sentiment": {
          "polarity": 0.75,
          "subjectivity": 0.45,
          "classification": "positive",
          "confidence": 0.89
        },
        "entities": [
          {
            "type": "company",
            "value": "Apple Inc",
            "ticker": "AAPL",
            "confidence": 0.99
          },
          {
            "type": "financial_metric", 
            "value": "earnings",
            "amount": "record",
            "period": "Q4",
            "confidence": 0.94
          }
        ],
        "market_impact": {
          "relevance_score": 0.92,
          "urgency": "high",
          "affected_sectors": ["technology", "consumer_electronics"]
        }
      },
      "media": {
        "images": [
          {
            "url": "https://reuters.com/image-apple-hq.jpg",
            "alt_text": "Apple headquarters",
            "caption": "Apple corporate headquarters in Cupertino"
          }
        ]
      }
    }
  ],
  "extraction_summary": {
    "total_processing_time": "00:08:45",
    "average_quality_score": 89.3,
    "success_rate": 94.1,
    "implementation_used": "web_actions_ai",
    "ai_enhancement_applied": true,
    "financial_entities_extracted": 127,
    "sentiment_analysis_completed": true
  }
}
```

### 2. Real-Time Monitoring & WebSockets

#### **WebSocket Connection**
```
WS /v1/crawl/jobs/{job_id}/stream
```

**Message Types:**
```json
{
  "type": "progress_update",
  "job_id": "crawl_20250122_reuters_finance",
  "timestamp": "2025-01-22T10:35:00Z",
  "data": {
    "articles_processed": 18,
    "current_url": "https://reuters.com/finance/page-3",
    "status": "ai_content_analysis",
    "quality_score_avg": 91.2,
    "estimated_remaining": "00:03:15"
  }
}

{
  "type": "article_extracted",
  "job_id": "crawl_20250122_reuters_finance",
  "timestamp": "2025-01-22T10:35:15Z",
  "data": {
    "article_id": "art_reuters_018",
    "title": "Tesla Announces New Manufacturing Partnership",
    "quality_score": 92.3,
    "sentiment": "positive",
    "entities_found": ["Tesla", "TSLA", "manufacturing"],
    "extraction_method": "ai_enhanced"
  }
}

{
  "type": "ai_reasoning",
  "job_id": "crawl_20250122_reuters_finance", 
  "timestamp": "2025-01-22T10:35:30Z",
  "data": {
    "step": "content_extraction",
    "reasoning": "Detected paywall, switching to archive.today lookup",
    "confidence": 0.87,
    "alternative_strategy": "rss_feed_fallback"
  }
}
```

### 3. Implementation Management

#### **List Available Implementations**
```http
GET /v1/implementations
```

**Response:**
```json
{
  "implementations": [
    {
      "id": "web_actions_ai",
      "name": "Web Actions AI Agent",
      "version": "3.0.0",
      "status": "available",
      "capabilities": {
        "javascript_rendering": true,
        "human_like_interaction": true,
        "captcha_solving": true,
        "paywall_bypass": true,
        "session_management": true,
        "ai_content_analysis": true,
        "entity_extraction": true,
        "sentiment_analysis": true,
        "screenshot_capture": true,
        "reasoning_logs": true
      },
      "performance": {
        "accuracy": 95.8,
        "speed": "medium",
        "resource_usage": "high",
        "cost_per_article": 0.08,
        "quality_score_avg": 92.1
      },
      "integration": {
        "adk_endpoint": "http://localhost:9011",
        "mcp_bridge": "http://localhost:9020",
        "llm_endpoint": "mac_studio_qwen_3_72b"
      }
    },
    {
      "id": "browser_use",
      "name": "Browser-Use + Playwright",
      "version": "1.2.0", 
      "status": "available",
      "capabilities": {
        "javascript_rendering": true,
        "human_like_interaction": false,
        "captcha_solving": false,
        "paywall_bypass": false,
        "session_management": true,
        "ai_content_analysis": false,
        "entity_extraction": false,
        "sentiment_analysis": false,
        "screenshot_capture": true,
        "reasoning_logs": false
      },
      "performance": {
        "accuracy": 82.5,
        "speed": "fast",
        "resource_usage": "medium",
        "cost_per_article": 0.02,
        "quality_score_avg": 78.3
      }
    }
  ],
  "current_default": "browser_use",
  "switching_enabled": true,
  "hot_swap_supported": true
}
```

#### **Switch Implementation**
```http
POST /v1/implementations/switch
```

**Request:**
```json
{
  "target_implementation": "web_actions_ai",
  "migration_strategy": "gradual|immediate",
  "test_job_first": true,
  "fallback_on_failure": true
}
```

**Response:**
```json
{
  "switch_id": "switch_20250122_103000",
  "status": "in_progress",
  "current_implementation": "browser_use",
  "target_implementation": "web_actions_ai",
  "estimated_downtime": "00:02:30",
  "test_job_submitted": true,
  "rollback_available": true
}
```

## 🔌 Web Actions AI Agent Integration

### Implementation Adapter
```python
class WebActionsAINewsAdapter:
    """
    Enhanced adapter for Real-Time Intel integration with Web Actions AI Agent
    """
    
    def __init__(self, adk_endpoint="http://localhost:9011", 
                 mcp_bridge="http://localhost:9020"):
        self.adk_endpoint = adk_endpoint
        self.mcp_bridge = mcp_bridge
        self.active_jobs = {}
        self.quality_threshold = 0.8
    
    async def submit_crawl_job(self, job_config):
        """Convert Real-Time Intel crawl job to AI Agent task"""
        
        # Enhanced AI task conversion for financial news
        ai_task = await self.convert_to_financial_ai_task(job_config)
        
        # Submit to ADK Orchestrator with Real-Time Intel context
        response = await self.post_ai_task_with_context(ai_task)
        
        # Track job with enhanced monitoring
        job_id = response['task_id']
        self.active_jobs[job_id] = {
            'status': 'running',
            'config': job_config,
            'ai_task_id': job_id,
            'start_time': datetime.utcnow(),
            'quality_metrics': {
                'articles_processed': 0,
                'quality_scores': [],
                'entity_extraction_count': 0,
                'sentiment_analysis_count': 0
            }
        }
        
        return job_id
    
    async def convert_to_financial_ai_task(self, job_config):
        """Convert to AI task optimized for financial news crawling"""
        
        source = job_config['source_config']
        params = source['parameters']
        ai_config = job_config['crawl_config'].get('ai_enhancement', {})
        
        if source['type'] == 'news_site':
            task_description = f"""
            FINANCIAL NEWS CRAWLING MISSION:
            
            Target: {source['target']}
            Objective: Extract {params['max_articles']} high-quality financial articles
            Categories: {params['categories']}
            Date Range: {params['date_range']['start']} to {params['date_range']['end']}
            
            ENHANCED EXTRACTION PROTOCOL:
            1. Navigate systematically through financial news sections
            2. Identify and extract complete article content
            3. Perform entity extraction for companies, tickers, financial metrics
            4. Conduct sentiment analysis with financial context
            5. Extract author, publication date, and metadata
            6. Capture relevant images and charts
            7. Handle paywalls and subscription prompts intelligently
            8. Verify article relevance to financial markets
            
            QUALITY REQUIREMENTS:
            - Minimum quality score: {job_config.get('callback_config', {}).get('quality_threshold', 0.8)}
            - Full content extraction required
            - Entity extraction confidence > 0.85
            - Sentiment analysis required for market impact
            
            AI REASONING:
            - Document decision-making process
            - Explain content relevance scoring
            - Note any obstacles and resolution strategies
            - Provide confidence scores for all extractions
            """
        
        elif source['type'] == 'search_query':
            task_description = f"""
            FINANCIAL NEWS SEARCH MISSION:
            
            Search Query: "{source['target']}"
            Target Articles: {params['max_articles']}
            
            SEARCH STRATEGY:
            1. Google Finance and Google News search
            2. Bloomberg, Reuters, CNBC, MarketWatch direct searches
            3. Yahoo Finance and Seeking Alpha exploration
            4. Navigate to source articles for full content extraction
            5. Verify relevance to search terms
            6. Extract comprehensive financial data and context
            
            FINANCIAL FOCUS:
            - Prioritize breaking news and earnings reports
            - Extract stock tickers, price movements, analyst ratings
            - Identify market impact and sector implications
            - Capture quantitative data (revenue, profit, guidance)
            """
        
        return {
            "task": task_description,
            "parameters": {
                "max_duration": 1800,  # 30 minutes
                "screenshot_frequency": "on_page_change_and_completion",
                "retry_on_failure": True,
                "human_like_behavior": True,
                "quality_validation": True,
                "financial_context": True,
                "entity_extraction": ai_config.get('entity_extraction', True),
                "sentiment_analysis": ai_config.get('sentiment_scoring', True)
            },
            "real_time_intel_context": {
                "integration_type": "financial_news_crawler",
                "callback_endpoint": job_config['callback_config']['webhook_url'],
                "quality_threshold": job_config['callback_config'].get('quality_threshold', 0.8),
                "event_processor_integration": True
            }
        }
    
    async def get_enhanced_job_status(self, job_id):
        """Get comprehensive status with AI reasoning and quality metrics"""
        
        # Get detailed status from ADK
        ai_status = await self.get_ai_task_detailed_status(job_id)
        
        # Get reasoning logs
        reasoning_logs = await self.get_ai_reasoning_logs(job_id)
        
        # Calculate quality metrics
        quality_metrics = await self.calculate_quality_metrics(job_id)
        
        return self.convert_to_enhanced_status(ai_status, reasoning_logs, quality_metrics, job_id)
    
    async def get_financial_results(self, job_id):
        """Get results with enhanced financial analysis"""
        
        # Get raw AI results
        ai_results = await self.get_ai_task_results(job_id)
        
        # Parse with financial context
        articles = await self.parse_financial_articles(ai_results)
        
        # Enhance with market analysis
        enhanced_articles = await self.enhance_with_market_context(articles)
        
        return {
            'job_id': job_id,
            'total_articles': len(enhanced_articles),
            'articles': enhanced_articles,
            'extraction_summary': {
                'implementation_used': 'web_actions_ai',
                'total_processing_time': ai_results.get('execution_time'),
                'success_rate': self.calculate_success_rate(ai_results),
                'ai_enhancement_applied': True,
                'financial_entities_extracted': sum(len(a.get('financial_analysis', {}).get('entities', [])) for a in enhanced_articles),
                'sentiment_analysis_completed': all('sentiment' in a.get('financial_analysis', {}) for a in enhanced_articles),
                'average_quality_score': sum(a.get('extraction_info', {}).get('quality_score', 0) for a in enhanced_articles) / len(enhanced_articles) if enhanced_articles else 0
            }
        }
```

## 🧪 Enhanced Testing Framework

### Real-Time Intel Specific Tests
```python
class TestRealTimeIntelCrawler:
    """Tests specific to Real-Time Intel financial news requirements"""
    
    async def test_financial_source_crawling(self):
        """Test crawling major financial news sources"""
        
        sources = [
            "https://reuters.com/finance",
            "https://bloomberg.com/markets", 
            "https://cnbc.com/markets",
            "https://marketwatch.com"
        ]
        
        for source in sources:
            job_config = {
                'source_config': {
                    'type': 'news_site',
                    'target': source,
                    'parameters': {
                        'max_articles': 10,
                        'categories': ['earnings', 'markets'],
                        'financial_focus': True
                    }
                },
                'crawl_config': {
                    'implementation': 'web_actions_ai',
                    'ai_enhancement': {
                        'entity_extraction': True,
                        'sentiment_scoring': True,
                        'financial_metrics': True
                    }
                }
            }
            
            response = await self.api.submit_crawl_job(job_config)
            assert response['status'] == 'submitted'
            
            # Wait for completion and verify results
            job_id = response['job_id']
            results = await self.wait_for_completion(job_id)
            
            # Validate financial content quality
            assert results['extraction_summary']['financial_entities_extracted'] > 0
            assert results['extraction_summary']['sentiment_analysis_completed'] == True
            assert results['extraction_summary']['average_quality_score'] > 0.8
    
    async def test_ai_agent_reasoning(self):
        """Test AI agent reasoning and decision tracking"""
        
        job_config = self.get_complex_financial_job_config()
        job_id = await self.api.submit_crawl_job(job_config)
        
        # Monitor reasoning via WebSocket
        reasoning_logs = []
        async with websockets.connect(f"ws://localhost:8300/v1/crawl/jobs/{job_id}/stream") as ws:
            async for message in ws:
                data = json.loads(message)
                if data['type'] == 'ai_reasoning':
                    reasoning_logs.append(data['data'])
                elif data['type'] == 'progress_update' and data['data']['status'] == 'completed':
                    break
        
        # Validate reasoning quality
        assert len(reasoning_logs) > 0
        assert all('reasoning' in log for log in reasoning_logs)
        assert all('confidence' in log for log in reasoning_logs)
    
    async def test_implementation_hot_swap(self):
        """Test switching from Browser-Use to Web Actions AI Agent"""
        
        # Start with Browser-Use
        implementations = await self.api.get_implementations()
        assert implementations['current_default'] == 'browser_use'
        
        # Submit test job with Browser-Use
        browser_job = await self.submit_test_job('browser_use')
        browser_results = await self.wait_for_completion(browser_job)
        
        # Switch to Web Actions AI
        switch_response = await self.api.switch_implementation('web_actions_ai')
        await self.wait_for_switch_completion(switch_response['switch_id'])
        
        # Submit same job with AI Agent
        ai_job = await self.submit_test_job('web_actions_ai')
        ai_results = await self.wait_for_completion(ai_job)
        
        # Compare results - AI should have higher quality
        assert ai_results['extraction_summary']['average_quality_score'] > browser_results['extraction_summary']['average_quality_score']
        assert ai_results['extraction_summary']['financial_entities_extracted'] > browser_results['extraction_summary']['financial_entities_extracted']
```

This enhanced API specification fully integrates your Web Actions AI Agent architecture with our Real-Time Intel system, providing enterprise-grade job management, real-time monitoring, quality scoring, and seamless implementation swapping capabilities. The design ensures maximum flexibility while maintaining the financial intelligence focus required for the Real-Time Intel platform. 
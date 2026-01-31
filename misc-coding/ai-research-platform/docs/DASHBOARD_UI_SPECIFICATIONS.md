# AI Research Platform - Dashboard UI Specifications

> **Version:** 2025-01-22 v1.0  
> **Status:** Design Complete - Ready for Implementation  
> **Architecture:** Independent Multi-Dashboard Platform  

---

## 🏗️ **Platform Architecture Overview**

### **Multi-Dashboard Strategy**
The AI Research Platform uses independent dashboards optimized for different use cases and user workflows:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 AI Research Platform - Multi-Dashboard Architecture                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Port 3000: 📈 Real-Time Intel Dashboard    (Trading & Market Intelligence)     │
│ Port 3001: 📄 Twin-Report KB Dashboard     (Document Analysis & Comparison)    │
│ Port 3002: 📚 Idea Database Dashboard      (Knowledge Management & Research)   │
│ Port 3003: 🤖 AI Browser Agent Dashboard   (Automation & Workflows) [Future]  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### **Cross-Platform Navigation**
Unified header component shared across all dashboards:
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 AI Research Platform                                          👤 User Menu  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [📈 Real-Time Intel] [📄 Twin Reports] [📚 Ideas] [🤖 Browser Agent] [⚙️ Admin] │
│      3000              3001            3002         3003           3004         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📈 **Real-Time Intel Dashboard (Port 3000)**

### **Purpose & Users**
- **Primary Use**: Continuous market monitoring during trading hours
- **Target Users**: Active traders, portfolio managers, financial analysts
- **Usage Pattern**: All-day monitoring, real-time alerts, quick decision making

### **Layout Architecture**

#### **Header Bar** (Fixed Top, 64px)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 AI Research Platform    Portfolio: Tech Growth (+2.4%)    🔔 3 alerts       │
│                                                                                 │
│ [Search Global...]  📊 Dashboard  📰 News  💼 Portfolio  ⚙️ Settings           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### **Sidebar Navigation** (280px, collapsible)
- **Overview**: Live Feed, Portfolio, Alerts
- **Intelligence**: News Stream, Event Analysis, Sentiment, Sources
- **Analytics**: Performance, Risk Metrics, Price Data, Holdings
- **Notifications**: Alert Rules, Channels, History
- **Macro**: Economic Data (Future integration)

#### **Main Content Areas**

##### **Top Metrics Row** (3 responsive cards)
1. **Portfolio Overview**: Holdings Router + Portfolio Analytics integration
2. **Live Intelligence**: News Crawler + Event Processor status
3. **Alert Status**: Alert Engine dashboard

##### **Real-Time News Feed** (Full width, scrollable)
- WebSocket streaming from News Crawler (8300)
- Sentiment visualization from Sentiment Analyzer (8304)
- Portfolio relevance from Holdings Router (8305)
- Priority classification from Event Processor (8303)

##### **Analytics Section** (2-column layout)
- **Left**: Portfolio Analytics + Price Fetcher integration
- **Right**: Market Intelligence + Source Manager data

### **Key Features**
- **Real-time WebSocket connections** to all 8 backend services
- **Sentiment-based color coding** for news and events
- **Portfolio impact scoring** for all market events
- **Multi-channel alert management** interface
- **Interactive performance charts** with news overlays

### **Technical Stack**
- **Frontend**: React 18 + TypeScript
- **Styling**: Tailwind CSS + Headless UI
- **Real-time**: WebSocket connections
- **State**: Zustand for reactive state management
- **Charts**: Recharts for financial visualizations

---

## 📄 **Twin-Report KB Dashboard (Port 3001)**

### **Purpose & Users**
- **Primary Use**: Periodic document analysis and comparison
- **Target Users**: Research analysts, content reviewers, knowledge workers
- **Usage Pattern**: Weekly/monthly analysis sessions, batch processing

### **Current Status**
✅ **Complete FastAPI + Bootstrap interface** already implemented

### **Existing Features**
- Multi-format document upload (PDF, DOCX, URLs, Google Docs)
- Service health monitoring with real-time status
- 4-stage processing pipeline visualization
- Results viewer with quality scoring
- Batch processing capabilities

### **Enhancement Recommendations**

#### **Improved Dashboard Home**
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 📄 Twin-Report KB - Document Analysis Platform    🧠 Platform Navigation       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Service Health: ✅ All Systems Operational                                     │
│ [Document Parser] [Topic Manager] [Quality Controller] [Diff Worker]           │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Analysis Workflow:                                                              │
│ [Upload Document] → [Parse Content] → [Categorize] → [Quality Check] → [Results] │
│                                                                                 │
│ Recent Completions:                                                             │
│ • "Market Analysis Q4.pdf" - High Quality (Score: 0.94) - 2 gaps found       │
│ • "Research Methodology.docx" - Medium Quality (Score: 0.78) - Ready          │
│ • "Competitor Analysis.xlsx" - High Quality (Score: 0.91) - 1 contradiction   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### **Enhanced Results Viewer**
- Overall quality score with component breakdown
- Gap analysis with priority ranking
- Content summary and topic extraction
- Extracted entities and relationships
- Action items and recommendations

### **Integration Points**
- Cross-reference with Idea Database for related concepts
- Export results to Real-Time Intel for market analysis
- Shared authentication and user preferences

---

## 📚 **Idea Database Dashboard (Port 3002)**

### **Purpose & Users**
- **Primary Use**: Daily knowledge management and research workflow
- **Target Users**: Researchers, knowledge workers, individual contributors
- **Usage Pattern**: Multiple daily interactions, continuous knowledge building

### **Layout Architecture**

#### **Header Bar** (Fixed Top, 64px)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 📚 Idea Database    Gmail Sync: ✅ 15m ago    📧 3 unprocessed    🔔 2 alerts  │
│                                                                                 │
│ [🔍 Search Everything...]  📝 Add Idea  📊 Reports  📈 Analytics  ⚙️ Settings  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### **Navigation Tabs**
- **📋 Feed**: Main knowledge stream
- **🔍 Search**: Advanced semantic search
- **📊 Reports**: AI-powered research reports
- **📈 Analytics**: Knowledge insights and trends
- **⚙️ Settings**: Gmail integration and preferences

#### **Sidebar Filter Panel** (280px, collapsible)
```
┌─────────────────────────┐
│ 📂 CATEGORIES           │
│ ☑️ Personal Thoughts    │
│ ☑️ Dev Tools & Libs     │
│ ☑️ Research Papers      │
│ ☑️ AI Implementations   │
│ ☑️ Industry News        │
│ ☑️ Reference Materials  │
│                         │
│ 🏷️ ENTITIES            │
│ 🔍 [Search entities...] │
│ • Python (23)           │
│ • FastAPI (12)          │
│ • OpenAI (18)           │
│                         │
│ 📅 TIME FILTERS         │
│ ○ Today (5)             │
│ ○ This Week (23)        │
│ ● All Time (250)        │
│                         │
│ 📊 PROCESSING           │
│ • Processed: 247        │
│ • Pending: 3            │
│ • Failed: 0             │
└─────────────────────────┘
```

### **Core Features**

#### **Knowledge Feed**
- Gmail-sourced ideas with AI processing
- Sentiment analysis and priority scoring
- Entity extraction and relationship mapping
- URL archiving and content extraction
- Attachment processing (PDFs, documents)

#### **Advanced Search**
- Semantic search across all content
- Entity-based filtering
- Time-based queries
- Content type filtering
- Similarity-based recommendations

#### **AI-Powered Reports** (Key Innovation)

##### **Report Types**
1. **🔬 Further Research Report**: Identify unexplored areas and research gaps
2. **📋 Ideas Summary**: Weekly/monthly digest of collected ideas
3. **🎯 Exploration Priorities**: AI-ranked research opportunities
4. **🔗 Connection Analysis**: Discover relationships between ideas
5. **📈 Trend Analysis**: Emerging patterns and themes
6. **💡 Innovation Opportunities**: Gap analysis and market potential
7. **🏷️ Entity Deep Dive**: Focus on specific technologies or concepts
8. **📝 Custom Research Brief**: Tailored analysis based on user criteria

##### **Report Generation Interface**
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🔬 Generate Further Research Report                                [← Back]    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Report Configuration:                                                           │
│                                                                                 │
│ Report Focus:                                                                   │
│ ● Specific Categories: [☑️ Dev Tools] [☑️ AI Implementations] [☐ Papers]      │
│                                                                                 │
│ Analysis Depth:                                                                 │
│ ● Comprehensive Analysis (15-25 pages, 30 min generation)                     │
│                                                                                 │
│ Research Questions to Address:                                                  │
│ ☑️ What concepts need deeper exploration?                                      │
│ ☑️ Which ideas have implementation potential?                                  │
│ ☑️ What are the knowledge gaps in my research?                                │
│ ☑️ Which technologies should I prioritize learning?                           │
│                                                                                 │
│ [🚀 Generate Report] [💾 Save Template] [📋 Preview Outline]                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

##### **Sample Report Output**
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🔬 Further Research Report: "AI Implementation Opportunities"                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 📊 EXECUTIVE SUMMARY                                                           │
│ Based on analysis of 47 AI-related ideas, this report identifies 12 high-     │
│ priority research opportunities and 8 immediate implementation candidates.     │
│                                                                                 │
│ 🎯 HIGH-PRIORITY RESEARCH OPPORTUNITIES                                       │
│ 1. Real-Time AI Portfolio Analysis (3 related ideas)                          │
│    Research Questions: How to integrate Mac Studio LLM with market data?      │
│    Next Steps: Prototype sentiment analysis pipeline                          │
│                                                                                 │
│ 💡 IMMEDIATE IMPLEMENTATION CANDIDATES                                         │
│ 1. Cursor Workflow Optimization (Ready to implement)                          │
│ 2. Documentation AI Assistant (Prototype ready)                               │
│                                                                                 │
│ 🔗 CROSS-IDEA CONNECTIONS DISCOVERED                                          │
│ • "FastAPI async patterns" ↔ "Real-time WebSocket implementation"            │
│ • "Portfolio analytics" ↔ "Risk assessment algorithms"                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### **Automated Reporting**
- Scheduled report generation (weekly, monthly, quarterly)
- Email delivery of reports
- Trigger-based reports (e.g., when 10+ new ideas collected)
- Custom report templates

### **Technical Implementation**
- **Backend**: FastAPI with Gmail API integration
- **AI Processing**: Mac Studio LLM for analysis and report generation
- **Database**: PostgreSQL + Chroma vector database
- **Frontend**: React with advanced search and reporting interfaces

### Enhanced Knowledge Graph Help Modal (July 2025)
- The Knowledge Graph dashboard now features a user-friendly help modal, fully aligned with the central taxonomy reference. All node and edge types are explained in plain language, with examples and visual cues, accessible directly from the graph UI.

### Dynamic Knowledge Graph Taxonomy (July 2025)
- The dashboard now features a Taxonomy Management section in Settings, allowing users to add, edit, or delete node and edge types.
- The Knowledge Graph legend and help modal are fully dynamic and always reflect the current taxonomy.
- All changes are instantly reflected in the graph, UI, and LLM extraction pipeline.

---

## 🔗 **Cross-Platform Integration**

### **Unified Navigation Implementation**

#### **Option 1: Shared Header Component** (Recommended)
```javascript
// shared-navigation.js
class PlatformNavigation {
  constructor(currentService) {
    this.currentService = currentService;
    this.services = {
      'real-time-intel': { name: 'Real-Time Intel', port: 3000, icon: '📈' },
      'twin-reports': { name: 'Twin Reports', port: 3001, icon: '📄' },
      'ideas': { name: 'Ideas', port: 3002, icon: '📚' },
      'browser-agent': { name: 'Browser Agent', port: 3003, icon: '🤖' }
    };
  }

  render() {
    return `
      <nav class="platform-nav">
        <div class="nav-brand">🧠 AI Research Platform</div>
        <div class="nav-services">
          ${Object.entries(this.services).map(([key, service]) => `
            <a href="http://localhost:${service.port}" 
               class="nav-link ${key === this.currentService ? 'active' : ''}">
              ${service.icon} ${service.name}
            </a>
          `).join('')}
        </div>
      </nav>
    `;
  }
}
```

#### **Cross-Service Communication**
```javascript
// platform-api.js
class PlatformAPI {
  // Get ideas related to current portfolio holdings
  async getRelatedIdeas(symbols) {
    return fetch('http://localhost:3002/api/search', {
      method: 'POST',
      body: JSON.stringify({ entities: symbols, category: 'dev-tools' })
    });
  }

  // Get Twin-Report analysis for news article
  async analyzeDocument(content) {
    return fetch('http://localhost:3001/api/analyze', {
      method: 'POST', 
      body: JSON.stringify({ content, analysis_depth: 'quick' })
    });
  }

  // Create alert based on idea database findings
  async createIdeaAlert(ideaId, conditions) {
    return fetch('http://localhost:3000/api/alerts', {
      method: 'POST',
      body: JSON.stringify({ source: 'ideas', reference: ideaId, ...conditions })
    });
  }
}
```

### **Shared Design System**

#### **Color Palette**
- **Primary**: Blue (#2563EB) - Actions, links, primary buttons
- **Success**: Green (#10B981) - Positive P&L, bullish sentiment
- **Warning**: Yellow (#F59E0B) - Medium priority, neutral sentiment
- **Danger**: Red (#EF4444) - Losses, bearish sentiment, high priority
- **Background**: Dark (#0F172A) / Light (#FFFFFF) mode support
- **Text**: Gray scale (#1E293B to #F8FAFC)

#### **Typography**
- **Headers**: Inter Bold (24px, 20px, 18px, 16px)
- **Body**: Inter Regular (14px, 16px)
- **Monospace**: JetBrains Mono (for prices, percentages)
- **Icons**: Lucide React (consistent 20px/24px sizing)

#### **Component Standards**
- **Cards**: Rounded corners (8px), subtle shadows
- **Buttons**: Primary, secondary, ghost variants
- **Inputs**: Consistent padding, focus states
- **Charts**: Consistent color scheme, responsive
- **Alerts**: Toast notifications with action buttons

---

## 📱 **Responsive Design Standards**

### **Breakpoints**
- **Desktop**: 1920x1080+ (primary target)
- **Laptop**: 1366x768+ (secondary target)
- **Tablet**: 768px+ (collapsible sidebars)
- **Mobile**: 375px+ (bottom navigation)

### **Mobile Adaptations**
- Collapsible sidebars become slide-out drawers
- Top navigation becomes bottom tab bar
- Cards stack vertically on mobile
- Charts become horizontally scrollable
- Touch-optimized button sizes (44px minimum)

---

## 🚀 **Implementation Priorities**

### **Phase 1: Core Dashboards**
1. **Real-Time Intel Dashboard** (Port 3000) - 6 hours
2. **Idea Database Dashboard** (Port 3002) - 12 hours
3. **Twin-Report KB Enhancements** (Port 3001) - 3 hours

### **Phase 2: Integration**
1. **Shared Navigation Component** - 2 hours
2. **Cross-Service API Integration** - 4 hours
3. **Unified Authentication** - 3 hours

### **Phase 3: Advanced Features**
1. **Mobile Responsive Design** - 8 hours
2. **Advanced Analytics** - 6 hours
3. **Performance Optimization** - 4 hours

---

## 📋 **Development Standards**

### **Code Organization**
```
dashboard-frontend/
├── shared/
│   ├── components/          # Reusable UI components
│   ├── navigation/          # Platform navigation
│   ├── api/                 # Cross-service communication
│   └── styles/              # Shared CSS/themes
├── real-time-intel/         # Port 3000 dashboard
├── twin-reports/            # Port 3001 enhancements
├── ideas/                   # Port 3002 dashboard
└── browser-agent/           # Port 3003 (future)
```

### **Testing Strategy**
- **Unit Tests**: Component testing with Jest + React Testing Library
- **Integration Tests**: Cross-service API communication
- **E2E Tests**: Critical user workflows with Playwright
- **Performance Tests**: WebSocket connections and real-time updates

### **Deployment Strategy**
- **Development**: Individual service ports for development
- **Production**: Nginx reverse proxy for unified access
- **Monitoring**: Health checks and performance metrics
- **Scaling**: Horizontal scaling for high-traffic services

---

**Status**: Complete UI specifications ready for implementation  
**Next Step**: Choose implementation priority and begin development  
**Estimated Total Effort**: 45-60 hours for complete platform  
**Last Updated**: January 22, 2025 
# Cross-Platform Integration Specification

> **Version:** 2025-01-22 v1.0  
> **Status:** Design Complete - Ready for Implementation  
> **Parent Project:** AI Research Platform - Multi-Dashboard Architecture  

---

## 🎯 **Overview**

The Cross-Platform Integration system provides unified navigation, shared components, and seamless data exchange between all AI Research Platform dashboards. This creates a cohesive user experience while maintaining the independence and optimization of each specialized dashboard.

### **Integration Goals**
- **🔗 Unified Navigation**: Seamless movement between dashboards
- **📊 Data Sharing**: Cross-service insights and correlations  
- **🎨 Consistent UX**: Shared design system and components
- **🔄 Real-time Sync**: Synchronized state across platforms
- **🔐 Single Sign-On**: Unified authentication and preferences

---

## 🏗️ **Architecture Overview**

### **Multi-Dashboard Strategy**
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 AI Research Platform - Integrated Architecture                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                           Shared Navigation Layer                               │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ [📈 Real-Time Intel] [📄 Twin Reports] [📚 Ideas] [🤖 Browser Agent]      │ │
│ │      Port 3000           Port 3001        Port 3002      Port 3003         │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Trading &       │ │ Document        │ │ Knowledge       │ │ Automation &    │ │
│ │ Market Intel    │ │ Analysis        │ │ Management      │ │ Workflows       │ │
│ │                 │ │                 │ │                 │ │                 │ │
│ │ • Live Feed     │ │ • Upload Docs   │ │ • Gmail Sync    │ │ • Task Automation│ │
│ │ • Portfolio     │ │ • Quality Check │ │ • AI Reports    │ │ • Web Scraping  │ │
│ │ • Alerts        │ │ • Gap Analysis  │ │ • Search        │ │ • Workflows     │ │
│ │ • Analytics     │ │ • Comparisons   │ │ • Insights      │ │ • Monitoring    │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│                                                                                 │
│                           Shared Services Layer                                │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Authentication • User Preferences • Cross-Service API • Event Bus           │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔗 **Unified Navigation System**

### **Shared Header Component**

#### **Visual Design**
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 AI Research Platform                                          👤 User Menu  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [📈 Real-Time Intel] [📄 Twin Reports] [📚 Ideas] [🤖 Browser Agent] [⚙️ Admin] │
│      Active/Current      Inactive         Inactive      Future        Settings  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### **Implementation Options**

##### **Option 1: Shared Component Library (Recommended)**
```javascript
// shared-navigation.js - Deployed to each service
class PlatformNavigation {
  constructor(currentService, userContext) {
    this.currentService = currentService;
    this.userContext = userContext;
    this.services = {
      'real-time-intel': { 
        name: 'Real-Time Intel', 
        port: 3000, 
        icon: '📈',
        description: 'Trading & Market Intelligence',
        status: 'active'
      },
      'twin-reports': { 
        name: 'Twin Reports', 
        port: 3001, 
        icon: '📄',
        description: 'Document Analysis & Comparison',
        status: 'active'
      },
      'ideas': { 
        name: 'Ideas', 
        port: 3002, 
        icon: '📚',
        description: 'Knowledge Management & Research',
        status: 'active'
      },
      'browser-agent': { 
        name: 'Browser Agent', 
        port: 3003, 
        icon: '🤖',
        description: 'Automation & Workflows',
        status: 'planned'
      }
    };
  }

  render() {
    return `
      <nav class="platform-nav bg-slate-900 text-white px-6 py-3">
        <div class="flex items-center justify-between">
          <!-- Brand -->
          <div class="flex items-center space-x-4">
            <div class="text-xl font-bold">🧠 AI Research Platform</div>
            ${this.renderBreadcrumb()}
          </div>
          
          <!-- Service Navigation -->
          <div class="flex items-center space-x-1">
            ${Object.entries(this.services).map(([key, service]) => 
              this.renderServiceLink(key, service)
            ).join('')}
          </div>
          
          <!-- User Menu -->
          <div class="flex items-center space-x-4">
            ${this.renderNotifications()}
            ${this.renderUserMenu()}
          </div>
        </div>
      </nav>
    `;
  }

  renderServiceLink(key, service) {
    const isActive = key === this.currentService;
    const isAvailable = service.status === 'active';
    
    return `
      <a href="${isAvailable ? `http://localhost:${service.port}` : '#'}"
         class="nav-link ${isActive ? 'active' : ''} ${!isAvailable ? 'disabled' : ''}"
         title="${service.description}">
        <span class="icon">${service.icon}</span>
        <span class="text">${service.name}</span>
        ${!isAvailable ? '<span class="badge">Soon</span>' : ''}
      </a>
    `;
  }

  renderBreadcrumb() {
    const service = this.services[this.currentService];
    return `
      <div class="breadcrumb text-sm text-slate-300">
        <span>${service?.icon} ${service?.name}</span>
      </div>
    `;
  }

  renderNotifications() {
    return `
      <div class="notifications relative">
        <button class="notification-bell">
          🔔 <span class="badge">${this.userContext.unreadCount || 0}</span>
        </button>
      </div>
    `;
  }

  renderUserMenu() {
    return `
      <div class="user-menu">
        <button class="user-avatar">
          👤 ${this.userContext.username || 'User'}
        </button>
      </div>
    `;
  }
}

// Usage in each dashboard
const navigation = new PlatformNavigation('real-time-intel', userContext);
document.getElementById('platform-nav').innerHTML = navigation.render();
```

##### **Option 2: Reverse Proxy Routing**
```nginx
# nginx.conf - Single entry point with path-based routing
server {
    listen 3000;
    server_name localhost;

    # Real-Time Intel (default dashboard)
    location / {
        proxy_pass http://real-time-intel:3000;
        proxy_set_header X-Platform-Service "real-time-intel";
    }

    # Twin Reports
    location /twin-reports {
        rewrite ^/twin-reports(.*) $1 break;
        proxy_pass http://twin-reports:3001;
        proxy_set_header X-Platform-Service "twin-reports";
    }

    # Ideas Database  
    location /ideas {
        rewrite ^/ideas(.*) $1 break;
        proxy_pass http://ideas:3002;
        proxy_set_header X-Platform-Service "ideas";
    }

    # Browser Agent (future)
    location /browser-agent {
        rewrite ^/browser-agent(.*) $1 break;
        proxy_pass http://browser-agent:3003;
        proxy_set_header X-Platform-Service "browser-agent";
    }

    # Shared assets
    location /shared {
        alias /var/www/shared;
    }
}
```

##### **Option 3: Micro-Frontend Architecture**
```javascript
// platform-shell.js - Module Federation
const ModuleFederationPlugin = require('@module-federation/webpack');

module.exports = {
  mode: 'development',
  devServer: {
    port: 3000,
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'platform_shell',
      remotes: {
        realTimeIntel: 'realTimeIntel@http://localhost:3001/remoteEntry.js',
        twinReports: 'twinReports@http://localhost:3002/remoteEntry.js',
        ideas: 'ideas@http://localhost:3003/remoteEntry.js',
        browserAgent: 'browserAgent@http://localhost:3004/remoteEntry.js'
      },
      shared: {
        react: { singleton: true },
        'react-dom': { singleton: true }
      }
    })
  ]
};

// Shell application
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

const RealTimeIntel = React.lazy(() => import('realTimeIntel/App'));
const TwinReports = React.lazy(() => import('twinReports/App'));
const Ideas = React.lazy(() => import('ideas/App'));

function App() {
  return (
    <BrowserRouter>
      <PlatformNavigation />
      <Routes>
        <Route path="/" element={<RealTimeIntel />} />
        <Route path="/twin-reports/*" element={<TwinReports />} />
        <Route path="/ideas/*" element={<Ideas />} />
      </Routes>
    </BrowserRouter>
  );
}
```

---

## 📊 **Cross-Service Data Integration**

### **Platform API Layer**

#### **Unified API Client**
```javascript
// platform-api.js - Cross-service communication
class PlatformAPI {
  constructor() {
    this.services = {
      realTimeIntel: 'http://localhost:3000/api',
      twinReports: 'http://localhost:3001/api', 
      ideas: 'http://localhost:3002/api',
      browserAgent: 'http://localhost:3003/api'
    };
    this.authToken = this.getAuthToken();
  }

  // Ideas Database Integration
  async getRelatedIdeas(entities, category = null) {
    return this.request('ideas', '/search', {
      method: 'POST',
      body: JSON.stringify({ 
        entities, 
        category,
        limit: 10 
      })
    });
  }

  async getIdeaTrends(timeframe = '30d') {
    return this.request('ideas', `/analytics/trends?timeframe=${timeframe}`);
  }

  async generateIdeaReport(reportType, parameters) {
    return this.request('ideas', '/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ reportType, parameters })
    });
  }

  // Twin Reports Integration  
  async analyzeDocument(content, analysisDepth = 'comprehensive') {
    return this.request('twinReports', '/analyze', {
      method: 'POST',
      body: JSON.stringify({ content, analysisDepth })
    });
  }

  async getDocumentQuality(documentId) {
    return this.request('twinReports', `/results/${documentId}/quality`);
  }

  // Real-Time Intel Integration
  async getPortfolioInsights(portfolioId) {
    return this.request('realTimeIntel', `/portfolio/${portfolioId}/insights`);
  }

  async createAlert(alertConfig) {
    return this.request('realTimeIntel', '/alerts', {
      method: 'POST',
      body: JSON.stringify(alertConfig)
    });
  }

  async getMarketSentiment(symbols = []) {
    return this.request('realTimeIntel', '/sentiment', {
      method: 'POST', 
      body: JSON.stringify({ symbols })
    });
  }

  // Cross-Platform Insights
  async getUnifiedInsights(context) {
    const [ideas, sentiment, documents] = await Promise.all([
      this.getRelatedIdeas(context.entities),
      this.getMarketSentiment(context.symbols),
      this.getRecentDocuments(context.topics)
    ]);

    return {
      ideas: ideas.data,
      sentiment: sentiment.data,
      documents: documents.data,
      correlations: this.findCorrelations(ideas, sentiment, documents)
    };
  }

  // Generic request handler
  async request(service, endpoint, options = {}) {
    const url = `${this.services[service]}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.authToken}`,
        'X-Platform-Request': 'true',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return response.json();
  }
}
```

### **Cross-Platform Use Cases**

#### **1. Portfolio-Driven Research**
```javascript
// When viewing a stock in Real-Time Intel, show related ideas
async function getPortfolioResearch(symbol) {
  const api = new PlatformAPI();
  
  // Get related ideas from Idea Database
  const relatedIdeas = await api.getRelatedIdeas([symbol], 'dev-tools');
  
  // Get document analysis from Twin Reports
  const marketAnalysis = await api.getDocumentQuality(`${symbol}_analysis`);
  
  // Combine insights
  return {
    symbol,
    relatedResearch: relatedIdeas,
    documentInsights: marketAnalysis,
    actionableItems: generateActionItems(relatedIdeas, marketAnalysis)
  };
}
```

#### **2. Idea-to-Implementation Pipeline**
```javascript
// Convert idea into actionable alert or portfolio position
async function ideaToAction(ideaId) {
  const api = new PlatformAPI();
  
  // Get idea details
  const idea = await api.getIdeaDetails(ideaId);
  
  // If idea mentions stocks/companies, create price alerts
  if (idea.entities.companies.length > 0) {
    const alertConfig = {
      type: 'price_movement',
      symbols: idea.entities.companies,
      threshold: 0.05, // 5% movement
      source: 'ideas',
      reference: ideaId
    };
    
    await api.createAlert(alertConfig);
  }
  
  // If idea has implementation potential, create task
  if (idea.implementationPotential === 'high') {
    await api.createBrowserAgentTask({
      type: 'research_task',
      description: `Research implementation of: ${idea.title}`,
      resources: idea.urls,
      priority: 'medium'
    });
  }
}
```

#### **3. Document-Enhanced Market Analysis**
```javascript
// Enhance market news with document analysis insights
async function enhanceMarketNews(newsArticle) {
  const api = new PlatformAPI();
  
  // Analyze document quality and extract insights
  const analysis = await api.analyzeDocument(newsArticle.content, 'quick');
  
  // Find related ideas
  const relatedIdeas = await api.getRelatedIdeas(
    analysis.entities, 
    'industry-news'
  );
  
  // Get market sentiment
  const sentiment = await api.getMarketSentiment(analysis.symbols);
  
  return {
    ...newsArticle,
    qualityScore: analysis.qualityScore,
    extractedEntities: analysis.entities,
    relatedResearch: relatedIdeas,
    marketImpact: sentiment,
    confidence: analysis.confidence
  };
}
```

---

## 🔄 **Real-Time State Synchronization**

### **Event Bus System**

#### **Cross-Platform Event Broadcasting**
```javascript
// platform-events.js - Shared event system
class PlatformEventBus {
  constructor() {
    this.eventTarget = new EventTarget();
    this.subscribers = new Map();
    this.setupStorageListener();
  }

  // Publish events across all dashboards
  publish(eventType, data, options = {}) {
    const event = {
      type: eventType,
      data,
      timestamp: Date.now(),
      source: options.source || 'unknown',
      id: this.generateEventId()
    };

    // Dispatch locally
    this.eventTarget.dispatchEvent(
      new CustomEvent(eventType, { detail: event })
    );

    // Broadcast to other browser tabs/windows
    if (options.broadcast !== false) {
      localStorage.setItem('platform-event', JSON.stringify(event));
    }

    // Send to WebSocket if connected
    if (this.websocket?.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify({
        type: 'platform_event',
        event
      }));
    }
  }

  // Subscribe to events
  subscribe(eventType, handler, options = {}) {
    const wrappedHandler = (event) => {
      if (options.source && event.detail.source !== options.source) {
        return; // Filter by source if specified
      }
      handler(event.detail);
    };

    this.eventTarget.addEventListener(eventType, wrappedHandler);
    
    // Store for cleanup
    if (!this.subscribers.has(eventType)) {
      this.subscribers.set(eventType, []);
    }
    this.subscribers.get(eventType).push(wrappedHandler);

    return () => {
      this.eventTarget.removeEventListener(eventType, wrappedHandler);
    };
  }

  // Listen for events from other tabs
  setupStorageListener() {
    window.addEventListener('storage', (e) => {
      if (e.key === 'platform-event' && e.newValue) {
        const event = JSON.parse(e.newValue);
        this.eventTarget.dispatchEvent(
          new CustomEvent(event.type, { detail: event })
        );
      }
    });
  }
}

// Global event bus instance
const platformEvents = new PlatformEventBus();
```

#### **Event Types & Schemas**
```javascript
// Event type definitions
const PlatformEvents = {
  // User & Authentication
  USER_LOGIN: 'user:login',
  USER_LOGOUT: 'user:logout',
  USER_PREFERENCES_UPDATED: 'user:preferences_updated',

  // Portfolio & Trading (Real-Time Intel)
  PORTFOLIO_UPDATED: 'portfolio:updated',
  ALERT_TRIGGERED: 'alert:triggered', 
  PRICE_ALERT: 'price:alert',
  SENTIMENT_CHANGE: 'sentiment:change',

  // Ideas & Research (Ideas Database)
  IDEA_ADDED: 'idea:added',
  IDEA_PROCESSED: 'idea:processed',
  REPORT_GENERATED: 'report:generated',
  RESEARCH_PRIORITY_UPDATED: 'research:priority_updated',

  // Documents (Twin Reports)
  DOCUMENT_ANALYZED: 'document:analyzed',
  QUALITY_ASSESSMENT_COMPLETE: 'quality:assessment_complete',
  GAP_ANALYSIS_COMPLETE: 'gap:analysis_complete',

  // Cross-Platform
  CONTEXT_CHANGED: 'context:changed',
  CROSS_REFERENCE_FOUND: 'cross_reference:found',
  INSIGHT_GENERATED: 'insight:generated'
};

// Event schemas
const EventSchemas = {
  [PlatformEvents.IDEA_ADDED]: {
    ideaId: 'string',
    title: 'string',
    category: 'string',
    entities: 'array',
    priority: 'number',
    source: 'string'
  },

  [PlatformEvents.PORTFOLIO_UPDATED]: {
    portfolioId: 'string',
    changes: 'object',
    performance: 'object',
    timestamp: 'number'
  },

  [PlatformEvents.DOCUMENT_ANALYZED]: {
    documentId: 'string',
    qualityScore: 'number',
    entities: 'array',
    gaps: 'array',
    recommendations: 'array'
  }
};
```

### **Shared State Management**

#### **Cross-Platform State Store**
```javascript
// platform-state.js - Shared state across dashboards
class PlatformState {
  constructor() {
    this.state = {
      user: null,
      activePortfolio: null,
      currentContext: {},
      crossServiceData: {},
      notifications: [],
      preferences: {}
    };
    
    this.subscribers = new Set();
    this.setupEventListeners();
  }

  // Get current state
  getState() {
    return { ...this.state };
  }

  // Update state and notify subscribers
  setState(updates) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...updates };
    
    // Notify subscribers of changes
    this.subscribers.forEach(callback => {
      callback(this.state, prevState);
    });

    // Broadcast state changes
    platformEvents.publish('state:updated', {
      updates,
      newState: this.state
    });
  }

  // Subscribe to state changes
  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  // Setup event listeners for cross-platform updates
  setupEventListeners() {
    // Listen for portfolio updates from Real-Time Intel
    platformEvents.subscribe(PlatformEvents.PORTFOLIO_UPDATED, (event) => {
      this.setState({
        activePortfolio: event.data.portfolio,
        currentContext: {
          ...this.state.currentContext,
          portfolio: event.data.portfolio
        }
      });
    });

    // Listen for new ideas from Ideas Database
    platformEvents.subscribe(PlatformEvents.IDEA_ADDED, (event) => {
      this.setState({
        notifications: [
          ...this.state.notifications,
          {
            type: 'idea_added',
            message: `New idea: ${event.data.title}`,
            timestamp: Date.now()
          }
        ]
      });
    });

    // Listen for document analysis completion
    platformEvents.subscribe(PlatformEvents.DOCUMENT_ANALYZED, (event) => {
      this.setState({
        crossServiceData: {
          ...this.state.crossServiceData,
          lastDocumentAnalysis: event.data
        }
      });
    });
  }

  // Context management for cross-platform insights
  updateContext(contextUpdates) {
    const newContext = {
      ...this.state.currentContext,
      ...contextUpdates
    };

    this.setState({ currentContext: newContext });

    // Trigger cross-platform insights refresh
    platformEvents.publish('context:changed', {
      context: newContext,
      timestamp: Date.now()
    });
  }
}

// Global state instance
const platformState = new PlatformState();
```

---

## 🎨 **Shared Design System**

### **Design Tokens**
```css
/* shared-tokens.css - Design system variables */
:root {
  /* Colors */
  --color-primary: #2563EB;
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-danger: #EF4444;
  --color-info: #3B82F6;
  
  /* Backgrounds */
  --bg-primary: #FFFFFF;
  --bg-secondary: #F8FAFC;
  --bg-dark: #0F172A;
  --bg-card: #FFFFFF;
  
  /* Text */
  --text-primary: #1E293B;
  --text-secondary: #64748B;
  --text-muted: #94A3B8;
  --text-inverse: #F8FAFC;
  
  /* Spacing */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2rem;
  --space-2xl: 3rem;
  
  /* Typography */
  --font-family: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  
  /* Borders */
  --border-radius: 0.5rem;
  --border-radius-sm: 0.25rem;
  --border-radius-lg: 0.75rem;
  --border-width: 1px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}

/* Dark mode overrides */
[data-theme="dark"] {
  --bg-primary: #0F172A;
  --bg-secondary: #1E293B;
  --bg-card: #334155;
  --text-primary: #F8FAFC;
  --text-secondary: #CBD5E1;
  --text-muted: #94A3B8;
}
```

### **Shared Components Library**
```javascript
// shared-components.js - Reusable UI components
export const Card = ({ children, className = '', ...props }) => (
  <div 
    className={`bg-white rounded-lg shadow-md border p-6 ${className}`}
    {...props}
  >
    {children}
  </div>
);

export const Button = ({ 
  variant = 'primary', 
  size = 'md', 
  children, 
  className = '',
  ...props 
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-md transition-colors';
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700',
    ghost: 'bg-transparent text-gray-700 hover:bg-gray-100'
  };
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  };
  
  return (
    <button 
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

export const Badge = ({ variant = 'default', children, className = '' }) => {
  const variantClasses = {
    default: 'bg-gray-100 text-gray-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800'
  };
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  );
};

export const LoadingSpinner = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6', 
    lg: 'w-8 h-8'
  };
  
  return (
    <div className={`animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 ${sizeClasses[size]} ${className}`} />
  );
};
```

---

## 🔐 **Authentication & User Management**

### **Single Sign-On System**
```javascript
// auth-service.js - Unified authentication
class AuthService {
  constructor() {
    this.token = localStorage.getItem('platform_auth_token');
    this.user = JSON.parse(localStorage.getItem('platform_user') || 'null');
    this.refreshTimer = null;
  }

  async login(credentials) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const { token, user, refreshToken } = await response.json();
    
    this.token = token;
    this.user = user;
    
    localStorage.setItem('platform_auth_token', token);
    localStorage.setItem('platform_user', JSON.stringify(user));
    localStorage.setItem('platform_refresh_token', refreshToken);
    
    this.setupTokenRefresh();
    
    // Broadcast login event
    platformEvents.publish(PlatformEvents.USER_LOGIN, { user });
    
    return { token, user };
  }

  async logout() {
    // Clear local storage
    localStorage.removeItem('platform_auth_token');
    localStorage.removeItem('platform_user');
    localStorage.removeItem('platform_refresh_token');
    
    // Clear instance variables
    this.token = null;
    this.user = null;
    
    // Clear refresh timer
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }
    
    // Broadcast logout event
    platformEvents.publish(PlatformEvents.USER_LOGOUT, {});
  }

  isAuthenticated() {
    return !!this.token && !!this.user;
  }

  getAuthHeaders() {
    return this.token ? {
      'Authorization': `Bearer ${this.token}`
    } : {};
  }

  setupTokenRefresh() {
    // Refresh token 5 minutes before expiry
    const refreshIn = (this.getTokenExpiry() - Date.now()) - (5 * 60 * 1000);
    
    if (refreshIn > 0) {
      this.refreshTimer = setTimeout(() => {
        this.refreshToken();
      }, refreshIn);
    }
  }

  async refreshToken() {
    const refreshToken = localStorage.getItem('platform_refresh_token');
    
    if (!refreshToken) {
      this.logout();
      return;
    }

    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken })
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const { token } = await response.json();
      this.token = token;
      localStorage.setItem('platform_auth_token', token);
      
      this.setupTokenRefresh();
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.logout();
    }
  }
}

// Global auth service
const authService = new AuthService();
```

---

## 📊 **Implementation Roadmap**

### **Phase 1: Foundation (Week 1)**
```yaml
tasks:
  - shared_navigation_component: 8 hours
  - platform_api_client: 6 hours  
  - event_bus_system: 4 hours
  - design_system_tokens: 2 hours
total_effort: 20 hours
```

### **Phase 2: Core Integration (Week 2)**
```yaml
tasks:
  - cross_service_api_endpoints: 8 hours
  - state_synchronization: 6 hours
  - authentication_system: 4 hours
  - shared_components_library: 2 hours
total_effort: 20 hours
```

### **Phase 3: Advanced Features (Week 3)**
```yaml
tasks:
  - real_time_insights: 8 hours
  - notification_system: 4 hours
  - user_preferences_sync: 4 hours
  - performance_optimization: 4 hours
total_effort: 20 hours
```

### **Phase 4: Polish & Testing (Week 4)**
```yaml
tasks:
  - integration_testing: 8 hours
  - performance_testing: 4 hours
  - user_experience_testing: 4 hours
  - documentation_completion: 4 hours
total_effort: 20 hours
```

---

**Status**: Complete specification ready for implementation  
**Total Estimated Effort**: 80 hours (4 weeks)  
**Priority**: Medium - Enhances user experience significantly  
**Dependencies**: All dashboard implementations  
**Recommended Approach**: Implement shared navigation first, then gradually add integration features  
**Last Updated**: January 22, 2025 
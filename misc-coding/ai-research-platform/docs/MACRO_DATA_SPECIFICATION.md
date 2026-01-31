# Macro Data System Specification

> **Version:** 2025-01-22 v1.0  
> **Status:** Documented - Ready for Implementation  
> **Priority:** Post Real-Time Intel Core Services  
> **Estimated Effort:** 20 hours

---

## 🎯 Executive Summary

A comprehensive macro economic data system that provides configurable country-based economic indicators, AI-generated economic briefs, and historical trend analysis. Features dual UI access (standalone + integrated), web scraping of Bloomberg/Trading Economics, and intelligent economic outlook generation.

## 📊 Requirements Summary

### Data Sources & Configuration
- **Configurable countries/regions** (US, EU, China, Japan, etc.)
- **Configurable macro indicators** (GDP, inflation, unemployment, interest rates, etc.)
- **Web scraping sources**: Bloomberg Economic Calendar + Trading Economics
- **API sources**: FRED, World Bank, IMF, national statistics offices
- **Historical data storage** for trend analysis

### UI Architecture
- **Dual access**: 
  - Standalone macro dashboard (Port 3001)
  - Integrated macro section in Real-Time Intel dashboard
- **Country selection**: Checkboxes for multi-country data display
- **Economic Brief**: AI-generated analysis combining current data + news research

### Features
- **Display only** (no portfolio correlation or triggers for now)
- **Historical trend analysis** with data storage
- **Economic Brief** with outlook and key indicators to watch
- **News integration** for context in economic analysis

## 🏗️ Service Architecture

### Macro Watcher Service (Port 8301)
**Purpose**: Economic data collection and web scraping
- Bloomberg Economic Calendar scraping
- Trading Economics data extraction
- FRED API integration
- World Bank/IMF API integration
- Configurable data collection by country/indicator
- Historical data backfill capabilities

### Macro Analyzer Service (Port 8309)
**Purpose**: AI-powered economic brief generation
- Economic Brief Generation using Mac Studio LLM
- Trend Analysis with historical data
- News Integration for context
- Outlook Generation with key indicators
- Multi-country comparative analysis

## 🎨 UI Architecture

### Standalone Macro Dashboard (Port 3001)
```
┌─────────────────────────────────────────────┐
│ 🌍 Macro Economic Dashboard                │
├─────────────────────────────────────────────┤
│ Country Selection:                          │
│ ☑️ United States  ☑️ European Union        │
│ ☑️ China          ☐ Japan                  │
│ ☐ United Kingdom  ☐ Canada                 │
├─────────────────────────────────────────────┤
│ Economic Indicators:                        │
│ [GDP Chart] [Inflation Chart] [Unemployment]│
│ [Interest Rates] [Trade Balance] [PMI]      │
├─────────────────────────────────────────────┤
│ 📊 Economic Brief (AI-Generated):          │
│ Current Situation: ...                      │
│ Key Trends: ...                            │
│ Outlook: ...                               │
│ What to Watch: ...                         │
└─────────────────────────────────────────────┘
```

### Real-Time Intel Integration
- **Macro tab** in main Real-Time Intel dashboard
- **Quick macro widgets** on main dashboard
- **Cross-linking** between macro events and news

## 📋 Implementation Timeline

**Total Effort: 20 hours**

### Phase 1: Database Schema Enhancement (2 hours)
- Create macro economic data tables
- Add country and indicator configuration tables
- Set up indexes for performance

### Phase 2: Macro Watcher Service (6 hours)
- FastAPI service setup
- Bloomberg Economic Calendar scraper
- Trading Economics scraper
- FRED API integration
- Database integration

### Phase 3: Macro Analyzer Service (4 hours)
- FastAPI service setup
- Mac Studio LLM integration
- Economic brief generation
- Trend analysis algorithms

### Phase 4: Macro Dashboard UI (6 hours)
- FastAPI + Jinja2 setup
- Country selection interface
- Chart visualization components
- Economic brief display

### Phase 5: Real-Time Intel Integration (2 hours)
- Add macro tab to main dashboard
- Quick macro widgets
- Navigation integration

---

**Status**: Ready for implementation after Real-Time Intel core services are complete.
**Next Action**: Continue with Sentiment Analyzer (8304) implementation.
**Documentation**: Complete specification available for future development.

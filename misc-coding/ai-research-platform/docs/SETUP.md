# AI Research Platform - Setup Guide

## Overview
Self-hosted intelligence platform with four sub-projects running on Docker with Mac Studio M3 Ultra LLM integration.

## Prerequisites
- Docker and Docker Compose installed
- Access to Mac Studio endpoint: `https://matiass-mac-studio.tail174e9b.ts.net/v1`
- DeepSeek R1 model verified working

## Quick Start

### 1. Environment Setup
```bash
cp config/environment.example .env
# Edit .env with your secure passwords
```

### 2. Start Core Infrastructure
```bash
docker-compose -f docker-compose.master.yml up -d
```

### 3. Verify Services
```bash
# Check all services are healthy
docker-compose -f docker-compose.master.yml ps

# Test database connection
docker exec ai_platform_postgres psql -U ai_user -d ai_platform -c "SELECT 1;"

# Test Chroma vector database
curl http://localhost:8000/api/v1/heartbeat

# Test MinIO object storage
curl http://localhost:9000/minio/health/live
```

## Services Overview

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| PostgreSQL | 5432 | Shared database | `docker exec ai_platform_postgres pg_isready` |
| Chroma | 8000 | Vector database | `curl localhost:8000/api/v1/heartbeat` |
| MinIO | 9000/9001 | Object storage | MinIO Console at http://localhost:9001 |
| NATS | 4222/8222 | Message bus | NATS Monitor at http://localhost:8222 |

## Database Schemas
- `idea_database` - Gmail knowledge ingestion
- `twin_report` - Dual AI research reports  
- `real_time_intel` - News crawling & analysis
- `browser_agent` - Premium AI automation
- `shared_services` - Cross-module functionality

## Next Steps
1. ✅ Infrastructure foundation complete
2. 🔄 Ready for sub-project implementation
3. 📧 Start with Idea Database Gmail integration

## Mac Studio Integration
- Endpoint: `https://matiass-mac-studio.tail174e9b.ts.net/v1`
- Verified Model: `deepseek-r1`
- Additional models being installed: `qwen2.5vl`, `llama4:scout`, `llama4:maverick` 
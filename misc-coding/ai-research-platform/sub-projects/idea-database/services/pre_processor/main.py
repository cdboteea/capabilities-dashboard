"""
Pre-Processor Service for Ideas Database
========================================

🎯 SERVICE PURPOSE & ARCHITECTURAL ROLE:
This service is the SINGLE SOURCE OF TRUTH for ALL TEXT NORMALIZATION in the 
AI Research Platform. It converts text content to standardized markdown format 
with YAML front-matter and semantic chunking for LLM processing.

⚠️ CRITICAL ARCHITECTURAL BOUNDARY:
===================================

✅ PRE-PROCESSOR HANDLES:
- HTML → markdown conversion using markdownify
- Plain text → formatted markdown
- YAML front-matter injection (idea_id, source, timestamps)  
- Semantic chunking (by headings, paragraphs, with overlap)
- Language detection and metadata enrichment
- Content deduplication by hash
- Text cleaning and standardization

❌ PRE-PROCESSOR DOES NOT HANDLE:
- Binary file processing (PDF, Word, Images) → Content Extractor handles this
- File upload/download operations → Email/Content services handle this
- Drive storage management → Other services handle this
- Direct file system operations → Other services handle this

🔗 INTEGRATION PATTERN:
======================
ALL text content flows through Pre-Processor for normalization:

Email Content → Pre-Processor → AI Processor
Content Extractor (raw text) → Pre-Processor → AI Processor  
Manual Text Input → Pre-Processor → AI Processor

🚨 DEVELOPER WARNING:
====================
This service contains the ONLY markdownify import in the platform!
DO NOT duplicate HTML→markdown conversion in other services.

Other services MUST call this service via HTTP API:
```python
# ✅ CORRECT - From Content Extractor or other services
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://idea_db_pre_processor:8000/normalize",
        json={
            "idea_id": idea_id,
            "source": source,
            "payload": text_content
        }
    )
    return response.json()["markdown"]

# ❌ WRONG - Don't import markdownify elsewhere!
from markdownify import markdownify  # Only allowed here!
```

📡 API ENDPOINTS:
================
- POST /normalize - Convert text/HTML to markdown with YAML front-matter
- POST /chunk - Split markdown into semantic chunks for LLM processing  
- GET /health - Service health check

🔧 TECHNICAL STACK:
==================
- markdownify: HTML → markdown conversion (ONLY here!)
- PyYAML: Front-matter injection
- langdetect: Language identification
- redis: Event publishing
- FastAPI: Async HTTP API

🏗️ PROCESSING PIPELINE:
=======================
1. Input Validation (size limits, content type)
2. Content Detection (HTML vs plain text)  
3. Normalization (markdownify or text formatting)
4. Metadata Injection (YAML front-matter)
5. Event Publishing (Redis notifications)

For chunking:
1. YAML front-matter removal
2. Section splitting by headings
3. Paragraph-based fallback  
4. Hash-based deduplication
5. Language detection per chunk
6. Metadata enrichment

Last Updated: 2025-07-17
Status: ✅ Production Ready - Text Normalization Authority
"""

from fastapi import FastAPI, Body, HTTPException, Request
from pydantic import BaseModel
from typing import List
from datetime import datetime
import yaml
from markdownify import markdownify as md_to_md
import re
import hashlib
from langdetect import detect, LangDetectException
import os
import redis
import json

app = FastAPI()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)
EVENT_CHANNEL = "idea.events"

@app.get("/health")
def health():
    return {"status": "ok"}

class NormalizeRequest(BaseModel):
    idea_id: str
    source: str
    payload: str

class NormalizeResponse(BaseModel):
    markdown: str

MAX_INPUT_SIZE = 1 * 1024 * 1024  # 1MB

@app.post("/normalize", response_model=NormalizeResponse)
def normalize(req: NormalizeRequest, request: Request):
    # Input validation
    if not isinstance(req.payload, str) or not req.payload.strip():
        raise HTTPException(status_code=400, detail="Payload must be a non-empty string.")
    # Size limit
    if len(req.payload.encode('utf-8')) > MAX_INPUT_SIZE:
        raise HTTPException(status_code=413, detail="Payload too large (max 1MB).")
    try:
        is_html = "<html" in req.payload.lower() or "<div" in req.payload.lower() or "<p" in req.payload.lower()
        if is_html:
            markdown = md_to_md(req.payload)
        else:
            markdown = req.payload
        front_matter = {
            "idea_id": req.idea_id,
            "source": req.source,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        yaml_str = yaml.dump(front_matter, sort_keys=False)
        markdown_with_yaml = f"---\n{yaml_str}---\n\n{markdown}"
        # Publish event (placeholder markdown_url)
        event = {
            "action": "idea.preprocessed",
            "data": {
                "idea_id": req.idea_id,
                "markdown_url": f"s3://placeholder/{req.idea_id}.md"
            }
        }
        try:
            redis_client.publish(EVENT_CHANNEL, json.dumps(event))
        except Exception as e:
            print(f"[WARN] Failed to publish event: {e}")
        return {"markdown": markdown_with_yaml}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Normalization failed: {str(e)}")

class ChunkRequest(BaseModel):
    idea_id: str
    markdown: str

class Chunk(BaseModel):
    chunk_id: str
    idea_id: str
    order: int
    text: str
    token_count: int
    lang: str
    hash: str
    created_at: str

@app.post("/chunk", response_model=List[Chunk])
def chunk(req: ChunkRequest, request: Request):
    # Input validation
    if not isinstance(req.markdown, str) or not req.markdown.strip():
        raise HTTPException(status_code=400, detail="Markdown must be a non-empty string.")
    if len(req.markdown.encode('utf-8')) > MAX_INPUT_SIZE:
        raise HTTPException(status_code=413, detail="Markdown too large (max 1MB).")
    try:
        # Remove YAML front-matter if present
        text = req.markdown
        if text.startswith('---'):
            text = text.split('---', 2)[-1].strip()
        section_pattern = re.compile(r'(^|\n)(##+ .+)', re.MULTILINE)
        sections = section_pattern.split(text)
        parsed_sections = []
        if len(sections) > 1:
            for i in range(1, len(sections), 2):
                title = sections[i].strip()
                body = sections[i+1].strip() if i+1 < len(sections) else ''
                parsed_sections.append(f"{title}\n{body}")
        else:
            parsed_sections = [text.strip()]
        max_chars = 4000
        overlap_chars = 400
        chunks = []
        chunk_order = 0
        for section in parsed_sections:
            if len(section) <= max_chars:
                chunks.append(section)
            else:
                paras = re.split(r'\n\s*\n', section)
                buf = ''
                for para in paras:
                    if len(buf) + len(para) + 2 <= max_chars:
                        buf += para + '\n\n'
                    else:
                        if buf:
                            chunks.append(buf.strip())
                            chunk_order += 1
                        buf = para + '\n\n'
                if buf:
                    chunks.append(buf.strip())
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_chars:
                final_chunks.append(chunk)
            else:
                for i in range(0, len(chunk), max_chars - overlap_chars):
                    final_chunks.append(chunk[i:i+max_chars])
        seen_hashes = set()
        chunk_objs = []
        for idx, chunk_text in enumerate(final_chunks):
            chunk_hash = hashlib.sha1(chunk_text.encode('utf-8')).hexdigest()
            if chunk_hash in seen_hashes:
                continue
            seen_hashes.add(chunk_hash)
            try:
                lang = detect(chunk_text)
            except LangDetectException:
                lang = 'unknown'
            chunk_objs.append(Chunk(
                chunk_id=f"{req.idea_id}_{idx}",
                idea_id=req.idea_id,
                order=idx,
                text=chunk_text,
                token_count=len(chunk_text.split()),
                lang=lang,
                hash=chunk_hash,
                created_at=datetime.utcnow().isoformat() + "Z"
            ))
        # After chunk_objs creation, filter out any empty chunks
        chunk_objs = [c for c in chunk_objs if c.text.strip()]
        if not chunk_objs:
            raise HTTPException(status_code=400, detail="No non-empty chunks could be created from input.")
        # Publish event
        event = {
            "action": "idea.chunked",
            "data": {
                "idea_id": req.idea_id,
                "chunks": [c.chunk_id for c in chunk_objs]
            }
        }
        try:
            redis_client.publish(EVENT_CHANNEL, json.dumps(event))
        except Exception as e:
            print(f"[WARN] Failed to publish event: {e}")
        return chunk_objs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chunking failed: {str(e)}") 
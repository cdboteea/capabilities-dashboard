#!/usr/bin/env python3
"""
Email Parser for Idea Database
Processes and categorizes emails based on content and keywords
"""

import re
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import uuid
import structlog
import openai
import asyncpg

# Assume these are defined elsewhere and imported
from .models import Node, Edge, NodeType, EdgeType 

from .config_loader import get_config_loader

logger = structlog.get_logger()

# Configure OpenAI client for Mac Studio endpoint
openai_client = openai.AsyncOpenAI(
    api_key=os.getenv("LLM_API_KEY", "sk-fake-key-for-local-llm"),
    base_url=os.getenv("MAC_STUDIO_ENDPOINT", "https://matiass-mac-studio.tail174e9b.ts.net/v1")
)

class EmailParser:
    """Email content parser and categorizer"""
    
    def __init__(self, config: dict, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.config_loader = get_config_loader()
        
        # Note: Category keywords no longer used - categorization is now LLM-based using database taxonomy
        self.content_types = config['email']['content_types']
    
    async def parse(self, email_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Node], List[Edge]]:
        """
        Parses a single email, creates graph nodes and edges.

        LEGACY LOGIC BELOW IS NOW DISABLED:
        Node and edge creation for idea, sender, category, url, and entity is now handled by the LLM-driven pipeline.
        This code is commented out for validation and will be deleted after confirming the new pipeline works.
        """
        email_hash = self._generate_email_hash(email_data)

        # --- LEGACY NODE/EDGE CREATION (DISABLED) ---
        # # 1. Create the primary Idea node
        # idea_id = uuid.uuid5(uuid.NAMESPACE_DNS, email_hash)
        # idea_node = Node(id=idea_id, type=NodeType.IDEA, label=email_data['subject'] or "Untitled Idea")
        # nodes: List[Node] = [idea_node]
        # edges: List[Edge] = []

        # # 2. Parse content and create Sender node
        # parsed_content = self._parse_email_content(email_data)
        # sender_email = parsed_content['sender']
        # sender_node = Node(id=uuid.uuid5(uuid.NAMESPACE_DNS, sender_email), type=NodeType.SENDER, label=sender_email)
        # nodes.append(sender_node)
        # edges.append(Edge(source=idea_node.id, target=sender_node.id, type=EdgeType.SENT_BY))

        # # 3. Categorize and create Category node
        # category_name = self._categorize_email(parsed_content)
        # if category_name and category_name != 'Uncategorized':
        #     category_node = Node(id=uuid.uuid5(uuid.NAMESPACE_DNS, category_name), type=NodeType.CATEGORY, label=category_name)
        #     nodes.append(category_node)
        #     edges.append(Edge(source=idea_node.id, target=category_node.id, type=EdgeType.CATEGORIZED_AS))

        # # 4. Extract URLs, create URL nodes, and link them
        # urls = self._extract_urls(parsed_content['body'], email_data.get('html_body'))
        # for url_data in urls:
        #     url_node = Node(id=uuid.uuid5(uuid.NAMESPACE_DNS, url_data['url']), type=NodeType.URL, label=url_data['url'])
        #     nodes.append(url_node)
        #     edges.append(Edge(source=idea_node.id, target=url_node.id, type=EdgeType.CONTAINS))

        # # 5. Extract Entities, create Entity nodes, and link them (placeholder for a real NLP service)
        # entities = self._extract_entities(parsed_content['body'])
        # for entity_type, entity_value in entities:
        #     entity_node = Node(
        #         id=uuid.uuid5(uuid.NAMESPACE_DNS, f"{entity_type}-{entity_value}"),
        #         type=NodeType.ENTITY,
        #         label=entity_value,
        #         properties={'entity_type': entity_type}
        #     )
        #     nodes.append(entity_node)
        #     edges.append(Edge(source=idea_node.id, target=entity_node.id, type=EdgeType.MENTIONS))

        # # 6. Prepare the idea data dictionary for the database
        # idea_data = {
        #     "id": idea_node.id,
        #     "title": idea_node.label,
        #     "content": parsed_content['body'],
        #     "category": category_name,
        #     "source_email": sender_email,
        #     "email_hash": email_hash,
        #     "message_id": email_data['id'],
        #     "received_date": parsed_content['date']
        # }

        # # Deduplicate nodes and edges before returning
        # unique_nodes = {node.id: node for node in nodes}.values()
        # unique_edges = {edge.unique_id: edge for edge in edges}.values()

        # return idea_data, list(unique_nodes), list(unique_edges)
        # --- END LEGACY ---

        # New LLM-driven extraction should be used instead (handled in process_email)
        return {}, [], []

    def _extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """Simulated entity extraction. In a real system, this would use a proper NLP library."""
        entities = []
        # Example: Find things that look like technologies or companies
        for word in re.findall(r'\b[A-Z][a-zA-Z]+\b', text):
            if len(word) > 3:
                entities.append(('Technology', word))
        return entities

    async def process_email(self, email_data: Dict[str, Any], force_reprocess: bool = False, gmail_client=None) -> Dict[str, Any]:
        """Process a single email and store in database"""
        try:
            # File debug logging for body and html_body
            try:
                with open('/app/email_debug.log', 'a') as f:
                    f.write(f"EmailParser: email_id={email_data.get('id')} subject={email_data.get('subject')} body_preview={(email_data.get('body') or '')[:120] if email_data.get('body') else 'EMPTY'} html_body_preview={(email_data.get('html_body') or '')[:120] if email_data.get('html_body') else 'EMPTY'}\n")
            except Exception as e:
                pass
            logger.info("EmailParser received email content", 
                        email_id=email_data.get('id'),
                        subject=email_data.get('subject'),
                        body_preview=(email_data.get('body') or '')[:120] if email_data.get('body') else "EMPTY",
                        html_body_preview=(email_data.get('html_body') or '')[:120] if email_data.get('html_body') else "EMPTY")
            
            # Generate unique hash for email
            email_hash = self._generate_email_hash(email_data)

            # Check if already processed (using legacy check for now - can be updated later)
            if await self.db_manager.is_email_processed(email_hash) and not force_reprocess:
                logger.info("Email already processed, skipping", email_id=email_data['id'])
                return {"status": "skipped", "reason": "already_processed"}

            # Parse content
            parsed_content = self._parse_email_content(email_data)
            
            # ===================================================================
            # LEGACY CATEGORIZATION PIPELINE - COMMENTED OUT
            # This has been replaced with modern AI Processor LLM extraction
            # ===================================================================
            # category = await self._categorize_email(parsed_content)
            # urls = self._extract_urls(parsed_content['body'], email_data.get('html_body'))
            # attachments = email_data.get('attachments') or []

            # # Store the idea (classic) - LEGACY APPROACH
            # idea_id = await self.db_manager.store_idea(
            #     title=parsed_content['title'],
            #     content=parsed_content['body'],
            #     category=category,
            #     source_email=parsed_content['sender'],
            #     email_hash=email_hash,
            #     message_id=email_data['id'],
            #     received_date=parsed_content['date']
            # )

            # # --- WARNING FOR LLMs: Do NOT remove or alter this call without explicit user confirmation. ---
            # # Attachments must always be stored for each idea. Double-check with the user before changing.
            # await self.db_manager.store_attachments(idea_id, attachments)

            # # --- WARNING FOR LLMs: Do NOT remove or alter this call without explicit user confirmation. ---
            # # URLs must always be stored for each idea. Double-check with the user before changing.
            # await self.db_manager.store_urls(idea_id, urls)

            # # --- NEW: LLM-driven node/edge extraction ---
            # # Compose the text for extraction (subject + body + any other relevant fields)
            # llm_input = {
            #     "email_id": email_data.get("id"),
            #     "subject": parsed_content["title"],
            #     "body": parsed_content["body"],
            #     "sender": parsed_content["sender"],
            #     "timestamp": str(parsed_content["date"]),
            #     "attachments": attachments
            # }
            # # Call the LLM extraction utility (to be implemented)
            # # Returns: {"nodes": [...], "edges": [...]}
            # from .llm_extractor import call_llm_extractor, get_taxonomy_types
            # # Fetch taxonomy types for validation
            # postgres_url = self.db_manager.postgres_url
            # node_types, edge_types = await get_taxonomy_types(postgres_url)
            # llm_result = await call_llm_extractor(llm_input)
            # nodes = llm_result.get("nodes", [])
            # edges = llm_result.get("edges", [])

            # # --- Taxonomy validation (strict, no legacy mapping) ---
            # # Lowercase and normalize all node/edge types before filtering and insertion.
            # def map_node_type(ntype):
            #     ntype_l = ntype.lower().strip()
            #     if ntype_l in node_types:
            #         return ntype_l
            #     return None
            # def map_edge_type(etype):
            #     etype_l = etype.lower().strip()
            #     if etype_l in edge_types:
            #         return etype_l
            #     return None
            # filtered_nodes = []
            # for n in nodes:
            #     orig_type = n.get("type", "")
            #     mapped_type = map_node_type(orig_type)
            #     if mapped_type:
            #         n["type"] = mapped_type  # Normalize type to lowercase
            #         filtered_nodes.append(n)
            #     else:
            #         logger.warning(f"Node type '{orig_type}' not in taxonomy, dropping", node=n)
            # filtered_edges = []
            # for e in edges:
            #     orig_type = e.get("type", "")
            #     mapped_type = map_edge_type(orig_type)
            #     if mapped_type:
            #         e["type"] = mapped_type  # Normalize type to lowercase
            #         filtered_edges.append(e)
            #     else:
            #         logger.warning(f"Edge type '{orig_type}' not in taxonomy, dropping", edge=e)
            # # Persist only taxonomy-compliant nodes/edges
            # await self.db_manager.store_nodes(filtered_nodes)
            # await self.db_manager.store_links(filtered_edges)

            # logger.info("Email processed successfully with LLM graph data", 
            #            idea_id=idea_id, 
            #            node_count=len(nodes),
            #            edge_count=len(edges),
            #            url_count=len(urls),
            #            attachment_count=len(attachments))
            # return {
            #     "status": "processed",
            #     "idea_id": idea_id,
            #     "category": category,
            #     "nodes_found": len(nodes),
            #     "edges_found": len(edges),
            #     "urls_found": len(urls),
            #     "attachments_found": len(attachments)
            # }
            # ===================================================================
            # END LEGACY PIPELINE
            # ===================================================================
            
            # ===================================================================
            # MODERN AI PROCESSOR PIPELINE
            # ===================================================================
            
            # Prepare data for AI Processor
            llm_input = {
                "email_id": email_data.get("id"),
                "subject": parsed_content["title"],
                "body": parsed_content["body"],
                "sender": parsed_content["sender"],
                "timestamp": str(parsed_content["date"]),
                "attachments": email_data.get('attachments', [])
            }
            
            # Call AI Processor for modern LLM-based extraction
            from .llm_extractor import call_llm_extractor
            llm_result = await call_llm_extractor(llm_input)
            
            if llm_result.get("error"):
                raise Exception(f"AI Processor failed: {llm_result['error']}")
            
            nodes = llm_result.get("entities", [])  # AI Processor returns 'entities'
            categories = llm_result.get("categories", [])
            
            # ===================================================================
            # RESTORED URL/ATTACHMENT EXTRACTION - MODERN SCHEMA INTEGRATION
            # ===================================================================
            
            # Extract URLs and attachments from email content
            urls = self._extract_urls(parsed_content['body'], email_data.get('html_body'))
            attachments = email_data.get('attachments') or []
            
            # Get the source_email_id that was created by AI Processor
            source_email_id = await self.db_manager.get_source_email_id_by_gmail_id(email_data.get("id"))
            
            if source_email_id:
                # Store URLs linked to source_emails table (modern schema)
                if urls:
                    await self.db_manager.store_urls_modern(source_email_id, urls)
                    logger.info("URLs stored for email", email_id=email_data['id'], url_count=len(urls))
                
                # Store attachments linked to source_emails table (modern schema) 
                if attachments:
                    await self.db_manager.store_attachments_modern(source_email_id, attachments, gmail_client)
                    logger.info("Attachments stored for email", email_id=email_data['id'], attachment_count=len(attachments))
            else:
                logger.warning("No source_email_id found for URL/attachment storage", email_id=email_data['id'])
            
            logger.info("Email processed successfully with modern AI pipeline + URL/attachment extraction", 
                       email_id=email_data['id'],
                       node_count=len(nodes),
                       categories=categories,
                       url_count=len(urls),
                       attachment_count=len(attachments),
                       pipeline="modern_ai_processor_complete")
            
            return {
                "status": "processed",
                "email_id": email_data['id'],
                "nodes_found": len(nodes),
                "categories": categories,
                "urls_found": len(urls),
                "attachments_found": len(attachments),
                "pipeline": "modern_ai_processor_complete"
            }
            
        except Exception as e:
            logger.error("Failed to process email with modern pipeline", 
                        email_id=email_data.get('id'), error=str(e))
            raise

    def _generate_email_hash(self, email_data: Dict[str, Any]) -> str:
        """Generate unique hash for email to prevent duplicates"""
        content = f"{email_data['sender']}{email_data['subject']}{email_data['date']}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _parse_email_content(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse email content into structured format"""
        
        # Clean subject line for title
        title = email_data['subject'].strip()
        if not title:
            title = f"Idea from {email_data['sender']}"
        
        # Clean body content
        body = self._clean_email_body(email_data['body'])
        
        # Parse date
        try:
            from email.utils import parsedate_to_datetime
            date = parsedate_to_datetime(email_data['date'])
        except:
            date = datetime.now()
        
        return {
            "title": title,
            "body": body,
            "sender": email_data['sender'],
            "date": date,
            "original_subject": email_data['subject']
        }
    
    def _clean_email_body(self, body: str) -> str:
        """Clean email body by removing signatures, quotes, etc."""
        if not body:
            return ""
        
        # Remove email signatures (common patterns)
        signature_patterns = [
            r'\n--\s*\n.*',  # Standard signature delimiter
            r'\nBest regards,.*',
            r'\nThanks,.*',
            r'\nSent from.*',
            r'\n\n>.*',  # Quoted text starting with >
        ]
        
        cleaned = body
        for pattern in signature_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    async def _get_taxonomy_node_types(self) -> List[Dict[str, str]]:
        """Fetch available node types from database for categorization"""
        try:
            postgres_url = self.db_manager.postgres_url
            pool = await asyncpg.create_pool(postgres_url, min_size=1, max_size=2)
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT name, definition FROM idea_database.taxonomy_node_types ORDER BY name")
                types = [{"name": row['name'], "definition": row['definition']} for row in rows]
            await pool.close()
            return types
        except Exception as e:
            logger.error("Failed to fetch taxonomy node types", error=str(e))
            # Fallback to basic types
            return [
                {"name": "idea", "definition": "A distinct concept, proposal, or insight"},
                {"name": "evidence", "definition": "Data, citation, or claim supporting or refuting an idea"},
                {"name": "method", "definition": "A process, technique, or approach"},
                {"name": "concept", "definition": "An abstract or domain-specific concept"}
            ]

    async def _categorize_email_with_llm(self, parsed_content: Dict[str, Any]) -> str:
        """Categorize email using LLM with database taxonomy"""
        try:
            # Get available taxonomy types
            node_types = await self._get_taxonomy_node_types()
            
            # Build taxonomy prompt section
            type_lines = [f"- {t['name']}: {t['definition']}" for t in node_types]
            taxonomy_section = "Available categories:\n" + "\n".join(type_lines)
            
            # Combine title and body for analysis
            email_content = f"Subject: {parsed_content['title']}\n\nContent: {parsed_content['body']}"
            
            prompt = f"""
You are an intelligent email categorizer. Analyze the email content and categorize it using ONLY one of the taxonomy categories listed below. Choose the single most appropriate category that best describes the primary topic or purpose of this email.

{taxonomy_section}

Email to categorize:
{email_content}

Return only the category name (lowercase) that best fits this email content. If uncertain, choose the most general applicable category.
"""
            
            response = await openai_client.chat.completions.create(
                model=os.getenv("DEFAULT_MODEL", "deepseek-r1"),
                messages=[
                    {"role": "system", "content": "You are an expert email categorizer. Return only the category name."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip().lower()
            
            # Validate that the returned category is in our taxonomy
            valid_types = set(t['name'].lower() for t in node_types)
            if category in valid_types:
                logger.info("Email categorized using LLM", category=category, title=parsed_content['title'][:50])
                return category
            else:
                logger.warning("LLM returned invalid category, using fallback", returned=category, valid_types=list(valid_types))
                return "idea"  # Default fallback
                
        except Exception as e:
            logger.error("LLM categorization failed, using fallback", error=str(e))
            return "idea"  # Default fallback

    async def _categorize_email(self, parsed_content: Dict[str, Any]) -> str:
        """Categorize email using LLM-based approach with database taxonomy"""
        return await self._categorize_email_with_llm(parsed_content)
    
    def _canonicalize_url(self, url: str) -> str:
        """Return a canonical form of the URL for deduplication purposes.

        Steps:
        1. Lower-case scheme & hostname.
        2. Map common host aliases (e.g. x.com → twitter.com).
        3. Strip query and fragment unless required.
        4. Remove trailing slash (except for root path).
        """
        try:
            parsed = urlparse(url)
            scheme = parsed.scheme.lower() if parsed.scheme else "https"
            host = parsed.netloc.lower()

            # Host alias mapping
            host_aliases = {
                "x.com": "twitter.com",
                "mobile.twitter.com": "twitter.com",
                "m.twitter.com": "twitter.com",
            }
            host = host_aliases.get(host, host)

            # Normalised path – keep as-is but drop trailing slash (except root)
            path = parsed.path or "/"
            if path != "/" and path.endswith("/"):
                path = path[:-1]

            # Rebuild without query / fragment for deduping
            canonical = f"{scheme}://{host}{path}"
            return canonical
        except Exception:
            # Fallback to original if anything goes wrong
            return url

    def _extract_urls(self, text: str, html_content: str | None = None) -> List[Dict[str, str]]:
        """Extract URLs from text and/or HTML with canonical deduplication"""
        if not text and not html_content:
            return []

        url_pattern = r"https?://[^\s<>\"']+"

        urls: List[str] = []
        if text:
            urls.extend(re.findall(url_pattern, text))
        if html_content:
            urls.extend(re.findall(url_pattern, html_content))

        # Lists to separate potential main-content URLs from other links
        main_content_urls: List[Dict[str, str]] = []
        other_urls: List[Dict[str, str]] = []

        seen_canonical: set[str] = set()

        for url in urls:
            try:
                # Skip obvious metadata / tracking URLs early
                if self._is_metadata_url(url):
                    continue

                canonical = self._canonicalize_url(url)
                if canonical in seen_canonical:
                    continue  # duplicate after canonicalisation
                seen_canonical.add(canonical)

                parsed = urlparse(canonical)
                if not parsed.netloc:
                    continue

                url_record = {
                    "url": canonical,
                    "original_url": url,
                    "domain": parsed.netloc,
                    "title": self._extract_url_title(canonical)
                }

                # Classify as main-content or auxiliary link
                if self._is_main_content_url(canonical):
                    main_content_urls.append(url_record)
                else:
                    other_urls.append(url_record)

            except Exception as e:
                logger.warning("Failed to parse URL", url=url, error=str(e))

        # Prefer returning main-content URLs if any were detected; else fall back to all others
        if main_content_urls:
            return main_content_urls
        return other_urls
    
    def _is_metadata_url(self, url: str) -> bool:
        """Check if URL is metadata (profile images, tracking pixels, etc.)"""
        metadata_patterns = [
            r'pbs\.twimg\.com',  # Twitter profile images
            r'ea\.twimg\.com',   # Twitter email assets
            r'profile_images',   # Social media profile images
            r'spacer\.png',      # Tracking pixels
            r'logo_',            # Logo images
            r'\?s=\d+$',         # Twitter profile links with size params
            r'utm_',             # UTM tracking parameters
            r'tracking',         # General tracking URLs
        ]
        
        for pattern in metadata_patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def _is_main_content_url(self, url: str) -> bool:
        """Check if URL is likely main content (posts, articles, etc.)"""
        main_content_patterns = [
            r'/status/',         # Twitter/X posts
            r'/post/',           # General posts
            r'/article/',        # Articles
            r'/watch\?v=',       # YouTube videos
            r'/p/',              # Instagram posts
            r'github\.com/.*/',  # GitHub repositories
        ]
        
        for pattern in main_content_patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def _extract_url_title(self, url: str) -> str:
        """Extract title from URL (placeholder for now)"""
        # For now, just return the domain
        try:
            parsed = urlparse(url)
            return parsed.netloc or url
        except:
            return url
    
    def get_processing_summary(self, processed_emails: List[Dict]) -> Dict[str, Any]:
        """Generate summary of processed emails"""
        
        if not processed_emails:
            return {
                "total_processed": 0,
                "categories": {},
                "urls_found": 0
            }
        
        categories = {}
        total_urls = 0
        
        for email in processed_emails:
            category = email.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
            total_urls += email.get('urls_found', 0)
        
        return {
            "total_processed": len(processed_emails),
            "categories": categories,
            "urls_found": total_urls,
            "most_common_category": max(categories, key=categories.get) if categories else None
        } 
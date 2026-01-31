"""
Entity Extraction Processor - Financial entity extraction and recognition
"""

import asyncio
import httpx
import json
import re
import structlog
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import spacy
from transformers import pipeline
import yfinance as yf

from ..models import Entity, NewsEvent

logger = structlog.get_logger(__name__)

class EntityExtractor:
    """Advanced financial entity extraction"""
    
    def __init__(self, mac_studio_endpoint: str = "http://10.0.0.100:8000"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Initialize NLP models
        self.nlp = None
        self.ner_pipeline = None
        
        # Financial data cache
        self.ticker_cache = {}
        self.company_cache = {}
        
        # Known ticker patterns and company mappings
        self.known_tickers = self._load_known_tickers()
        self.sector_mappings = self._load_sector_mappings()
        
        # Model state
        self.models_loaded = False
    
    async def initialize(self):
        """Initialize NLP models and resources"""
        try:
            logger.info("Initializing Entity Extractor")
            
            # Load spaCy model for NER
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found, using basic entity extraction")
            
            # Load NER pipeline for financial entities
            try:
                self.ner_pipeline = pipeline(
                    "ner",
                    model="dbmdz/bert-large-cased-finetuned-conll03-english",
                    aggregation_strategy="simple"
                )
            except Exception as e:
                logger.warning("Failed to load NER pipeline", error=str(e))
            
            self.models_loaded = True
            logger.info("Entity Extractor initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Entity Extractor", error=str(e))
            raise
    
    async def extract_entities(self, event: NewsEvent) -> List[Entity]:
        """Extract all entities from news event"""
        logger.info("Extracting entities", event_id=event.event_id)
        
        try:
            text = f"{event.title} {event.content}"
            
            # Multiple extraction approaches
            extraction_tasks = [
                self._extract_financial_entities(text),
                self._extract_named_entities(text),
                self._extract_ticker_symbols(text),
                self._extract_financial_terms(text)
            ]
            
            # Execute all extraction tasks
            results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
            
            # Combine and deduplicate entities
            all_entities = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error("Entity extraction task failed", error=str(result))
                    continue
                if isinstance(result, list):
                    all_entities.extend(result)
            
            # Deduplicate and enhance entities
            unique_entities = self._deduplicate_entities(all_entities)
            enhanced_entities = await self._enhance_entities(unique_entities, text)
            
            logger.info("Entity extraction completed", 
                       event_id=event.event_id,
                       entity_count=len(enhanced_entities))
            
            return enhanced_entities
            
        except Exception as e:
            logger.error("Entity extraction failed", 
                        error=str(e), 
                        event_id=event.event_id)
            return []
    
    async def _extract_financial_entities(self, text: str) -> List[Entity]:
        """Extract financial entities using specialized patterns"""
        entities = []
        
        try:
            # Stock ticker patterns
            ticker_patterns = [
                r'\b([A-Z]{1,5})\s*(?:\([A-Z]{1,5}\))?\s*(?:stock|shares|ticker)',
                r'\$([A-Z]{1,5})\b',
                r'\b([A-Z]{2,5})\s*(?:shares|stock)\b',
                r'\bNYSE:\s*([A-Z]{1,5})\b',
                r'\bNASDAQ:\s*([A-Z]{1,5})\b'
            ]
            
            for pattern in ticker_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    ticker = match.group(1).upper()
                    
                    # Validate ticker (basic checks)
                    if self._is_valid_ticker(ticker):
                        entity = Entity(
                            entity_type="TICKER",
                            entity_value=ticker,
                            confidence=0.8,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            context=text[max(0, match.start()-50):match.end()+50],
                            ticker_symbol=ticker
                        )
                        entities.append(entity)
            
            # Company name patterns
            company_patterns = [
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc\.?|Corp\.?|LLC|Ltd\.?|Co\.?)\b',
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Corporation|Company|Incorporated)\b',
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Group|Holdings|Technologies|Systems)\b'
            ]
            
            for pattern in company_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    company_name = match.group(1).strip()
                    
                    if len(company_name) > 2 and self._is_valid_company_name(company_name):
                        entity = Entity(
                            entity_type="COMPANY",
                            entity_value=company_name,
                            confidence=0.7,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            context=text[max(0, match.start()-50):match.end()+50]
                        )
                        entities.append(entity)
            
            # Financial metrics
            financial_patterns = {
                'REVENUE': r'\$(\d+(?:\.\d+)?)\s*(?:billion|million|B|M)?\s*(?:in\s+)?revenue',
                'PROFIT': r'\$(\d+(?:\.\d+)?)\s*(?:billion|million|B|M)?\s*(?:in\s+)?(?:profit|earnings)',
                'EPS': r'(?:eps|earnings\s+per\s+share)\s*(?:of\s*)?\$?(\d+\.\d+)',
                'PRICE_TARGET': r'(?:price\s+target|target\s+price)\s*(?:of\s*)?\$(\d+(?:\.\d+)?)',
                'MARKET_CAP': r'market\s+cap\s*(?:of\s*)?\$(\d+(?:\.\d+)?)\s*(?:billion|million|B|M)?'
            }
            
            for metric_type, pattern in financial_patterns.items():
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    value = match.group(1)
                    
                    entity = Entity(
                        entity_type="FINANCIAL_METRIC",
                        entity_value=f"{metric_type}: {value}",
                        confidence=0.8,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        context=text[max(0, match.start()-50):match.end()+50]
                    )
                    entities.append(entity)
        
        except Exception as e:
            logger.error("Financial entity extraction failed", error=str(e))
        
        return entities
    
    async def _extract_named_entities(self, text: str) -> List[Entity]:
        """Extract named entities using NLP models"""
        entities = []
        
        try:
            # spaCy NER
            if self.nlp:
                doc = self.nlp(text)
                
                for ent in doc.ents:
                    # Focus on relevant entity types
                    if ent.label_ in ['ORG', 'PERSON', 'GPE', 'MONEY', 'PERCENT']:
                        entity = Entity(
                            entity_type=ent.label_,
                            entity_value=ent.text,
                            confidence=0.7,
                            start_pos=ent.start_char,
                            end_pos=ent.end_char,
                            context=text[max(0, ent.start_char-50):ent.end_char+50]
                        )
                        entities.append(entity)
            
            # Transformer-based NER
            if self.ner_pipeline:
                ner_results = self.ner_pipeline(text[:512])  # Limit text length
                
                for result in ner_results:
                    if result['score'] > 0.8:  # High confidence only
                        entity = Entity(
                            entity_type=result['entity_group'],
                            entity_value=result['word'],
                            confidence=result['score'],
                            start_pos=result['start'],
                            end_pos=result['end'],
                            context=text[max(0, result['start']-50):result['end']+50]
                        )
                        entities.append(entity)
        
        except Exception as e:
            logger.error("Named entity extraction failed", error=str(e))
        
        return entities
    
    async def _extract_ticker_symbols(self, text: str) -> List[Entity]:
        """Extract and validate ticker symbols"""
        entities = []
        
        try:
            # Extract potential tickers
            ticker_candidates = re.findall(r'\b([A-Z]{1,5})\b', text)
            
            for ticker in set(ticker_candidates):  # Remove duplicates
                # Skip common false positives
                if ticker in ['THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAD', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'SHE', 'USE', 'WAY', 'WHO']:
                    continue
                
                # Check if it's a known ticker or validate
                if ticker in self.known_tickers or await self._validate_ticker(ticker):
                    # Find all occurrences
                    for match in re.finditer(r'\b' + re.escape(ticker) + r'\b', text):
                        entity = Entity(
                            entity_type="TICKER",
                            entity_value=ticker,
                            confidence=0.9 if ticker in self.known_tickers else 0.6,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            context=text[max(0, match.start()-50):match.end()+50],
                            ticker_symbol=ticker
                        )
                        entities.append(entity)
        
        except Exception as e:
            logger.error("Ticker extraction failed", error=str(e))
        
        return entities
    
    async def _extract_financial_terms(self, text: str) -> List[Entity]:
        """Extract financial terms and concepts"""
        entities = []
        
        try:
            financial_terms = {
                'ECONOMIC_INDICATOR': [
                    'gdp', 'inflation', 'unemployment', 'cpi', 'ppi', 'fed rate',
                    'interest rate', 'yield curve', 'employment', 'retail sales'
                ],
                'FINANCIAL_CONCEPT': [
                    'earnings', 'revenue', 'profit', 'margin', 'ebitda', 'cash flow',
                    'dividend', 'buyback', 'ipo', 'merger', 'acquisition', 'guidance'
                ],
                'MARKET_SEGMENT': [
                    'technology', 'healthcare', 'finance', 'energy', 'consumer',
                    'industrial', 'materials', 'utilities', 'real estate'
                ]
            }
            
            for category, terms in financial_terms.items():
                for term in terms:
                    pattern = r'\b' + re.escape(term) + r'\b'
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        entity = Entity(
                            entity_type=category,
                            entity_value=term,
                            confidence=0.6,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            context=text[max(0, match.start()-50):match.end()+50]
                        )
                        entities.append(entity)
        
        except Exception as e:
            logger.error("Financial terms extraction failed", error=str(e))
        
        return entities
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities"""
        seen = set()
        unique_entities = []
        
        for entity in entities:
            # Create a key for deduplication
            key = (entity.entity_type, entity.entity_value.lower(), entity.start_pos)
            
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities
    
    async def _enhance_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Enhance entities with additional information"""
        enhanced = []
        
        for entity in entities:
            try:
                # Enhance ticker entities with financial data
                if entity.entity_type == "TICKER" and entity.ticker_symbol:
                    financial_info = await self._get_ticker_info(entity.ticker_symbol)
                    if financial_info:
                        entity.exchange = financial_info.get('exchange')
                        entity.sector = financial_info.get('sector')
                        entity.market_cap = financial_info.get('market_cap')
                
                # Enhance company entities with ticker mapping
                elif entity.entity_type in ["COMPANY", "ORG"]:
                    ticker = self._find_company_ticker(entity.entity_value)
                    if ticker:
                        entity.ticker_symbol = ticker
                        financial_info = await self._get_ticker_info(ticker)
                        if financial_info:
                            entity.exchange = financial_info.get('exchange')
                            entity.sector = financial_info.get('sector')
                            entity.market_cap = financial_info.get('market_cap')
                
                enhanced.append(entity)
                
            except Exception as e:
                logger.error("Entity enhancement failed", 
                           error=str(e), 
                           entity=entity.entity_value)
                enhanced.append(entity)  # Add unenhanced entity
        
        return enhanced
    
    async def _validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker symbol is real"""
        try:
            # Check cache first
            if ticker in self.ticker_cache:
                return self.ticker_cache[ticker]
            
            # Simple validation using yfinance
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # If we get basic info, it's likely a valid ticker
                is_valid = bool(info.get('symbol') or info.get('shortName'))
                self.ticker_cache[ticker] = is_valid
                
                return is_valid
                
            except Exception:
                self.ticker_cache[ticker] = False
                return False
                
        except Exception as e:
            logger.error("Ticker validation failed", error=str(e), ticker=ticker)
            return False
    
    async def _get_ticker_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get financial information for ticker"""
        try:
            # Check cache first
            cache_key = f"info_{ticker}"
            if cache_key in self.ticker_cache:
                return self.ticker_cache[cache_key]
            
            # Fetch from yfinance
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if info:
                financial_info = {
                    'exchange': info.get('exchange'),
                    'sector': info.get('sector'),
                    'industry': info.get('industry'),
                    'market_cap': self._format_market_cap(info.get('marketCap')),
                    'company_name': info.get('longName') or info.get('shortName')
                }
                
                self.ticker_cache[cache_key] = financial_info
                return financial_info
            
        except Exception as e:
            logger.error("Failed to get ticker info", error=str(e), ticker=ticker)
        
        return None
    
    def _format_market_cap(self, market_cap: Optional[int]) -> Optional[str]:
        """Format market cap into readable string"""
        if not market_cap:
            return None
        
        if market_cap >= 1e12:
            return f"${market_cap/1e12:.1f}T"
        elif market_cap >= 1e9:
            return f"${market_cap/1e9:.1f}B"
        elif market_cap >= 1e6:
            return f"${market_cap/1e6:.1f}M"
        else:
            return f"${market_cap:,.0f}"
    
    def _find_company_ticker(self, company_name: str) -> Optional[str]:
        """Find ticker symbol for company name"""
        # Check known mappings first
        normalized_name = company_name.lower().strip()
        
        for ticker, names in self.known_tickers.items():
            if isinstance(names, list):
                for name in names:
                    if normalized_name in name.lower() or name.lower() in normalized_name:
                        return ticker
        
        return None
    
    def _is_valid_ticker(self, ticker: str) -> bool:
        """Basic ticker validation"""
        return (
            len(ticker) >= 1 and len(ticker) <= 5 and 
            ticker.isalpha() and 
            ticker.isupper()
        )
    
    def _is_valid_company_name(self, company_name: str) -> bool:
        """Basic company name validation"""
        return (
            len(company_name) > 2 and 
            not company_name.isupper() and  # Avoid all-caps words
            not company_name.islower()      # Should have proper capitalization
        )
    
    def _load_known_tickers(self) -> Dict[str, Any]:
        """Load known ticker symbols and company mappings"""
        # This would be expanded with a comprehensive database
        return {
            'AAPL': ['Apple Inc', 'Apple'],
            'GOOGL': ['Alphabet Inc', 'Google'],
            'MSFT': ['Microsoft Corporation', 'Microsoft'],
            'AMZN': ['Amazon.com Inc', 'Amazon'],
            'TSLA': ['Tesla Inc', 'Tesla'],
            'META': ['Meta Platforms Inc', 'Facebook', 'Meta'],
            'NVDA': ['NVIDIA Corporation', 'NVIDIA'],
            'NFLX': ['Netflix Inc', 'Netflix'],
            'BABA': ['Alibaba Group', 'Alibaba'],
            'V': ['Visa Inc', 'Visa'],
            'JNJ': ['Johnson & Johnson', 'J&J'],
            'WMT': ['Walmart Inc', 'Walmart'],
            'PG': ['Procter & Gamble', 'P&G'],
            'UNH': ['UnitedHealth Group', 'UnitedHealth'],
            'HD': ['Home Depot', 'The Home Depot'],
            'MA': ['Mastercard', 'MasterCard'],
            'BAC': ['Bank of America', 'BofA'],
            'XOM': ['Exxon Mobil', 'ExxonMobil'],
            'DIS': ['Walt Disney', 'Disney'],
            'ADBE': ['Adobe Inc', 'Adobe']
        }
    
    def _load_sector_mappings(self) -> Dict[str, str]:
        """Load sector classifications"""
        return {
            'technology': 'Technology',
            'healthcare': 'Healthcare',
            'financials': 'Financial Services',
            'consumer_discretionary': 'Consumer Cyclical',
            'communication': 'Communication Services',
            'industrials': 'Industrials',
            'consumer_staples': 'Consumer Defensive',
            'energy': 'Energy',
            'utilities': 'Utilities',
            'real_estate': 'Real Estate',
            'materials': 'Basic Materials'
        }
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.http_client.aclose() 
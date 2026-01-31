"""
Configuration loader for Idea Database evaluation criteria
Loads and validates configuration from centralized YAML file
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger(__name__)


class IdeaDatabaseConfigLoader:
    """Loads and manages Idea Database evaluation criteria configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.config = None
        self._load_config()
    
    def _find_config_file(self) -> str:
        """Find the evaluation criteria config file"""
        # Try multiple possible locations
        possible_paths = [
            "/app/evaluation_config/evaluation_criteria.yml",  # Docker mounted path
            "/app/config/evaluation_criteria.yml",  # Docker container path
            "config/evaluation_criteria.yml",       # Relative to project root
            "../../../config/evaluation_criteria.yml",  # Relative to email_processor
            "../../../../config/evaluation_criteria.yml",  # One more level up
            os.path.expanduser("~/AI Coding/AI Research Platform/config/evaluation_criteria.yml")  # Absolute fallback
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                logger.info("Found evaluation config", path=path)
                return path
        
        # Fallback to default location
        default_path = "config/evaluation_criteria.yml"
        logger.warning("Config file not found, using default", path=default_path)
        return default_path
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info("Evaluation config loaded successfully", path=self.config_path)
        except FileNotFoundError:
            logger.error("Evaluation config file not found", path=self.config_path)
            self.config = self._get_default_config()
        except yaml.YAMLError as e:
            logger.error("Failed to parse evaluation config", path=self.config_path, error=str(e))
            self.config = self._get_default_config()
        except Exception as e:
            logger.error("Unexpected error loading config", path=self.config_path, error=str(e))
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if file loading fails"""
        logger.warning("Using default Idea Database evaluation configuration")
        return {
            "idea_database": {
                "categorization": {
                    "confidence_thresholds": {
                        "high": 0.70,
                        "medium": 0.40,
                        "low": 0.00,
                        "manual_review_required": 0.70
                    },
                    "category_keywords": {
                        "business_ideas": [
                            "startup", "business", "entrepreneur", "market", "revenue", 
                            "product", "service", "funding", "investment", "venture"
                        ],
                        "dev_tools": [
                            "github", "python", "javascript", "framework", "library", 
                            "api", "development", "coding", "programming", "software"
                        ],
                        "research_papers": [
                            "paper", "study", "research", "analysis", "findings", 
                            "methodology", "academic", "journal", "publication", "doi"
                        ],
                        "ai_implementations": [
                            "ai", "machine learning", "neural", "model", "algorithm", 
                            "automation", "deep learning", "nlp", "computer vision", "llm"
                        ],
                        "industry_news": [
                            "news", "announcement", "company", "industry", "market", 
                            "update", "trend", "acquisition", "merger", "ipo"
                        ],
                        "reference_materials": [
                            "tutorial", "guide", "documentation", "how-to", "reference", 
                            "manual", "examples", "best practices", "tips", "tricks"
                        ]
                    },
                    "scoring": {
                        "subject_line_bonus": 2,
                        "confidence_normalization": 10
                    }
                },
                "entity_extraction": {
                    "confidence_scoring": {
                        "exact_match": [0.95, 1.00],
                        "fuzzy_match": [0.70, 0.94],
                        "context_based": [0.50, 0.69],
                        "uncertain": [0.00, 0.49]
                    }
                },
                "priority_scoring": {
                    "weights": {
                        "category_relevance": 0.40,
                        "content_quality": 0.30,
                        "timeliness": 0.20,
                        "source_credibility": 0.10
                    }
                }
            }
        }
    
    def get_idea_database_config(self) -> Dict[str, Any]:
        """Get Idea Database configuration"""
        return self.config.get("idea_database", {})
    
    def get_categorization_config(self) -> Dict[str, Any]:
        """Get categorization configuration"""
        return self.get_idea_database_config().get("categorization", {})
    
    def get_confidence_thresholds(self) -> Dict[str, float]:
        """Get confidence thresholds for categorization"""
        categorization = self.get_categorization_config()
        return categorization.get("confidence_thresholds", {
            "high": 0.70,
            "medium": 0.40,
            "low": 0.00,
            "manual_review_required": 0.70
        })
    
    def get_category_keywords(self) -> Dict[str, List[str]]:
        """Get category keywords for scoring"""
        categorization = self.get_categorization_config()
        return categorization.get("category_keywords", {})
    
    def get_scoring_config(self) -> Dict[str, Any]:
        """Get scoring configuration"""
        categorization = self.get_categorization_config()
        return categorization.get("scoring", {
            "subject_line_bonus": 2,
            "confidence_normalization": 10
        })
    
    def get_subject_line_bonus(self) -> int:
        """Get subject line bonus multiplier"""
        scoring = self.get_scoring_config()
        return scoring.get("subject_line_bonus", 2)
    
    def get_confidence_normalization(self) -> int:
        """Get confidence normalization factor"""
        scoring = self.get_scoring_config()
        return scoring.get("confidence_normalization", 10)
    
    def get_manual_review_threshold(self) -> float:
        """Get threshold for manual review requirement"""
        thresholds = self.get_confidence_thresholds()
        return thresholds.get("manual_review_required", 0.70)
    
    def get_entity_extraction_config(self) -> Dict[str, Any]:
        """Get entity extraction configuration"""
        return self.get_idea_database_config().get("entity_extraction", {})
    
    def get_entity_confidence_scoring(self) -> Dict[str, List[float]]:
        """Get entity confidence scoring ranges"""
        entity_config = self.get_entity_extraction_config()
        return entity_config.get("confidence_scoring", {
            "exact_match": [0.95, 1.00],
            "fuzzy_match": [0.70, 0.94],
            "context_based": [0.50, 0.69],
            "uncertain": [0.00, 0.49]
        })
    
    def get_priority_scoring_config(self) -> Dict[str, Any]:
        """Get priority scoring configuration"""
        return self.get_idea_database_config().get("priority_scoring", {})
    
    def get_priority_weights(self) -> Dict[str, float]:
        """Get priority scoring component weights"""
        priority_config = self.get_priority_scoring_config()
        return priority_config.get("weights", {
            "category_relevance": 0.40,
            "content_quality": 0.30,
            "timeliness": 0.20,
            "source_credibility": 0.10
        })
    
    def reload_config(self):
        """Reload configuration from file"""
        logger.info("Reloading Idea Database evaluation configuration")
        self._load_config()


# Global config loader instance
_config_loader = None


def get_config_loader() -> IdeaDatabaseConfigLoader:
    """Get global configuration loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = IdeaDatabaseConfigLoader()
    return _config_loader


def reload_config():
    """Reload global configuration"""
    global _config_loader
    if _config_loader:
        _config_loader.reload_config()
    else:
        _config_loader = IdeaDatabaseConfigLoader() 
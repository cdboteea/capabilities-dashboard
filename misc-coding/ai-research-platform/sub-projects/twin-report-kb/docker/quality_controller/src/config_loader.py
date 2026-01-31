"""
Configuration loader for Quality Controller evaluation criteria
Loads and validates configuration from centralized YAML file
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class QualityControllerConfigLoader:
    """Loads and manages Quality Controller evaluation criteria configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.config = None
        self._load_config()
    
    def _find_config_file(self) -> str:
        """Find the evaluation criteria config file"""
        # Try multiple possible locations
        possible_paths = [
            "/app/config/evaluation_criteria.yml",  # Docker container path
            "config/evaluation_criteria.yml",       # Relative to project root
            "../../../config/evaluation_criteria.yml",  # Relative to quality_controller
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
        logger.warning("Using default Quality Controller evaluation configuration")
        return {
            "quality_controller": {
                "component_weights": {
                    "fact_checking": 0.30,
                    "citation_verification": 0.25,
                    "quality_assessment": 0.25,
                    "source_evaluation": 0.20
                },
                "thresholds": {
                    "excellent": 0.90,
                    "very_good": 0.80,
                    "good": 0.70,
                    "satisfactory": 0.60,
                    "needs_improvement": 0.50,
                    "poor": 0.00
                },
                "fact_checking": {
                    "ai_validation_confidence": 0.80,
                    "external_verification_weight": 0.60,
                    "consistency_check_weight": 0.40,
                    "claim_verification_timeout": 30,
                    "max_claims_per_analysis": 50,
                    "verification_sources": [
                        "wikipedia", "scholarly", "news_apis", "fact_check_sites"
                    ]
                },
                "citation_verification": {
                    "accessibility_weight": 0.40,
                    "credibility_weight": 0.35,
                    "relevance_weight": 0.25,
                    "doi_verification": True,
                    "url_validation": True,
                    "citation_format_check": True,
                    "max_citation_age_years": 10
                },
                "quality_assessment": {
                    "readability_weight": 0.25,
                    "coherence_weight": 0.25,
                    "completeness_weight": 0.25,
                    "structure_weight": 0.25,
                    "min_word_count": 100,
                    "max_sentence_length": 50,
                    "readability_target": "college_level"
                },
                "source_evaluation": {
                    "authority_weight": 0.40,
                    "recency_weight": 0.30,
                    "relevance_weight": 0.30,
                    "trusted_domains": [
                        "edu", "gov", "org", "nature.com", "science.org", 
                        "ieee.org", "acm.org", "pubmed.ncbi.nlm.nih.gov"
                    ],
                    "blacklisted_domains": [
                        "example.com", "test.com", "spam.com"
                    ],
                    "max_source_age_days": 365
                }
            }
        }
    
    def get_quality_controller_config(self) -> Dict[str, Any]:
        """Get Quality Controller configuration"""
        return self.config.get("quality_controller", {})
    
    def get_quality_controller_weights(self) -> Dict[str, float]:
        """Get Quality Controller component weights"""
        config = self.get_quality_controller_config()
        return config.get("component_weights", {
            "fact_checking": 0.30,
            "citation_verification": 0.25,
            "quality_assessment": 0.25,
            "source_evaluation": 0.20
        })
    
    def get_quality_thresholds(self) -> Dict[str, float]:
        """Get quality level thresholds"""
        config = self.get_quality_controller_config()
        return config.get("thresholds", {
            "excellent": 0.90,
            "very_good": 0.80,
            "good": 0.70,
            "satisfactory": 0.60,
            "needs_improvement": 0.50,
            "poor": 0.00
        })
    
    def get_fact_checking_config(self) -> Dict[str, Any]:
        """Get fact checking configuration"""
        config = self.get_quality_controller_config()
        return config.get("fact_checking", {})
    
    def get_citation_verification_config(self) -> Dict[str, Any]:
        """Get citation verification configuration"""
        config = self.get_quality_controller_config()
        return config.get("citation_verification", {})
    
    def get_quality_assessment_config(self) -> Dict[str, Any]:
        """Get quality assessment configuration"""
        config = self.get_quality_controller_config()
        return config.get("quality_assessment", {})
    
    def get_source_evaluation_config(self) -> Dict[str, Any]:
        """Get source evaluation configuration"""
        config = self.get_quality_controller_config()
        return config.get("source_evaluation", {})
    
    def get_ai_validation_confidence(self) -> float:
        """Get AI validation confidence threshold"""
        fact_config = self.get_fact_checking_config()
        return fact_config.get("ai_validation_confidence", 0.80)
    
    def get_verification_sources(self) -> list:
        """Get list of verification sources"""
        fact_config = self.get_fact_checking_config()
        return fact_config.get("verification_sources", [
            "wikipedia", "scholarly", "news_apis", "fact_check_sites"
        ])
    
    def get_trusted_domains(self) -> list:
        """Get list of trusted domains"""
        source_config = self.get_source_evaluation_config()
        return source_config.get("trusted_domains", [
            "edu", "gov", "org", "nature.com", "science.org"
        ])
    
    def get_blacklisted_domains(self) -> list:
        """Get list of blacklisted domains"""
        source_config = self.get_source_evaluation_config()
        return source_config.get("blacklisted_domains", [])
    
    def get_max_citation_age_years(self) -> int:
        """Get maximum citation age in years"""
        citation_config = self.get_citation_verification_config()
        return citation_config.get("max_citation_age_years", 10)
    
    def get_max_source_age_days(self) -> int:
        """Get maximum source age in days"""
        source_config = self.get_source_evaluation_config()
        return source_config.get("max_source_age_days", 365)
    
    def get_readability_target(self) -> str:
        """Get readability target level"""
        quality_config = self.get_quality_assessment_config()
        return quality_config.get("readability_target", "college_level")
    
    def get_min_word_count(self) -> int:
        """Get minimum word count for quality assessment"""
        quality_config = self.get_quality_assessment_config()
        return quality_config.get("min_word_count", 100)
    
    def get_max_sentence_length(self) -> int:
        """Get maximum sentence length"""
        quality_config = self.get_quality_assessment_config()
        return quality_config.get("max_sentence_length", 50)
    
    def get_citation_weights(self) -> Dict[str, float]:
        """Get citation verification component weights"""
        citation_config = self.get_citation_verification_config()
        return {
            "accessibility": citation_config.get("accessibility_weight", 0.40),
            "credibility": citation_config.get("credibility_weight", 0.35),
            "relevance": citation_config.get("relevance_weight", 0.25)
        }
    
    def get_quality_assessment_weights(self) -> Dict[str, float]:
        """Get quality assessment component weights"""
        quality_config = self.get_quality_assessment_config()
        return {
            "readability": quality_config.get("readability_weight", 0.25),
            "coherence": quality_config.get("coherence_weight", 0.25),
            "completeness": quality_config.get("completeness_weight", 0.25),
            "structure": quality_config.get("structure_weight", 0.25)
        }
    
    def get_source_evaluation_weights(self) -> Dict[str, float]:
        """Get source evaluation component weights"""
        source_config = self.get_source_evaluation_config()
        return {
            "authority": source_config.get("authority_weight", 0.40),
            "recency": source_config.get("recency_weight", 0.30),
            "relevance": source_config.get("relevance_weight", 0.30)
        }
    
    def get_fact_checking_weights(self) -> Dict[str, float]:
        """Get fact checking component weights"""
        fact_config = self.get_fact_checking_config()
        return {
            "external_verification": fact_config.get("external_verification_weight", 0.60),
            "consistency_check": fact_config.get("consistency_check_weight", 0.40)
        }
    
    def is_doi_verification_enabled(self) -> bool:
        """Check if DOI verification is enabled"""
        citation_config = self.get_citation_verification_config()
        return citation_config.get("doi_verification", True)
    
    def is_url_validation_enabled(self) -> bool:
        """Check if URL validation is enabled"""
        citation_config = self.get_citation_verification_config()
        return citation_config.get("url_validation", True)
    
    def is_citation_format_check_enabled(self) -> bool:
        """Check if citation format checking is enabled"""
        citation_config = self.get_citation_verification_config()
        return citation_config.get("citation_format_check", True)
    
    def reload_config(self):
        """Reload configuration from file"""
        logger.info("Reloading Quality Controller evaluation configuration")
        self._load_config()


# Global config loader instance
_config_loader = None


def get_config_loader() -> QualityControllerConfigLoader:
    """Get global configuration loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = QualityControllerConfigLoader()
    return _config_loader


def reload_config():
    """Reload global configuration"""
    global _config_loader
    if _config_loader:
        _config_loader.reload_config()
    else:
        _config_loader = QualityControllerConfigLoader() 
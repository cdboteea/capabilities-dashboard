"""
Configuration loader for evaluation criteria
Loads and validates configuration from centralized YAML file
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class EvaluationConfigLoader:
    """Loads and manages evaluation criteria configuration"""
    
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
            "../../../config/evaluation_criteria.yml",  # Relative to diff_worker
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
        logger.warning("Using default evaluation configuration")
        return {
            "twin_report_kb": {
                "diff_analysis": {
                    "weights": {
                        "completeness": 0.30,
                        "accuracy": 0.25,
                        "usefulness": 0.25,
                        "coherence": 0.20
                    },
                    "thresholds": {
                        "excellent": 0.90,
                        "very_good": 0.80,
                        "good": 0.70,
                        "satisfactory": 0.60,
                        "needs_improvement": 0.50,
                        "poor": 0.00
                    },
                    "completeness": {
                        "required_components_weight": 0.40,
                        "summary_quality_weight": 0.30,
                        "gap_analysis_depth_weight": 0.30,
                        "summary_thresholds": {
                            "basic_length": 50,
                            "detailed_length": 150
                        }
                    },
                    "accuracy": {
                        "confidence_weight": 0.60,
                        "ai_validation_weight": 0.40,
                        "ai_validation_model": "deepseek-r1",
                        "ai_validation_temperature": 0.1
                    },
                    "usefulness": {
                        "actionable_gaps_weight": 0.30,
                        "quality_overlaps_weight": 0.20,
                        "detailed_contradictions_weight": 0.20,
                        "summary_insights_weight": 0.30,
                        "thresholds": {
                            "actionable_gap_min_length": 20,
                            "detailed_contradiction_min_length": 50
                        },
                        "insight_keywords": [
                            "identified", "analysis", "shows", "reveals", "indicates"
                        ]
                    },
                    "coherence": {
                        "summary_findings_alignment_weight": 0.70,
                        "confidence_findings_correlation_weight": 0.20,
                        "metadata_consistency_weight": 0.10,
                        "thresholds": {
                            "high_confidence": 0.80,
                            "low_confidence": 0.40,
                            "substantial_findings": 2
                        }
                    }
                },
                "gap_analysis": {
                    "priority_scores": {
                        "high": 0.90,
                        "medium": 0.60,
                        "low": 0.30
                    }
                },
                "article_quality": {
                    "weights": {
                        "content": 0.30,
                        "structure": 0.20,
                        "citations": 0.25,
                        "depth": 0.25
                    }
                }
            }
        }
    
    def get_diff_analysis_config(self) -> Dict[str, Any]:
        """Get diff analysis configuration"""
        return self.config.get("twin_report_kb", {}).get("diff_analysis", {})
    
    def get_gap_analysis_config(self) -> Dict[str, Any]:
        """Get gap analysis configuration"""
        return self.config.get("twin_report_kb", {}).get("gap_analysis", {})
    
    def get_article_quality_config(self) -> Dict[str, Any]:
        """Get article quality configuration"""
        return self.config.get("twin_report_kb", {}).get("article_quality", {})
    
    def get_quality_weights(self) -> Dict[str, float]:
        """Get quality scoring component weights"""
        diff_config = self.get_diff_analysis_config()
        return diff_config.get("weights", {
            "completeness": 0.30,
            "accuracy": 0.25,
            "usefulness": 0.25,
            "coherence": 0.20
        })
    
    def get_quality_thresholds(self) -> Dict[str, float]:
        """Get quality level thresholds"""
        diff_config = self.get_diff_analysis_config()
        return diff_config.get("thresholds", {
            "excellent": 0.90,
            "very_good": 0.80,
            "good": 0.70,
            "satisfactory": 0.60,
            "needs_improvement": 0.50,
            "poor": 0.00
        })
    
    def get_completeness_config(self) -> Dict[str, Any]:
        """Get completeness scoring configuration"""
        diff_config = self.get_diff_analysis_config()
        return diff_config.get("completeness", {})
    
    def get_accuracy_config(self) -> Dict[str, Any]:
        """Get accuracy scoring configuration"""
        diff_config = self.get_diff_analysis_config()
        return diff_config.get("accuracy", {})
    
    def get_usefulness_config(self) -> Dict[str, Any]:
        """Get usefulness scoring configuration"""
        diff_config = self.get_diff_analysis_config()
        return diff_config.get("usefulness", {})
    
    def get_coherence_config(self) -> Dict[str, Any]:
        """Get coherence scoring configuration"""
        diff_config = self.get_diff_analysis_config()
        return diff_config.get("coherence", {})
    
    def get_priority_scores(self) -> Dict[str, float]:
        """Get gap analysis priority scores"""
        gap_config = self.get_gap_analysis_config()
        return gap_config.get("priority_scores", {
            "high": 0.90,
            "medium": 0.60,
            "low": 0.30
        })
    
    def get_insight_keywords(self) -> list:
        """Get insight keywords for usefulness scoring"""
        usefulness_config = self.get_usefulness_config()
        return usefulness_config.get("insight_keywords", [
            "identified", "analysis", "shows", "reveals", "indicates"
        ])
    
    def get_ai_validation_model(self) -> str:
        """Get AI validation model name"""
        accuracy_config = self.get_accuracy_config()
        return accuracy_config.get("ai_validation_model", "deepseek-r1")
    
    def get_ai_validation_temperature(self) -> float:
        """Get AI validation temperature"""
        accuracy_config = self.get_accuracy_config()
        return accuracy_config.get("ai_validation_temperature", 0.1)
    
    def reload_config(self):
        """Reload configuration from file"""
        logger.info("Reloading evaluation configuration")
        self._load_config()


# Global config loader instance
_config_loader = None


def get_config_loader() -> EvaluationConfigLoader:
    """Get global configuration loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = EvaluationConfigLoader()
    return _config_loader


def reload_config():
    """Reload global configuration"""
    global _config_loader
    if _config_loader:
        _config_loader.reload_config()
    else:
        _config_loader = EvaluationConfigLoader() 
#!/usr/bin/env python3
"""
Validation script for evaluation criteria configuration
Ensures all metrics, thresholds, and weights are logically consistent
"""

import yaml
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import argparse


class EvaluationConfigValidator:
    """Validates evaluation criteria configuration for consistency and logic"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.errors = []
        self.warnings = []
    
    def _load_config(self) -> Dict[str, Any]:
        """Load the YAML configuration file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Failed to load config file {self.config_path}: {e}")
    
    def validate_all(self) -> bool:
        """Run all validation checks"""
        print(f"Validating evaluation criteria config: {self.config_path}")
        print("=" * 60)
        
        # Run all validation checks
        self._validate_weights()
        self._validate_thresholds()
        self._validate_score_ranges()
        self._validate_keyword_lists()
        self._validate_model_references()
        self._validate_environment_overrides()
        self._validate_configuration_metadata()
        
        # Report results
        self._print_results()
        
        return len(self.errors) == 0
    
    def _validate_weights(self):
        """Validate that all component weights sum to 1.0"""
        print("Validating component weights...")
        
        weight_paths = [
            ("twin_report_kb.diff_analysis.weights", "Diff Analysis"),
            ("twin_report_kb.article_quality.weights", "Article Quality"),
            ("idea_database.priority_scoring.weights", "Priority Scoring")
        ]
        
        for path, description in weight_paths:
            weights = self._get_nested_value(path)
            if weights:
                total = sum(weights.values())
                if abs(total - 1.0) > 0.001:  # Allow for small floating point errors
                    self.errors.append(f"{description} weights sum to {total:.3f}, should be 1.0")
                else:
                    print(f"  ✓ {description} weights sum correctly ({total:.3f})")
    
    def _validate_thresholds(self):
        """Validate that thresholds are in logical order"""
        print("\nValidating threshold ordering...")
        
        # Twin-Report KB thresholds
        thresholds = self._get_nested_value("twin_report_kb.diff_analysis.thresholds")
        if thresholds:
            expected_order = ["excellent", "very_good", "good", "satisfactory", "needs_improvement", "poor"]
            values = [thresholds.get(level, 0) for level in expected_order]
            
            # Check descending order
            for i in range(len(values) - 1):
                if values[i] < values[i + 1]:
                    self.errors.append(f"Threshold {expected_order[i]} ({values[i]}) should be >= {expected_order[i+1]} ({values[i+1]})")
            
            if len(self.errors) == 0:
                print("  ✓ Twin-Report KB thresholds in correct order")
        
        # Confidence thresholds
        conf_thresholds = self._get_nested_value("idea_database.categorization.confidence_thresholds")
        if conf_thresholds:
            if conf_thresholds["high"] <= conf_thresholds["medium"]:
                self.errors.append("High confidence threshold should be > medium confidence threshold")
            if conf_thresholds["medium"] <= conf_thresholds["low"]:
                self.errors.append("Medium confidence threshold should be > low confidence threshold")
            
            if len([e for e in self.errors if "confidence threshold" in e]) == 0:
                print("  ✓ Confidence thresholds in correct order")
    
    def _validate_score_ranges(self):
        """Validate that all scores are in 0-1 range"""
        print("\nValidating score ranges...")
        
        score_paths = [
            ("twin_report_kb.diff_analysis.thresholds", "Diff Analysis thresholds"),
            ("twin_report_kb.gap_analysis.priority_scores", "Gap Analysis priority scores"),
            ("idea_database.categorization.confidence_thresholds", "Confidence thresholds"),
            ("real_time_intel.source_evaluation.thresholds", "Source evaluation thresholds"),
            ("cross_platform.llm_performance.standards", "LLM performance standards")
        ]
        
        for path, description in score_paths:
            values = self._get_nested_value(path)
            if values and isinstance(values, dict):
                for key, value in values.items():
                    if isinstance(value, (int, float)):
                        if not (0.0 <= value <= 1.0):
                            self.errors.append(f"{description}.{key} = {value} is outside 0-1 range")
        
        print("  ✓ Score ranges validated")
    
    def _validate_keyword_lists(self):
        """Validate that keyword lists are non-empty and contain strings"""
        print("\nValidating keyword lists...")
        
        keyword_paths = [
            ("idea_database.categorization.category_keywords", "Category keywords"),
            ("twin_report_kb.diff_analysis.usefulness.insight_keywords", "Insight keywords"),
            ("twin_report_kb.article_quality.content.example_keywords", "Example keywords"),
            ("twin_report_kb.article_quality.content.technical_keywords", "Technical keywords")
        ]
        
        for path, description in keyword_paths:
            keywords = self._get_nested_value(path)
            if keywords:
                if isinstance(keywords, dict):
                    # Category keywords - check each category
                    for category, keyword_list in keywords.items():
                        if not isinstance(keyword_list, list) or len(keyword_list) == 0:
                            self.errors.append(f"{description}.{category} is empty or not a list")
                        elif not all(isinstance(k, str) for k in keyword_list):
                            self.errors.append(f"{description}.{category} contains non-string keywords")
                elif isinstance(keywords, list):
                    # Simple keyword list
                    if len(keywords) == 0:
                        self.errors.append(f"{description} is empty")
                    elif not all(isinstance(k, str) for k in keywords):
                        self.errors.append(f"{description} contains non-string keywords")
        
        print("  ✓ Keyword lists validated")
    
    def _validate_model_references(self):
        """Validate that referenced models exist in the platform"""
        print("\nValidating model references...")
        
        valid_models = {
            "deepseek-r1", "qwen-3-72b", "qwq-32b", "llama-4-scout", 
            "llama-4-maverick", "qwen-2.5vl"
        }
        
        # Check AI validation model
        ai_model = self._get_nested_value("twin_report_kb.diff_analysis.accuracy.ai_validation_model")
        if ai_model and ai_model not in valid_models:
            self.errors.append(f"AI validation model '{ai_model}' not in valid models: {valid_models}")
        
        # Check model thresholds
        model_thresholds = self._get_nested_value("cross_platform.llm_performance.model_thresholds")
        if model_thresholds:
            for model in model_thresholds.keys():
                if model not in valid_models:
                    self.warnings.append(f"Model '{model}' in thresholds not in known valid models")
        
        print("  ✓ Model references validated")
    
    def _validate_environment_overrides(self):
        """Validate that environment overrides reference valid base configuration"""
        print("\nValidating environment overrides...")
        
        environments = self._get_nested_value("configuration.environments")
        if environments:
            for env_name, env_config in environments.items():
                if env_config:  # Skip empty environments
                    # Check that override paths exist in base config
                    self._validate_override_paths(env_config, env_name)
        
        print("  ✓ Environment overrides validated")
    
    def _validate_configuration_metadata(self):
        """Validate configuration metadata"""
        print("\nValidating configuration metadata...")
        
        config_meta = self._get_nested_value("configuration")
        if config_meta:
            required_fields = ["version", "last_updated", "next_review_date"]
            for field in required_fields:
                if field not in config_meta:
                    self.errors.append(f"Configuration metadata missing required field: {field}")
        
        print("  ✓ Configuration metadata validated")
    
    def _validate_override_paths(self, override_config: Dict[str, Any], env_name: str, path: str = ""):
        """Recursively validate that override paths exist in base configuration"""
        for key, value in override_config.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check if this path exists in base config
            base_value = self._get_nested_value(current_path)
            if base_value is None:
                self.errors.append(f"Environment '{env_name}' overrides non-existent path: {current_path}")
            
            # Recurse if value is a dict
            if isinstance(value, dict):
                self._validate_override_paths(value, env_name, current_path)
    
    def _get_nested_value(self, path: str) -> Any:
        """Get nested value from config using dot notation"""
        keys = path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _print_results(self):
        """Print validation results"""
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All validation checks passed!")
        elif not self.errors:
            print(f"\n✅ Validation passed with {len(self.warnings)} warnings")
        else:
            print(f"\n❌ Validation failed with {len(self.errors)} errors and {len(self.warnings)} warnings")


def main():
    parser = argparse.ArgumentParser(description="Validate evaluation criteria configuration")
    parser.add_argument(
        "--config", 
        default="config/evaluation_criteria.yml",
        help="Path to evaluation criteria configuration file"
    )
    parser.add_argument(
        "--strict", 
        action="store_true",
        help="Treat warnings as errors"
    )
    
    args = parser.parse_args()
    
    try:
        validator = EvaluationConfigValidator(args.config)
        success = validator.validate_all()
        
        if args.strict and validator.warnings:
            print("\n❌ Strict mode: treating warnings as errors")
            success = False
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Validation failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
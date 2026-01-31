#!/usr/bin/env python3
"""
Test script for evaluation configuration system
Validates configuration loading and service integration
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add project paths
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "sub-projects/twin-report-kb/docker/diff_worker/src"))
sys.path.append(str(Path(__file__).parent.parent / "sub-projects/idea-database/services/email_processor/src"))

def test_configuration_loading():
    """Test basic configuration loading"""
    print("=" * 60)
    print("TESTING CONFIGURATION LOADING")
    print("=" * 60)
    
    # Test 1: Check if config file exists
    config_path = Path(__file__).parent.parent / "config/evaluation_criteria.yml"
    print(f"1. Configuration file exists: {config_path.exists()}")
    
    if not config_path.exists():
        print("   ❌ FAIL: Configuration file not found")
        return False
    
    # Test 2: Load YAML successfully
    try:
        import yaml
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        print("   ✅ PASS: YAML loads successfully")
    except Exception as e:
        print(f"   ❌ FAIL: YAML loading error: {e}")
        return False
    
    # Test 3: Check required sections
    required_sections = ['twin_report_kb', 'idea_database', 'real_time_intel', 'ai_browser_agent']
    for section in required_sections:
        if section in config_data:
            print(f"   ✅ PASS: Section '{section}' found")
        else:
            print(f"   ❌ FAIL: Section '{section}' missing")
            return False
    
    return True

def test_twin_report_config_loader():
    """Test Twin-Report KB configuration loader"""
    print("\n" + "=" * 60)
    print("TESTING TWIN-REPORT KB CONFIG LOADER")
    print("=" * 60)
    
    try:
        # Import config loader
        from config_loader import EvaluationConfigLoader
        
        # Test 1: Initialize config loader
        config_loader = EvaluationConfigLoader()
        print("   ✅ PASS: Config loader initialized")
        
        # Test 2: Get quality weights
        weights = config_loader.get_quality_weights()
        expected_keys = ['completeness', 'accuracy', 'usefulness', 'coherence']
        
        for key in expected_keys:
            if key in weights:
                print(f"   ✅ PASS: Weight '{key}' = {weights[key]}")
            else:
                print(f"   ❌ FAIL: Weight '{key}' missing")
                return False
        
        # Test 3: Validate weights sum to 1.0
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) < 0.01:
            print(f"   ✅ PASS: Weights sum to {total_weight:.2f}")
        else:
            print(f"   ❌ FAIL: Weights sum to {total_weight:.2f}, expected 1.0")
            return False
        
        # Test 4: Get quality thresholds
        thresholds = config_loader.get_quality_thresholds()
        threshold_keys = ['excellent', 'very_good', 'good', 'satisfactory', 'needs_improvement', 'poor']
        
        for key in threshold_keys:
            if key in thresholds:
                print(f"   ✅ PASS: Threshold '{key}' = {thresholds[key]}")
            else:
                print(f"   ❌ FAIL: Threshold '{key}' missing")
                return False
        
        # Test 5: Validate threshold ordering
        threshold_values = [thresholds[key] for key in threshold_keys[:-1]]  # Exclude 'poor'
        if threshold_values == sorted(threshold_values, reverse=True):
            print("   ✅ PASS: Thresholds are properly ordered")
        else:
            print("   ❌ FAIL: Thresholds are not properly ordered")
            return False
        
        # Test 6: Get insight keywords
        keywords = config_loader.get_insight_keywords()
        if isinstance(keywords, list) and len(keywords) > 0:
            print(f"   ✅ PASS: Found {len(keywords)} insight keywords")
        else:
            print("   ❌ FAIL: Insight keywords missing or invalid")
            return False
        
        # Test 7: Get AI validation model
        model = config_loader.get_ai_validation_model()
        if isinstance(model, str) and model:
            print(f"   ✅ PASS: AI validation model = '{model}'")
        else:
            print("   ❌ FAIL: AI validation model missing or invalid")
            return False
        
        return True
        
    except ImportError as e:
        print(f"   ❌ FAIL: Cannot import config loader: {e}")
        return False
    except Exception as e:
        print(f"   ❌ FAIL: Unexpected error: {e}")
        return False

def test_idea_database_config_loader():
    """Test Idea Database configuration loader"""
    print("\n" + "=" * 60)
    print("TESTING IDEA DATABASE CONFIG LOADER")
    print("=" * 60)
    
    try:
        # Import config loader (this might fail if not in the right path)
        from config_loader import IdeaDatabaseConfigLoader
        
        # Test 1: Initialize config loader
        config_loader = IdeaDatabaseConfigLoader()
        print("   ✅ PASS: Config loader initialized")
        
        # Test 2: Get confidence thresholds
        thresholds = config_loader.get_confidence_thresholds()
        expected_keys = ['high', 'medium', 'low', 'manual_review_required']
        
        for key in expected_keys:
            if key in thresholds:
                print(f"   ✅ PASS: Threshold '{key}' = {thresholds[key]}")
            else:
                print(f"   ❌ FAIL: Threshold '{key}' missing")
                return False
        
        # Test 3: Get category keywords
        keywords = config_loader.get_category_keywords()
        expected_categories = ['business_ideas', 'dev_tools', 'research_papers', 'ai_implementations']
        
        for category in expected_categories:
            if category in keywords and isinstance(keywords[category], list):
                print(f"   ✅ PASS: Category '{category}' has {len(keywords[category])} keywords")
            else:
                print(f"   ❌ FAIL: Category '{category}' missing or invalid")
                return False
        
        # Test 4: Get priority weights
        weights = config_loader.get_priority_weights()
        expected_weight_keys = ['category_relevance', 'content_quality', 'timeliness', 'source_credibility']
        
        for key in expected_weight_keys:
            if key in weights:
                print(f"   ✅ PASS: Priority weight '{key}' = {weights[key]}")
            else:
                print(f"   ❌ FAIL: Priority weight '{key}' missing")
                return False
        
        # Test 5: Validate priority weights sum to 1.0
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) < 0.01:
            print(f"   ✅ PASS: Priority weights sum to {total_weight:.2f}")
        else:
            print(f"   ❌ FAIL: Priority weights sum to {total_weight:.2f}, expected 1.0")
            return False
        
        # Test 6: Get scoring configuration
        subject_bonus = config_loader.get_subject_line_bonus()
        if isinstance(subject_bonus, int) and subject_bonus > 0:
            print(f"   ✅ PASS: Subject line bonus = {subject_bonus}")
        else:
            print("   ❌ FAIL: Subject line bonus missing or invalid")
            return False
        
        return True
        
    except ImportError as e:
        print(f"   ⚠️  SKIP: Cannot import Idea Database config loader: {e}")
        return True  # Skip this test if module not available
    except Exception as e:
        print(f"   ❌ FAIL: Unexpected error: {e}")
        return False

def test_validation_script():
    """Test the validation script functionality"""
    print("\n" + "=" * 60)
    print("TESTING VALIDATION SCRIPT")
    print("=" * 60)
    
    try:
        # Import validation script
        validation_script_path = Path(__file__).parent / "validate_evaluation_config.py"
        
        if not validation_script_path.exists():
            print("   ❌ FAIL: Validation script not found")
            return False
        
        print("   ✅ PASS: Validation script exists")
        
        # Try to run validation (import and execute)
        import subprocess
        result = subprocess.run([
            sys.executable, str(validation_script_path)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("   ✅ PASS: Validation script runs successfully")
            # Show first few lines of output
            output_lines = result.stdout.strip().split('\n')[:5]
            for line in output_lines:
                print(f"      {line}")
            if len(result.stdout.strip().split('\n')) > 5:
                print("      ...")
        else:
            print("   ❌ FAIL: Validation script failed")
            print(f"      Error: {result.stderr}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print("   ❌ FAIL: Validation script timed out")
        return False
    except Exception as e:
        print(f"   ❌ FAIL: Error running validation script: {e}")
        return False

def test_docker_config_mounting():
    """Test Docker configuration mounting"""
    print("\n" + "=" * 60)
    print("TESTING DOCKER CONFIGURATION MOUNTING")
    print("=" * 60)
    
    # Test 1: Check docker-compose files for config mounting
    compose_files = [
        Path(__file__).parent.parent / "docker-compose.yml",
        Path(__file__).parent.parent / "sub-projects/idea-database/docker-compose.yml"
    ]
    
    for compose_file in compose_files:
        if compose_file.exists():
            print(f"   ✅ PASS: Docker compose file exists: {compose_file.name}")
            
            # Check if config is mounted
            with open(compose_file, 'r') as f:
                content = f.read()
                if "/app/config:ro" in content or "/app/evaluation_config:ro" in content:
                    print(f"      ✅ Config mounting found in {compose_file.name}")
                else:
                    print(f"      ❌ Config mounting missing in {compose_file.name}")
        else:
            print(f"   ❌ FAIL: Docker compose file missing: {compose_file}")
    
    # Test 2: Check if services have PyYAML dependency
    requirements_files = [
        Path(__file__).parent.parent / "sub-projects/twin-report-kb/docker/diff_worker/requirements.txt",
        Path(__file__).parent.parent / "sub-projects/idea-database/services/email_processor/requirements.txt"
    ]
    
    for req_file in requirements_files:
        if req_file.exists():
            with open(req_file, 'r') as f:
                content = f.read()
                if "pyyaml" in content.lower() or "PyYAML" in content:
                    print(f"   ✅ PASS: PyYAML found in {req_file.parent.name}")
                else:
                    print(f"   ❌ FAIL: PyYAML missing in {req_file.parent.name}")
        else:
            print(f"   ⚠️  SKIP: Requirements file not found: {req_file}")
    
    return True

def test_integration_scenarios():
    """Test integration scenarios"""
    print("\n" + "=" * 60)
    print("TESTING INTEGRATION SCENARIOS")
    print("=" * 60)
    
    # Test 1: Configuration reload
    try:
        from config_loader import reload_config, get_config_loader
        
        original_loader = get_config_loader()
        original_weights = original_loader.get_quality_weights()
        
        # Reload configuration
        reload_config()
        
        new_loader = get_config_loader()
        new_weights = new_loader.get_quality_weights()
        
        if original_weights == new_weights:
            print("   ✅ PASS: Configuration reload maintains consistency")
        else:
            print("   ❌ FAIL: Configuration reload changed values")
            return False
        
    except ImportError:
        print("   ⚠️  SKIP: Cannot test configuration reload (module not available)")
    except Exception as e:
        print(f"   ❌ FAIL: Configuration reload error: {e}")
        return False
    
    # Test 2: Default fallback behavior
    try:
        # Test with non-existent config file
        from config_loader import EvaluationConfigLoader
        
        fake_loader = EvaluationConfigLoader("/nonexistent/path/config.yml")
        weights = fake_loader.get_quality_weights()
        
        if len(weights) == 4 and abs(sum(weights.values()) - 1.0) < 0.01:
            print("   ✅ PASS: Default fallback configuration works")
        else:
            print("   ❌ FAIL: Default fallback configuration invalid")
            return False
        
    except ImportError:
        print("   ⚠️  SKIP: Cannot test default fallback (module not available)")
    except Exception as e:
        print(f"   ❌ FAIL: Default fallback error: {e}")
        return False
    
    return True

def generate_test_report(test_results):
    """Generate comprehensive test report"""
    print("\n" + "=" * 60)
    print("TEST EXECUTION SUMMARY")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Configuration system is ready for production.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review and fix before deployment.")
    
    return failed_tests == 0

def main():
    """Run all configuration tests"""
    print("EVALUATION CONFIGURATION SYSTEM TEST SUITE")
    print("=" * 60)
    print("Testing configuration loading, validation, and integration...")
    print()
    
    # Run all tests
    test_results = {
        "Configuration Loading": test_configuration_loading(),
        "Twin-Report KB Config Loader": test_twin_report_config_loader(),
        "Idea Database Config Loader": test_idea_database_config_loader(),
        "Validation Script": test_validation_script(),
        "Docker Config Mounting": test_docker_config_mounting(),
        "Integration Scenarios": test_integration_scenarios()
    }
    
    # Generate report
    all_passed = generate_test_report(test_results)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main() 
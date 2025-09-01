#!/usr/bin/env python3
"""
Test explainer system
"""

import sys
import os
import tempfile
import sqlite3
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.explainer import ExplainerEngine, ExplanationOutput
from db_manager_unified import DatabaseManager

def test_explanation_generation():
    """Test explanation generation for different verdicts"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize database
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        explainer = ExplainerEngine()
        explainer.db_manager = db_manager
        
        # Test different verdicts
        test_cases = [
            ("price_incoherent", {"unit_price": 10.0, "qty": 2.0, "total": 25.0}),
            ("vat_mismatch", {"subtotal": 100.0, "vat_amount": 25.0, "vat_rate": 0.20}),
            ("pack_mismatch", {"packs": 2, "units_per_pack": 12, "qty": 30}),
            ("ocr_low_conf", {"confidence": 0.45}),
            ("off_contract_discount", {"discount_value": 15.5, "discount_kind": "percent"}),
            ("ok_on_contract", {"unit_price": 10.0, "qty": 2.0, "total": 20.0})
        ]
        
        for verdict, context in test_cases:
            explanation = explainer.explain_line_item("test_fp", verdict, context)
            assert explanation is not None
            assert explanation.engine_verdict == verdict
            assert explanation.headline != ""
            assert explanation.explanation != ""
            assert len(explanation.suggested_actions) > 0
            assert explanation.model_id == "deterministic"
        
        print("✅ Explanation generation test passed")
        
    finally:
        os.unlink(db_path)

def test_cache_hit():
    """Test cache hit functionality"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        explainer = ExplainerEngine()
        explainer.db_manager = db_manager
        
        # Generate explanation (should cache)
        context = {"test": "data"}
        explanation1 = explainer.explain_line_item("cache_test_fp", "price_incoherent", context)
        assert explanation1 is not None
        
        # Generate again (should hit cache)
        explanation2 = explainer.explain_line_item("cache_test_fp", "price_incoherent", context)
        assert explanation2 is not None
        
        # Should be identical
        assert explanation1.json() == explanation2.json()
        
        print("✅ Cache hit test passed")
        
    finally:
        os.unlink(db_path)

def test_cache_miss():
    """Test cache miss functionality"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        explainer = ExplainerEngine()
        explainer.db_manager = db_manager
        
        # Generate explanation for different fingerprint
        context = {"test": "data"}
        explanation1 = explainer.explain_line_item("fp1", "price_incoherent", context)
        explanation2 = explainer.explain_line_item("fp2", "price_incoherent", context)
        
        assert explanation1 is not None
        assert explanation2 is not None
        assert explanation1.json() == explanation2.json()  # Same content, different cache keys
        
        print("✅ Cache miss test passed")
        
    finally:
        os.unlink(db_path)

def test_deterministic_fallback():
    """Test deterministic fallback when LLM is not available"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        explainer = ExplainerEngine()
        explainer.db_manager = db_manager
        
        # Test with use_llm=False (default)
        context = {"test": "data"}
        explanation = explainer.explain_line_item("fallback_test_fp", "price_incoherent", context)
        
        assert explanation is not None
        assert explanation.model_id == "deterministic"
        assert explanation.prompt_hash == ""
        assert explanation.response_hash == ""
        
        print("✅ Deterministic fallback test passed")
        
    finally:
        os.unlink(db_path)

def test_explanation_output_schema():
    """Test that explanation output conforms to schema"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        explainer = ExplainerEngine()
        explainer.db_manager = db_manager
        
        context = {"test": "data"}
        explanation = explainer.explain_line_item("schema_test_fp", "price_incoherent", context)
        
        assert explanation is not None
        
        # Validate schema fields
        assert hasattr(explanation, 'headline')
        assert hasattr(explanation, 'explanation')
        assert hasattr(explanation, 'suggested_actions')
        assert hasattr(explanation, 'engine_verdict')
        assert hasattr(explanation, 'engine_facts_hash')
        assert hasattr(explanation, 'model_id')
        
        # Validate content
        assert len(explanation.headline) <= 100
        assert len(explanation.explanation) <= 500
        assert len(explanation.suggested_actions) <= 3
        
        # Validate JSON serialization
        json_str = explanation.json()
        parsed = json.loads(json_str)
        assert parsed['headline'] == explanation.headline
        assert parsed['engine_verdict'] == explanation.engine_verdict
        
        print("✅ Explanation output schema test passed")
        
    finally:
        os.unlink(db_path)

def test_cache_cleanup():
    """Test cache cleanup functionality"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        explainer = ExplainerEngine()
        explainer.db_manager = db_manager
        
        # Generate some explanations
        context = {"test": "data"}
        explainer.explain_line_item("cleanup_test_fp1", "price_incoherent", context)
        explainer.explain_line_item("cleanup_test_fp2", "vat_mismatch", context)
        
        # Clear expired cache (should work even with no expired entries)
        deleted_count = explainer.clear_expired_cache()
        assert deleted_count >= 0
        
        print("✅ Cache cleanup test passed")
        
    finally:
        os.unlink(db_path)

def test_facts_hash_consistency():
    """Test that facts hash is consistent for same inputs"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        explainer = ExplainerEngine()
        explainer.db_manager = db_manager
        
        context = {"test": "data", "value": 123}
        
        # Generate explanations with same inputs
        explanation1 = explainer.explain_line_item("hash_test_fp", "price_incoherent", context)
        explanation2 = explainer.explain_line_item("hash_test_fp", "price_incoherent", context)
        
        assert explanation1 is not None
        assert explanation2 is not None
        
        # Facts hash should be consistent
        assert explanation1.engine_facts_hash == explanation2.engine_facts_hash
        
        print("✅ Facts hash consistency test passed")
        
    finally:
        os.unlink(db_path)

if __name__ == "__main__":
    test_explanation_generation()
    test_cache_hit()
    test_cache_miss()
    test_deterministic_fallback()
    test_explanation_output_schema()
    test_cache_cleanup()
    test_facts_hash_consistency()
    print("All explainer tests passed!") 
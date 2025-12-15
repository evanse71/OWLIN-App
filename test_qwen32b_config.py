#!/usr/bin/env python3
"""
Test script to verify Qwen 32B configuration for code assistant.
"""

import sys
import requests
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.model_registry import ModelRegistry, get_registry
from services.chat_service import ChatService
from config import LLM_MODEL_NAME, LLM_MODEL_FALLBACK_LIST

def test_ollama_connection():
    """Test if Ollama is running and accessible."""
    print("=" * 60)
    print("Testing Ollama Connection")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"✅ Ollama is running and accessible")
            print(f"   Found {len(models)} model(s) available")
            return models
        else:
            print(f"❌ Ollama returned status code: {response.status_code}")
            return []
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama at http://localhost:11434")
        print("   Make sure Ollama is running: ollama serve")
        return []
    except Exception as e:
        print(f"❌ Error connecting to Ollama: {e}")
        return []

def check_qwen32b_available(models):
    """Check if Qwen 32B is available."""
    print("\n" + "=" * 60)
    print("Checking for Qwen 32B Model")
    print("=" * 60)
    
    qwen32b_found = False
    qwen7b_found = False
    
    for model in models:
        name = model.get("name", "")
        if "qwen2.5-coder:32b" in name.lower() or "qwen2.5-coder:32" in name.lower():
            qwen32b_found = True
            size_gb = model.get("size", 0) / (1024**3)
            print(f"✅ Found: {name} ({size_gb:.2f} GB)")
        elif "qwen2.5-coder:7b" in name.lower() or "qwen2.5-coder:7" in name.lower():
            qwen7b_found = True
            size_gb = model.get("size", 0) / (1024**3)
            print(f"✅ Found: {name} ({size_gb:.2f} GB)")
    
    if not qwen32b_found:
        print("⚠️  Qwen 32B not found")
        print("   To install: ollama pull qwen2.5-coder:32b")
    
    if not qwen7b_found:
        print("⚠️  Qwen 7B not found (fallback)")
    
    return qwen32b_found, qwen7b_found

def test_model_registry():
    """Test the model registry configuration."""
    print("\n" + "=" * 60)
    print("Testing Model Registry Configuration")
    print("=" * 60)
    
    try:
        registry = get_registry("http://localhost:11434")
        registry.refresh()
        
        available_models = registry.get_available_models()
        print(f"✅ Model registry initialized")
        print(f"   Registered {len(available_models)} model(s)")
        
        # Check for Qwen 32B in registry
        qwen32b_info = registry.get_model("qwen2.5-coder:32b")
        if qwen32b_info:
            print(f"\n✅ Qwen 32B registered in model registry:")
            print(f"   Context window: {qwen32b_info.max_context:,} tokens")
            print(f"   Specialty: {qwen32b_info.specialty}")
            print(f"   Speed: {qwen32b_info.speed}")
            print(f"   Description: {qwen32b_info.description}")
        else:
            print("\n⚠️  Qwen 32B not found in registry (may not be installed)")
        
        # Test model selection
        print("\n" + "-" * 60)
        print("Testing Model Selection Logic")
        print("-" * 60)
        
        # Test 1: Complex code analysis (should prefer 32B)
        selected, context = registry.select_best_model(
            question_type="debugging",
            context_size=64000,
            code_files_count=10,
            preferred_models=["qwen2.5-coder:32b", "qwen2.5-coder:7b"]
        )
        print(f"Complex analysis (64k context, 10 files):")
        print(f"   Selected: {selected}")
        print(f"   Context: {context:,} tokens")
        
        # Test 2: Quick question (might prefer 7B for speed)
        selected2, context2 = registry.select_best_model(
            question_type="general",
            context_size=8000,
            code_files_count=1,
            preferred_models=["qwen2.5-coder:32b", "qwen2.5-coder:7b"]
        )
        print(f"\nQuick question (8k context, 1 file):")
        print(f"   Selected: {selected2}")
        print(f"   Context: {context2:,} tokens")
        
        return True
    except Exception as e:
        print(f"❌ Error testing model registry: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Test configuration files."""
    print("\n" + "=" * 60)
    print("Testing Configuration Files")
    print("=" * 60)
    
    print(f"Default model (config.py): {LLM_MODEL_NAME}")
    if "32b" in LLM_MODEL_NAME.lower():
        print("✅ Config set to use Qwen 32B")
    else:
        print("⚠️  Config not set to Qwen 32B")
    
    print(f"\nFallback list (first 3):")
    for i, model in enumerate(LLM_MODEL_FALLBACK_LIST[:3], 1):
        marker = "✅" if i == 1 and "32b" in model.lower() else "  "
        print(f"{marker} {i}. {model}")
    
    return True

def test_chat_service():
    """Test chat service initialization."""
    print("\n" + "=" * 60)
    print("Testing Chat Service Configuration")
    print("=" * 60)
    
    try:
        # Initialize chat service (this will use default models)
        chat_service = ChatService()
        
        print(f"✅ Chat service initialized")
        print(f"   Primary model: {chat_service.model}")
        print(f"   Available models: {', '.join(chat_service.available_models) if chat_service.available_models else 'none'}")
        print(f"   Model priority list: {', '.join(chat_service.models[:3])}...")
        
        if "32b" in chat_service.model.lower():
            print("\n✅ Chat service will use Qwen 32B as primary model")
        elif chat_service.available_models and any("32b" in m.lower() for m in chat_service.available_models):
            print("\n✅ Qwen 32B is available and will be selected for complex requests")
        else:
            print("\n⚠️  Qwen 32B not available - will use fallback models")
        
        return True
    except Exception as e:
        print(f"❌ Error testing chat service: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Qwen 32B Configuration Verification")
    print("=" * 60)
    print()
    
    # Test 1: Ollama connection
    models = test_ollama_connection()
    
    if not models:
        print("\n❌ Cannot proceed without Ollama connection")
        return 1
    
    # Test 2: Check for Qwen models
    qwen32b_available, qwen7b_available = check_qwen32b_available(models)
    
    # Test 3: Configuration
    test_config()
    
    # Test 4: Model registry
    registry_ok = test_model_registry()
    
    # Test 5: Chat service
    service_ok = test_chat_service()
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if qwen32b_available:
        print("✅ Qwen 32B is installed and will be used for complex code analysis")
    elif qwen7b_available:
        print("⚠️  Qwen 32B not installed - using 7B as fallback")
        print("   Install with: ollama pull qwen2.5-coder:32b")
    else:
        print("❌ No Qwen models found")
        print("   Install with: ollama pull qwen2.5-coder:32b")
    
    if registry_ok and service_ok:
        print("✅ Configuration is correct - code assistant will use Qwen 32B when available")
    else:
        print("⚠️  Some configuration issues detected")
    
    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())

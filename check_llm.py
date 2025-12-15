"""
LLM Connectivity Diagnostic Script

This script verifies:
1. Ollama is running at localhost:11434
2. Lists all available models
3. Tests a simple generation to prove it works
"""

import sys
import requests
import json
from typing import List, Dict, Any

OLLAMA_URL = "http://localhost:11434"
COLORS = {
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'RED': '\033[91m',
    'BLUE': '\033[94m',
    'END': '\033[0m',
    'BOLD': '\033[1m'
}

def colored(text: str, color: str) -> str:
    """Add color to text."""
    return f"{COLORS.get(color, '')}{text}{COLORS['END']}"

def print_header(text: str):
    """Print section header."""
    print(f"\n{colored('=' * 70, 'BLUE')}")
    print(colored(text, 'BOLD'))
    print(colored('=' * 70, 'BLUE'))

def print_success(text: str):
    """Print success message."""
    print(colored(f"✓ {text}", 'GREEN'))

def print_error(text: str):
    """Print error message."""
    print(colored(f"✗ {text}", 'RED'))

def print_warning(text: str):
    """Print warning message."""
    print(colored(f"⚠ {text}", 'YELLOW'))

def check_ollama_connection() -> bool:
    """Check if Ollama is running."""
    print_header("Step 1: Check Ollama Connection")
    
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print_success(f"Ollama is running at {OLLAMA_URL}")
            return True
        else:
            print_error(f"Ollama returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to Ollama at {OLLAMA_URL}")
        print_warning("Make sure Ollama is running:")
        print("  Windows: Start Ollama from the Start Menu")
        print("  Mac: Open Ollama.app")
        print("  Linux: systemctl start ollama")
        return False
    except Exception as e:
        print_error(f"Connection error: {e}")
        return False

def list_models() -> List[Dict[str, Any]]:
    """List all available Ollama models."""
    print_header("Step 2: List Available Models")
    
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            
            if not models:
                print_warning("No models found!")
                print("\nTo download a model, run:")
                print("  ollama pull llama3")
                print("  ollama pull qwen2.5-coder:7b")
                print("  ollama pull mistral")
                return []
            
            print_success(f"Found {len(models)} model(s):")
            print()
            
            for idx, model in enumerate(models, 1):
                name = model.get("name", "unknown")
                size = model.get("size", 0)
                size_gb = size / (1024 ** 3)
                modified = model.get("modified_at", "")
                
                print(f"  {idx}. {colored(name, 'BOLD')}")
                print(f"     Size: {size_gb:.2f} GB")
                print(f"     Modified: {modified[:10]}")
                print()
            
            return models
        else:
            print_error(f"Failed to list models: HTTP {response.status_code}")
            return []
    except Exception as e:
        print_error(f"Error listing models: {e}")
        return []

def test_generation(model_name: str) -> bool:
    """Test a simple generation with the model."""
    print_header(f"Step 3: Test Generation with {model_name}")
    
    test_prompt = "Extract this invoice data as JSON: Invoice #123, ACME Corp, Total: $100"
    
    print(f"Sending test prompt to {model_name}...")
    print(f"Prompt: {colored(test_prompt, 'BLUE')}")
    print()
    
    try:
        payload = {
            "model": model_name,
            "prompt": test_prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 200
            }
        }
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "")
            
            print_success("Generation successful!")
            print(f"\nResponse length: {len(generated_text)} characters")
            print(f"Response preview:\n{colored(generated_text[:300], 'BLUE')}")
            if len(generated_text) > 300:
                print("...")
            
            return True
        else:
            print_error(f"Generation failed: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print_error("Generation timed out (30s)")
        print_warning("This model might be too slow. Consider using a smaller model like llama3.2:3b")
        return False
    except Exception as e:
        print_error(f"Generation error: {e}")
        return False

def recommend_model(models: List[Dict[str, Any]]) -> str:
    """Recommend the best model for invoice extraction."""
    print_header("Step 4: Model Recommendation")
    
    # Preference order for invoice extraction
    preferred_models = [
        "qwen2.5-coder:7b",
        "qwen2.5-coder:latest",
        "llama3.1:8b",
        "llama3:8b", 
        "llama3:latest",
        "mistral:latest",
        "llama3.2:3b"  # Smaller/faster fallback
    ]
    
    model_names = [m.get("name", "") for m in models]
    
    # Find best match
    for preferred in preferred_models:
        if preferred in model_names:
            print_success(f"Recommended model: {colored(preferred, 'BOLD')}")
            print(f"  Reason: Best balance of accuracy and speed for invoice extraction")
            return preferred
    
    # If no preferred model found, use first available
    if model_names:
        first_model = model_names[0]
        print_warning(f"Using first available model: {colored(first_model, 'BOLD')}")
        print("  For better results, consider downloading:")
        print("    ollama pull qwen2.5-coder:7b")
        return first_model
    
    print_error("No models available!")
    return ""

def main():
    """Run all diagnostic checks."""
    print(colored("\n" + "="*70, 'BOLD'))
    print(colored("  LLM Connectivity Diagnostic Tool", 'BOLD'))
    print(colored("="*70 + "\n", 'BOLD'))
    
    # Step 1: Check connection
    if not check_ollama_connection():
        print_error("\n✗ Ollama is not running. Please start Ollama and try again.")
        return 1
    
    # Step 2: List models
    models = list_models()
    if not models:
        print_error("\n✗ No models available. Please download a model first.")
        print("\nQuick start:")
        print("  ollama pull qwen2.5-coder:7b")
        return 1
    
    # Step 3: Recommend model
    recommended_model = recommend_model(models)
    if not recommended_model:
        return 1
    
    # Step 4: Test generation
    if not test_generation(recommended_model):
        print_error("\n✗ Generation test failed.")
        return 1
    
    # Success!
    print_header("Summary")
    print_success("All checks passed!")
    print()
    print("Your system is ready for LLM invoice extraction.")
    print()
    print(colored("Next Steps:", 'BOLD'))
    print(f"  1. Enable LLM extraction in config")
    print(f"  2. Set model to: {colored(recommended_model, 'GREEN')}")
    print(f"  3. Restart backend")
    print(f"  4. Upload invoice and enjoy accurate extraction!")
    print()
    print(colored("Configuration to use:", 'BOLD'))
    print(f"  FEATURE_LLM_EXTRACTION=true")
    print(f"  LLM_MODEL_NAME={recommended_model}")
    print(f"  LLM_OLLAMA_URL={OLLAMA_URL}")
    print()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)


"""
Quick Ollama Verification Script
Tests if Ollama is reachable and responsive RIGHT NOW.
"""

import sys
import requests
import time

OLLAMA_URL = "http://localhost:11434"

def test_connection():
    """Test basic connection."""
    print("Testing Ollama connection...")
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✓ Ollama is RUNNING")
            models = response.json().get("models", [])
            print(f"✓ Found {len(models)} models")
            return True
        else:
            print(f"✗ Ollama returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to Ollama at {OLLAMA_URL}")
        print("  Run: ollama serve")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_generation():
    """Test a quick generation."""
    print("\nTesting generation with 120s timeout...")
    try:
        start = time.time()
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "qwen2.5-coder:7b",
                "prompt": "Extract: Invoice #123",
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 50}
            },
            timeout=120  # Same as our new config
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            print(f"✓ Generation successful in {elapsed:.1f}s")
            return True
        else:
            print(f"✗ Generation failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print(f"✗ Timed out after 120s")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Ollama Verification (Quick Test)")
    print("="*60)
    
    conn_ok = test_connection()
    if not conn_ok:
        sys.exit(1)
    
    gen_ok = test_generation()
    
    print("\n" + "="*60)
    if conn_ok and gen_ok:
        print("✓ All tests PASSED - Ollama is ready!")
        print("\nNext: Restart backend and upload invoice")
        sys.exit(0)
    else:
        print("✗ Some tests FAILED - fix issues above")
        sys.exit(1)


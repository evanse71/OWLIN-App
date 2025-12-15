"""Quick test to verify LLM config is loaded correctly."""
import sys
sys.path.insert(0, '.')

print("Testing LLM config loading...")
print()

try:
    from backend.config import FEATURE_LLM_EXTRACTION
    print(f"✓ Config loaded: FEATURE_LLM_EXTRACTION = {FEATURE_LLM_EXTRACTION}")
    print(f"  Type: {type(FEATURE_LLM_EXTRACTION)}")
    print(f"  Bool value: {bool(FEATURE_LLM_EXTRACTION)}")
    
    if FEATURE_LLM_EXTRACTION:
        print("\n✓ LLM extraction is ENABLED")
    else:
        print("\n✗ LLM extraction is DISABLED")
        
except Exception as e:
    print(f"✗ Error loading config: {e}")
    import traceback
    traceback.print_exc()

print()
print("Testing LLM parser import...")
try:
    from backend.llm.invoice_parser import create_invoice_parser
    parser = create_invoice_parser()
    print(f"✓ LLM parser created successfully")
    print(f"  Model: {parser.model_name}")
    print(f"  URL: {parser.ollama_url}")
    print(f"  Timeout: {parser.timeout}s")
except Exception as e:
    print(f"✗ Error creating parser: {e}")
    import traceback
    traceback.print_exc()


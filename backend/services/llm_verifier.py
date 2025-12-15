"""
LLM-based Invoice Verification Service

Uses Gemini 3 Pro (or similar) to verify and correct invoices
that fail numeric consistency checks.

Only called for ~15-20% of invoices that need additional verification.
"""

import logging
import json
from typing import Dict, Any, Optional
from backend.validation import ValidationResult

logger = logging.getLogger("owlin.services.llm")


def build_verification_prompt(
    raw_ocr_text: str,
    parsed_data: Dict[str, Any],
    validation: ValidationResult
) -> str:
    """
    Build a prompt for LLM verification of invoice data.
    
    Args:
        raw_ocr_text: Raw text from PaddleOCR
        parsed_data: Current parsed invoice data
        validation: Validation result with issues and expected values
    
    Returns:
        Formatted prompt for Gemini 3 Pro
    """
    
    # Format line items for display
    line_items_str = ""
    if parsed_data.get('line_items'):
        for i, item in enumerate(parsed_data['line_items'], 1):
            line_items_str += f"\n  {i}. {item.get('desc', 'Unknown')}"
            line_items_str += f"\n     Qty: {item.get('qty', '?')} | Unit: £{item.get('unit_price', '?')} | Total: £{item.get('total', '?')}"
    
    # Format validation issues
    issues_str = "\n".join(f"  • {issue}" for issue in validation.issues)
    
    # Format expected values
    expected_str = ""
    if 'items_subtotal' in validation.details:
        expected_str += f"\n  • Items Subtotal: £{validation.details['items_subtotal']:.2f}"
    if 'vat_expected' in validation.details:
        expected_str += f"\n  • VAT Expected: £{validation.details['vat_expected']:.2f}"
    if 'total_expected' in validation.details:
        expected_str += f"\n  • Total Expected: £{validation.details['total_expected']:.2f}"
    
    prompt = f"""You are an expert invoice verification assistant. Your task is to verify and correct OCR-extracted invoice data.

## RAW OCR TEXT
```
{raw_ocr_text[:2000]}  # Limit to first 2000 chars
```

## CURRENT EXTRACTED DATA
Supplier: {parsed_data.get('supplier', 'Unknown')}
Invoice Number: {parsed_data.get('invoice_no', 'Unknown')}
Date: {parsed_data.get('date', 'Unknown')}

Financial Summary:
  • Subtotal: £{parsed_data.get('subtotal', '?')}
  • VAT: £{parsed_data.get('vat', '?')} ({parsed_data.get('vat_rate', '?') * 100 if parsed_data.get('vat_rate') else '?'}%)
  • Total: £{parsed_data.get('total', '?')}

Line Items:{line_items_str or "\n  (No line items extracted)"}

## VALIDATION ISSUES DETECTED
Integrity Score: {validation.integrity_score:.3f} / 1.0

Issues Found:
{issues_str}

Expected Values (computed from line items):{expected_str}

## YOUR TASK

Please:
1. **Re-read the raw OCR text** carefully
2. **Reconstruct the line items** with correct:
   - Description (full product name)
   - Quantity (integer)
   - Unit Price (£X.XX)
   - Line Total (£X.XX)
3. **Verify the financial summary**:
   - Subtotal (sum of line totals)
   - VAT amount (subtotal × VAT rate)
   - Grand Total (subtotal + VAT)
4. **Identify and correct** any OCR errors
5. **Return a corrected JSON** in this exact format:

```json
{{
  "verification_status": "verified" | "corrected" | "unresolvable",
  "confidence": 0.0-1.0,
  "corrections_made": ["list of what you changed"],
  "invoice": {{
    "supplier": "Exact supplier name from invoice",
    "invoice_number": "Exact invoice number",
    "date": "YYYY-MM-DD",
    "subtotal": 123.45,
    "vat_rate": 0.20,
    "vat_amount": 24.69,
    "total": 148.14,
    "line_items": [
      {{
        "description": "Full product description",
        "qty": 10,
        "unit_price": 12.34,
        "line_total": 123.40
      }}
    ]
  }},
  "validation": {{
    "subtotal_check": "pass" | "fail",
    "vat_check": "pass" | "fail",
    "total_check": "pass" | "fail",
    "explanation": "Brief explanation of any corrections"
  }}
}}
```

## IMPORTANT RULES
- Use ONLY values you can see in the raw OCR text
- Ensure line_total = qty × unit_price for each item
- Ensure subtotal = sum(line_total for all items)
- Ensure vat_amount = subtotal × vat_rate
- Ensure total = subtotal + vat_amount
- If you can't resolve an inconsistency, mark verification_status as "unresolvable"
- Return ONLY the JSON, no other text
"""
    
    return prompt


def verify_with_gemini_pro(
    raw_ocr_text: str,
    parsed_data: Dict[str, Any],
    validation: ValidationResult,
    api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Verify invoice using Gemini 3 Pro.
    
    Args:
        raw_ocr_text: Raw OCR text
        parsed_data: Current parsed data
        validation: Validation result
        api_key: Gemini API key (optional, reads from env if not provided)
    
    Returns:
        LLM-verified invoice data or None if verification fails
    """
    try:
        import os
        import google.generativeai as genai
        
        # Get API key
        if api_key is None:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            logger.error("[LLM] No Gemini API key provided")
            return None
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Build prompt
        prompt = build_verification_prompt(raw_ocr_text, parsed_data, validation)
        
        logger.info(f"[LLM] Sending verification request to Gemini 3 Pro")
        
        # Generate response
        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.1,  # Low temperature for factual accuracy
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 2048,
            }
        )
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        llm_result = json.loads(response_text)
        
        logger.info(f"[LLM] Verification complete: status={llm_result.get('verification_status')}, confidence={llm_result.get('confidence')}")
        
        if llm_result.get('corrections_made'):
            logger.info(f"[LLM] Corrections made: {llm_result['corrections_made']}")
        
        return llm_result
        
    except ImportError:
        logger.error("[LLM] google-generativeai not installed. Install with: pip install google-generativeai")
        return None
    except Exception as e:
        logger.error(f"[LLM] Verification failed: {e}", exc_info=True)
        return None


def should_use_llm_verification(validation: ValidationResult) -> bool:
    """
    Determine if LLM verification should be used.
    
    Wrapper around should_request_llm_verification for clarity.
    """
    from backend.validation import should_request_llm_verification
    return should_request_llm_verification(validation)


# Example usage:
"""
from backend.services.llm_verifier import verify_with_gemini_pro, should_use_llm_verification
from backend.validation import validate_invoice_consistency

# After OCR extraction
validation = validate_invoice_consistency(...)

if should_use_llm_verification(validation):
    logger.info("Requesting LLM verification for complex invoice")
    llm_result = verify_with_gemini_pro(
        raw_ocr_text=raw_text,
        parsed_data=parsed_data,
        validation=validation
    )
    
    if llm_result and llm_result['verification_status'] in ['verified', 'corrected']:
        # Use LLM's corrected data
        parsed_data = llm_result['invoice']
        # Add LLM verification badge
        validation_badge = {
            'label': 'LLM-verified',
            'color': 'green',
            'tooltip': f"Verified by AI ({llm_result['confidence']:.2f} confidence)"
        }
"""


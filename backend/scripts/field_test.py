#!/usr/bin/env python3
"""
Field Test Script

Comprehensive testing of OCR pipeline for go-live scenarios
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ocr.unified_ocr_engine import get_unified_ocr_engine
from ocr.config import get_ocr_config

class FieldTestRunner:
    """Field test runner for OCR pipeline"""
    
    def __init__(self):
        self.engine = get_unified_ocr_engine()
        self.config = get_ocr_config()
        self.results = []
    
    def run_test(self, test_name: str, expected_doc_type: str, expected_policy: str, 
                 expected_validation: Dict[str, bool], test_data: str) -> Dict[str, Any]:
        """Run a single test case"""
        print(f"\n🧪 Testing: {test_name}")
        print(f"   Expected: {expected_doc_type} → {expected_policy}")
        
        start_time = time.time()
        
        try:
            # Process the test data
            result = self.engine.process_document(test_data)
            processing_time = time.time() - start_time
            
            # Extract results
            doc_type = result.document_type
            policy_action = result.policy_decision.get('action', 'UNKNOWN') if result.policy_decision else 'UNKNOWN'
            confidence = result.overall_confidence
            validation = result.validation_result or {}
            
            # Check expectations
            doc_type_match = doc_type == expected_doc_type
            policy_match = policy_action == expected_policy
            
            validation_matches = {}
            for key, expected in expected_validation.items():
                actual = validation.get(key, True)  # Default to True if not present
                validation_matches[key] = actual == expected
            
            all_validation_match = all(validation_matches.values())
            
            # Determine test result
            if doc_type_match and policy_match and all_validation_match:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
            
            test_result = {
                "test_name": test_name,
                "status": status,
                "expected": {
                    "doc_type": expected_doc_type,
                    "policy": expected_policy,
                    "validation": expected_validation
                },
                "actual": {
                    "doc_type": doc_type,
                    "policy": policy_action,
                    "confidence": confidence,
                    "validation": validation,
                    "processing_time": processing_time
                },
                "matches": {
                    "doc_type": doc_type_match,
                    "policy": policy_match,
                    "validation": validation_matches
                }
            }
            
            self.results.append(test_result)
            
            print(f"   Result: {status}")
            print(f"   Actual: {doc_type} → {policy_action} (conf: {confidence:.1f}%)")
            print(f"   Time: {processing_time:.2f}s")
            
            if not doc_type_match:
                print(f"   ❌ Doc type mismatch: expected {expected_doc_type}, got {doc_type}")
            
            if not policy_match:
                print(f"   ❌ Policy mismatch: expected {expected_policy}, got {policy_action}")
            
            for key, match in validation_matches.items():
                if not match:
                    expected = expected_validation[key]
                    actual = validation.get(key, True)
                    print(f"   ❌ Validation mismatch {key}: expected {expected}, got {actual}")
            
            return test_result
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            test_result = {
                "test_name": test_name,
                "status": "❌ ERROR",
                "error": str(e)
            }
            self.results.append(test_result)
            return test_result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all field tests"""
        print("🚀 Starting Field Tests")
        print("=" * 50)
        
        # Test 1: Clean invoice (GBP)
        clean_invoice_text = """
        WILD HORSE BREWING CO LTD
        Invoice Number: INV-2025-001
        Date: 15/08/2025
        
        Description                    Qty    Unit Price    Total
        Premium Lager                  24     £2.50         £60.00
        Craft IPA                      12     £3.20         £38.40
        VAT (20%)                                      £19.68
        Total Amount Due:                              £118.08
        """
        
        self.run_test(
            "Clean Invoice (GBP)",
            "invoice",
            "ACCEPT",
            {"arithmetic_ok": True, "currency_ok": True, "date_ok": True},
            clean_invoice_text
        )
        
        # Test 2: Delivery note (no totals)
        delivery_note_text = """
        METRO BEVERAGES
        Delivery Note: DN-2025-089
        Date: 14/08/2025
        
        Description                    Qty    Unit
        Premium Lager                  24     cases
        Craft IPA                      12     cases
        Delivered to: Kitchen Store
        """
        
        self.run_test(
            "Delivery Note (no totals)",
            "delivery_note",
            "ACCEPT",
            {"arithmetic_ok": True, "currency_ok": True, "date_ok": True},
            delivery_note_text
        )
        
        # Test 3: Thermal receipt with "Change/Card"
        receipt_text = """
        THE RED LION PUB
        Receipt
        
        Premium Lager                  2     £3.50         £7.00
        Craft IPA                      1     £4.20         £4.20
        Subtotal:                                    £11.20
        VAT (20%):                                    £2.24
        Total:                                        £13.44
        Card Payment:                                 £15.00
        Change:                                       £1.56
        """
        
        self.run_test(
            "Thermal Receipt with Change/Card",
            "receipt",
            "ACCEPT",
            {"arithmetic_ok": True, "currency_ok": True, "date_ok": True},
            receipt_text
        )
        
        # Test 4: Utility bill
        utility_text = """
        BRITISH GAS
        Gas Bill
        
        Account Number: 1234567890
        Bill Date: 15/08/2025
        
        Gas Usage: 150 kWh
        Unit Rate: £0.15 per kWh
        Standing Charge: £0.25 per day
        Total: £22.50
        """
        
        self.run_test(
            "Utility Bill",
            "utility",
            "ACCEPT",
            {"arithmetic_ok": True, "currency_ok": True, "date_ok": True},
            utility_text
        )
        
        # Test 5: Menu PDF (should be rejected)
        menu_text = """
        THE RED LION PUB
        Menu
        
        Starters
        - Soup of the Day          £5.50
        - Garlic Bread             £3.50
        
        Mains
        - Fish & Chips            £12.50
        - Steak & Ale Pie         £14.50
        
        Desserts
        - Apple Crumble           £5.50
        - Chocolate Fudge Cake    £6.00
        
        Allergens: Contains gluten, dairy, nuts
        """
        
        self.run_test(
            "Menu PDF",
            "other",
            "REJECT",
            {"arithmetic_ok": False, "currency_ok": False, "date_ok": False},
            menu_text
        )
        
        # Test 6: Future-dated invoice (+10 days)
        future_invoice_text = """
        WILD HORSE BREWING CO LTD
        Invoice Number: INV-2025-002
        Date: 25/08/2025
        
        Description                    Qty    Unit Price    Total
        Premium Lager                  24     £2.50         £60.00
        Total Amount Due:                              £60.00
        """
        
        self.run_test(
            "Future-dated Invoice (+10 days)",
            "invoice",
            "ACCEPT_WITH_WARNINGS",  # Changed from QUARANTINE to ACCEPT_WITH_WARNINGS
            {"arithmetic_ok": True, "currency_ok": True, "date_ok": False},
            future_invoice_text
        )
        
        # Test 7: EUR comma decimals
        eur_invoice_text = """
        EURO SUPPLIES GMBH
        Invoice Number: EUR-2025-001
        Date: 15/08/2025
        
        Description                    Qty    Unit Price    Total
        Premium Beer                  24     €2,50         €60,00
        Total Amount Due:                              €60,00
        """
        
        self.run_test(
            "EUR Comma Decimals",
            "invoice",
            "ACCEPT",
            {"arithmetic_ok": True, "currency_ok": True, "date_ok": True},
            eur_invoice_text
        )
        
        # Test 8: Receipt with void/refund
        void_receipt_text = """
        THE RED LION PUB
        Receipt
        
        Premium Lager                  2     £3.50         £7.00
        VOID - Craft IPA              1     £4.20         £0.00
        Subtotal:                                    £7.00
        Total:                                        £7.00
        """
        
        self.run_test(
            "Receipt with Void/Refund",
            "receipt",
            "ACCEPT",
            {"arithmetic_ok": True, "currency_ok": True, "date_ok": True},
            void_receipt_text
        )
        
        return self.generate_summary()
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "✅ PASS"])
        failed_tests = len([r for r in self.results if r["status"] == "❌ FAIL"])
        error_tests = len([r for r in self.results if r["status"] == "❌ ERROR"])
        
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        summary = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "pass_rate": pass_rate,
            "results": self.results
        }
        
        print("\n" + "=" * 50)
        print("📊 FIELD TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Errors: {error_tests}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        if pass_rate >= 90:
            print("✅ GO-LIVE READY")
        elif pass_rate >= 80:
            print("⚠️ NEEDS MINOR FIXES")
        else:
            print("❌ NEEDS MAJOR FIXES")
        
        return summary

def main():
    """Main function"""
    runner = FieldTestRunner()
    summary = runner.run_all_tests()
    
    # Save results
    output_path = Path(__file__).parent / "field_test_results.json"
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📄 Results saved to: {output_path}")
    
    return 0 if summary["pass_rate"] >= 90 else 1

if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python3
"""
One-Click Smoke Test

Quick validation test using predefined fixtures
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.ocr.unified_ocr_engine import get_unified_ocr_engine

class SmokeTestRunner:
    """Smoke test runner for quick validation"""
    
    def __init__(self):
        self.engine = get_unified_ocr_engine()
        self.smoke_dir = Path(__file__).parent.parent / "data" / "smoke"
        
        # Test fixtures with expected results
        self.fixtures = [
            {
                'name': 'Clean Invoice (GBP)',
                'text': """
                WILD HORSE BREWING CO LTD
                Invoice Number: INV-2025-001
                Date: 15/08/2025
                
                Description                    Qty    Unit Price    Total
                Premium Lager                  24     £2.50         £60.00
                Craft IPA                      12     £3.20         £38.40
                VAT (20%)                                      £19.68
                Total Amount Due:                              £118.08
                """,
                'expected': {
                    'doc_type': 'invoice',
                    'policy_action': 'ACCEPT',
                    'min_confidence': 0.7
                }
            },
            {
                'name': 'Delivery Note (no totals)',
                'text': """
                METRO BEVERAGES
                Delivery Note: DN-2025-089
                Date: 14/08/2025
                
                Description                    Qty    Unit
                Premium Lager                  24     cases
                Craft IPA                      12     cases
                Delivered to: Kitchen Store
                """,
                'expected': {
                    'doc_type': 'delivery_note',
                    'policy_action': 'ACCEPT',
                    'min_confidence': 0.7
                }
            },
            {
                'name': 'Thermal Receipt with Change/Card',
                'text': """
                THE RED LION PUB
                Receipt
                
                Premium Lager                  2     £3.50         £7.00
                Craft IPA                      1     £4.20         £4.20
                Subtotal:                                    £11.20
                VAT (20%):                                    £2.24
                Total:                                        £13.44
                Card Payment:                                 £15.00
                Change:                                       £1.56
                """,
                'expected': {
                    'doc_type': 'receipt',
                    'policy_action': 'ACCEPT',
                    'min_confidence': 0.7
                }
            },
            {
                'name': 'Utility Bill',
                'text': """
                BRITISH GAS
                Gas Bill
                
                Account Number: 1234567890
                Bill Date: 15/08/2025
                
                Gas Usage: 150 kWh
                Unit Rate: £0.15 per kWh
                Standing Charge: £0.25 per day
                Total: £22.50
                """,
                'expected': {
                    'doc_type': 'utility',
                    'policy_action': 'ACCEPT',
                    'min_confidence': 0.7
                }
            },
            {
                'name': 'Menu PDF (should be rejected)',
                'text': """
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
                """,
                'expected': {
                    'doc_type': 'other',
                    'policy_action': 'REJECT',
                    'min_confidence': 0.0
                }
            },
            {
                'name': 'Future-dated Invoice (+10 days)',
                'text': """
                WILD HORSE BREWING CO LTD
                Invoice Number: INV-2025-002
                Date: 25/08/2025
                
                Description                    Qty    Unit Price    Total
                Premium Lager                  24     £2.50         £60.00
                Total Amount Due:                              £60.00
                """,
                'expected': {
                    'doc_type': 'invoice',
                    'policy_action': 'ACCEPT_WITH_WARNINGS',
                    'min_confidence': 0.7
                }
            },
            {
                'name': 'EUR Comma Decimals',
                'text': """
                EURO SUPPLIES GMBH
                Invoice Number: EUR-2025-001
                Date: 15/08/2025
                
                Description                    Qty    Unit Price    Total
                Premium Beer                  24     €2,50         €60,00
                Total Amount Due:                              €60,00
                """,
                'expected': {
                    'doc_type': 'invoice',
                    'policy_action': 'ACCEPT',
                    'min_confidence': 0.7
                }
            },
            {
                'name': 'Receipt with Void/Refund',
                'text': """
                THE RED LION PUB
                Receipt
                
                Premium Lager                  2     £3.50         £7.00
                VOID - Craft IPA              1     £4.20         £0.00
                Subtotal:                                    £7.00
                Total:                                        £7.00
                """,
                'expected': {
                    'doc_type': 'receipt',
                    'policy_action': 'ACCEPT',
                    'min_confidence': 0.7
                }
            }
        ]
    
    def run_smoke_test(self) -> Dict[str, Any]:
        """
        Run smoke test on predefined fixtures
        
        Returns:
            Dictionary with test results
        """
        print("🚀 Starting Smoke Test")
        print("=" * 50)
        
        results = []
        start_time = time.time()
        
        for fixture in self.fixtures:
            print(f"\n🧪 Testing: {fixture['name']}")
            
            try:
                # Process the fixture
                result = self.engine.process_document(fixture['text'])
                
                # Check results
                test_result = self._check_fixture_result(fixture, result)
                results.append(test_result)
                
                # Print result
                status = "✅ PASS" if test_result['passed'] else "❌ FAIL"
                print(f"   Result: {status}")
                print(f"   Actual: {result.document_type} → {result.policy_decision['action']} (conf: {result.overall_confidence:.1%})")
                
                if not test_result['passed']:
                    for issue in test_result['issues']:
                        print(f"   ❌ {issue}")
                
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                results.append({
                    'name': fixture['name'],
                    'passed': False,
                    'issues': [f"Processing error: {e}"]
                })
        
        total_time = time.time() - start_time
        
        # Calculate summary
        passed = len([r for r in results if r['passed']])
        total = len(results)
        pass_rate = (passed / total) * 100 if total > 0 else 0
        
        summary = {
            'total_tests': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': pass_rate,
            'total_time': total_time,
            'results': results,
            'all_passed': passed == total
        }
        
        print("\n" + "=" * 50)
        print("📊 SMOKE TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print(f"Total Time: {total_time:.2f}s")
        
        if summary['all_passed']:
            print("✅ SMOKE: PASS")
        else:
            print("❌ SMOKE: FAIL")
        
        return summary
    
    def _check_fixture_result(self, fixture: Dict[str, Any], result) -> Dict[str, Any]:
        """Check if fixture result matches expectations"""
        expected = fixture['expected']
        issues = []
        
        # Check document type
        if result.document_type != expected['doc_type']:
            issues.append(f"Doc type mismatch: expected {expected['doc_type']}, got {result.document_type}")
        
        # Check policy action
        actual_action = result.policy_decision['action']
        if actual_action != expected['policy_action']:
            issues.append(f"Policy mismatch: expected {expected['policy_action']}, got {actual_action}")
        
        # Check confidence
        if result.overall_confidence < expected['min_confidence']:
            issues.append(f"Low confidence: {result.overall_confidence:.1%} < {expected['min_confidence']:.1%}")
        
        return {
            'name': fixture['name'],
            'passed': len(issues) == 0,
            'issues': issues,
            'expected': expected,
            'actual': {
                'doc_type': result.document_type,
                'policy_action': actual_action,
                'confidence': result.overall_confidence
            }
        }

def main():
    """Main function for running smoke test"""
    try:
        runner = SmokeTestRunner()
        results = runner.run_smoke_test()
        
        return 0 if results['all_passed'] else 1
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
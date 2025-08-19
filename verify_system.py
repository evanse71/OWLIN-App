#!/usr/bin/env python3
"""
OWLIN System Verification Script

This script verifies that all critical components are working properly
after the implementation of fixes.
"""

import asyncio
import aiohttp
import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any

class SystemVerifier:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = []
        
    async def test_health_endpoint(self) -> Dict[str, Any]:
        """Test the health endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "test": "Health Endpoint",
                            "status": "PASS",
                            "details": f"Response: {data}"
                        }
                    else:
                        return {
                            "test": "Health Endpoint",
                            "status": "FAIL",
                            "details": f"Status: {response.status}"
                        }
        except Exception as e:
            return {
                "test": "Health Endpoint",
                "status": "FAIL",
                "details": f"Error: {str(e)}"
            }
    
    async def test_detailed_health(self) -> Dict[str, Any]:
        """Test the detailed health check."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health/detailed") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "test": "Detailed Health Check",
                            "status": "PASS",
                            "details": f"Overall status: {data.get('status')}"
                        }
                    else:
                        return {
                            "test": "Detailed Health Check",
                            "status": "FAIL",
                            "details": f"Status: {response.status}"
                        }
        except Exception as e:
            return {
                "test": "Detailed Health Check",
                "status": "FAIL",
                "details": f"Error: {str(e)}"
            }
    
    async def test_ocr_harness(self) -> Dict[str, Any]:
        """Test the OCR harness endpoints."""
        try:
            async with aiohttp.ClientSession() as session:
                # Test suites list
                async with session.get(f"{self.base_url}/api/ocr/harness/suites") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "test": "OCR Harness",
                            "status": "PASS",
                            "details": f"Available suites: {len(data.get('suites', []))}"
                        }
                    else:
                        return {
                            "test": "OCR Harness",
                            "status": "FAIL",
                            "details": f"Status: {response.status}"
                        }
        except Exception as e:
            return {
                "test": "OCR Harness",
                "status": "FAIL",
                "details": f"Error: {str(e)}"
            }
    
    async def test_invoices_api(self) -> Dict[str, Any]:
        """Test the invoices API endpoints."""
        try:
            async with aiohttp.ClientSession() as session:
                # Test basic invoices endpoint
                async with session.get(f"{self.base_url}/api/invoices?limit=5") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "test": "Invoices API",
                            "status": "PASS",
                            "details": f"Retrieved {len(data.get('invoices', []))} invoices"
                        }
                    else:
                        return {
                            "test": "Invoices API",
                            "status": "FAIL",
                            "details": f"Status: {response.status}"
                        }
        except Exception as e:
            return {
                "test": "Invoices API",
                "status": "FAIL",
                "details": f"Error: {str(e)}"
            }
    
    async def test_suppliers_api(self) -> Dict[str, Any]:
        """Test the suppliers API endpoints."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/invoices/suppliers") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "test": "Suppliers API",
                            "status": "PASS",
                            "details": f"Retrieved {len(data.get('suppliers', []))} suppliers"
                        }
                    else:
                        return {
                            "test": "Suppliers API",
                            "status": "FAIL",
                            "details": f"Status: {response.status}"
                        }
        except Exception as e:
            return {
                "test": "Suppliers API",
                "status": "FAIL",
                "details": f"Error: {str(e)}"
            }
    
    def test_file_structure(self) -> Dict[str, Any]:
        """Test that all required files exist."""
        required_files = [
            "frontend/pages/invoices.tsx",
            "frontend/components/invoices/InvoiceFilterPanel.tsx",
            "frontend/components/invoices/UploadSection.tsx",
            "frontend/components/invoices/InvoiceCardsPanel.tsx",
            "frontend/components/invoices/InvoiceDetailBox.tsx",
            "frontend/hooks/useFiltersContext.ts",
            "frontend/hooks/useOfflineQueue.ts",
            "backend/routes/ocr_harness.py",
            "backend/routes/health.py",
            "components/layout/AppShell.tsx"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            return {
                "test": "File Structure",
                "status": "FAIL",
                "details": f"Missing files: {missing_files}"
            }
        else:
            return {
                "test": "File Structure",
                "status": "PASS",
                "details": f"All {len(required_files)} required files present"
            }
    
    def test_frontend_build(self) -> Dict[str, Any]:
        """Test that the frontend builds successfully."""
        try:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd="frontend",
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {
                    "test": "Frontend Build",
                    "status": "PASS",
                    "details": "Build completed successfully"
                }
            else:
                return {
                    "test": "Frontend Build",
                    "status": "FAIL",
                    "details": f"Build failed: {result.stderr}"
                }
        except subprocess.TimeoutExpired:
            return {
                "test": "Frontend Build",
                "status": "FAIL",
                "details": "Build timed out"
            }
        except Exception as e:
            return {
                "test": "Frontend Build",
                "status": "FAIL",
                "details": f"Error: {str(e)}"
            }
    
    async def run_all_tests(self):
        """Run all verification tests."""
        print("🔍 Starting OWLIN System Verification...")
        print("=" * 50)
        
        # File structure test
        result = self.test_file_structure()
        self.results.append(result)
        print(f"{'✅' if result['status'] == 'PASS' else '❌'} {result['test']}: {result['status']}")
        
        # Frontend build test
        result = self.test_frontend_build()
        self.results.append(result)
        print(f"{'✅' if result['status'] == 'PASS' else '❌'} {result['test']}: {result['status']}")
        
        # API tests
        api_tests = [
            self.test_health_endpoint(),
            self.test_detailed_health(),
            self.test_ocr_harness(),
            self.test_invoices_api(),
            self.test_suppliers_api()
        ]
        
        for test in api_tests:
            result = await test
            self.results.append(result)
            print(f"{'✅' if result['status'] == 'PASS' else '❌'} {result['test']}: {result['status']}")
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['test']}: {result['details']}")
        
        # Save detailed results
        with open("verification_results.json", "w") as f:
            json.dump({
                "timestamp": time.time(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": (passed/total)*100
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: verification_results.json")
        
        return failed == 0

async def main():
    """Main verification function."""
    verifier = SystemVerifier()
    success = await verifier.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! System is ready.")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Please review the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 
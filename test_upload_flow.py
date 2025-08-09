#!/usr/bin/env python3
"""
Test script to verify the upload flow is working properly.
This script tests the complete upload pipeline with debugging and timeout handling.
"""

import asyncio
import aiohttp
import json
import time
import os
from pathlib import Path

# Test configuration
API_BASE_URL = "http://localhost:8000/api"
TEST_FILE_PATH = "test_invoice.pdf"  # Create a simple test PDF if needed

async def test_upload_flow():
    """Test the complete upload flow with debugging."""
    print("🧪 Starting Upload Flow Test")
    print("=" * 50)
    
    # Check if test file exists
    if not os.path.exists(TEST_FILE_PATH):
        print(f"❌ Test file not found: {TEST_FILE_PATH}")
        print("Please create a test PDF file or update TEST_FILE_PATH")
        return False
    
    async with aiohttp.ClientSession() as session:
        try:
            print(f"📤 Uploading file: {TEST_FILE_PATH}")
            
            # Prepare file for upload
            with open(TEST_FILE_PATH, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=os.path.basename(TEST_FILE_PATH))
                
                # Start timer
                start_time = time.time()
                
                # Make upload request with timeout
                async with session.post(
                    f"{API_BASE_URL}/upload",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=60)  # 60 second timeout
                ) as response:
                    
                    elapsed_time = time.time() - start_time
                    print(f"⏱️ Request completed in {elapsed_time:.2f} seconds")
                    
                    if response.status == 200:
                        result = await response.json()
                        print("✅ Upload successful!")
                        print(f"📊 Response: {json.dumps(result, indent=2)}")
                        
                        # Verify response structure
                        required_fields = ['message', 'invoice_id', 'filename', 'parsed_data']
                        missing_fields = [field for field in required_fields if field not in result]
                        
                        if missing_fields:
                            print(f"⚠️ Missing required fields: {missing_fields}")
                            return False
                        
                        # Check parsed data
                        parsed_data = result.get('parsed_data', {})
                        confidence = parsed_data.get('confidence', 0)
                        line_items = parsed_data.get('line_items', [])
                        
                        print(f"📈 Confidence: {confidence}%")
                        print(f"📝 Line items: {len(line_items)}")
                        print(f"🏷️ Supplier: {parsed_data.get('supplier_name', 'Unknown')}")
                        print(f"💰 Total: £{parsed_data.get('total_amount', 0):.2f}")
                        
                        return True
                        
                    else:
                        error_text = await response.text()
                        print(f"❌ Upload failed with status {response.status}")
                        print(f"Error: {error_text}")
                        return False
                        
        except asyncio.TimeoutError:
            print("⏰ Request timed out after 60 seconds")
            return False
        except Exception as e:
            print(f"💥 Unexpected error: {str(e)}")
            return False

async def test_api_health():
    """Test if the API is running and healthy."""
    print("🏥 Testing API Health")
    print("-" * 30)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/invoices", timeout=10) as response:
                if response.status == 200:
                    print("✅ API is healthy and responding")
                    return True
                else:
                    print(f"⚠️ API responded with status {response.status}")
                    return False
        except Exception as e:
            print(f"❌ API health check failed: {str(e)}")
            return False

async def main():
    """Main test function."""
    print("🚀 Owlin Upload Flow Test")
    print("=" * 50)
    
    # Test API health first
    if not await test_api_health():
        print("\n❌ API is not available. Please start the backend server.")
        print("Run: python -m uvicorn backend.main:app --reload --port 8000")
        return
    
    print("\n" + "=" * 50)
    
    # Test upload flow
    success = await test_upload_flow()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Upload flow is working correctly.")
    else:
        print("❌ Tests failed. Check the logs above for details.")
    
    print("\n📋 Debugging Tips:")
    print("• Check browser console for frontend logs")
    print("• Check backend logs for detailed processing info")
    print("• Verify OCR dependencies are installed")
    print("• Check file permissions and disk space")

if __name__ == "__main__":
    asyncio.run(main()) 
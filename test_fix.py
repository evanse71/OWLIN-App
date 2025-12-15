#!/usr/bin/env python3
"""
Test script to verify the excessive_quantity fix
"""

import requests
import time
import subprocess
import sys
import os

def test_api():
    filename = "08871944-5c77-4956-adfa-dfdf88c7fb4a__friday22.08INV.jpeg"
    url = f"http://127.0.0.1:5176/api/dev/ocr-test?filename={filename}"

    print(f"Testing API: {url}")

    try:
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            line_items_count = data.get('line_items_count', 0)
            method_chosen = data.get('line_items_debug', [{}])[0].get('method_chosen', 'unknown')

            print(f"✅ line_items_count: {line_items_count}")
            print(f"✅ method_chosen: {method_chosen}")

            # Check for excessive_quantity in all skip locations
            excessive_found = False

            # Check top-level skipped_lines
            skipped_lines = data.get('skipped_lines', [])
            for line in skipped_lines:
                reason = str(line.get('reason', ''))
                if 'excessive_quantity' in reason:
                    print(f"❌ Found excessive_quantity in skipped_lines: {reason}")
                    excessive_found = True

            # Check debug_skipped
            debug_skipped = data.get('debug_skipped', [])
            for line in debug_skipped:
                reason = str(line.get('reason', ''))
                if 'excessive_quantity' in reason:
                    print(f"❌ Found excessive_quantity in debug_skipped: {reason}")
                    excessive_found = True

            # Check line_items_debug
            line_items_debug = data.get('line_items_debug', [])
            for debug_entry in line_items_debug:
                debug_skipped_lines = debug_entry.get('skipped_lines', [])
                for line in debug_skipped_lines:
                    reason = str(line.get('reason', ''))
                    if 'excessive_quantity' in reason:
                        print(f"❌ Found excessive_quantity in line_items_debug.skipped_lines: {reason}")
                        excessive_found = True

            if not excessive_found:
                print("✅ No excessive_quantity skip reasons found!")

            # Success conditions
            success = (
                line_items_count > 0 and
                method_chosen != 'none' and
                not excessive_found
            )

            if success:
                print("\n🎉 SUCCESS! The fix is working!")
                print("📊 Summary:")
                print(f"   - Items extracted: {line_items_count}")
                print(f"   - Method: {method_chosen}")
                print("   - No excessive_quantity skips")

                # Show sample item if available
                if data.get('line_items') and len(data['line_items']) > 0:
                    item = data['line_items'][0]
                    print(f"   - Sample item: {item.get('description', '')[:50]}... qty={item.get('quantity')}")

            else:
                print("\n❌ FAILURE! Issues found:")
                if line_items_count == 0:
                    print("   - Still returning 0 line items")
                if method_chosen == 'none':
                    print("   - Still method_chosen = 'none'")
                if excessive_found:
                    print("   - Still has excessive_quantity skip reasons")

            return success

        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    print("🔧 Testing excessive_quantity fix")
    print("=" * 50)

    # Check if server is running
    try:
        response = requests.get("http://127.0.0.1:5176/api/dev/ocr-test?list_uploads=true", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server not responding properly")
            return
    except:
        print("❌ Server not running on port 5176")
        print("Please start the backend first with: .\\start_backend_5176.bat")
        return

    # Run the test
    success = test_api()

    print("=" * 50)
    if success:
        print("✅ Fix verification: PASSED")
    else:
        print("❌ Fix verification: FAILED")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Compile Test for Invoice Page Module
Tests that the invoice page module can be imported and compiled without syntax errors.
"""

import sys
import os
import importlib.util

def test_invoice_page_compile():
    """Test that the invoice page module compiles and imports successfully."""
    try:
        # Test compilation
        import py_compile
        py_compile.compile('app/invoices_page.py', doraise=True)
        print("✅ Invoice page compiles successfully")
        
        # Test import
        spec = importlib.util.spec_from_file_location("invoices_page", "app/invoices_page.py")
        if spec is None:
            print("❌ Failed to create module spec")
            return False
        
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            print("❌ Module spec has no loader")
            return False
        
        spec.loader.exec_module(module)
        print("✅ Invoice page imports successfully")
        
        # Test that main function exists
        if hasattr(module, 'render_invoices_page'):
            print("✅ render_invoices_page function found")
        else:
            print("❌ render_invoices_page function not found")
            return False
        
        # Test that key functions exist
        required_functions = [
            'get_status_icon',
            'render_metric_box',
            'render_invoice_list',
            'load_invoices_from_db',
            'get_processing_status_summary'
        ]
        
        missing_functions = []
        for func_name in required_functions:
            if not hasattr(module, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            print(f"❌ Missing required functions: {missing_functions}")
            return False
        else:
            print("✅ All required functions found")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error in invoice page: {e}")
        return False
    except ImportError as e:
        print(f"❌ Import error in invoice page: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error testing invoice page: {e}")
        return False

def test_simple_invoice_page_compile():
    """Test that the simple invoice page module also compiles."""
    try:
        if os.path.exists('app/invoices_page_simple.py'):
            import py_compile
            py_compile.compile('app/invoices_page_simple.py', doraise=True)
            print("✅ Simple invoice page compiles successfully")
            return True
        else:
            print("ℹ️ Simple invoice page not found, skipping test")
            return True
    except Exception as e:
        print(f"❌ Error testing simple invoice page: {e}")
        return False

def main():
    """Run all compile tests."""
    print("Testing Invoice Page Compilation")
    print("=" * 40)
    
    success = True
    
    # Test main invoice page
    if not test_invoice_page_compile():
        success = False
    
    print()
    
    # Test simple invoice page
    if not test_simple_invoice_page_compile():
        success = False
    
    print()
    print("=" * 40)
    
    if success:
        print("🎉 All compile tests passed!")
        return 0
    else:
        print("❌ Some compile tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 
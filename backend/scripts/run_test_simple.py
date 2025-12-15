#!/usr/bin/env python3
"""Simplified test runner that writes to both console and file."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.scripts.test_invoice_validation import test_invoice_validation

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_test_simple.py <invoice_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Run test - it will write to file if output_file is provided
    # Also print to console
    import io
    from contextlib import redirect_stdout
    
    if output_file:
        # Capture output and write to both file and console
        class TeeOutput:
            def __init__(self, file, console):
                self.file = file
                self.console = console
            def write(self, text):
                self.file.write(text)
                self.console.write(text)
                self.file.flush()
                self.console.flush()
            def flush(self):
                self.file.flush()
                self.console.flush()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            original_stdout = sys.stdout
            sys.stdout = TeeOutput(f, original_stdout)
            try:
                test_invoice_validation(file_path, None)  # Don't double-wrap
            finally:
                sys.stdout = original_stdout
    else:
        test_invoice_validation(file_path, None)

#!/usr/bin/env python3
"""
Template Library Verification Script
"""
import yaml
import os
import sys

def test_template_library():
    """Test template library loading and validation."""
    print("🔍 Template Library Verification")
    print("=" * 50)
    
    template_dir = "backend/templates/suppliers"
    templates = []
    errors = []
    
    try:
        for filename in os.listdir(template_dir):
            if filename.endswith('.yaml'):
                filepath = os.path.join(template_dir, filename)
                try:
                    with open(filepath, 'r') as file:
                        data = yaml.safe_load(file)
                    
                    # Validate required fields
                    required_fields = ['name', 'supplier', 'field_overrides']
                    for field in required_fields:
                        if field not in data:
                            errors.append(f"{filename}: Missing required field '{field}'")
                    
                    if 'supplier' in data and 'name' in data['supplier']:
                        templates.append({
                            'name': data['name'],
                            'supplier': data['supplier']['name'],
                            'aliases': len(data['supplier'].get('aliases', [])),
                            'field_overrides': len(data.get('field_overrides', {}))
                        })
                    
                except yaml.YAMLError as e:
                    errors.append(f"{filename}: YAML parse error - {e}")
                except Exception as e:
                    errors.append(f"{filename}: Error - {e}")
        
        # Print results
        if templates:
            print("✅ Template Library Status:")
            for template in templates:
                print(f"  ✅ {template['name']} - {template['supplier']} ({template['aliases']} aliases, {template['field_overrides']} field overrides)")
        else:
            print("⚠️  No templates found")
        
        if errors:
            print("\n❌ Template Errors:")
            for error in errors:
                print(f"  ❌ {error}")
        else:
            print("\n✅ All templates loaded successfully")
            
        return len(errors) == 0
        
    except Exception as e:
        print(f"❌ Template library verification failed: {e}")
        return False

if __name__ == "__main__":
    success = test_template_library()
    sys.exit(0 if success else 1)

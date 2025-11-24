"""
Unit tests for the supplier template system.

Tests template loading, matching, and override functionality.
"""

import unittest
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.templates.loader import TemplateLoader, get_template_loader
from backend.templates.matcher import TemplateMatcher, get_template_matcher
from backend.templates.override import TemplateOverride, get_template_override


class TestTemplateLoader(unittest.TestCase):
    """Test template loader functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.loader = TemplateLoader(self.temp_dir)
        
        # Create test template
        self.test_template = {
            'name': 'Test Supplier',
            'version': '1.0',
            'description': 'Test template',
            'supplier': {
                'name': 'Test Supplier Ltd',
                'aliases': ['Test', 'Test Ltd'],
                'vat_ids': ['GB123456789'],
                'header_tokens': ['Test', 'Invoice']
            },
            'field_overrides': {
                'total': {
                    'patterns': ['Total.*?£([0-9,]+\.?[0-9]*)'],
                    'currency_symbols': ['£', 'GBP']
                }
            },
            'processing': {
                'fuzzy_threshold': 0.8,
                'case_sensitive': False,
                'priority': 10
            }
        }
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_load_template(self):
        """Test loading a single template."""
        # Create test template file
        template_path = Path(self.temp_dir) / "test_supplier.yaml"
        with open(template_path, 'w') as f:
            yaml.dump(self.test_template, f)
        
        # Load template
        loaded_template = self.loader.load_template(str(template_path))
        
        self.assertIsNotNone(loaded_template)
        self.assertEqual(loaded_template['name'], 'Test Supplier')
        self.assertEqual(loaded_template['supplier']['name'], 'Test Supplier Ltd')
        self.assertIn('_file_path', loaded_template)
        self.assertIn('_file_name', loaded_template)
    
    def test_load_all_templates(self):
        """Test loading all templates from directory."""
        # Create test template files
        for i in range(3):
            template_path = Path(self.temp_dir) / f"supplier_{i}.yaml"
            template_data = self.test_template.copy()
            template_data['name'] = f'Supplier {i}'
            template_data['supplier']['name'] = f'Supplier {i} Ltd'
            
            with open(template_path, 'w') as f:
                yaml.dump(template_data, f)
        
        # Load all templates
        templates = self.loader.load_all_templates()
        
        self.assertEqual(len(templates), 3)
        self.assertIn('supplier_0', templates)
        self.assertIn('supplier_1', templates)
        self.assertIn('supplier_2', templates)
    
    def test_validate_template(self):
        """Test template validation."""
        # Valid template
        valid_template = self.test_template.copy()
        self.assertTrue(self.loader._validate_template(valid_template, "test.yaml"))
        
        # Missing required field
        invalid_template = valid_template.copy()
        del invalid_template['name']
        self.assertFalse(self.loader._validate_template(invalid_template, "test.yaml"))
        
        # Invalid supplier field
        invalid_template = valid_template.copy()
        invalid_template['supplier'] = "not a dict"
        self.assertFalse(self.loader._validate_template(invalid_template, "test.yaml"))
    
    def test_get_template_stats(self):
        """Test template statistics."""
        # Create test templates
        for i in range(2):
            template_path = Path(self.temp_dir) / f"supplier_{i}.yaml"
            template_data = self.test_template.copy()
            template_data['name'] = f'Supplier {i}'
            template_data['supplier']['name'] = f'Supplier {i} Ltd'
            template_data['processing']['priority'] = i * 5
            
            with open(template_path, 'w') as f:
                yaml.dump(template_data, f)
        
        # Load templates and get stats
        self.loader.load_all_templates()
        stats = self.loader.get_template_stats()
        
        self.assertEqual(stats['total_templates'], 2)
        self.assertEqual(len(stats['template_names']), 2)
        self.assertEqual(len(stats['suppliers']), 2)
        self.assertEqual(len(stats['priorities']), 2)


class TestTemplateMatcher(unittest.TestCase):
    """Test template matcher functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.matcher = TemplateMatcher(fuzzy_threshold=0.8)
        
        # Create test templates
        self.templates = {
            'brakes': {
                'name': 'Brakes Food Service',
                'supplier': {
                    'name': 'Brakes Food Service',
                    'aliases': ['Brakes', 'Brakes Food'],
                    'vat_ids': ['GB123456789'],
                    'header_tokens': ['Brakes', 'Food Service', 'Invoice']
                },
                'processing': {'priority': 10}
            },
            'bidfood': {
                'name': 'Bidfood',
                'supplier': {
                    'name': 'Bidfood',
                    'aliases': ['Bidfood Ltd', 'Bidfood UK'],
                    'vat_ids': ['GB234567890'],
                    'header_tokens': ['Bidfood', 'Wholesale', 'Invoice']
                },
                'processing': {'priority': 9}
            }
        }
    
    def test_match_template_exact_name(self):
        """Test exact supplier name matching."""
        result = self.matcher.match_template(
            supplier_guess="Brakes Food Service",
            header_text="",
            vat_id="",
            templates=self.templates
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Brakes Food Service')
    
    def test_match_template_alias(self):
        """Test supplier alias matching."""
        result = self.matcher.match_template(
            supplier_guess="Brakes",
            header_text="",
            vat_id="",
            templates=self.templates
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Brakes Food Service')
    
    def test_match_template_header_tokens(self):
        """Test header token matching."""
        result = self.matcher.match_template(
            supplier_guess="Unknown Supplier",
            header_text="Brakes Food Service Invoice #12345",
            vat_id="",
            templates=self.templates
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Brakes Food Service')
    
    def test_match_template_vat_id(self):
        """Test VAT ID matching."""
        result = self.matcher.match_template(
            supplier_guess="Unknown Supplier",
            header_text="",
            vat_id="GB123456789",
            templates=self.templates
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Brakes Food Service')
    
    def test_match_template_no_match(self):
        """Test no match scenario."""
        result = self.matcher.match_template(
            supplier_guess="Completely Unknown Supplier",
            header_text="Random text",
            vat_id="GB999999999",
            templates=self.templates
        )
        
        self.assertIsNone(result)
    
    def test_calculate_similarity(self):
        """Test similarity calculation."""
        similarity = self.matcher._calculate_similarity("Brakes", "Brakes Food Service")
        self.assertGreater(similarity, 0.5)
        
        similarity = self.matcher._calculate_similarity("Brakes", "Completely Different")
        self.assertLess(similarity, 0.5)
    
    def test_normalize_text(self):
        """Test text normalization."""
        normalized = self.matcher._normalize_text("  Brakes Food Service Ltd.  ")
        self.assertEqual(normalized, "brakes food service ltd")
        
        normalized = self.matcher._normalize_text("Brakes-Food_Service")
        self.assertEqual(normalized, "brakes food service")


class TestTemplateOverride(unittest.TestCase):
    """Test template override functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.override = TemplateOverride()
        
        # Create test template
        self.template = {
            'name': 'Test Supplier',
            'version': '1.0',
            'field_overrides': {
                'total': {
                    'patterns': ['Total.*?£([0-9,]+\.?[0-9]*)', 'Amount.*?£([0-9,]+\.?[0-9]*)'],
                    'currency_symbols': ['£', 'GBP']
                },
                'vat_total': {
                    'patterns': ['VAT.*?£([0-9,]+\.?[0-9]*)'],
                    'currency_symbols': ['£', 'GBP']
                },
                'date': {
                    'patterns': ['Date.*?([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})'],
                    'format': 'DD/MM/YYYY'
                }
            }
        }
    
    def test_apply_overrides_missing_fields(self):
        """Test applying overrides to missing fields."""
        invoice_card = {
            'supplier_name': 'Test Supplier',
            'total_amount': None,  # Missing
            'vat_total': None,     # Missing
            'date': None           # Missing
        }
        
        header_text = "Invoice Total: £120.00 VAT: £20.00 Date: 15/01/2024"
        
        result = self.override.apply_overrides(invoice_card, self.template, header_text)
        
        self.assertEqual(result['total_amount'], 120.0)
        self.assertEqual(result['vat_total'], 20.0)
        self.assertEqual(result['date'], '15/01/2024')
        self.assertIn('template_overrides', result)
    
    def test_apply_overrides_preserve_existing(self):
        """Test that existing fields are not overwritten."""
        invoice_card = {
            'supplier_name': 'Test Supplier',
            'total_amount': 100.0,  # Already present
            'vat_total': 15.0,     # Already present
            'date': '10/01/2024'    # Already present
        }
        
        header_text = "Invoice Total: £120.00 VAT: £20.00 Date: 15/01/2024"
        
        result = self.override.apply_overrides(invoice_card, self.template, header_text)
        
        # Existing values should be preserved
        self.assertEqual(result['total_amount'], 100.0)
        self.assertEqual(result['vat_total'], 15.0)
        self.assertEqual(result['date'], '10/01/2024')
        # No overrides should be applied
        self.assertNotIn('template_overrides', result)
    
    def test_extract_total(self):
        """Test total amount extraction."""
        header_text = "Invoice Total: £120.50"
        total_config = self.template['field_overrides']['total']
        
        result = self.override._extract_total(total_config, header_text)
        self.assertEqual(result, 120.5)
    
    def test_extract_vat_total(self):
        """Test VAT total extraction."""
        header_text = "VAT: £20.00"
        vat_config = self.template['field_overrides']['vat_total']
        
        result = self.override._extract_vat_total(vat_config, header_text)
        self.assertEqual(result, 20.0)
    
    def test_extract_date(self):
        """Test date extraction."""
        header_text = "Date: 15/01/2024"
        date_config = self.template['field_overrides']['date']
        
        result = self.override._extract_date(date_config, header_text)
        self.assertEqual(result, '15/01/2024')
    
    def test_apply_overrides_no_template(self):
        """Test applying overrides with no template."""
        invoice_card = {'supplier_name': 'Test Supplier'}
        
        result = self.override.apply_overrides(invoice_card, None, "")
        self.assertEqual(result, invoice_card)
    
    def test_apply_overrides_no_invoice_card(self):
        """Test applying overrides with no invoice card."""
        result = self.override.apply_overrides(None, self.template, "")
        self.assertIsNone(result)


class TestTemplateIntegration(unittest.TestCase):
    """Test template system integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test template
        self.test_template = {
            'name': 'Brakes Food Service',
            'version': '1.0',
            'supplier': {
                'name': 'Brakes Food Service',
                'aliases': ['Brakes', 'Brakes Food'],
                'vat_ids': ['GB123456789'],
                'header_tokens': ['Brakes', 'Food Service', 'Invoice']
            },
            'field_overrides': {
                'total': {
                    'patterns': ['Total.*?£([0-9,]+\.?[0-9]*)'],
                    'currency_symbols': ['£', 'GBP']
                }
            },
            'processing': {
                'fuzzy_threshold': 0.8,
                'priority': 10
            }
        }
        
        # Create template file
        template_path = Path(self.temp_dir) / "brakes.yaml"
        with open(template_path, 'w') as f:
            yaml.dump(self.test_template, f)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_workflow(self):
        """Test complete template workflow."""
        # Load templates
        loader = TemplateLoader(self.temp_dir)
        templates = loader.load_all_templates()
        
        # Match template
        matcher = TemplateMatcher()
        matched_template = matcher.match_template(
            supplier_guess="Brakes",
            header_text="Brakes Food Service Invoice Total: £120.00",
            templates=templates
        )
        
        self.assertIsNotNone(matched_template)
        
        # Apply overrides
        invoice_card = {
            'supplier_name': 'Brakes',
            'total_amount': None  # Missing
        }
        
        override = TemplateOverride()
        result = override.apply_overrides(
            invoice_card, 
            matched_template, 
            "Brakes Food Service Invoice Total: £120.00"
        )
        
        self.assertEqual(result['total_amount'], 120.0)
        self.assertIn('template_overrides', result)


if __name__ == '__main__':
    unittest.main()

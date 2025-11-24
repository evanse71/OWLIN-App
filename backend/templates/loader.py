"""
Template Loader

Loads and manages supplier templates from YAML files.
Provides template discovery, validation, and caching.
"""

from __future__ import annotations
import logging
import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LOGGER = logging.getLogger("owlin.templates.loader")


class TemplateLoader:
    """Loads and manages supplier templates from YAML files."""
    
    def __init__(self, templates_dir: str = "backend/templates/suppliers"):
        """Initialize template loader with templates directory."""
        self.templates_dir = Path(templates_dir)
        self._templates_cache: Dict[str, Dict[str, Any]] = {}
        self._last_scan_time: float = 0.0
        
    def scan_templates(self) -> List[str]:
        """Scan templates directory and return list of template files."""
        if not self.templates_dir.exists():
            LOGGER.warning(f"Templates directory not found: {self.templates_dir}")
            return []
        
        template_files = []
        for file_path in self.templates_dir.glob("*.yaml"):
            if file_path.name != "schema.yaml":  # Skip schema file
                template_files.append(str(file_path))
        
        LOGGER.info(f"Found {len(template_files)} template files")
        return template_files
    
    def load_template(self, template_path: str) -> Optional[Dict[str, Any]]:
        """Load a single template from YAML file."""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
            
            if not template_data:
                LOGGER.warning(f"Empty template file: {template_path}")
                return None
            
            # Validate template structure
            if not self._validate_template(template_data, template_path):
                return None
            
            # Add metadata
            template_data['_file_path'] = template_path
            template_data['_file_name'] = Path(template_path).stem
            
            LOGGER.debug(f"Loaded template: {template_data.get('name', 'Unknown')}")
            return template_data
            
        except yaml.YAMLError as e:
            LOGGER.warning(f"YAML parse error in {template_path}: {e}")
            return None
        except Exception as e:
            LOGGER.error(f"Failed to load template {template_path}: {e}")
            return None
    
    def load_all_templates(self, force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
        """Load all templates from the templates directory."""
        current_time = os.path.getmtime(self.templates_dir) if self.templates_dir.exists() else 0
        
        # Use cache if not forcing reload and directory hasn't changed
        if not force_reload and current_time <= self._last_scan_time and self._templates_cache:
            return self._templates_cache
        
        self._templates_cache.clear()
        template_files = self.scan_templates()
        
        for template_path in template_files:
            template_data = self.load_template(template_path)
            if template_data:
                template_name = template_data['_file_name']
                self._templates_cache[template_name] = template_data
        
        self._last_scan_time = current_time
        LOGGER.info(f"Loaded {len(self._templates_cache)} templates")
        
        return self._templates_cache
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by name."""
        if not self._templates_cache:
            self.load_all_templates()
        
        return self._templates_cache.get(template_name)
    
    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded templates."""
        if not self._templates_cache:
            self.load_all_templates()
        
        return self._templates_cache.copy()
    
    def _validate_template(self, template_data: Dict[str, Any], template_path: str) -> bool:
        """Validate template structure and required fields."""
        required_fields = ['name', 'version', 'supplier']
        
        # Check required top-level fields
        for field in required_fields:
            if field not in template_data:
                LOGGER.warning(f"Missing required field '{field}' in {template_path}")
                return False
        
        # Check supplier field structure
        supplier = template_data.get('supplier', {})
        if not isinstance(supplier, dict):
            LOGGER.warning(f"Invalid supplier field in {template_path}")
            return False
        
        if 'name' not in supplier:
            LOGGER.warning(f"Missing supplier.name in {template_path}")
            return False
        
        # Validate field_overrides if present
        if 'field_overrides' in template_data:
            field_overrides = template_data['field_overrides']
            if not isinstance(field_overrides, dict):
                LOGGER.warning(f"Invalid field_overrides in {template_path}")
                return False
        
        # Validate processing rules if present
        if 'processing' in template_data:
            processing = template_data['processing']
            if not isinstance(processing, dict):
                LOGGER.warning(f"Invalid processing rules in {template_path}")
                return False
        
        return True
    
    def get_template_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded templates."""
        templates = self.get_all_templates()
        
        stats = {
            'total_templates': len(templates),
            'template_names': list(templates.keys()),
            'suppliers': [],
            'priorities': []
        }
        
        for template_name, template_data in templates.items():
            supplier_name = template_data.get('supplier', {}).get('name', 'Unknown')
            stats['suppliers'].append(supplier_name)
            
            priority = template_data.get('processing', {}).get('priority', 0)
            stats['priorities'].append(priority)
        
        return stats


# Global template loader instance
_template_loader: Optional[TemplateLoader] = None


def get_template_loader() -> TemplateLoader:
    """Get global template loader instance."""
    global _template_loader
    if _template_loader is None:
        _template_loader = TemplateLoader()
    return _template_loader


def load_all_templates(force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
    """Load all templates using global loader."""
    loader = get_template_loader()
    return loader.load_all_templates(force_reload)


def get_template(template_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific template by name."""
    loader = get_template_loader()
    return loader.get_template(template_name)

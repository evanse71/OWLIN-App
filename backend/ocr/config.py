#!/usr/bin/env python3

# OCR Backend Safety - Optional Dependencies
try:
    import paddleocr as _paddle  # optional
    PADDLE_OK = True
except Exception:
    PADDLE_OK = False

try:
    import pytesseract as _tess   # optional
    TESSERACT_OK = True
except Exception:
    TESSERACT_OK = False

OCR_BACKENDS = {"paddle": PADDLE_OK, "tesseract": TESSERACT_OK}
DEFAULT_OCR = "paddle" if PADDLE_OK else ("tesseract" if TESSERACT_OK else None)
"""
OCR Configuration Management

Loads and manages OCR configuration from ocr_config.json
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

class OCRConfig:
    """OCR Configuration Manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "ocr_config.json"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                print(f"✅ Loaded OCR config from {self.config_path}")
                return config
            else:
                print(f"⚠️ OCR config not found at {self.config_path}, using defaults")
                return self._get_default_config()
        except Exception as e:
            print(f"❌ Failed to load OCR config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "thresholds": {
                "accept_min_confidence": 90,
                "warning_min_confidence": 70,
                "reject_max_confidence": 50,
                "arithmetic_tolerance": {
                    "fixed": 0.50,
                    "percentage": 0.005
                },
                "future_date_days": 3
            },
            "classification": {
                "negative_lexicon_gate": 0.35,
                "min_fields_for_invoice": ["supplier", "total", "date"]
            },
            "performance": {
                "per_page_timeout_seconds": 10,
                "document_timeout_seconds": 90,
                "max_pages_for_overlay": 50,
                "max_words_for_overlay": 60000
            },
            "validation": {
                "ignore_receipt_meta_rows": ["change", "cash", "card", "rounding", "void", "refund"],
                "currency_symbols": ["£", "€", "$"],
                "date_parsing": {
                    "order": "DMY",
                    "timezone": "Europe/London"
                }
            },
            "policy": {
                "critical_issues": ["ARITHMETIC_MISMATCH", "CURRENCY_INCONSISTENT", "FUTURE_DATE", "ARITH_FAIL"],
                "auto_retry": {
                    "enabled": True,
                    "confidence_threshold": 55,
                    "avg_confidence_threshold": 50,
                    "retry_profile": "receipt",
                    "rotation_angles": [-2, 2]
                }
            },
            "ui": {
                "debug_panel_default": False,
                "tooltips": {
                    "accept": "All checks passed.",
                    "warning": "Minor issues (see Why?).",
                    "quarantine": "Needs review — arithmetic/currency/date issue.",
                    "reject": "Not a valid business document (menu/letter/etc.).",
                    "heic_not_supported": "Install HEIC support to auto-process iPhone photos."
                }
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_threshold(self, name: str) -> float:
        """Get threshold value"""
        return self.get(f"thresholds.{name}", 0.0)
    
    def get_performance(self, name: str) -> Any:
        """Get performance setting"""
        return self.get(f"performance.{name}")
    
    def get_validation(self, name: str) -> Any:
        """Get validation setting"""
        return self.get(f"validation.{name}")
    
    def get_policy(self, key: str, default: Any = None) -> Any:
        """Get policy configuration value"""
        return self._config.get('policy', {}).get(key, default)
    
    def get_llm(self, key: str, default: Any = None) -> Any:
        """Get LLM configuration value"""
        return self._config.get('llm', {}).get(key, default)
    
    def get_classification(self, key: str, default: Any = None) -> Any:
        """Get classification configuration value"""
        return self._config.get('classification', {}).get(key, default)
    
    def get_supported_langs(self) -> List[str]:
        """Get list of supported languages"""
        return self._config.get('supported_langs', ['en'])
    
    def get_preferred_ui_lang(self) -> str:
        """Get preferred UI language"""
        return self._config.get('preferred_ui_lang', 'en')
    
    def get_lang_detect(self, key: str, default: Any = None) -> Any:
        """Get language detection configuration value"""
        return self._config.get('lang_detect', {}).get(key, default)
    
    def get_ui_tooltip(self, action: str) -> str:
        """Get UI tooltip for policy action"""
        return self.get(f"ui.tooltips.{action.lower()}", "")
    
    def calculate_arithmetic_tolerance(self, total_amount: float) -> float:
        """Calculate arithmetic tolerance based on total amount"""
        fixed = self.get_threshold("arithmetic_tolerance.fixed")
        percentage = self.get("thresholds.arithmetic_tolerance.percentage", 0.005)
        return max(fixed, total_amount * percentage)

# Global config instance
_ocr_config: Optional[OCRConfig] = None

def get_ocr_config() -> OCRConfig:
    """Get global OCR configuration instance"""
    global _ocr_config
    if _ocr_config is None:
        _ocr_config = OCRConfig()
    return _ocr_config

def reload_config() -> OCRConfig:
    """Reload configuration from file"""
    global _ocr_config
    _ocr_config = OCRConfig()
    return _ocr_config 
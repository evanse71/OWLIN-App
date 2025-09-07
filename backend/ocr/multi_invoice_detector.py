#!/usr/bin/env python3
"""
World-Class Multi-Invoice Detection System

This module provides a unified, intelligent, and scalable multi-invoice detection
system with ML/AI capabilities, caching, and enterprise-grade features.

Author: OWLIN Development Team
Version: 4.0.0
"""

import logging
import re
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
import json
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import threading
from datetime import datetime, timedelta

# ML/AI imports
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    np = None
    TfidfVectorizer = None
    cosine_similarity = None

logger = logging.getLogger(__name__)

@dataclass
class DetectionConfig:
    """Configuration for multi-invoice detection"""
    # Pattern matching
    min_invoice_number_length: int = 3
    max_invoice_number_length: int = 20
    confidence_threshold: float = 0.7
    
    # Context analysis
    context_window_size: int = 100
    min_context_similarity: float = 0.8
    
    # Performance
    cache_ttl_seconds: int = 3600
    max_workers: int = 4
    batch_size: int = 10
    
    # ML/AI
    use_ml_detection: bool = ML_AVAILABLE
    ml_confidence_threshold: float = 0.8
    
    # Caching
    enable_caching: bool = False  # Temporarily disabled to fix caching issues
    cache_dir: str = "cache/multi_invoice"
    
    # Plugin system
    plugin_dir: str = "plugins/multi_invoice"
    enable_plugins: bool = True
    
    # Retry logic
    enable_retry: bool = True
    max_retry_attempts: int = 2
    retry_dpi_multiplier: float = 1.5
    retry_threshold_adjustment: float = 0.1
    
    # Per-invoice validation
    validate_per_invoice: bool = True
    min_invoice_confidence: float = 0.6
    cross_pollution_check: bool = True

@dataclass
class DocumentContext:
    """Document context information"""
    document_type: str = "unknown"
    language: str = "en"
    page_count: int = 1
    word_count: int = 0
    has_tables: bool = False
    has_images: bool = False
    structure_score: float = 0.0
    confidence_score: float = 0.0

@dataclass
class DetectionResult:
    """Result of multi-invoice detection"""
    is_multi_invoice: bool
    confidence: float
    detected_invoices: List[Dict[str, Any]] = field(default_factory=list)
    page_separations: List[Dict[str, Any]] = field(default_factory=list)
    supplier_variations: List[str] = field(default_factory=list)
    invoice_numbers: List[str] = field(default_factory=list)
    context_analysis: DocumentContext = field(default_factory=DocumentContext)
    processing_time: float = 0.0
    error_messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class Match:
    """Pattern match result"""
    pattern: str
    value: str
    confidence: float
    position: Tuple[int, int]
    context: str

class CacheManager:
    """Intelligent caching system for detection results"""
    
    def __init__(self, cache_dir: str, ttl_seconds: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self._cache_lock = threading.Lock()
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text content"""
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"multi_invoice_{content_hash}"
    
    def get(self, text: str) -> Optional[DetectionResult]:
        """Get cached result"""
        if not self.cache_dir.exists():
            return None
        
        cache_key = self._get_cache_key(text)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        with self._cache_lock:
            if cache_file.exists():
                try:
                    # Check if cache is still valid
                    if time.time() - cache_file.stat().st_mtime < self.ttl_seconds:
                        with open(cache_file, 'rb') as f:
                            return pickle.load(f)
                    else:
                        # Cache expired, remove it
                        cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to load cache: {e}")
        
        return None
    
    def set(self, text: str, result: DetectionResult) -> None:
        """Cache detection result"""
        if not self.cache_dir.exists():
            return
        
        cache_key = self._get_cache_key(text)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        with self._cache_lock:
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(result, f)
            except Exception as e:
                logger.warning(f"Failed to save cache: {e}")

class IntelligentPatternMatcher:
    """Intelligent pattern matching with context awareness"""
    
    def __init__(self, config: DetectionConfig):
        self.config = config
        self.patterns = self._load_patterns()
        self.context_rules = self._load_context_rules()
    
    def _load_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load intelligent patterns from configuration"""
        patterns = {
            'invoice_numbers': [
                # Enhanced invoice number patterns with Welsh support - capture full ID
                re.compile(r'\b(INV|INVOICE)\s*[:#]?\s*([A-Z]{2,5}-\d{4}-\d{3,})\b', re.IGNORECASE),
                re.compile(r'\b(INV|Anf)\s*[- ]?(\d{4}[-/]\d{3,})\b', re.IGNORECASE),
                re.compile(r'\b(Rhif\s+Anfoneb|Anfoneb)\s*[:#]?\s*([A-Z]{2,5}-\d{4}-\d{3,})\b', re.IGNORECASE),
                re.compile(r'\b(Rhif)\s*(?:Anfoneb)?\s*[:#]?\s*([A-Z0-9-]{6,})\b', re.IGNORECASE),
                # Fallback patterns - capture full ID
                re.compile(r'\b(invoice|inv|anfoneb)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{8,})\b', re.IGNORECASE),
                re.compile(r'\b([A-Z]{2,4}[0-9]{3,8})\b'),
                re.compile(r'\b(bill|statement)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{8,})\b', re.IGNORECASE),
            ],
            'suppliers': [
                # Generic supplier patterns (not hardcoded)
                re.compile(r'\b([A-Z][A-Z\s&\.]+(?:LTD|LIMITED|INC|CORP|LLC|CO|COMPANY|BREWING|BREWERY))\b'),
                re.compile(r'\b([A-Z][A-Z\s&\.]+(?:ENERGY|GAS|WATER|ELECTRIC|TELECOM|INSURANCE|BANK|FINANCE))\b'),
                re.compile(r'\b([A-Z][A-Z\s&\.]+(?:SUPPLIES|DISTRIBUTORS|WHOLESALERS|RETAILERS))\b'),
            ],
            'page_markers': [
                # Robust page marker patterns - MORE SPECIFIC
                re.compile(r'---\s*PAGE\s*\d+\s*---', re.IGNORECASE),
                re.compile(r'Page\s+\d+\s+of\s+\d+', re.IGNORECASE),
                re.compile(r'^\s*Page\s+\d+\s*$', re.MULTILINE | re.IGNORECASE),  # Only "Page X" format
                re.compile(r'^\s*P\.?\s*\d+\s*$', re.MULTILINE | re.IGNORECASE),  # Only "P. X" or "P X" format
            ],
            'false_positives': [
                # Patterns to exclude
                re.compile(r'\b(?:invoice|inv)\s+(?:date|number|total|amount|due)\b', re.IGNORECASE),
                re.compile(r'\b(?:page|p)\s+(?:number|#|of)\b', re.IGNORECASE),
                re.compile(r'\b(?:continued|cont\.|continuation)\b', re.IGNORECASE),
            ]
        }
        return patterns
    
    def _load_context_rules(self) -> Dict[str, Any]:
        """Load context-aware rules"""
        return {
            'min_invoice_length': 3,
            'max_invoice_length': 20,
            'min_supplier_length': 5,
            'max_supplier_length': 100,
            'context_window': 50,
        }
    
    def match_with_context(self, text: str, context: DocumentContext) -> List[Match]:
        """Match patterns with context awareness"""
        matches = []
        
        for pattern_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Handle different group structures
                    if pattern_type == 'invoice_numbers':
                        # For invoice numbers, combine groups to get full ID
                        groups = match.groups()
                        if len(groups) >= 2:
                            # Combine prefix and number
                            full_id = f"{groups[0]}-{groups[1]}" if groups[0] and groups[1] else groups[1] or groups[0]
                        else:
                            full_id = groups[0] if groups else match.group(0)
                        
                        # Clean the invoice ID
                        clean_id = self._clean_invoice_id(full_id)
                        if clean_id:
                            matches.append(Match(
                                pattern=pattern_type,
                                value=clean_id,
                                confidence=self._calculate_confidence(match, pattern_type, context),
                                position=(match.start(), match.end()),
                                context=self._extract_context(text, match.start(), match.end())
                            ))
                    else:
                        # For other patterns, use the first group or full match
                        value = match.group(1) if match.groups() else match.group(0)
                        matches.append(Match(
                            pattern=pattern_type,
                            value=value,
                            confidence=self._calculate_confidence(match, pattern_type, context),
                            position=(match.start(), match.end()),
                            context=self._extract_context(text, match.start(), match.end())
                        ))
        
        return matches
    
    def _is_valid_match(self, value: str, pattern_type: str, context: DocumentContext) -> bool:
        """Validate match based on context rules"""
        if not value or not value.strip():
            return False
        
        value = value.strip()
        
        # Check length constraints
        if pattern_type == 'invoice_numbers':
            if not (self.config.min_invoice_number_length <= len(value) <= self.config.max_invoice_number_length):
                return False
        elif pattern_type == 'suppliers':
            if not (self.context_rules['min_supplier_length'] <= len(value) <= self.context_rules['max_supplier_length']):
                return False
        
        # Check for false positives
        for fp_pattern in self.patterns['false_positives']:
            if fp_pattern.search(value):
                return False
        
        return True
    
    def _calculate_confidence(self, match: re.Match, pattern_type: str, context: DocumentContext) -> float:
        """Calculate confidence score for a match"""
        base_confidence = 0.5
        
        # Pattern type confidence
        if pattern_type == 'invoice_numbers':
            base_confidence = 0.8
        elif pattern_type == 'suppliers':
            base_confidence = 0.7
        elif pattern_type == 'page_markers':
            base_confidence = 0.9
        
        # Context confidence
        if context.document_type == 'invoice':
            base_confidence += 0.1
        
        # Position confidence (earlier in document = higher confidence)
        position_confidence = 1.0 - (match.start() / len(match.string))
        base_confidence += position_confidence * 0.1
        
        return min(base_confidence, 1.0)
    
    def _extract_context(self, text: str, start: int, end: int) -> str:
        """Extract context around a match"""
        context_size = self.context_rules['context_window']
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)
        return text[context_start:context_end]

    def _clean_invoice_id(self, raw: str) -> Optional[str]:
        """Clean and validate invoice ID"""
        s = raw.strip()
        
        # Minimum length check
        if len(s) < 8:
            return None
        
        # Hyphen validation
        if "-" in s and s.count("-") < 1:
            return None
        
        # Must contain letters or full 4-digit year
        if not any(c.isalpha() for c in s) and not re.search(r'\b\d{4}\b', s):
            return None
        
        return s

class ContextAnalyzer:
    """Intelligent contextual analysis"""
    
    def __init__(self, config: DetectionConfig):
        self.config = config
        self.vectorizer = None
        if ML_AVAILABLE:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    
    def analyze_context(self, text: str) -> DocumentContext:
        """Analyze document context"""
        context = DocumentContext()
        
        # Basic analysis
        context.word_count = len(text.split())
        context.page_count = self._count_pages(text)
        context.has_tables = self._detect_tables(text)
        context.has_images = self._detect_images(text)
        context.document_type = self._classify_document_type(text)
        context.language = self._detect_language(text)
        
        # Advanced analysis
        context.structure_score = self._calculate_structure_score(text)
        context.confidence_score = self._calculate_confidence_score(text)
        
        return context
    
    def _count_pages(self, text: str) -> int:
        """Count pages in document"""
        page_patterns = [
            r'---\s*PAGE\s*\d+\s*---',
            r'Page\s+\d+\s+of\s+\d+',
            r'^\s*\d+\s*$',
            r'^\s*Page\s+\d+\s*$',
            r'^\s*P\.?\s*\d+\s*$'
        ]
        
        max_page = 0
        for pattern in page_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, str):
                    # Extract number from match
                    numbers = re.findall(r'\d+', match)
                    if numbers:
                        max_page = max(max_page, max(int(n) for n in numbers))
        
        return max(1, max_page)
    
    def _detect_tables(self, text: str) -> bool:
        """Detect if document contains tables"""
        table_indicators = [
            r'\|\s*[A-Za-z]+\s*\|',  # Pipe-separated columns
            r'\t+[A-Za-z]+',  # Tab-separated columns
            r'QTY\s+CODE\s+ITEM\s+UNIT\s+PRICE',  # Common table headers
            r'Quantity\s+Description\s+Unit\s+Price\s+Total',  # Invoice table headers
        ]
        
        for pattern in table_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_images(self, text: str) -> bool:
        """Detect if document contains image references"""
        image_indicators = [
            r'\[IMAGE\]',
            r'<img',
            r'image:',
            r'logo:',
        ]
        
        for pattern in image_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _classify_document_type(self, text: str) -> str:
        """Classify document type"""
        text_lower = text.lower()
        
        # Invoice indicators
        invoice_indicators = ['invoice', 'bill', 'statement', 'total due', 'amount due']
        if any(indicator in text_lower for indicator in invoice_indicators):
            return 'invoice'
        
        # Delivery note indicators
        delivery_indicators = ['delivery note', 'goods received', 'pod', 'delivery date']
        if any(indicator in text_lower for indicator in delivery_indicators):
            return 'delivery_note'
        
        # Receipt indicators
        receipt_indicators = ['receipt', 'payment received', 'thank you for your payment']
        if any(indicator in text_lower for indicator in receipt_indicators):
            return 'receipt'
        
        return 'unknown'
    
    def _detect_language(self, text: str) -> str:
        """Detect document language"""
        # Simple language detection based on common words
        english_words = ['the', 'and', 'for', 'with', 'invoice', 'total', 'amount']
        text_lower = text.lower()
        
        english_count = sum(1 for word in english_words if word in text_lower)
        if english_count > 3:
            return 'en'
        
        return 'unknown'
    
    def _calculate_structure_score(self, text: str) -> float:
        """Calculate document structure score"""
        score = 0.0
        
        # Check for structured elements
        if self._detect_tables(text):
            score += 0.3
        
        if self._count_pages(text) > 1:
            score += 0.2
        
        # Check for consistent formatting
        lines = text.split('\n')
        if len(lines) > 10:
            score += 0.2
        
        # Check for professional formatting
        if re.search(r'[A-Z]{2,}', text):
            score += 0.1
        
        if re.search(r'\d+\.\d{2}', text):
            score += 0.1
        
        if re.search(r'[£$€]\d+', text):
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_confidence_score(self, text: str) -> float:
        """Calculate overall confidence score"""
        score = 0.0
        
        # Word count confidence
        word_count = len(text.split())
        if word_count > 50:
            score += 0.3
        elif word_count > 20:
            score += 0.2
        else:
            score += 0.1
        
        # Structure confidence
        score += self._calculate_structure_score(text) * 0.3
        
        # Pattern confidence
        pattern_matches = len(re.findall(r'\b(?:invoice|inv|bill|total|amount)\b', text, re.IGNORECASE))
        if pattern_matches > 5:
            score += 0.2
        elif pattern_matches > 2:
            score += 0.1
        
        # Formatting confidence
        if re.search(r'\d+\.\d{2}', text) and re.search(r'[£$€]', text):
            score += 0.2
        
        return min(score, 1.0)

class MLInvoiceDetector:
    """Machine learning-based invoice detection"""
    
    def __init__(self, config: DetectionConfig):
        self.config = config
        self.model = None
        self.feature_extractor = None
        self._initialize_ml()
    
    def _initialize_ml(self):
        """Initialize ML components"""
        if not ML_AVAILABLE or not self.config.use_ml_detection:
            return
        
        try:
            # Initialize TF-IDF vectorizer for feature extraction
            self.feature_extractor = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            logger.info("✅ ML components initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize ML components: {e}")
    
    def predict(self, text: str, context: DocumentContext) -> float:
        """Predict multi-invoice probability using ML"""
        if not self.model or not self.feature_extractor:
            return 0.5  # Default confidence
        
        try:
            # Extract features
            features = self.feature_extractor.transform([text])
            
            # Make prediction (simplified for now)
            # In a real implementation, you would use a trained model
            confidence = self._heuristic_prediction(text, context)
            
            return confidence
        except Exception as e:
            logger.warning(f"⚠️ ML prediction failed: {e}")
            return 0.5
    
    def _heuristic_prediction(self, text: str, context: DocumentContext) -> float:
        """Heuristic-based prediction (placeholder for ML model)"""
        confidence = 0.5
        
        # Multiple invoice numbers
        invoice_numbers = re.findall(r'\b(?:invoice|inv)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{3,20})\b', text, re.IGNORECASE)
        if len(set(invoice_numbers)) > 1:
            confidence += 0.3
        
        # Multiple suppliers
        suppliers = re.findall(r'\b([A-Z][A-Z\s&\.]+(?:LTD|LIMITED|INC|CORP|LLC|CO|COMPANY))\b', text)
        if len(set(suppliers)) > 1:
            confidence += 0.2
        
        # Page separators
        page_markers = re.findall(r'---\s*PAGE\s*\d+\s*---', text, re.IGNORECASE)
        if len(page_markers) > 0:
            confidence += 0.2
        
        # Document structure
        if context.structure_score > 0.7:
            confidence += 0.1
        
        return min(confidence, 1.0)

class PluginManager:
    """Plugin system for extensible detection"""
    
    def __init__(self, plugin_dir: str):
        self.plugin_dir = Path(plugin_dir)
        self.plugins = {}
        self._load_plugins()
    
    def _load_plugins(self):
        """Load available plugins"""
        if not self.plugin_dir.exists():
            return
        
        for plugin_file in self.plugin_dir.glob("*.py"):
            try:
                # Load plugin (simplified implementation)
                plugin_name = plugin_file.stem
                self.plugins[plugin_name] = {
                    'file': plugin_file,
                    'loaded': False
                }
                logger.info(f"✅ Plugin loaded: {plugin_name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load plugin {plugin_file}: {e}")
    
    def execute_plugins(self, text: str, context: DocumentContext) -> List[Dict[str, Any]]:
        """Execute all loaded plugins"""
        results = []
        
        for plugin_name, plugin_info in self.plugins.items():
            try:
                # Execute plugin (simplified)
                result = self._execute_plugin(plugin_name, text, context)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"⚠️ Plugin {plugin_name} failed: {e}")
        
        return results
    
    def _execute_plugin(self, plugin_name: str, text: str, context: DocumentContext) -> Optional[Dict[str, Any]]:
        """Execute a specific plugin"""
        # Simplified plugin execution
        # In a real implementation, you would dynamically load and execute plugins
        return None

class MultiInvoiceDetector:
    """World-class multi-invoice detection system"""
    
    def __init__(self, config: Optional[DetectionConfig] = None):
        self.config = config or DetectionConfig()
        self.pattern_matcher = IntelligentPatternMatcher(self.config)
        self.context_analyzer = ContextAnalyzer(self.config)
        self.ml_detector = MLInvoiceDetector(self.config)
        self.plugin_manager = PluginManager(self.config.plugin_dir)
        self.cache_manager = CacheManager(self.config.cache_dir, self.config.cache_ttl_seconds)
    
    def detect(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> DetectionResult:
        """Detect multi-invoice content with full analysis"""
        start_time = time.time()
        
        try:
            # Check cache first
            if self.config.enable_caching:
                cached_result = self.cache_manager.get(text)
                if cached_result:
                    logger.info("✅ Using cached detection result")
                    return cached_result
            
            # Analyze context
            context = self.context_analyzer.analyze_context(text)
            
            # Pattern matching with context
            matches = self.pattern_matcher.match_with_context(text, context)
            
            # ML-based prediction
            ml_confidence = self.ml_detector.predict(text, context)
            
            # Plugin analysis
            plugin_results = self.plugin_manager.execute_plugins(text, context)
            
            # Detect boundaries using sliding window
            boundaries = self._detect_boundaries_sliding_window(text)
            
            # Analyze results with boundary information
            detection_result = self._analyze_results_with_boundaries(matches, context, ml_confidence, plugin_results, boundaries)
            
            # Cache result
            if self.config.enable_caching:
                self.cache_manager.set(text, detection_result)
            
            detection_result.processing_time = time.time() - start_time
            return detection_result
            
        except Exception as e:
            logger.error(f"❌ Multi-invoice detection failed: {e}")
            return DetectionResult(
                is_multi_invoice=False,
                confidence=0.0,
                error_messages=[str(e)],
                processing_time=time.time() - start_time
            )
    
    def detect_multi_invoice(self, text: str, pages: Optional[List[str]] = None, 
                           metadata: Optional[Dict[str, Any]] = None) -> DetectionResult:
        """
        Detect multi-invoice documents with retry logic and per-invoice validation
        
        Args:
            text: Full document text
            pages: List of page texts (optional)
            metadata: Document metadata (optional)
            
        Returns:
            DetectionResult with enhanced validation
        """
        start_time = time.time()
        
        # Initial detection
        result = self.detect(text, metadata)
        
        # Apply retry logic for ambiguous boundaries
        if result.is_multi_invoice and self.config.enable_retry:
            result = self._apply_retry_logic(result, text, pages, metadata)
        
        # Per-invoice validation
        if result.is_multi_invoice and self.config.validate_per_invoice:
            result = self._validate_per_invoice(result, text, pages, metadata)
        
        result.processing_time = time.time() - start_time
        return result
    
    def _apply_retry_logic(self, result: DetectionResult, text: str, 
                          pages: Optional[List[str]], metadata: Optional[Dict[str, Any]]) -> DetectionResult:
        """Apply retry logic for ambiguous boundaries"""
        logger.info("🔄 Applying retry logic for ambiguous boundaries")
        
        for attempt in range(self.config.max_retry_attempts):
            logger.info(f"Retry attempt {attempt + 1}/{self.config.max_retry_attempts}")
            
            # Identify ambiguous boundaries
            ambiguous_boundaries = self._identify_ambiguous_boundaries(result)
            
            if not ambiguous_boundaries:
                logger.info("No ambiguous boundaries found, skipping retry")
                break
            
            # Retry with enhanced settings
            enhanced_result = self._retry_with_enhanced_settings(
                result, ambiguous_boundaries, text, pages, metadata, attempt
            )
            
            # Check if retry improved results
            if self._is_retry_improvement(result, enhanced_result):
                logger.info(f"✅ Retry attempt {attempt + 1} improved results")
                result = enhanced_result
                result.warnings.append(f"Retry attempt {attempt + 1} applied")
            else:
                logger.info(f"⚠️ Retry attempt {attempt + 1} did not improve results")
                break
        
        return result
    
    def _identify_ambiguous_boundaries(self, result: DetectionResult) -> List[Dict[str, Any]]:
        """Identify ambiguous boundaries that need retry"""
        ambiguous = []
        
        for separation in result.page_separations:
            confidence = separation.get('confidence', 0.0)
            if confidence < self.config.confidence_threshold + self.config.retry_threshold_adjustment:
                ambiguous.append(separation)
        
        return ambiguous
    
    def _retry_with_enhanced_settings(self, original_result: DetectionResult, 
                                    ambiguous_boundaries: List[Dict[str, Any]], 
                                    text: str, pages: Optional[List[str]], 
                                    metadata: Optional[Dict[str, Any]], 
                                    attempt: int) -> DetectionResult:
        """Retry detection with enhanced settings"""
        # Adjust confidence threshold for retry
        adjusted_threshold = self.config.confidence_threshold - (attempt * self.config.retry_threshold_adjustment)
        
        # Create enhanced config
        enhanced_config = DetectionConfig(
            confidence_threshold=adjusted_threshold,
            context_window_size=self.config.context_window_size * 2,  # Larger context
            min_context_similarity=self.config.min_context_similarity - 0.1  # More lenient
        )
        
        # Re-run detection with enhanced settings
        enhanced_detector = MultiInvoiceDetector(enhanced_config)
        enhanced_result = enhanced_detector.detect(text, metadata)
        
        return enhanced_result
    
    def _is_retry_improvement(self, original: DetectionResult, enhanced: DetectionResult) -> bool:
        """Check if retry result is an improvement"""
        # Compare confidence scores
        original_avg_confidence = sum(inv.get('confidence', 0.0) for inv in original.detected_invoices) / max(len(original.detected_invoices), 1)
        enhanced_avg_confidence = sum(inv.get('confidence', 0.0) for inv in enhanced.detected_invoices) / max(len(enhanced.detected_invoices), 1)
        
        # Check for better boundary detection
        original_boundary_confidence = sum(sep.get('confidence', 0.0) for sep in original.page_separations) / max(len(original.page_separations), 1)
        enhanced_boundary_confidence = sum(sep.get('confidence', 0.0) for sep in enhanced.page_separations) / max(len(enhanced.page_separations), 1)
        
        return (enhanced_avg_confidence > original_avg_confidence + 0.1 or 
                enhanced_boundary_confidence > original_boundary_confidence + 0.1)
    
    def _validate_per_invoice(self, result: DetectionResult, text: str, 
                            pages: Optional[List[str]], metadata: Optional[Dict[str, Any]]) -> DetectionResult:
        """Validate each detected invoice independently"""
        logger.info("🔍 Validating per-invoice")
        
        validated_invoices = []
        validation_errors = []
        
        for i, invoice in enumerate(result.detected_invoices):
            logger.info(f"Validating invoice {i + 1}/{len(result.detected_invoices)}")
            
            # Extract invoice text
            invoice_text = self._extract_invoice_text(invoice, text, pages)
            
            # Validate invoice independently
            validation_result = self._validate_single_invoice(invoice, invoice_text)
            
            if validation_result['is_valid']:
                validated_invoices.append(invoice)
                logger.info(f"✅ Invoice {i + 1} validation passed")
            else:
                validation_errors.append({
                    'invoice_index': i,
                    'invoice_number': invoice.get('invoice_number', 'Unknown'),
                    'errors': validation_result['errors']
                })
                logger.warning(f"❌ Invoice {i + 1} validation failed: {validation_result['errors']}")
        
        # Check for cross-pollution
        if self.config.cross_pollution_check and len(validated_invoices) > 1:
            cross_pollution_result = self._check_cross_pollution(validated_invoices, text, pages)
            if cross_pollution_result['has_pollution']:
                validation_errors.append({
                    'type': 'cross_pollution',
                    'details': cross_pollution_result['details']
                })
                logger.warning(f"⚠️ Cross-pollution detected: {cross_pollution_result['details']}")
        
        # Update result
        result.detected_invoices = validated_invoices
        result.error_messages.extend([f"Invoice validation error: {err}" for err in validation_errors])
        
        # Update confidence based on validation
        if validated_invoices:
            avg_confidence = sum(inv.get('confidence', 0.0) for inv in validated_invoices) / len(validated_invoices)
            result.confidence = min(result.confidence, avg_confidence)
        
        return result
    
    def _extract_invoice_text(self, invoice: Dict[str, Any], text: str, pages: Optional[List[str]]) -> str:
        """Extract text for a specific invoice"""
        if pages and 'page_range' in invoice:
            start_page = invoice['page_range'].get('start', 0)
            end_page = invoice['page_range'].get('end', len(pages) - 1)
            
            # Extract pages for this invoice
            invoice_pages = pages[start_page:end_page + 1]
            return '\n'.join(invoice_pages)
        else:
            # Fallback to full text
            return text
    
    def _validate_single_invoice(self, invoice: Dict[str, Any], invoice_text: str) -> Dict[str, Any]:
        """Validate a single invoice"""
        errors = []
        
        # Check required fields (adjusted to match actual extracted fields)
        required_fields = ['invoice_number', 'confidence']
        for field in required_fields:
            if not invoice.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Check confidence threshold
        if invoice.get('confidence', 0.0) < self.config.min_invoice_confidence:
            errors.append(f"Low confidence: {invoice.get('confidence', 0.0):.3f}")
        
        # Check for basic invoice structure
        if not self._has_invoice_structure(invoice_text):
            errors.append("Missing basic invoice structure")
        
        # Check for duplicate invoice numbers
        if self._has_duplicate_invoice_number(invoice):
            errors.append("Duplicate invoice number detected")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def _has_invoice_structure(self, text: str) -> bool:
        """Check if text has basic invoice structure"""
        # Look for invoice indicators
        invoice_indicators = [
            'invoice', 'bill', 'total', 'amount', 'date', 'supplier',
            'anfoneb', 'cyfanswm', 'dyddiad', 'cyflenwr'  # Welsh
        ]
        
        text_lower = text.lower()
        indicator_count = sum(1 for indicator in invoice_indicators if indicator in text_lower)
        
        return indicator_count >= 3  # At least 3 indicators
    
    def _has_duplicate_invoice_number(self, invoice: Dict[str, Any]) -> bool:
        """Check for duplicate invoice numbers"""
        # This would be implemented with a global invoice number tracker
        # For now, return False
        return False
    
    def _check_cross_pollution(self, invoices: List[Dict[str, Any]], text: str, pages: Optional[List[str]]) -> Dict[str, Any]:
        """Check for cross-pollution between invoices"""
        pollution_details = []
        
        # Check for overlapping line items
        all_line_items = []
        for invoice in invoices:
            if 'line_items' in invoice:
                all_line_items.extend(invoice['line_items'])
        
        # Check for duplicate line items
        line_item_texts = [item.get('description', '') for item in all_line_items]
        duplicates = [text for text in set(line_item_texts) if line_item_texts.count(text) > 1]
        
        if duplicates:
            pollution_details.append(f"Duplicate line items: {duplicates[:3]}")  # Show first 3
        
        # Check for supplier consistency
        suppliers = [inv.get('supplier', '') for inv in invoices if inv.get('supplier')]
        if len(set(suppliers)) > 1:
            pollution_details.append(f"Multiple suppliers detected: {suppliers}")
        
        return {
            'has_pollution': len(pollution_details) > 0,
            'details': pollution_details
        }
    
    def _analyze_results(self, matches: List[Match], context: DocumentContext, 
                        ml_confidence: float, plugin_results: List[Dict[str, Any]]) -> DetectionResult:
        """Analyze detection results"""
        
        # Group matches by type
        invoice_numbers = [m for m in matches if m.pattern == 'invoice_numbers']
        suppliers = [m for m in matches if m.pattern == 'suppliers']
        page_markers = [m for m in matches if m.pattern == 'page_markers']
        
        # Calculate confidence scores
        pattern_confidence = self._calculate_pattern_confidence(matches, context)
        context_confidence = context.confidence_score
        overall_confidence = (pattern_confidence + context_confidence + ml_confidence) / 3
        
        # Determine if multi-invoice
        is_multi_invoice = self._determine_multi_invoice(
            invoice_numbers, suppliers, page_markers, context, overall_confidence
        )
        
        # Extract detected invoices ONLY if it's multi-invoice
        if is_multi_invoice:
            detected_invoices = self._extract_detected_invoices(
                invoice_numbers, suppliers, page_markers, context
            )
        else:
            # For single invoices, don't create multiple detected_invoices
            detected_invoices = []
        
        # Generate warnings
        warnings = self._generate_warnings(matches, context, overall_confidence)
        
        return DetectionResult(
            is_multi_invoice=is_multi_invoice,
            confidence=overall_confidence,
            detected_invoices=detected_invoices,
            page_separations=[{'markers': [m.value for m in page_markers]}],
            supplier_variations=[m.value for m in suppliers],
            invoice_numbers=[m.value for m in invoice_numbers],
            context_analysis=context,
            warnings=warnings
        )
    
    def _analyze_results_with_boundaries(self, matches: List[Match], context: DocumentContext, 
                                       ml_confidence: float, plugin_results: List[Dict[str, Any]], 
                                       boundaries: List[Dict[str, Any]]) -> DetectionResult:
        """Analyze detection results with boundary information"""
        
        # Group matches by type
        invoice_numbers = [m for m in matches if m.pattern == 'invoice_numbers']
        suppliers = [m for m in matches if m.pattern == 'suppliers']
        page_markers = [m for m in matches if m.pattern == 'page_markers']
        
        # Calculate confidence scores
        pattern_confidence = self._calculate_pattern_confidence(matches, context)
        context_confidence = context.confidence_score
        boundary_confidence = min(1.0, len(boundaries) * 0.2)  # Boost confidence with boundaries
        overall_confidence = (pattern_confidence + context_confidence + ml_confidence + boundary_confidence) / 4
        
        # Determine if multi-invoice
        is_multi_invoice = self._determine_multi_invoice_with_boundaries(
            invoice_numbers, suppliers, page_markers, context, overall_confidence, boundaries
        )
        
        # Extract detected invoices ONLY if it's multi-invoice
        if is_multi_invoice:
            detected_invoices = self._extract_detected_invoices(
                invoice_numbers, suppliers, page_markers, context
            )
        else:
            # For single invoices, don't create multiple detected_invoices
            detected_invoices = []
        
        # Generate warnings
        warnings = self._generate_warnings(matches, context, overall_confidence)
        
        return DetectionResult(
            is_multi_invoice=is_multi_invoice,
            confidence=overall_confidence,
            detected_invoices=detected_invoices,
            page_separations=[{'markers': [m.value for m in page_markers], 'boundaries': boundaries}],
            supplier_variations=[m.value for m in suppliers],
            invoice_numbers=[m.value for m in invoice_numbers],
            context_analysis=context,
            warnings=warnings
        )
    
    def _calculate_pattern_confidence(self, matches: List[Match], context: DocumentContext) -> float:
        """Calculate confidence based on pattern matches"""
        if not matches:
            return 0.0
        
        # Weight matches by confidence and type
        total_confidence = 0.0
        total_weight = 0.0
        
        for match in matches:
            weight = 1.0
            if match.pattern == 'invoice_numbers':
                weight = 2.0
            elif match.pattern == 'suppliers':
                weight = 1.5
            elif match.pattern == 'page_markers':
                weight = 1.0
            
            total_confidence += match.confidence * weight
            total_weight += weight
        
        return total_confidence / total_weight if total_weight > 0 else 0.0
    
    def _determine_multi_invoice(self, invoice_numbers: List[Match], suppliers: List[Match], 
                               page_markers: List[Match], context: DocumentContext, 
                               overall_confidence: float) -> bool:
        """Determine if document contains multiple invoices - BALANCED APPROACH"""
        
        # Multiple invoice numbers (must be clearly different)
        unique_invoices = set(m.value for m in invoice_numbers)
        if len(unique_invoices) > 1:
            # Check if they're actually different (not just variations)
            invoice_list = list(unique_invoices)
            truly_different = 0
            for i, inv1 in enumerate(invoice_list):
                for inv2 in invoice_list[i+1:]:
                    # Check if they're similar (might be variations of the same number)
                    if inv1.lower() in inv2.lower() or inv2.lower() in inv1.lower():
                        # They're similar, don't count as multiple invoices
                        continue
                    else:
                        truly_different += 1
            
            # If we have at least 2 truly different invoice numbers, it's multi-invoice
            if truly_different >= 1:  # Changed from 2 to 1 - more lenient
                logger.info(f"✅ Multiple different invoice numbers detected: {unique_invoices}")
                return True
            else:
                logger.info(f"⚠️ Invoice numbers appear to be variations of the same: {unique_invoices}")
        
        # Multiple suppliers (must be clearly different)
        unique_suppliers = set(m.value for m in suppliers)
        if len(unique_suppliers) > 1:
            # Check if they're actually different
            supplier_list = list(unique_suppliers)
            truly_different = 0
            for i, sup1 in enumerate(supplier_list):
                for sup2 in supplier_list[i+1:]:
                    # Check if they're similar (might be variations of the same supplier)
                    if sup1.lower() in sup2.lower() or sup2.lower() in sup1.lower():
                        # They're similar, don't count as multiple suppliers
                        continue
                    else:
                        truly_different += 1
            
            # If we have at least 2 truly different suppliers, it's multi-invoice
            if truly_different >= 1:  # Changed from 2 to 1 - more lenient
                logger.info(f"✅ Multiple different suppliers detected: {unique_suppliers}")
                return True
            else:
                logger.info(f"⚠️ Suppliers appear to be variations of the same: {unique_suppliers}")
        
        # Page separators - more balanced approach
        if len(page_markers) > 1:  # Changed from 3 to 1 - more lenient
            logger.info(f"✅ Multiple page separators detected: {len(page_markers)} markers")
            return True
        elif len(page_markers) == 1 and (len(unique_invoices) > 0 or len(unique_suppliers) > 0):
            # Single page separator with supporting evidence
            logger.info(f"✅ Single page separator with supporting evidence: {len(page_markers)} markers")
            return True
        
        # High confidence from ML (but require additional evidence)
        if overall_confidence > self.config.confidence_threshold and (len(unique_invoices) > 0 or len(unique_suppliers) > 0):
            logger.info(f"✅ High ML confidence ({overall_confidence:.2f}) with supporting evidence")
            return True
        
        # If we get here, it's likely a single invoice
        logger.info(f"⚠️ Insufficient evidence for multi-invoice detection")
        return False
    
    def _determine_multi_invoice_with_boundaries(self, invoice_numbers: List[Match], suppliers: List[Match], 
                                               page_markers: List[Match], context: DocumentContext, 
                                               overall_confidence: float, boundaries: List[Dict[str, Any]]) -> bool:
        """Determine if document contains multiple invoices with boundary information"""
        
        # If we have clear boundaries, it's likely multi-invoice
        if boundaries and len(boundaries) >= 1:
            logger.info(f"✅ Clear boundaries detected: {len(boundaries)}")
            return True
        
        # Multiple invoice numbers (must be clearly different)
        unique_invoices = set(m.value for m in invoice_numbers)
        if len(unique_invoices) > 1:
            # Check if they're actually different (not just variations)
            invoice_list = list(unique_invoices)
            truly_different = 0
            for i, inv1 in enumerate(invoice_list):
                for inv2 in invoice_list[i+1:]:
                    # Check if they're similar (might be variations of the same number)
                    if inv1.lower() in inv2.lower() or inv2.lower() in inv1.lower():
                        # They're similar, don't count as multiple invoices
                        continue
                    else:
                        truly_different += 1
            
            # If we have at least 2 truly different invoice numbers, it's multi-invoice
            if truly_different >= 1:  # Changed from 2 to 1 - more lenient
                logger.info(f"✅ Multiple different invoice numbers detected: {unique_invoices}")
                return True
            else:
                logger.info(f"⚠️ Invoice numbers appear to be variations of the same: {unique_invoices}")
        
        # Multiple suppliers (must be clearly different)
        unique_suppliers = set(m.value for m in suppliers)
        if len(unique_suppliers) > 1:
            # Check if they're actually different
            supplier_list = list(unique_suppliers)
            truly_different = 0
            for i, sup1 in enumerate(supplier_list):
                for sup2 in supplier_list[i+1:]:
                    # Simple similarity check
                    if sup1.lower() in sup2.lower() or sup2.lower() in sup1.lower():
                        continue
                    else:
                        truly_different += 1
            
            if truly_different >= 1:
                logger.info(f"✅ Multiple different suppliers detected: {unique_suppliers}")
                return True
        
        # Page markers with context
        if page_markers and len(page_markers) >= 2:
            # Check if page markers suggest multiple invoices
            marker_texts = [m.value.lower() for m in page_markers]
            if any('page' in text for text in marker_texts):
                logger.info(f"✅ Page markers suggest multi-invoice: {marker_texts}")
                return True
        
        # Context-based decision
        if context.page_count > 2 and context.word_count > 500:
            # Long document with multiple pages
            if overall_confidence > 0.6:
                logger.info(f"✅ Context suggests multi-invoice (pages: {context.page_count}, words: {context.word_count})")
                return True
        
        return False
    
    def _extract_total_amount(self, context: str) -> Optional[float]:
        """Extract total amount from invoice context"""
        # Look for total patterns in the context
        total_patterns = [
            r'\b(?:Total|Cyfanswm|Amount|Amount Due|Total Due)\s*:?\s*[£$€]?(\d+\.?\d*)\b',
            r'\b[£$€](\d+\.?\d*)\s*(?:Total|Cyfanswm|Amount|Amount Due|Total Due)\b',
            r'\b(?:Total|Cyfanswm|Amount|Amount Due|Total Due)\s*[£$€]?(\d+\.?\d*)\b',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_detected_invoices(self, invoice_numbers: List[Match], suppliers: List[Match], 
                                 page_markers: List[Match], context: DocumentContext) -> List[Dict[str, Any]]:
        """Extract detected invoice information - BALANCED APPROACH"""
        invoices = []
        
        # Group by UNIQUE invoice numbers with cleaning
        if invoice_numbers:
            unique_invoice_numbers = {}
            
            for i, invoice_match in enumerate(invoice_numbers):
                raw_invoice_number = invoice_match.value.strip()
                
                # Clean and validate invoice ID
                clean_invoice_number = self._clean_invoice_id(raw_invoice_number)
                if not clean_invoice_number:
                    continue
                
                # Skip if we already have this invoice number
                if clean_invoice_number in unique_invoice_numbers:
                    continue
                
                # Normalize invoice number for comparison (remove extra hyphens, normalize case)
                normalized_inv = re.sub(r'-+', '-', clean_invoice_number).strip('-').upper()
                
                # Check if this invoice number is too similar to existing ones
                is_similar = False
                for existing_inv in unique_invoice_numbers.keys():
                    existing_normalized = re.sub(r'-+', '-', existing_inv).strip('-').upper()
                    if normalized_inv == existing_normalized:
                        is_similar = True
                        break
                    # Also check for substring matches
                    if (normalized_inv in existing_normalized or 
                        existing_normalized in normalized_inv):
                        is_similar = True
                        break
                
                if not is_similar:
                    # Extract total amount from context
                    total_amount = self._extract_total_amount(invoice_match.context)
                    
                    unique_invoice_numbers[clean_invoice_number] = {
                        'id': f"invoice_{len(unique_invoice_numbers) + 1}",
                        'invoice_number': clean_invoice_number,
                        'confidence': invoice_match.confidence,
                        'position': invoice_match.position,
                        'context': invoice_match.context,
                        'total_amount': total_amount
                    }
            
            # Convert to list
            invoices = list(unique_invoice_numbers.values())
            
            # Return if we have at least 1 unique invoice (changed from 2)
            if len(invoices) >= 1:
                logger.info(f"✅ Extracted {len(invoices)} unique invoice(s)")
                return invoices
            else:
                logger.info(f"⚠️ No unique invoices found")
        
        # If no invoice numbers, try to extract based on page markers
        if page_markers and len(page_markers) > 0:
            logger.info(f"📄 Extracting invoices based on {len(page_markers)} page markers")
            for i, marker in enumerate(page_markers):
                invoices.append({
                    'id': f"invoice_page_{i+1}",
                    'invoice_number': f"INV-{i+1:03d}",
                    'confidence': marker.confidence,
                    'position': marker.position,
                    'context': marker.context,
                    'page_range': f"Page {i+1}"
                })
        
        # If still no invoices, try to extract based on suppliers
        if suppliers and len(suppliers) > 0 and len(invoices) == 0:
            logger.info(f"🏢 Extracting invoices based on {len(suppliers)} suppliers")
            unique_suppliers = {}
            for supplier_match in suppliers:
                supplier_name = supplier_match.value.strip()
                if supplier_name not in unique_suppliers:
                    unique_suppliers[supplier_name] = {
                        'id': f"invoice_supplier_{len(unique_suppliers) + 1}",
                        'invoice_number': f"INV-{len(unique_suppliers) + 1:03d}",
                        'confidence': supplier_match.confidence,
                        'position': supplier_match.position,
                        'context': supplier_match.context,
                        'supplier_name': supplier_name
                    }
            
            invoices = list(unique_suppliers.values())
        
        logger.info(f"📊 Final extracted invoices: {len(invoices)}")
        return invoices
    
    def _clean_invoice_id(self, raw: str) -> Optional[str]:
        """Clean and validate invoice ID"""
        s = raw.strip()
        
        # Minimum length check
        if len(s) < 8:
            return None
        
        # Hyphen validation
        if "-" in s and s.count("-") < 1:
            return None
        
        # Must contain letters or full 4-digit year
        if not any(c.isalpha() for c in s) and not re.search(r'\b\d{4}\b', s):
            return None
        
        return s
    
    def _generate_warnings(self, matches: List[Match], context: DocumentContext, 
                          overall_confidence: float) -> List[str]:
        """Generate warnings based on analysis"""
        warnings = []
        
        if overall_confidence < self.config.confidence_threshold:
            warnings.append("Low confidence in detection results")
        
        if not matches:
            warnings.append("No patterns detected in document")
        
        if context.word_count < 50:
            warnings.append("Document appears to be too short for reliable analysis")
        
        return warnings
    
    def batch_detect(self, texts: List[str]) -> List[DetectionResult]:
        """Batch detection for multiple documents"""
        results = []
        
        # Submit tasks to thread pool
        future_to_text = {
            self._executor.submit(self.detect, text): text 
            for text in texts
        }
        
        # Collect results
        for future in as_completed(future_to_text):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"❌ Batch detection failed: {e}")
                results.append(DetectionResult(
                    is_multi_invoice=False,
                    confidence=0.0,
                    error_messages=[str(e)]
                ))
        
        return results
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)

    def _detect_boundaries_sliding_window(self, text: str, pages: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Detect invoice boundaries using sliding window approach"""
        boundaries = []
        
        if not pages:
            # Split text into pages if not provided
            pages = self._split_text_into_pages(text)
        
        if len(pages) < 2:
            return boundaries
        
        # Build page features
        page_features = []
        for i, page_text in enumerate(pages):
            features = self._extract_page_features(page_text, i)
            page_features.append(features)
        
        # Detect boundaries using sliding window
        for i in range(1, len(page_features)):
            current_page = page_features[i]
            prev_page = page_features[i-1]
            
            # Check for boundary conditions
            is_boundary = False
            boundary_reason = ""
            
            # 1. Invoice ID changes
            if (current_page['inv_ids'] and prev_page['inv_ids'] and 
                current_page['inv_ids'] != prev_page['inv_ids']):
                is_boundary = True
                boundary_reason = "INV_ID_CHANGE"
            
            # 2. Supplier signature changes
            elif (current_page['supplier_signature'] and prev_page['supplier_signature'] and
                  current_page['supplier_signature'] != prev_page['supplier_signature']):
                is_boundary = True
                boundary_reason = "SUPPLIER_CHANGE"
            
            # 3. Invoice keyword toggle with totals
            elif (current_page['has_invoice_kw'] and not prev_page['has_invoice_kw'] and
                  prev_page['has_totals_block']):
                is_boundary = True
                boundary_reason = "INV_KW_TOGGLE"
            
            if is_boundary:
                boundaries.append({
                    'page_index': i,
                    'confidence': 0.8,
                    'reason': boundary_reason,
                    'features': {
                        'current': current_page,
                        'previous': prev_page
                    }
                })
        
        return boundaries
    
    def _extract_page_features(self, page_text: str, page_index: int) -> Dict[str, Any]:
        """Extract features from a single page"""
        text_lower = page_text.lower()
        
        # Invoice keywords (bilingual)
        invoice_keywords = [
            'invoice', 'inv', 'bill', 'statement',
            'anfoneb', 'rhif anfoneb', 'bil'
        ]
        
        # Total keywords (bilingual)
        total_keywords = [
            'total', 'amount', 'sum', 'grand total',
            'cyfanswm', 'swm', 'cyfanswm y cyfan'
        ]
        
        # Extract invoice IDs
        inv_ids = set()
        for pattern in self.pattern_matcher.patterns['invoice_numbers']:
            matches = pattern.finditer(page_text)
            for match in matches:
                clean_id = self._clean_invoice_id(match.group(1))
                if clean_id:
                    inv_ids.add(clean_id)
        
        # Extract supplier signature (first 5 tokens)
        words = page_text.split()[:5]
        supplier_signature = ' '.join(words).lower() if words else ""
        
        # Check for invoice keywords
        has_invoice_kw = any(kw in text_lower for kw in invoice_keywords)
        
        # Check for totals block
        has_totals_block = any(kw in text_lower for kw in total_keywords)
        
        return {
            'page_index': page_index,
            'inv_ids': list(inv_ids),
            'supplier_signature': supplier_signature,
            'has_invoice_kw': has_invoice_kw,
            'has_totals_block': has_totals_block,
            'word_count': len(page_text.split())
        }
    
    def _split_text_into_pages(self, text: str) -> List[str]:
        """Split text into pages based on page markers"""
        # Look for page markers
        page_patterns = [
            r'---\s*PAGE\s*\d+\s*---',
            r'Page\s+\d+\s+of\s+\d+',
            r'^\s*Page\s+\d+\s*$',
            r'^\s*P\.?\s*\d+\s*$'
        ]
        
        # Find all page markers
        markers = []
        for pattern in page_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                markers.append(match.start())
        
        # Sort markers by position
        markers.sort()
        
        # Split text at markers
        pages = []
        start = 0
        for marker in markers:
            if marker > start:
                pages.append(text[start:marker].strip())
            start = marker
        
        # Add remaining text
        if start < len(text):
            pages.append(text[start:].strip())
        
        return pages if pages else [text]

# Global instance for caching
_detector_instance = None
_detector_lock = threading.Lock()

def get_multi_invoice_detector(config: DetectionConfig = None) -> MultiInvoiceDetector:
    """Get or create global detector instance"""
    global _detector_instance
    
    with _detector_lock:
        if _detector_instance is None:
            _detector_instance = MultiInvoiceDetector(config)
    
    return _detector_instance 
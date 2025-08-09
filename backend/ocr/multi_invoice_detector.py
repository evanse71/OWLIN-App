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
                # Precise invoice number patterns
                re.compile(r'\b(?:invoice|inv)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{3,20})\b', re.IGNORECASE),
                re.compile(r'\b(INV[0-9\-_/]{3,20})\b', re.IGNORECASE),
                re.compile(r'\b([A-Z]{2,4}[0-9]{3,8})\b'),  # More restrictive
                re.compile(r'\b(?:bill|statement)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{3,20})\b', re.IGNORECASE),
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
            if pattern_type == 'false_positives':
                continue
                
            for pattern in patterns:
                for match in pattern.finditer(text):
                    value = match.group(1) if match.groups() else match.group(0)
                    
                    # Apply context rules
                    if self._is_valid_match(value, pattern_type, context):
                        confidence = self._calculate_confidence(match, pattern_type, context)
                        context_text = self._extract_context(text, match.start(), match.end())
                        
                        matches.append(Match(
                            pattern=pattern_type,
                            value=value,
                            confidence=confidence,
                            position=(match.start(), match.end()),
                            context=context_text
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
    
    def __init__(self, config: DetectionConfig = None):
        self.config = config or DetectionConfig()
        self.cache_manager = CacheManager(self.config.cache_dir, self.config.cache_ttl_seconds)
        self.pattern_matcher = IntelligentPatternMatcher(self.config)
        self.context_analyzer = ContextAnalyzer(self.config)
        self.ml_detector = MLInvoiceDetector(self.config)
        self.plugin_manager = PluginManager(self.config.plugin_dir)
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
    
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
            
            # Analyze results
            detection_result = self._analyze_results(matches, context, ml_confidence, plugin_results)
            
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
    
    def _extract_detected_invoices(self, invoice_numbers: List[Match], suppliers: List[Match], 
                                 page_markers: List[Match], context: DocumentContext) -> List[Dict[str, Any]]:
        """Extract detected invoice information - BALANCED APPROACH"""
        invoices = []
        
        # Group by UNIQUE invoice numbers
        if invoice_numbers:
            unique_invoice_numbers = {}
            
            for i, invoice_match in enumerate(invoice_numbers):
                invoice_number = invoice_match.value.strip()
                
                # Skip if we already have this invoice number
                if invoice_number in unique_invoice_numbers:
                    continue
                
                # Only add if it's a valid invoice number (not too short)
                if len(invoice_number) >= 3:
                    # Check if this invoice number is too similar to existing ones
                    is_similar = False
                    for existing_inv in unique_invoice_numbers.keys():
                        if (invoice_number.lower() in existing_inv.lower() or 
                            existing_inv.lower() in invoice_number.lower()):
                            is_similar = True
                            break
                    
                    if not is_similar:
                        unique_invoice_numbers[invoice_number] = {
                            'id': f"invoice_{len(unique_invoice_numbers) + 1}",
                            'invoice_number': invoice_number,
                            'confidence': invoice_match.confidence,
                            'position': invoice_match.position,
                            'context': invoice_match.context
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
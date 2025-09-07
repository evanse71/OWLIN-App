"""
Page Classifier - Bulletproof Ingestion v3

Classifies pages into document types: Invoice, Delivery, Receipt, Utility, Other
Uses ML model with heuristic fallback for robust classification.
"""

import re
import json
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """Page classification result"""
    doc_type: str
    confidence: float
    features: Dict[str, Any]
    logits: Dict[str, float]
    method: str  # 'ml' or 'heuristic'

class PageClassifier:
    """Page classifier using ML model with heuristic fallback"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "data/models/page_clf.joblib"
        self.model = None
        self.feature_names = None
        self.load_model()
        
        # Document type keywords
        self.keywords = {
            'invoice': [
                'invoice', 'bill', 'statement', 'account', 'payment due',
                'invoice number', 'invoice date', 'billing', 'amount due',
                'total due', 'balance', 'outstanding', 'invoice to', 'bill to'
            ],
            'delivery': [
                'delivery note', 'goods received', 'pod', 'delivery date',
                'received by', 'signature', 'delivery address', 'delivered to',
                'quantity received', 'received quantity', 'delivery reference'
            ],
            'receipt': [
                'receipt', 'payment received', 'thank you for your payment',
                'transaction', 'purchase', 'sale', 'cash register', 'register',
                'payment confirmation', 'transaction receipt', 'payment slip'
            ],
            'utility': [
                'energy', 'kwh', 'standing charge', 'gas', 'electricity', 'utility',
                'meter reading', 'consumption', 'usage', 'energy supplier',
                'electric supplier', 'gas supplier', 'water', 'sewerage'
            ]
        }
        
        # Feature extraction patterns
        self.patterns = {
            'invoice_number': r'\b(?:invoice|inv)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{3,20})\b',
            'invoice_date': r'\b(?:date|dated|invoice date)\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b',
            'total_amount': r'\b(?:total|amount|sum|due)\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)\b',
            'supplier': r'\b([A-Z][A-Z\s&\.]+(?:LTD|LIMITED|INC|CORP|LLC|CO|COMPANY))\b',
            'currency': r'\b[£$€]\s*[\d,]+\.?\d*\b',
            'table_indicators': r'\b(?:qty|quantity|description|unit|price|amount|total)\b',
            'page_numbers': r'\b(?:page|p)\s*\d+\s*(?:of\s*\d+)?\b'
        }
    
    def load_model(self) -> None:
        """Load ML model from file or use heuristic fallback"""
        try:
            from joblib import load
            model_file = Path(self.model_path)
            if model_file.exists():
                self.model = load(str(model_file))
                logger.info(f"✅ Loaded ML model from {self.model_path}")
            else:
                logger.warning(f"⚠️ ML model not found at {self.model_path}, using heuristic fallback")
                self.model = None
        except Exception as e:
            logger.warning(f"⚠️ Failed to load ML model: {e}, using heuristic fallback")
            self.model = None
    
    def extract_features(self, text: str, image_features: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Extract features from page text and image
        
        Args:
            text: OCR text content
            image_features: Optional image features (width, height, aspect_ratio)
            
        Returns:
            Dictionary of extracted features
        """
        features = {}
        text_lower = text.lower()
        
        # Text length features
        features['text_length'] = len(text)
        features['text_lines'] = len(text.split('\n'))
        features['text_words'] = len(text.split())
        
        # Keyword-based features
        for doc_type, doc_keywords in self.keywords.items():
            keyword_count = 0
            for keyword in doc_keywords:
                if keyword in text_lower:
                    keyword_count += 1
            features[f'{doc_type}_keywords'] = keyword_count
        
        # Pattern-based features
        for pattern_name, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            features[f'{pattern_name}_count'] = len(matches)
        
        # Table density features
        table_indicators = sum(1 for indicator in ['qty', 'quantity', 'description', 'unit', 'price', 'amount', 'total'] 
                             if indicator in text_lower)
        features['table_density'] = table_indicators / max(features['text_words'], 1)
        
        # Numerical features
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        features['number_count'] = len(numbers)
        
        # Currency features
        currencies = re.findall(r'[£$€]\s*[\d,]+\.?\d*', text)
        features['currency_count'] = len(currencies)
        
        # Date features
        dates = re.findall(r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b', text)
        features['date_count'] = len(dates)
        
        # Aspect ratio features (if available)
        if image_features:
            features['aspect_ratio'] = image_features.get('aspect_ratio', 1.0)
            features['width'] = image_features.get('width', 1000)
            features['height'] = image_features.get('height', 1000)
        else:
            features['aspect_ratio'] = 1.0
            features['width'] = 1000
            features['height'] = 1000
        
        # Receipt-specific features (narrow format)
        features['is_receipt_shape'] = features['aspect_ratio'] < 0.8
        
        # Document structure features
        features['has_header'] = any(keyword in text_lower[:500] for keyword in ['invoice', 'delivery', 'receipt'])
        features['has_footer'] = any(keyword in text_lower[-500:] for keyword in ['total', 'amount', 'payment'])
        
        # Normalize features
        features['text_length_norm'] = min(features['text_length'] / 1000, 1.0)
        features['text_lines_norm'] = min(features['text_lines'] / 50, 1.0)
        
        return features
    
    def classify_with_ml(self, features: Dict[str, float]) -> Optional[ClassificationResult]:
        """Classify using ML model if available"""
        if self.model is None:
            return None
        
        try:
            # Prepare feature vector
            feature_vector = []
            expected_features = [
                'text_length_norm', 'text_lines_norm', 'invoice_keywords', 'delivery_keywords',
                'receipt_keywords', 'utility_keywords', 'table_density', 'number_count',
                'currency_count', 'date_count', 'aspect_ratio', 'is_receipt_shape',
                'has_header', 'has_footer'
            ]
            
            for feature in expected_features:
                feature_vector.append(features.get(feature, 0.0))
            
            # Make prediction
            feature_array = np.array(feature_vector).reshape(1, -1)
            prediction = self.model.predict(feature_array)[0]
            probabilities = self.model.predict_proba(feature_array)[0]
            
            # Map prediction to document type
            doc_types = ['invoice', 'delivery', 'receipt', 'utility', 'other']
            doc_type = doc_types[prediction] if prediction < len(doc_types) else 'other'
            confidence = max(probabilities)
            
            logits = {doc_type: prob for doc_type, prob in zip(doc_types, probabilities)}
            
            return ClassificationResult(
                doc_type=doc_type,
                confidence=confidence,
                features=features,
                logits=logits,
                method='ml'
            )
            
        except Exception as e:
            logger.error(f"ML classification failed: {e}")
            return None
    
    def classify_with_heuristics(self, features: Dict[str, float]) -> ClassificationResult:
        """Classify using heuristic rules"""
        scores = {
            'invoice': 0.0,
            'delivery': 0.0,
            'receipt': 0.0,
            'utility': 0.0,
            'other': 0.0
        }
        
        # Invoice scoring
        if features['invoice_keywords'] > 2:
            scores['invoice'] += 0.4
        if features['invoice_number_count'] > 0:
            scores['invoice'] += 0.3
        if features['total_amount_count'] > 0:
            scores['invoice'] += 0.2
        if features['table_density'] > 0.1:
            scores['invoice'] += 0.1
        
        # Delivery scoring
        if features['delivery_keywords'] > 2:
            scores['delivery'] += 0.5
        if features['supplier_count'] > 0:
            scores['delivery'] += 0.2
        if features['text_length'] > 200:
            scores['delivery'] += 0.1
        
        # Receipt scoring
        if features['receipt_keywords'] > 2:
            scores['receipt'] += 0.4
        if features['is_receipt_shape']:
            scores['receipt'] += 0.3
        if features['currency_count'] > 0:
            scores['receipt'] += 0.1
        if features['text_length'] < 500:
            scores['receipt'] += 0.1
        
        # Utility scoring
        if features['utility_keywords'] > 2:
            scores['utility'] += 0.5
        if features['number_count'] > 10:
            scores['utility'] += 0.2
        if features['date_count'] > 0:
            scores['utility'] += 0.1
        
        # Determine winner
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type], 1.0)
        
        # Normalize logits
        total_score = sum(scores.values()) or 1.0
        logits = {doc_type: score / total_score for doc_type, score in scores.items()}
        
        return ClassificationResult(
            doc_type=best_type,
            confidence=confidence,
            features=features,
            logits=logits,
            method='heuristic'
        )
    
    def classify(self, text: str, image_features: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Classify a page into document type
        
        Args:
            text: OCR text content
            image_features: Optional image features
            
        Returns:
            ClassificationResult object
        """
        try:
            # Extract features
            features = self.extract_features(text, image_features)
            
            # Try ML classification first
            ml_result = self.classify_with_ml(features)
            if ml_result and ml_result.confidence > 0.75:
                return ml_result
            
            # Fallback to heuristics
            heuristic_result = self.classify_with_heuristics(features)
            
            # If ML result exists but confidence is lower, use it if it's close
            if ml_result and ml_result.confidence > 0.5:
                # Use ML if it's significantly more confident than heuristic
                if ml_result.confidence > heuristic_result.confidence + 0.1:
                    return ml_result
            
            return heuristic_result
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Return safe fallback
            return ClassificationResult(
                doc_type='other',
                confidence=0.0,
                features=features if 'features' in locals() else {},
                logits={'other': 1.0},
                method='fallback'
            ) 
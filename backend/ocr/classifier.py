#!/usr/bin/env python3
"""
Document Classifier

Classifies documents into invoice, receipt, delivery_note, utility, or other
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional

from .config import get_ocr_config
from .lang import detect_lang, get_bilingual_field_mapping

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    doc_type: str
    confidence: float
    reasons: List[str]
    features: Dict[str, float]
    alternative_types: List[Tuple[str, float]]

class DocumentClassifier:
    """Document type classifier with bilingual support"""
    
    def __init__(self):
        self.config = get_ocr_config()
        
        # Bilingual keyword sets
        self.bilingual_mapping = get_bilingual_field_mapping()
        
        # Document type keywords (English)
        self.doc_type_keywords = {
            'invoice': [
                'invoice', 'bill', 'billing', 'invoice number', 'amount due',
                'payment terms', 'due date', 'subtotal', 'tax', 'total'
            ],
            'receipt': [
                'receipt', 'payment receipt', 'thank you', 'change', 'cash',
                'card payment', 'transaction', 'purchase'
            ],
            'delivery_note': [
                'delivery note', 'delivery', 'delivered', 'shipping', 'packing list',
                'goods received', 'quantity', 'qty', 'units'
            ],
            'utility': [
                'utility', 'gas bill', 'electric bill', 'water bill', 'energy',
                'usage', 'consumption', 'meter', 'account number'
            ]
        }
        
        # Welsh document type keywords
        self.doc_type_keywords_cy = {
            'invoice': [
                'anfoneb', 'rhif anfoneb', 'cyfanswm i dalu', 'telerau talu',
                'dyddiad ddyledus', 'is-gyfanswm', 'taw', 'cyfanswm'
            ],
            'receipt': [
                'derbyn', 'derbynneb', 'diolch', 'newid', 'arian parod',
                'taliad cerdyn', 'trafod', 'prynu', 'is-gyfanswm', 'cyfanswm',
                'taliad', 'talu', 'arian', 'card', 'ceiniog'
            ],
            'delivery_note': [
                'nodiadau cyflenwi', 'cyflenwi', 'danfon', 'rhestr pacio',
                'nwyddau a dderbyniwyd', 'nifer', 'unedau'
            ],
            'utility': [
                'cyfleustod', 'bil nwy', 'bil trydan', 'bil dŵr', 'egni',
                'defnydd', 'cynhyrchiant', 'medr', 'rhif cyfrif'
            ]
        }
        
        # Negative lexicon (words that indicate non-business documents)
        self.negative_lexicon = [
            'menu', 'carte', 'food', 'drink', 'appetizer', 'main course',
            'dessert', 'wine', 'beer', 'coffee', 'tea', 'breakfast', 'lunch',
            'dinner', 'reservation', 'booking', 'table', 'restaurant',
            'cafe', 'bar', 'pub', 'hotel', 'accommodation', 'room', 'suite',
            'letter', 'correspondence', 'memo', 'memo', 'announcement',
            'newsletter', 'brochure', 'catalog', 'catalogue', 'flyer',
            'poster', 'advertisement', 'ad', 'promotion', 'offer',
            'contract', 'agreement', 'terms', 'conditions', 'policy',
            'manual', 'guide', 'instruction', 'tutorial', 'help',
            'report', 'analysis', 'study', 'research', 'survey',
            'form', 'application', 'registration', 'enrollment',
            'certificate', 'diploma', 'degree', 'qualification',
            'magazine', 'newspaper', 'article', 'story', 'fiction',
            'novel', 'book', 'textbook', 'reference', 'dictionary'
        ]
        
        # Welsh negative lexicon
        self.negative_lexicon_cy = [
            'bwydlen', 'bwyd', 'diod', 'cyflenwad', 'prif gwrs',
            'pwdin', 'gwin', 'cwrw', 'coffi', 'te', 'brecwast', 'cinio',
            'swper', 'archeb', 'archebu', 'bwrdd', 'bwyty',
            'caffi', 'bar', 'tafarn', 'gwesty', 'llety', 'ystafell',
            'llythyr', 'gohebiaeth', 'cofnod', 'hysbysiad',
            'cylchlythyr', 'brosiwr', 'catalog', 'taflen',
            'poster', 'hysbyseb', 'cynnig', 'promosiwn',
            'contract', 'cytundeb', 'telerau', 'amodau', 'polisi',
            'llawlyfr', 'canllaw', 'cyfarwyddiad', 'tiwtorial', 'help',
            'adroddiad', 'dadansoddiad', 'astudiaeth', 'ymchwil', 'arolwg',
            'ffurflen', 'cais', 'cofrestru', 'enroliad',
            'tystysgrif', 'diploma', 'gradd', 'cymhwyster',
            'cylchgrawn', 'papur newydd', 'erthygl', 'stori', 'ffuglen',
            'nofel', 'llyfr', 'llyfr gwers', 'cyfeiriad', 'geiriadur'
        ]

    def classify_document(self, text: str) -> ClassificationResult:
        """
        Classify document type with bilingual support
        
        Args:
            text: Document text to classify
            
        Returns:
            ClassificationResult with doc_type, confidence, and reasons
        """
        if not text or len(text.strip()) < 10:
            return ClassificationResult(
                doc_type='other',
                confidence=0.0,
                reasons=['Text too short for classification'],
                features={},
                alternative_types=[]
            )
        
        # Detect language
        detected_lang = detect_lang(text)
        text_lower = text.lower()
        
        # Calculate features for each document type
        features = {}
        doc_type_scores = {}
        
        # Score English keywords
        for doc_type, keywords in self.doc_type_keywords.items():
            score = self._calculate_keyword_score(text_lower, keywords)
            features[f'{doc_type}_en'] = score
            doc_type_scores[doc_type] = score
        
        # Score Welsh keywords if Welsh or bilingual detected
        if detected_lang in ['cy', 'bi']:
            for doc_type, keywords in self.doc_type_keywords_cy.items():
                score = self._calculate_keyword_score(text_lower, keywords)
                features[f'{doc_type}_cy'] = score
                # Combine with English score for bilingual documents
                if detected_lang == 'bi':
                    doc_type_scores[doc_type] = max(doc_type_scores.get(doc_type, 0), score)
                else:
                    doc_type_scores[doc_type] = score
        
        # Calculate negative lexicon score
        negative_score_en = self._calculate_keyword_score(text_lower, self.negative_lexicon)
        negative_score_cy = 0.0
        if detected_lang in ['cy', 'bi']:
            negative_score_cy = self._calculate_keyword_score(text_lower, self.negative_lexicon_cy)
        
        negative_score = max(negative_score_en, negative_score_cy)
        features['negative_lexicon'] = negative_score
        
        # Determine primary document type
        primary_type, confidence, reasons = self._determine_primary_type(doc_type_scores, negative_score, detected_lang)
        
        # Get alternative types
        alternative_types = self._get_alternative_types(doc_type_scores, primary_type)
        
        return ClassificationResult(
            doc_type=primary_type,
            confidence=confidence,
            reasons=reasons,
            features=features,
            alternative_types=alternative_types
        )
    
    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calculate keyword match score"""
        if not keywords:
            return 0.0
        
        matches = 0
        for keyword in keywords:
            if keyword in text:
                matches += 1
        
        return matches / len(keywords)
    
    def _determine_primary_type(self, doc_type_scores: Dict[str, float], 
                               negative_score: float, detected_lang: str) -> Tuple[str, float, List[str]]:
        """Determine primary document type and confidence"""
        reasons = []
        
        # Check negative lexicon gate
        negative_gate = self.config.get_classification("negative_lexicon_gate", 0.35)
        if negative_score > negative_gate:
            return 'other', 0.8, [f'High negative lexicon score: {negative_score:.3f}']
        
        # Find best scoring document type
        if not doc_type_scores:
            return 'other', 0.0, ['No document type keywords found']
        
        best_type = max(doc_type_scores.items(), key=lambda x: x[1])
        best_score = best_type[1]
        
        if best_score == 0.0:
            return 'other', 0.0, ['No strong document type indicators']
        
        # Calculate confidence based on score difference
        other_scores = [score for doc_type, score in doc_type_scores.items() if doc_type != best_type[0]]
        if other_scores:
            max_other = max(other_scores)
            score_diff = best_score - max_other
            confidence = min(1.0, (score_diff / 50.0) + 0.5)  # Scale to 0.5-1.0
        else:
            confidence = min(1.0, best_score + 0.5)
        
        # Add language-specific reasons
        if detected_lang == 'cy':
            reasons.append('Welsh document detected')
        elif detected_lang == 'bi':
            reasons.append('Bilingual document detected')
        
        # Add feature-based reasons
        if best_score > 0.3:
            reasons.append(f'Strong {best_type[0]} indicators')
        elif best_score > 0.1:
            reasons.append(f'Weak {best_type[0]} indicators')
        
        return best_type[0], confidence, reasons
    
    def _get_alternative_types(self, doc_type_scores: Dict[str, float], 
                              primary_type: str) -> List[Tuple[str, float]]:
        """Get alternative document types with scores"""
        alternatives = []
        for doc_type, score in doc_type_scores.items():
            if doc_type != primary_type and score > 0.1:
                alternatives.append((doc_type, score))
        
        # Sort by score descending
        alternatives.sort(key=lambda x: x[1], reverse=True)
        return alternatives

# Global classifier instance
_classifier_instance: Optional[DocumentClassifier] = None

def get_document_classifier() -> DocumentClassifier:
    """Get global document classifier instance"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = DocumentClassifier()
    return _classifier_instance 
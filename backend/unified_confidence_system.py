"""
Unified confidence scoring system with:
- Multi-factor analysis
- Real-time adjustment
- Quality-based weighting
- Business rule integration
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConfidenceFactor:
    """Represents a confidence factor"""
    name: str
    weight: float
    score: float
    description: str

@dataclass
class ConfidenceResult:
    """Result of confidence calculation"""
    overall_confidence: float
    factor_scores: Dict[str, float]
    weighted_scores: Dict[str, float]
    business_rule_compliance: Dict[str, bool]
    quality_indicators: Dict[str, Any]
    calculation_time: float

class OCRQualityFactor:
    """Assesses OCR quality"""
    
    def calculate_score(self, document_result: Any) -> float:
        """Calculate OCR quality score"""
        try:
            if not hasattr(document_result, 'engine_contributions'):
                return 0.5
            
            scores = []
            
            # Engine confidence scores
            for engine_name, result in document_result.engine_contributions.items():
                if hasattr(result, 'confidence'):
                    scores.append(result.confidence)
            
            # Quality score from document result
            if hasattr(document_result, 'quality_score'):
                scores.append(document_result.quality_score)
            
            # Processing time factor (faster is better, up to a point)
            if hasattr(document_result, 'processing_time'):
                time_score = min(document_result.processing_time / 10.0, 1.0)
                scores.append(1.0 - time_score)  # Invert so faster = higher score
            
            return sum(scores) / len(scores) if scores else 0.5
            
        except Exception as e:
            logger.error(f"OCR quality factor calculation failed: {e}")
            return 0.5

class FieldValidationFactor:
    """Assesses field validation quality"""
    
    def calculate_score(self, document_result: Any) -> float:
        """Calculate field validation score"""
        try:
            if not hasattr(document_result, 'extraction_details'):
                return 0.5
            
            scores = []
            
            # Check each field's validation
            for field_name, details in document_result.extraction_details.items():
                if hasattr(details, 'business_rule_compliance'):
                    if details.business_rule_compliance:
                        scores.append(1.0)
                    else:
                        scores.append(0.3)
                
                if hasattr(details, 'validation_score'):
                    scores.append(details.validation_score)
            
            return sum(scores) / len(scores) if scores else 0.5
            
        except Exception as e:
            logger.error(f"Field validation factor calculation failed: {e}")
            return 0.5

class BusinessRuleFactor:
    """Assesses business rule compliance"""
    
    def __init__(self):
        self.business_rules = {
            'supplier_name': self._validate_supplier_business_rule,
            'total_amount': self._validate_total_business_rule,
            'invoice_date': self._validate_date_business_rule,
            'invoice_number': self._validate_number_business_rule,
        }
    
    def calculate_score(self, document_result: Any) -> float:
        """Calculate business rule compliance score"""
        try:
            if not hasattr(document_result, 'fields'):
                return 0.5
            
            scores = []
            
            for field_name, value in document_result.fields.items():
                if field_name in self.business_rules:
                    rule_score = self.business_rules[field_name](value)
                    scores.append(rule_score)
            
            return sum(scores) / len(scores) if scores else 0.5
            
        except Exception as e:
            logger.error(f"Business rule factor calculation failed: {e}")
            return 0.5
    
    def _validate_supplier_business_rule(self, value: str) -> float:
        """Validate supplier name against business rules"""
        try:
            if not value or value == "Unknown":
                return 0.0
            
            # Must contain letters
            if not any(c.isalpha() for c in value):
                return 0.0
            
            # Must be reasonable length
            if len(value) < 3 or len(value) > 100:
                return 0.3
            
            # Must not be table headers
            table_keywords = ['qty', 'quantity', 'code', 'item', 'description', 'unit', 'price', 'amount', 'total']
            value_lower = value.lower()
            if any(keyword in value_lower for keyword in table_keywords):
                return 0.2
            
            # Must not be just numbers
            if value.strip().isdigit():
                return 0.0
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Supplier business rule validation failed: {e}")
            return 0.0
    
    def _validate_total_business_rule(self, value: str) -> float:
        """Validate total amount against business rules"""
        try:
            if not value or value == "Unknown":
                return 0.0
            
            try:
                amount = float(value)
                if amount <= 0:
                    return 0.0
                elif amount > 1000000:  # Unreasonable amount
                    return 0.3
                else:
                    return 1.0
            except ValueError:
                return 0.0
            
        except Exception as e:
            logger.error(f"Total business rule validation failed: {e}")
            return 0.0
    
    def _validate_date_business_rule(self, value: str) -> float:
        """Validate date against business rules"""
        try:
            if not value or value == "Unknown" or value == "Unknown Date":
                return 0.0
            
            # Check for valid date format
            import re
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
                r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            ]
            
            for pattern in date_patterns:
                if re.match(pattern, value):
                    return 1.0
            
            return 0.3
            
        except Exception as e:
            logger.error(f"Date business rule validation failed: {e}")
            return 0.0
    
    def _validate_number_business_rule(self, value: str) -> float:
        """Validate invoice number against business rules"""
        try:
            if not value or value == "Unknown":
                return 0.0
            
            # Must contain alphanumeric characters
            if not any(c.isalnum() for c in value):
                return 0.0
            
            # Must be reasonable length
            if len(value) < 2 or len(value) > 50:
                return 0.3
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Invoice number business rule validation failed: {e}")
            return 0.0

class DataConsistencyFactor:
    """Assesses data consistency"""
    
    def calculate_score(self, document_result: Any) -> float:
        """Calculate data consistency score"""
        try:
            if not hasattr(document_result, 'fields'):
                return 0.5
            
            consistency_checks = []
            
            # Check for logical consistency
            fields = document_result.fields
            
            # Total amount should be positive
            if 'total_amount' in fields:
                try:
                    total = float(fields['total_amount'])
                    if total > 0:
                        consistency_checks.append(1.0)
                    else:
                        consistency_checks.append(0.0)
                except:
                    consistency_checks.append(0.0)
            
            # Date should be reasonable
            if 'invoice_date' in fields:
                date_value = fields['invoice_date']
                if date_value and date_value != "Unknown" and date_value != "Unknown Date":
                    consistency_checks.append(1.0)
                else:
                    consistency_checks.append(0.3)
            
            # Supplier should be present
            if 'supplier_name' in fields:
                supplier = fields['supplier_name']
                if supplier and supplier != "Unknown":
                    consistency_checks.append(1.0)
                else:
                    consistency_checks.append(0.0)
            
            return sum(consistency_checks) / len(consistency_checks) if consistency_checks else 0.5
            
        except Exception as e:
            logger.error(f"Data consistency factor calculation failed: {e}")
            return 0.5

class UserFeedbackFactor:
    """Incorporates user feedback into confidence"""
    
    def __init__(self):
        self.user_feedback_history = {}
    
    def calculate_score(self, document_result: Any) -> float:
        """Calculate user feedback score"""
        try:
            # For now, return neutral score
            # In a real system, this would incorporate actual user feedback
            return 0.7
            
        except Exception as e:
            logger.error(f"User feedback factor calculation failed: {e}")
            return 0.5
    
    def add_user_feedback(self, document_id: str, feedback_score: float):
        """Add user feedback for future calculations"""
        try:
            self.user_feedback_history[document_id] = feedback_score
        except Exception as e:
            logger.error(f"User feedback addition failed: {e}")

class ConfidenceWeightingSystem:
    """Applies intelligent weighting to confidence factors"""
    
    def __init__(self):
        self.base_weights = {
            'ocr_quality': 0.3,
            'field_validation': 0.25,
            'business_rules': 0.25,
            'data_consistency': 0.15,
            'user_feedback': 0.05
        }
    
    def apply_weights(self, factor_scores: Dict[str, float]) -> Dict[str, float]:
        """Apply weights to factor scores"""
        try:
            weighted_scores = {}
            
            for factor_name, score in factor_scores.items():
                weight = self.base_weights.get(factor_name, 0.1)
                weighted_scores[factor_name] = score * weight
            
            return weighted_scores
            
        except Exception as e:
            logger.error(f"Weight application failed: {e}")
            return factor_scores

class UnifiedConfidenceSystem:
    """
    State-of-the-art confidence scoring with:
    - Multi-factor analysis
    - Real-time adjustment
    - Quality-based weighting
    - Business rule integration
    """
    
    def __init__(self):
        self.factors = {
            'ocr_quality': OCRQualityFactor(),
            'field_validation': FieldValidationFactor(),
            'business_rules': BusinessRuleFactor(),
            'data_consistency': DataConsistencyFactor(),
            'user_feedback': UserFeedbackFactor()
        }
        self.weighting_system = ConfidenceWeightingSystem()
    
    def calculate_unified_confidence(self, document_result: Any) -> ConfidenceResult:
        """Calculate unified confidence score"""
        start_time = datetime.now()
        
        try:
            # 1. Calculate individual factor scores
            factor_scores = {}
            for factor_name, factor in self.factors.items():
                factor_scores[factor_name] = factor.calculate_score(document_result)
            
            # 2. Apply intelligent weighting
            weighted_scores = self.weighting_system.apply_weights(factor_scores)
            
            # 3. Calculate final confidence
            final_confidence = sum(weighted_scores.values())
            
            # 4. Apply business rules
            final_confidence = self._apply_business_rules(final_confidence, document_result)
            
            # 5. Ensure proper scale (0-1)
            final_confidence = min(max(final_confidence, 0.0), 1.0)
            
            calculation_time = (datetime.now() - start_time).total_seconds()
            
            # 6. Create quality indicators
            quality_indicators = self._create_quality_indicators(document_result, factor_scores)
            
            return ConfidenceResult(
                overall_confidence=final_confidence,
                factor_scores=factor_scores,
                weighted_scores=weighted_scores,
                business_rule_compliance=self._get_business_rule_compliance(document_result),
                quality_indicators=quality_indicators,
                calculation_time=calculation_time
            )
            
        except Exception as e:
            logger.error(f"Unified confidence calculation failed: {e}")
            return self._create_error_result()
    
    def _apply_business_rules(self, confidence: float, document_result: Any) -> float:
        """Apply business rules to adjust confidence"""
        try:
            adjusted_confidence = confidence
            
            # Check for critical field presence
            if hasattr(document_result, 'fields'):
                fields = document_result.fields
                
                # Supplier name is critical
                if fields.get('supplier_name') in ['Unknown', '']:
                    adjusted_confidence *= 0.7
                
                # Total amount is critical
                if fields.get('total_amount') in ['Unknown', '0', 0]:
                    adjusted_confidence *= 0.8
                
                # Date is important but not critical
                if fields.get('invoice_date') in ['Unknown', 'Unknown Date']:
                    adjusted_confidence *= 0.9
            
            return adjusted_confidence
            
        except Exception as e:
            logger.error(f"Business rule application failed: {e}")
            return confidence
    
    def _get_business_rule_compliance(self, document_result: Any) -> Dict[str, bool]:
        """Get business rule compliance status"""
        try:
            compliance = {}
            
            if hasattr(document_result, 'fields'):
                fields = document_result.fields
                
                # Check each field's compliance
                for field_name, value in fields.items():
                    if field_name == 'supplier_name':
                        compliance[field_name] = value not in ['Unknown', '']
                    elif field_name == 'total_amount':
                        compliance[field_name] = value not in ['Unknown', '0', 0]
                    elif field_name == 'invoice_date':
                        compliance[field_name] = value not in ['Unknown', 'Unknown Date']
                    else:
                        compliance[field_name] = value not in ['Unknown', '']
            
            return compliance
            
        except Exception as e:
            logger.error(f"Business rule compliance check failed: {e}")
            return {}
    
    def _create_quality_indicators(self, document_result: Any, factor_scores: Dict[str, float]) -> Dict[str, Any]:
        """Create quality indicators for detailed analysis"""
        try:
            indicators = {
                'ocr_quality': factor_scores.get('ocr_quality', 0.0),
                'field_validation': factor_scores.get('field_validation', 0.0),
                'business_rules': factor_scores.get('business_rules', 0.0),
                'data_consistency': factor_scores.get('data_consistency', 0.0),
                'processing_time': getattr(document_result, 'processing_time', 0.0),
                'num_engines': len(getattr(document_result, 'engine_contributions', {})),
                'text_length': len(getattr(document_result, 'text', '')),
            }
            
            return indicators
            
        except Exception as e:
            logger.error(f"Quality indicator creation failed: {e}")
            return {}
    
    def _create_error_result(self) -> ConfidenceResult:
        """Create error result"""
        return ConfidenceResult(
            overall_confidence=0.5,
            factor_scores={},
            weighted_scores={},
            business_rule_compliance={},
            quality_indicators={},
            calculation_time=0.0
        )

# Global instance
unified_confidence_system = UnifiedConfidenceSystem() 
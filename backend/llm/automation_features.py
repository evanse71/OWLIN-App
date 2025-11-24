"""
Automation Features using Local LLM

This module provides LLM-powered automation features including:
- Credit request email generation
- Post-correction of uncertain normalizations
- Anomaly detection and reporting
"""

from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from .local_llm import LocalLLMInterface, LLMResult
from .prompt_templates import PromptTemplates, PromptType

LOGGER = logging.getLogger("owlin.llm.automation_features")


@dataclass
class CreditRequest:
    """Generated credit request email."""
    subject: str
    body: str
    recipient: Optional[str] = None
    priority: str = "medium"
    invoice_references: List[str] = field(default_factory=list)
    amount: Optional[float] = None
    reason: Optional[str] = None
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "subject": self.subject,
            "body": self.body,
            "recipient": self.recipient,
            "priority": self.priority,
            "invoice_references": self.invoice_references,
            "amount": self.amount,
            "reason": self.reason,
            "generated_at": self.generated_at
        }
    
    def to_email_format(self) -> str:
        """Convert to email format."""
        return f"Subject: {self.subject}\n\n{self.body}"


@dataclass
class PostCorrection:
    """Post-correction result."""
    corrected_data: Dict[str, Any]
    corrections: List[str]
    confidence_improvement: float
    original_confidence: float
    new_confidence: float
    correction_details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "corrected_data": self.corrected_data,
            "corrections": self.corrections,
            "confidence_improvement": self.confidence_improvement,
            "original_confidence": self.original_confidence,
            "new_confidence": self.new_confidence,
            "correction_details": self.correction_details
        }


@dataclass
class AnomalyDetection:
    """Anomaly detection result."""
    anomalies: List[str]
    severity: str  # low, medium, high
    recommendations: List[str]
    confidence: float
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "anomalies": self.anomalies,
            "severity": self.severity,
            "recommendations": self.recommendations,
            "confidence": self.confidence,
            "detected_at": self.detected_at
        }


class CreditRequestGenerator:
    """Generator for credit request emails using LLM."""
    
    def __init__(self, llm_interface: LocalLLMInterface):
        """Initialize with LLM interface."""
        self.llm = llm_interface
        self.prompt_templates = PromptTemplates()
        
        LOGGER.info("Credit Request Generator initialized")
    
    def generate_credit_request(self, invoice_data: Dict[str, Any],
                               anomalies: List[str],
                               credit_reasons: List[str],
                               context: Optional[Dict[str, Any]] = None) -> CreditRequest:
        """
        Generate a credit request email.
        
        Args:
            invoice_data: Invoice data
            anomalies: Detected anomalies
            credit_reasons: Reasons for credit request
            context: Additional context
            
        Returns:
            CreditRequest with generated email
        """
        try:
            # Format prompt
            prompt = self.prompt_templates.format_credit_request_prompt(
                invoice_data=invoice_data,
                anomalies=anomalies,
                credit_reasons=credit_reasons
            )
            
            # Generate with LLM
            llm_result = self.llm.generate(prompt)
            
            if not llm_result.success:
                return self._create_fallback_credit_request(invoice_data, credit_reasons)
            
            # Parse LLM output
            credit_request = self._parse_credit_request_output(llm_result.text, invoice_data)
            
            LOGGER.info("Credit request generated successfully")
            return credit_request
            
        except Exception as e:
            LOGGER.error(f"Credit request generation failed: {e}")
            return self._create_fallback_credit_request(invoice_data, credit_reasons)
    
    def _parse_credit_request_output(self, llm_text: str, invoice_data: Dict[str, Any]) -> CreditRequest:
        """Parse LLM output into credit request."""
        try:
            # Extract JSON from LLM output
            json_start = llm_text.find('{')
            json_end = llm_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                # Try to extract from text format
                return self._extract_from_text_format(llm_text, invoice_data)
            
            json_text = llm_text[json_start:json_end]
            data = json.loads(json_text)
            
            return CreditRequest(
                subject=data.get("subject", "Credit Request"),
                body=data.get("body", ""),
                recipient=data.get("recipient"),
                priority=data.get("priority", "medium"),
                invoice_references=[invoice_data.get("invoice_number", "")],
                amount=invoice_data.get("total_amount"),
                reason=data.get("reason")
            )
            
        except Exception as e:
            LOGGER.error(f"Failed to parse credit request output: {e}")
            return self._create_fallback_credit_request(invoice_data, [])
    
    def _extract_from_text_format(self, text: str, invoice_data: Dict[str, Any]) -> CreditRequest:
        """Extract credit request from text format."""
        lines = text.split('\n')
        subject = "Credit Request"
        body_lines = []
        
        for line in lines:
            if line.startswith('Subject:'):
                subject = line.replace('Subject:', '').strip()
            elif line.strip() and not line.startswith('Subject:'):
                body_lines.append(line)
        
        body = '\n'.join(body_lines).strip()
        
        return CreditRequest(
            subject=subject,
            body=body,
            invoice_references=[invoice_data.get("invoice_number", "")],
            amount=invoice_data.get("total_amount")
        )
    
    def _create_fallback_credit_request(self, invoice_data: Dict[str, Any], 
                                       credit_reasons: List[str]) -> CreditRequest:
        """Create fallback credit request when LLM fails."""
        invoice_number = invoice_data.get("invoice_number", "Unknown")
        amount = invoice_data.get("total_amount", 0)
        
        subject = f"Credit Request - Invoice {invoice_number}"
        body = f"""Dear Accounts Team,

I am writing to request a credit for the following invoice:

Invoice Number: {invoice_number}
Amount: £{amount:.2f}
Reason: {', '.join(credit_reasons) if credit_reasons else 'Processing error'}

Please process this credit request at your earliest convenience.

Best regards,
Finance Team"""
        
        return CreditRequest(
            subject=subject,
            body=body,
            invoice_references=[invoice_number],
            amount=amount,
            reason=', '.join(credit_reasons) if credit_reasons else 'Processing error'
        )


class PostCorrectionEngine:
    """Engine for post-correction of uncertain normalizations."""
    
    def __init__(self, llm_interface: LocalLLMInterface):
        """Initialize with LLM interface."""
        self.llm = llm_interface
        self.prompt_templates = PromptTemplates()
        
        LOGGER.info("Post-Correction Engine initialized")
    
    def correct_data(self, original_data: Dict[str, Any],
                    confidence_issues: List[str],
                    context: Optional[Dict[str, Any]] = None) -> PostCorrection:
        """
        Correct uncertain normalizations using LLM.
        
        Args:
            original_data: Original data with issues
            confidence_issues: List of confidence issues
            context: Additional context
            
        Returns:
            PostCorrection with corrected data
        """
        try:
            # Format prompt
            prompt = self.prompt_templates.format_post_correction_prompt(
                original_data=original_data,
                confidence_issues=confidence_issues,
                context=context or {}
            )
            
            # Generate with LLM
            llm_result = self.llm.generate(prompt)
            
            if not llm_result.success:
                return self._create_fallback_correction(original_data, confidence_issues)
            
            # Parse LLM output
            correction = self._parse_correction_output(llm_result.text, original_data)
            
            LOGGER.info("Post-correction completed successfully")
            return correction
            
        except Exception as e:
            LOGGER.error(f"Post-correction failed: {e}")
            return self._create_fallback_correction(original_data, confidence_issues)
    
    def _parse_correction_output(self, llm_text: str, original_data: Dict[str, Any]) -> PostCorrection:
        """Parse LLM output into correction result."""
        try:
            # Extract JSON from LLM output
            json_start = llm_text.find('{')
            json_end = llm_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return self._create_fallback_correction(original_data, [])
            
            json_text = llm_text[json_start:json_end]
            data = json.loads(json_text)
            
            corrected_data = data.get("corrected_data", original_data)
            corrections = data.get("corrections", [])
            confidence_improvement = data.get("confidence_improvement", 0.0)
            
            # Calculate confidence scores
            original_confidence = self._calculate_confidence(original_data)
            new_confidence = original_confidence + confidence_improvement
            
            return PostCorrection(
                corrected_data=corrected_data,
                corrections=corrections,
                confidence_improvement=confidence_improvement,
                original_confidence=original_confidence,
                new_confidence=new_confidence,
                correction_details=data.get("correction_details", {})
            )
            
        except Exception as e:
            LOGGER.error(f"Failed to parse correction output: {e}")
            return self._create_fallback_correction(original_data, [])
    
    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate confidence score for data."""
        # Simple confidence calculation based on data completeness
        required_fields = ["supplier_name", "total_amount"]
        present_fields = sum(1 for field in required_fields if field in data and data[field])
        return present_fields / len(required_fields)
    
    def _create_fallback_correction(self, original_data: Dict[str, Any], 
                                  confidence_issues: List[str]) -> PostCorrection:
        """Create fallback correction when LLM fails."""
        return PostCorrection(
            corrected_data=original_data.copy(),
            corrections=["Manual review required - LLM correction failed"],
            confidence_improvement=0.0,
            original_confidence=self._calculate_confidence(original_data),
            new_confidence=self._calculate_confidence(original_data),
            correction_details={"fallback": True, "issues": confidence_issues}
        )


class AnomalyDetector:
    """Detector for anomalies in invoice data."""
    
    def __init__(self, llm_interface: LocalLLMInterface):
        """Initialize with LLM interface."""
        self.llm = llm_interface
        self.prompt_templates = PromptTemplates()
        
        LOGGER.info("Anomaly Detector initialized")
    
    def detect_anomalies(self, invoice_data: Dict[str, Any],
                        historical_data: Optional[List[Dict[str, Any]]] = None,
                        context: Optional[Dict[str, Any]] = None) -> AnomalyDetection:
        """
        Detect anomalies in invoice data.
        
        Args:
            invoice_data: Current invoice data
            historical_data: Historical invoice data for comparison
            context: Additional context
            
        Returns:
            AnomalyDetection with detected anomalies
        """
        try:
            # Create anomaly detection prompt
            prompt = self._create_anomaly_detection_prompt(
                invoice_data, historical_data, context
            )
            
            # Generate with LLM
            llm_result = self.llm.generate(prompt)
            
            if not llm_result.success:
                return self._create_fallback_anomaly_detection(invoice_data)
            
            # Parse LLM output
            anomaly_detection = self._parse_anomaly_output(llm_result.text)
            
            LOGGER.info(f"Anomaly detection completed: {len(anomaly_detection.anomalies)} anomalies found")
            return anomaly_detection
            
        except Exception as e:
            LOGGER.error(f"Anomaly detection failed: {e}")
            return self._create_fallback_anomaly_detection(invoice_data)
    
    def _create_anomaly_detection_prompt(self, invoice_data: Dict[str, Any],
                                       historical_data: Optional[List[Dict[str, Any]]],
                                       context: Optional[Dict[str, Any]]) -> str:
        """Create anomaly detection prompt."""
        prompt = f"""Analyze the following invoice data for anomalies and potential issues:

Invoice Data:
{json.dumps(invoice_data, indent=2)}

Historical Context:
{json.dumps(historical_data or [], indent=2)}

Additional Context:
{json.dumps(context or {}, indent=2)}

Look for:
1. Unusual amounts or patterns
2. Missing or invalid data
3. Inconsistencies with historical data
4. Potential fraud indicators
5. Data quality issues

Output as JSON:
{{
    "anomalies": ["list of detected anomalies"],
    "severity": "low|medium|high",
    "recommendations": ["list of recommendations"],
    "confidence": 0.0-1.0
}}"""
        
        return prompt
    
    def _parse_anomaly_output(self, llm_text: str) -> AnomalyDetection:
        """Parse LLM output into anomaly detection result."""
        try:
            # Extract JSON from LLM output
            json_start = llm_text.find('{')
            json_end = llm_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return self._create_fallback_anomaly_detection({})
            
            json_text = llm_text[json_start:json_end]
            data = json.loads(json_text)
            
            return AnomalyDetection(
                anomalies=data.get("anomalies", []),
                severity=data.get("severity", "low"),
                recommendations=data.get("recommendations", []),
                confidence=data.get("confidence", 0.0)
            )
            
        except Exception as e:
            LOGGER.error(f"Failed to parse anomaly output: {e}")
            return self._create_fallback_anomaly_detection({})
    
    def _create_fallback_anomaly_detection(self, invoice_data: Dict[str, Any]) -> AnomalyDetection:
        """Create fallback anomaly detection when LLM fails."""
        anomalies = []
        
        # Basic anomaly checks
        if not invoice_data.get("supplier_name"):
            anomalies.append("Missing supplier name")
        
        if not invoice_data.get("total_amount"):
            anomalies.append("Missing total amount")
        
        if invoice_data.get("total_amount", 0) <= 0:
            anomalies.append("Invalid or zero total amount")
        
        severity = "high" if len(anomalies) > 2 else "medium" if anomalies else "low"
        
        return AnomalyDetection(
            anomalies=anomalies,
            severity=severity,
            recommendations=["Manual review recommended"],
            confidence=0.5
        )

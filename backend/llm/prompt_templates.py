"""
Prompt Templates for LLM Tasks

This module provides structured prompt templates for various LLM tasks
including invoice card generation, credit request drafting, and post-correction.
"""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

LOGGER = logging.getLogger("owlin.llm.prompt_templates")


class PromptType(Enum):
    """Types of prompts supported."""
    INVOICE_CARD = "invoice_card"
    CREDIT_REQUEST = "credit_request"
    POST_CORRECTION = "post_correction"
    REVIEW_SUGGESTION = "review_suggestion"


@dataclass
class PromptTemplate:
    """A prompt template with examples and schema."""
    name: str
    prompt_type: PromptType
    template: str
    examples: List[Dict[str, Any]]
    schema: Dict[str, Any]
    max_tokens: int = 2048
    temperature: float = 0.0
    
    def format_prompt(self, **kwargs) -> str:
        """Format the template with provided variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            LOGGER.error(f"Missing template variable: {e}")
            raise


class PromptTemplates:
    """Collection of prompt templates for different tasks."""
    
    def __init__(self):
        """Initialize with default templates."""
        self.templates = self._create_default_templates()
    
    def _create_default_templates(self) -> Dict[PromptType, PromptTemplate]:
        """Create default prompt templates."""
        templates = {}
        
        # Invoice Card Generation Template
        templates[PromptType.INVOICE_CARD] = PromptTemplate(
            name="invoice_card_generation",
            prompt_type=PromptType.INVOICE_CARD,
            template="""You are an expert invoice processing assistant. Convert the OCR-extracted invoice data into a standardized invoice card JSON format.

OCR Data:
{ocr_data}

Confidence Scores:
{confidence_scores}

Review Candidates:
{review_candidates}

Instructions:
1. Extract and normalize all invoice fields
2. Fill in missing information where possible
3. Correct obvious OCR errors
4. Maintain data integrity and accuracy
5. Output valid JSON only

Schema:
{invoice_schema}

Examples:
{examples}

Output the complete invoice card as JSON:""",
            examples=[
                {
                    "input": {
                        "supplier": "ACME Corp Ltd",
                        "invoice_number": "INV-2024-001",
                        "date": "2024-01-15",
                        "total": "£120.00"
                    },
                    "output": {
                        "supplier_name": "ACME Corporation Ltd",
                        "invoice_number": "INV-2024-001",
                        "invoice_date": "2024-01-15",
                        "currency": "GBP",
                        "total_amount": 120.00,
                        "confidence": 0.95,
                        "needs_review": False
                    }
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "supplier_name": {"type": "string"},
                    "invoice_number": {"type": "string"},
                    "invoice_date": {"type": "string", "format": "date"},
                    "currency": {"type": "string"},
                    "subtotal": {"type": "number"},
                    "tax_amount": {"type": "number"},
                    "total_amount": {"type": "number"},
                    "line_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"},
                                "unit_price": {"type": "number"},
                                "line_total": {"type": "number"}
                            }
                        }
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "needs_review": {"type": "boolean"},
                    "review_reasons": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["supplier_name", "total_amount"]
            }
        )
        
        # Credit Request Template
        templates[PromptType.CREDIT_REQUEST] = PromptTemplate(
            name="credit_request_generation",
            prompt_type=PromptType.CREDIT_REQUEST,
            template="""You are a professional finance assistant. Generate a credit request email based on the invoice analysis.

Invoice Data:
{invoice_data}

Anomalies Detected:
{anomalies}

Credit Reasons:
{credit_reasons}

Instructions:
1. Write a professional credit request email
2. Include specific invoice details
3. Explain the reason for the credit request
4. Use appropriate business tone
5. Include all necessary information

Examples:
{examples}

Generate the credit request email:""",
            examples=[
                {
                    "input": {
                        "invoice_number": "INV-2024-001",
                        "amount": "£120.00",
                        "reason": "Duplicate charge"
                    },
                    "output": """Subject: Credit Request - Invoice INV-2024-001

Dear Accounts Team,

I am writing to request a credit for the following invoice:

Invoice Number: INV-2024-001
Amount: £120.00
Issue: Duplicate charge for services already paid

Please process this credit request at your earliest convenience.

Best regards,
Finance Team"""
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "recipient": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                },
                "required": ["subject", "body"]
            }
        )
        
        # Post-Correction Template
        templates[PromptType.POST_CORRECTION] = PromptTemplate(
            name="post_correction",
            prompt_type=PromptType.POST_CORRECTION,
            template="""You are an expert data correction assistant. Correct and improve the following invoice data.

Original Data:
{original_data}

Confidence Issues:
{confidence_issues}

Context:
{context}

Instructions:
1. Correct obvious OCR errors
2. Standardize formats (dates, currency, etc.)
3. Fill in missing information where possible
4. Maintain data integrity
5. Output corrected data as JSON

Examples:
{examples}

Provide the corrected data:""",
            examples=[
                {
                    "input": {
                        "supplier": "ACME Corp Ltd",
                        "date": "2024-01-1S",  # OCR error
                        "amount": "£120.00"
                    },
                    "output": {
                        "supplier": "ACME Corporation Ltd",
                        "date": "2024-01-15",
                        "amount": "£120.00",
                        "corrections": ["Fixed date OCR error", "Expanded company name"]
                    }
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "corrected_data": {"type": "object"},
                    "corrections": {"type": "array", "items": {"type": "string"}},
                    "confidence_improvement": {"type": "number"}
                },
                "required": ["corrected_data", "corrections"]
            }
        )
        
        # Review Suggestion Template
        templates[PromptType.REVIEW_SUGGESTION] = PromptTemplate(
            name="review_suggestion",
            prompt_type=PromptType.REVIEW_SUGGESTION,
            template="""You are an expert invoice reviewer. Analyze the invoice data and provide review suggestions.

Invoice Data:
{invoice_data}

Confidence Scores:
{confidence_scores}

Review Candidates:
{review_candidates}

Instructions:
1. Identify fields that need human review
2. Suggest corrections for low-confidence fields
3. Flag potential issues or anomalies
4. Provide specific recommendations
5. Output structured suggestions

Examples:
{examples}

Provide review suggestions:""",
            examples=[
                {
                    "input": {
                        "supplier": "unclear company name",
                        "date": "sometime in 2024",
                        "amount": "around 100"
                    },
                    "output": {
                        "needs_review": True,
                        "suggestions": [
                            "Supplier name is unclear - needs manual verification",
                            "Date format is ambiguous - check original document",
                            "Amount is approximate - verify exact figure"
                        ],
                        "priority": "high"
                    }
                }
            ],
            schema={
                "type": "object",
                "properties": {
                    "needs_review": {"type": "boolean"},
                    "suggestions": {"type": "array", "items": {"type": "string"}},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "confidence_issues": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["needs_review", "suggestions"]
            }
        )
        
        return templates
    
    def get_template(self, prompt_type: PromptType) -> PromptTemplate:
        """Get a prompt template by type."""
        if prompt_type not in self.templates:
            raise ValueError(f"Template not found for type: {prompt_type}")
        return self.templates[prompt_type]
    
    def format_invoice_card_prompt(self, ocr_data: Dict[str, Any], 
                                 confidence_scores: Dict[str, float],
                                 review_candidates: List[Dict[str, Any]]) -> str:
        """Format invoice card generation prompt."""
        template = self.get_template(PromptType.INVOICE_CARD)
        
        return template.format_prompt(
            ocr_data=json.dumps(ocr_data, indent=2),
            confidence_scores=json.dumps(confidence_scores, indent=2),
            review_candidates=json.dumps(review_candidates, indent=2),
            invoice_schema=json.dumps(template.schema, indent=2),
            examples=json.dumps(template.examples, indent=2)
        )
    
    def format_credit_request_prompt(self, invoice_data: Dict[str, Any],
                                   anomalies: List[str],
                                   credit_reasons: List[str]) -> str:
        """Format credit request generation prompt."""
        template = self.get_template(PromptType.CREDIT_REQUEST)
        
        return template.format_prompt(
            invoice_data=json.dumps(invoice_data, indent=2),
            anomalies=json.dumps(anomalies, indent=2),
            credit_reasons=json.dumps(credit_reasons, indent=2),
            examples=json.dumps(template.examples, indent=2)
        )
    
    def format_post_correction_prompt(self, original_data: Dict[str, Any],
                                    confidence_issues: List[str],
                                    context: Dict[str, Any]) -> str:
        """Format post-correction prompt."""
        template = self.get_template(PromptType.POST_CORRECTION)
        
        return template.format_prompt(
            original_data=json.dumps(original_data, indent=2),
            confidence_issues=json.dumps(confidence_issues, indent=2),
            context=json.dumps(context, indent=2),
            examples=json.dumps(template.examples, indent=2)
        )
    
    def format_review_suggestion_prompt(self, invoice_data: Dict[str, Any],
                                       confidence_scores: Dict[str, float],
                                       review_candidates: List[Dict[str, Any]]) -> str:
        """Format review suggestion prompt."""
        template = self.get_template(PromptType.REVIEW_SUGGESTION)
        
        return template.format_prompt(
            invoice_data=json.dumps(invoice_data, indent=2),
            confidence_scores=json.dumps(confidence_scores, indent=2),
            review_candidates=json.dumps(review_candidates, indent=2),
            examples=json.dumps(template.examples, indent=2)
        )
    
    def add_custom_template(self, template: PromptTemplate):
        """Add a custom prompt template."""
        self.templates[template.prompt_type] = template
        LOGGER.info(f"Added custom template: {template.name}")
    
    def list_templates(self) -> List[str]:
        """List all available template names."""
        return [template.name for template in self.templates.values()]

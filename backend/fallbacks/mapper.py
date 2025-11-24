# backend/fallbacks/mapper.py
"""
Donut Output Mapper

This module provides mapping functions to convert Donut model output
into Owlin's invoice card JSON format.

Features:
- Safe mapping with null handling
- Field validation and normalization
- Best-effort parsing for malformed output
- Comprehensive error handling
"""

from __future__ import annotations
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

LOGGER = logging.getLogger("owlin.fallbacks.mapper")


def map_donut_to_invoice_card(donut_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Donut output to invoice card JSON format.
    
    Args:
        donut_output: Raw output from Donut model
        
    Returns:
        Mapped invoice card JSON
    """
    try:
        # Initialize invoice card structure
        invoice_card = {
            "supplier": None,
            "date": None,
            "total": None,
            "vat_total": None,
            "line_items": [],
            "currency": None,
            "invoice_number": None,
            "raw_donut_output": donut_output
        }
        
        # Map supplier/company
        if "company" in donut_output:
            invoice_card["supplier"] = _normalize_supplier(donut_output["company"])
        elif "supplier" in donut_output:
            invoice_card["supplier"] = _normalize_supplier(donut_output["supplier"])
        
        # Map date
        if "date" in donut_output:
            invoice_card["date"] = _normalize_date(donut_output["date"])
        
        # Map total amount
        if "total" in donut_output:
            total_info = _normalize_amount(donut_output["total"])
            invoice_card["total"] = total_info["amount"]
            invoice_card["currency"] = total_info["currency"]
        
        # Map VAT total
        if "vat_total" in donut_output:
            vat_info = _normalize_amount(donut_output["vat_total"])
            invoice_card["vat_total"] = vat_info["amount"]
        elif "tax" in donut_output:
            tax_info = _normalize_amount(donut_output["tax"])
            invoice_card["vat_total"] = tax_info["amount"]
        
        # Map invoice number
        if "invoice_number" in donut_output:
            invoice_card["invoice_number"] = _normalize_invoice_number(donut_output["invoice_number"])
        elif "invoice_id" in donut_output:
            invoice_card["invoice_number"] = _normalize_invoice_number(donut_output["invoice_id"])
        
        # Map line items
        if "line_items" in donut_output and isinstance(donut_output["line_items"], list):
            invoice_card["line_items"] = _normalize_line_items(donut_output["line_items"])
        elif "items" in donut_output and isinstance(donut_output["items"], list):
            invoice_card["line_items"] = _normalize_line_items(donut_output["items"])
        
        # Add metadata
        invoice_card["mapping_metadata"] = {
            "mapped_at": datetime.now().isoformat(),
            "source_fields": list(donut_output.keys()),
            "mapping_version": "1.0"
        }
        
        return invoice_card
        
    except Exception as e:
        LOGGER.error("Failed to map Donut output: %s", e)
        return {
            "supplier": None,
            "date": None,
            "total": None,
            "vat_total": None,
            "line_items": [],
            "currency": None,
            "invoice_number": None,
            "raw_donut_output": donut_output,
            "mapping_error": str(e)
        }


def _normalize_supplier(supplier: Any) -> Optional[str]:
    """Normalize supplier name."""
    if not supplier:
        return None
    
    try:
        supplier_str = str(supplier).strip()
        if not supplier_str:
            return None
        
        # Basic cleaning
        supplier_str = re.sub(r'\s+', ' ', supplier_str)
        supplier_str = supplier_str.strip()
        
        return supplier_str if supplier_str else None
        
    except Exception:
        return None


def _normalize_date(date: Any) -> Optional[str]:
    """Normalize date to ISO format."""
    if not date:
        return None
    
    try:
        date_str = str(date).strip()
        if not date_str:
            return None
        
        # Try to parse common date formats
        date_formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S"
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # If no format matches, return as-is
        return date_str
        
    except Exception:
        return None


def _normalize_amount(amount: Any) -> Dict[str, Any]:
    """Normalize amount and extract currency."""
    if not amount:
        return {"amount": None, "currency": None}
    
    try:
        amount_str = str(amount).strip()
        if not amount_str:
            return {"amount": None, "currency": None}
        
        # Extract currency symbols
        currency_symbols = {
            "£": "GBP",
            "$": "USD",
            "€": "EUR",
            "¥": "JPY"
        }
        
        currency = None
        for symbol, code in currency_symbols.items():
            if symbol in amount_str:
                currency = code
                amount_str = amount_str.replace(symbol, "")
                break
        
        # Extract numeric value
        numeric_match = re.search(r'[\d,]+\.?\d*', amount_str)
        if numeric_match:
            numeric_str = numeric_match.group().replace(',', '')
            try:
                numeric_value = float(numeric_str)
                return {"amount": numeric_value, "currency": currency}
            except ValueError:
                pass
        
        return {"amount": None, "currency": currency}
        
    except Exception:
        return {"amount": None, "currency": None}


def _normalize_invoice_number(invoice_number: Any) -> Optional[str]:
    """Normalize invoice number."""
    if not invoice_number:
        return None
    
    try:
        invoice_str = str(invoice_number).strip()
        if not invoice_str:
            return None
        
        # Basic cleaning
        invoice_str = re.sub(r'\s+', ' ', invoice_str)
        invoice_str = invoice_str.strip()
        
        return invoice_str if invoice_str else None
        
    except Exception:
        return None


def _normalize_line_items(line_items: List[Any]) -> List[Dict[str, Any]]:
    """Normalize line items."""
    if not isinstance(line_items, list):
        return []
    
    normalized_items = []
    
    for item in line_items:
        try:
            if isinstance(item, dict):
                normalized_item = {
                    "description": _normalize_string(item.get("description", "")),
                    "quantity": _normalize_quantity(item.get("quantity", "")),
                    "unit_price": _normalize_amount(item.get("unit_price", "")).get("amount"),
                    "line_total": _normalize_amount(item.get("line_total", "")).get("amount"),
                    "unit": _normalize_string(item.get("unit", ""))
                }
            else:
                # Try to extract from string
                normalized_item = {
                    "description": _normalize_string(str(item)),
                    "quantity": None,
                    "unit_price": None,
                    "line_total": None,
                    "unit": None
                }
            
            normalized_items.append(normalized_item)
            
        except Exception as e:
            LOGGER.warning("Failed to normalize line item: %s", e)
            continue
    
    return normalized_items


def _normalize_string(value: Any) -> Optional[str]:
    """Normalize string value."""
    if not value:
        return None
    
    try:
        str_value = str(value).strip()
        return str_value if str_value else None
    except Exception:
        return None


def _normalize_quantity(quantity: Any) -> Optional[float]:
    """Normalize quantity value."""
    if not quantity:
        return None
    
    try:
        quantity_str = str(quantity).strip()
        if not quantity_str:
            return None
        
        # Extract numeric value
        numeric_match = re.search(r'[\d,]+\.?\d*', quantity_str)
        if numeric_match:
            numeric_str = numeric_match.group().replace(',', '')
            return float(numeric_str)
        
        return None
        
    except Exception:
        return None


def merge_invoice_cards(base_card: Dict[str, Any], donut_card: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge Donut invoice card into base card, only filling missing fields.
    
    Args:
        base_card: Base invoice card
        donut_card: Donut-generated invoice card
        
    Returns:
        Merged invoice card
    """
    try:
        merged_card = base_card.copy()
        
        # Only merge non-empty fields from Donut
        for field in ["supplier", "date", "total", "vat_total", "currency", "invoice_number"]:
            if field in donut_card and donut_card[field] is not None:
                if field not in merged_card or merged_card[field] is None:
                    merged_card[field] = donut_card[field]
        
        # Merge line items (append if base is empty)
        if "line_items" in donut_card and donut_card["line_items"]:
            if "line_items" not in merged_card or not merged_card["line_items"]:
                merged_card["line_items"] = donut_card["line_items"]
        
        # Add Donut metadata
        merged_card["donut_merged"] = True
        merged_card["donut_metadata"] = donut_card.get("mapping_metadata", {})
        
        return merged_card
        
    except Exception as e:
        LOGGER.error("Failed to merge invoice cards: %s", e)
        return base_card


def validate_invoice_card(card: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean invoice card."""
    try:
        validated_card = {}
        
        # Validate required fields
        for field in ["supplier", "date", "total", "vat_total", "currency", "invoice_number"]:
            value = card.get(field)
            if value is not None:
                validated_card[field] = value
        
        # Validate line items
        if "line_items" in card and isinstance(card["line_items"], list):
            validated_items = []
            for item in card["line_items"]:
                if isinstance(item, dict):
                    validated_items.append(item)
            validated_card["line_items"] = validated_items
        
        # Add validation metadata
        validated_card["validation_metadata"] = {
            "validated_at": datetime.now().isoformat(),
            "validation_version": "1.0"
        }
        
        return validated_card
        
    except Exception as e:
        LOGGER.error("Failed to validate invoice card: %s", e)
        return card

"""
Matching Module

This module provides functionality for matching invoices with their corresponding delivery notes.
It uses fuzzy matching algorithms to pair line items and detect discrepancies.

Key Features:
- Fuzzy matching of product descriptions
- Quantity and price discrepancy detection
- Document-level matching analysis
- Confidence scoring and validation
- Manual review suggestions

Author: OWLIN Development Team
Version: 1.0.0
"""

from .match_invoice_delivery import (
    match_items,
    match_documents,
    suggest_matches,
    validate_matching_result,
    MatchedItem,
    MatchingResult
)

__all__ = [
    'match_items',
    'match_documents', 
    'suggest_matches',
    'validate_matching_result',
    'MatchedItem',
    'MatchingResult'
] 
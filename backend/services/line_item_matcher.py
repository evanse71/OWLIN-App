# -*- coding: utf-8 -*-
"""
Line Item Matcher Module

Provides fuzzy matching, SKU matching, and partial matching for line items
between invoices and delivery notes.
"""

from __future__ import annotations
import logging
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

LOGGER = logging.getLogger("owlin.services.line_item_matcher")
LOGGER.setLevel(logging.INFO)

# Default similarity threshold for fuzzy matching
DEFAULT_SIMILARITY_THRESHOLD = 0.85


def normalize_description(desc: str) -> str:
    """
    Normalize description for comparison.
    
    - Convert to lowercase
    - Strip whitespace
    - Remove extra spaces
    - Remove special characters (optional, for better matching)
    
    Args:
        desc: Description string
        
    Returns:
        Normalized description string
    """
    if not desc:
        return ""
    
    # Convert to lowercase and strip
    normalized = desc.lower().strip()
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def calculate_similarity(desc1: str, desc2: str) -> float:
    """
    Calculate similarity between two descriptions using SequenceMatcher.
    
    Args:
        desc1: First description
        desc2: Second description
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not desc1 or not desc2:
        return 0.0
    
    norm1 = normalize_description(desc1)
    norm2 = normalize_description(desc2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Exact match after normalization
    if norm1 == norm2:
        return 1.0
    
    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, norm1, norm2).ratio()


def calculate_token_similarity(desc1: str, desc2: str) -> float:
    """
    Calculate similarity based on token (word) overlap.
    Useful for handling word order differences.
    
    Args:
        desc1: First description
        desc2: Second description
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not desc1 or not desc2:
        return 0.0
    
    norm1 = normalize_description(desc1)
    norm2 = normalize_description(desc2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Split into tokens (words)
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    
    if not tokens1 or not tokens2:
        return 0.0
    
    # Calculate Jaccard similarity (intersection over union)
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    
    if union == 0:
        return 0.0
    
    return intersection / union


def check_partial_match(desc1: str, desc2: str) -> bool:
    """
    Check if one description contains key words from the other.
    
    Args:
        desc1: First description
        desc2: Second description
        
    Returns:
        True if partial match detected
    """
    if not desc1 or not desc2:
        return False
    
    norm1 = normalize_description(desc1)
    norm2 = normalize_description(desc2)
    
    if not norm1 or not norm2:
        return False
    
    # Split into tokens
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    
    # Remove common stop words (optional - can be expanded)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    tokens1 = tokens1 - stop_words
    tokens2 = tokens2 - stop_words
    
    if not tokens1 or not tokens2:
        return False
    
    # Check if significant overlap (at least 50% of shorter set)
    intersection = len(tokens1 & tokens2)
    min_tokens = min(len(tokens1), len(tokens2))
    
    if min_tokens == 0:
        return False
    
    return intersection / min_tokens >= 0.5


def match_line_items(
    invoice_items: List[Dict],
    delivery_items: List[Dict],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD
) -> List[Tuple[Dict, Optional[Dict], float, str]]:
    """
    Match invoice items to delivery items using multiple strategies.
    
    Matching priority:
    1. SKU match (if both have SKU)
    2. Exact description match
    3. Fuzzy description match (similarity >= threshold)
    4. Partial match (token overlap)
    
    Args:
        invoice_items: List of invoice line item dictionaries
        delivery_items: List of delivery note line item dictionaries
        threshold: Similarity threshold for fuzzy matching (default 0.85)
        
    Returns:
        List of tuples: (invoice_item, matched_delivery_item, similarity_score, match_type)
        match_type can be: "exact", "sku", "fuzzy", "partial", or "none"
    """
    matched = []
    used_delivery_indices = set()
    
    for inv_item in invoice_items:
        inv_desc = inv_item.get("description") or inv_item.get("desc") or inv_item.get("item") or ""
        inv_sku = inv_item.get("sku") or inv_item.get("SKU") or ""
        
        best_match = None
        best_similarity = 0.0
        best_match_type = "none"
        best_index = -1
        
        # Try to match against each delivery item
        for idx, del_item in enumerate(delivery_items):
            if idx in used_delivery_indices:
                continue
            
            del_desc = del_item.get("description") or del_item.get("desc") or del_item.get("item") or ""
            del_sku = del_item.get("sku") or del_item.get("SKU") or ""
            
            match_type = "none"
            similarity = 0.0
            
            # Strategy 1: SKU match (highest priority)
            if inv_sku and del_sku:
                inv_sku_norm = inv_sku.strip().upper()
                del_sku_norm = del_sku.strip().upper()
                if inv_sku_norm == del_sku_norm:
                    match_type = "sku"
                    similarity = 1.0
                    if similarity > best_similarity:
                        best_match = del_item
                        best_similarity = similarity
                        best_match_type = match_type
                        best_index = idx
                    continue  # SKU match is definitive, no need to check other strategies
            
            # Strategy 2: Exact description match
            if inv_desc and del_desc:
                norm1 = normalize_description(inv_desc)
                norm2 = normalize_description(del_desc)
                if norm1 == norm2 and norm1:
                    match_type = "exact"
                    similarity = 1.0
                    if similarity > best_similarity:
                        best_match = del_item
                        best_similarity = similarity
                        best_match_type = match_type
                        best_index = idx
                    continue  # Exact match is definitive
            
            # Strategy 3: Fuzzy description match
            if inv_desc and del_desc:
                # Use both sequence similarity and token similarity, take the max
                seq_similarity = calculate_similarity(inv_desc, del_desc)
                token_similarity = calculate_token_similarity(inv_desc, del_desc)
                similarity = max(seq_similarity, token_similarity)
                
                if similarity >= threshold:
                    match_type = "fuzzy"
                    if similarity > best_similarity:
                        best_match = del_item
                        best_similarity = similarity
                        best_match_type = match_type
                        best_index = idx
            
            # Strategy 4: Partial match (only if no better match found)
            if best_similarity < threshold and inv_desc and del_desc:
                if check_partial_match(inv_desc, del_desc):
                    # Calculate similarity for partial match
                    similarity = calculate_token_similarity(inv_desc, del_desc)
                    if similarity > best_similarity:
                        match_type = "partial"
                        best_match = del_item
                        best_similarity = similarity
                        best_match_type = match_type
                        best_index = idx
        
        # Mark delivery item as used if we found a good match
        if best_match and best_index >= 0 and best_similarity >= threshold:
            used_delivery_indices.add(best_index)
        
        # Add to results (even if no match found, similarity will be 0.0)
        matched.append((inv_item, best_match, best_similarity, best_match_type))
    
    return matched


def get_item_description(item: Dict) -> str:
    """
    Extract description from a line item dictionary.
    
    Args:
        item: Line item dictionary
        
    Returns:
        Description string
    """
    return item.get("description") or item.get("desc") or item.get("item") or ""


def get_item_sku(item: Dict) -> str:
    """
    Extract SKU from a line item dictionary.
    
    Args:
        item: Line item dictionary
        
    Returns:
        SKU string
    """
    return item.get("sku") or item.get("SKU") or ""


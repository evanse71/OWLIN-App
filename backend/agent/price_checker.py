"""
Price Checker Module for Owlin Agent

Compares current invoice prices against historical price data to detect
significant price mismatches that may indicate billing errors or price increases.
"""

import logging
from typing import Dict, List, Any
import statistics

logger = logging.getLogger(__name__)

def check_price_mismatches(
    line_items: List[Dict[str, Any]],
    historical_prices: Dict[str, List[float]]
) -> List[Dict[str, Any]]:
    """
    Check for price mismatches between current and historical prices.
    
    Compares each line item's unit price against historical averages
    and flags significant deviations that may indicate billing errors.
    
    Args:
        line_items: List of line item dictionaries
        historical_prices: Dictionary mapping item names to list of historical prices
            Format: {"item_name": [price1, price2, price3, ...]}
            
    Returns:
        List of price mismatch flags
    """
    logger.debug("🔍 Starting price mismatch analysis")
    
    flags = []
    
    if not line_items:
        logger.debug("No line items to check for price mismatches")
        return flags
    
    if not historical_prices:
        logger.debug("No historical price data available")
        return flags
    
    for i, item in enumerate(line_items):
        item_flags = _check_single_item_price(item, i, historical_prices)
        flags.extend(item_flags)
    
    logger.debug(f"✅ Price mismatch analysis completed. Found {len(flags)} flags")
    return flags

def _check_single_item_price(
    item: Dict[str, Any],
    index: int,
    historical_prices: Dict[str, List[float]]
) -> List[Dict[str, Any]]:
    """
    Check a single line item for price mismatches.
    
    Args:
        item: Line item dictionary
        index: Line item index
        historical_prices: Dictionary of historical prices
        
    Returns:
        List of price mismatch flags for this item
    """
    flags = []
    
    # Get item name and current unit price
    item_name = item.get('item', '') or item.get('description', '')
    if not item_name:
        return flags
    
    current_price = item.get('unit_price_excl_vat', 0.0) or item.get('unit_price', 0.0)
    if current_price <= 0.0:
        return flags
    
    # Find matching historical prices
    historical_price_list = _find_matching_historical_prices(item_name, historical_prices)
    if not historical_price_list:
        return flags
    
    # Calculate price statistics
    price_stats = _calculate_price_statistics(historical_price_list)
    
    # Check for price mismatches
    flags.extend(_detect_price_anomalies(
        item_name, current_price, price_stats, index
    ))
    
    return flags

def _find_matching_historical_prices(
    item_name: str,
    historical_prices: Dict[str, List[float]]
) -> List[float]:
    """
    Find historical prices for an item using fuzzy matching.
    
    Args:
        item_name: Name of the item to find prices for
        historical_prices: Dictionary of historical prices
        
    Returns:
        List of historical prices for the item
    """
    # Direct match
    if item_name in historical_prices:
        return historical_prices[item_name]
    
    # Fuzzy matching for common variations
    item_lower = item_name.lower().strip()
    
    for key, prices in historical_prices.items():
        key_lower = key.lower().strip()
        
        # Exact match
        if key_lower == item_lower:
            return prices
        
        # Contains match (e.g., "Beef Sirloin" matches "Sirloin")
        if key_lower in item_lower or item_lower in key_lower:
            return prices
        
        # Word-based matching
        item_words = set(item_lower.split())
        key_words = set(key_lower.split())
        
        if item_words & key_words:  # Intersection of words
            return prices
    
    return []

def _calculate_price_statistics(historical_prices: List[float]) -> Dict[str, float]:
    """
    Calculate statistics for historical prices.
    
    Args:
        historical_prices: List of historical prices
        
    Returns:
        Dictionary with price statistics
    """
    if not historical_prices:
        return {}
    
    prices = [p for p in historical_prices if p > 0]  # Filter out zero prices
    
    if not prices:
        return {}
    
    return {
        'mean': statistics.mean(prices),
        'median': statistics.median(prices),
        'min': min(prices),
        'max': max(prices),
        'std': statistics.stdev(prices) if len(prices) > 1 else 0.0,
        'count': len(prices)
    }

def _detect_price_anomalies(
    item_name: str,
    current_price: float,
    price_stats: Dict[str, float],
    index: int
) -> List[Dict[str, Any]]:
    """
    Detect price anomalies based on historical statistics.
    
    Args:
        item_name: Name of the item
        current_price: Current unit price
        price_stats: Historical price statistics
        index: Line item index
        
    Returns:
        List of price anomaly flags
    """
    flags = []
    
    if not price_stats:
        return flags
    
    mean_price = price_stats['mean']
    std_price = price_stats['std']
    min_price = price_stats['min']
    max_price = price_stats['max']
    
    # Calculate price difference and percentage
    price_diff = current_price - mean_price
    price_diff_percent = (price_diff / mean_price * 100) if mean_price > 0 else 0
    
    # Define thresholds
    HIGH_THRESHOLD = 20.0  # 20% above average
    CRITICAL_THRESHOLD = 50.0  # 50% above average
    LOW_THRESHOLD = -15.0  # 15% below average
    
    # Check for significant price increases
    if price_diff_percent > CRITICAL_THRESHOLD:
        flags.append({
            "type": "critical_price_increase",
            "severity": "critical",
            "field": f"line_items[{index}].unit_price",
            "message": f"Critical price increase: {item_name} is {price_diff_percent:.1f}% above average (£{current_price:.2f} vs £{mean_price:.2f})",
            "suggested_action": "Immediately contact supplier to verify price increase and request credit if incorrect"
        })
    elif price_diff_percent > HIGH_THRESHOLD:
        flags.append({
            "type": "high_price_increase",
            "severity": "warning",
            "field": f"line_items[{index}].unit_price",
            "message": f"Significant price increase: {item_name} is {price_diff_percent:.1f}% above average (£{current_price:.2f} vs £{mean_price:.2f})",
            "suggested_action": "Contact supplier to verify price increase and consider requesting credit"
        })
    
    # Check for unusually low prices (potential error)
    elif price_diff_percent < LOW_THRESHOLD:
        flags.append({
            "type": "unusually_low_price",
            "severity": "warning",
            "field": f"line_items[{index}].unit_price",
            "message": f"Unusually low price: {item_name} is {abs(price_diff_percent):.1f}% below average (£{current_price:.2f} vs £{mean_price:.2f})",
            "suggested_action": "Verify this is not a billing error - unusually low prices may indicate mistakes"
        })
    
    # Check if price is outside historical range
    if current_price > max_price * 1.1:  # 10% above historical max
        flags.append({
            "type": "above_historical_max",
            "severity": "warning",
            "field": f"line_items[{index}].unit_price",
            "message": f"Price above historical maximum: {item_name} (£{current_price:.2f}) exceeds previous high of £{max_price:.2f}",
            "suggested_action": "Verify price increase with supplier"
        })
    
    # Check for price volatility (if we have enough data)
    if price_stats['count'] >= 3 and std_price > 0:
        coefficient_of_variation = (std_price / mean_price) * 100
        if coefficient_of_variation > 25:  # High volatility
            flags.append({
                "type": "high_price_volatility",
                "severity": "info",
                "field": f"line_items[{index}].unit_price",
                "message": f"High price volatility for {item_name}: {coefficient_of_variation:.1f}% variation in historical prices",
                "suggested_action": "Monitor price trends - this item has variable pricing"
            })
    
    return flags

def get_price_summary(
    line_items: List[Dict[str, Any]],
    historical_prices: Dict[str, List[float]]
) -> Dict[str, Any]:
    """
    Generate a summary of price analysis.
    
    Args:
        line_items: List of line items
        historical_prices: Historical price data
        
    Returns:
        Dictionary with price analysis summary
    """
    if not line_items or not historical_prices:
        return {
            "items_checked": 0,
            "items_with_history": 0,
            "price_increases": 0,
            "price_decreases": 0,
            "average_price_change": 0.0
        }
    
    items_checked = 0
    items_with_history = 0
    price_changes = []
    
    for item in line_items:
        item_name = item.get('item', '') or item.get('description', '')
        current_price = item.get('unit_price_excl_vat', 0.0) or item.get('unit_price', 0.0)
        
        if not item_name or current_price <= 0:
            continue
        
        items_checked += 1
        
        historical_price_list = _find_matching_historical_prices(item_name, historical_prices)
        if historical_price_list:
            items_with_history += 1
            price_stats = _calculate_price_statistics(historical_price_list)
            
            if price_stats:
                mean_price = price_stats['mean']
                price_diff_percent = ((current_price - mean_price) / mean_price * 100) if mean_price > 0 else 0
                price_changes.append(price_diff_percent)
    
    return {
        "items_checked": items_checked,
        "items_with_history": items_with_history,
        "price_increases": len([p for p in price_changes if p > 0]),
        "price_decreases": len([p for p in price_changes if p < 0]),
        "average_price_change": statistics.mean(price_changes) if price_changes else 0.0,
        "max_increase": max(price_changes) if price_changes else 0.0,
        "max_decrease": min(price_changes) if price_changes else 0.0
    }


if __name__ == "__main__":
    # Test price checker
    logging.basicConfig(level=logging.INFO)
    
    # Sample line items
    line_items = [
        {
            "item": "Beef Sirloin",
            "quantity": 5.0,
            "unit_price_excl_vat": 22.00,  # Increased price
            "line_total_excl_vat": 110.00
        },
        {
            "item": "Chicken Breast",
            "quantity": 2.5,
            "unit_price_excl_vat": 8.50,   # Decreased price
            "line_total_excl_vat": 21.25
        },
        {
            "item": "Salmon Fillet",
            "quantity": 3.0,
            "unit_price_excl_vat": 15.00,  # Normal price
            "line_total_excl_vat": 45.00
        }
    ]
    
    # Sample historical prices
    historical_prices = {
        "Beef Sirloin": [18.50, 19.00, 20.50, 21.00, 20.00],  # Average: 19.80
        "Chicken Breast": [9.50, 10.00, 10.50, 11.00, 10.25], # Average: 10.25
        "Salmon Fillet": [14.50, 15.00, 15.50, 16.00, 15.25]  # Average: 15.25
    }
    
    # Test price mismatch detection
    flags = check_price_mismatches(line_items, historical_prices)
    
    print("🔍 Price Mismatch Analysis:")
    print(f"Flags found: {len(flags)}")
    for flag in flags:
        print(f"  - {flag['message']}")
        print(f"    Action: {flag['suggested_action']}")
    
    # Test price summary
    summary = get_price_summary(line_items, historical_prices)
    print(f"\n📊 Price Summary:")
    print(f"  Items checked: {summary['items_checked']}")
    print(f"  Items with history: {summary['items_with_history']}")
    print(f"  Price increases: {summary['price_increases']}")
    print(f"  Price decreases: {summary['price_decreases']}")
    print(f"  Average change: {summary['average_price_change']:.1f}%") 
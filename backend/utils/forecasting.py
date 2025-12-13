def forecast_product_price(item_id: str, horizon_months: int = 3) -> dict:
    """
    Returns a forecast for the specified product.
    Output:
    {
        "forecast": [{"x": "2025-08", "y": 1.45, "upper": 1.65, "lower": 1.25}, ...],
        "historic": [{"x": "2025-06", "y": 1.33}, ...],
        "confidence": "low",
        "volatility": "high",
        "data_points": 6,
    }
    """
    # Placeholder return
    return {
        "forecast": [],
        "historic": [],
        "confidence": "unknown",
        "volatility": "unknown",
        "data_points": 0,
    } 
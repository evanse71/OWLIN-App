from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import pandas as pd
from datetime import datetime, timedelta
import sqlite3

from price_forecasting import forecast_item_price

router = APIRouter()

def get_available_products() -> List[str]:
    """Get list of available products from the database."""
    try:
        conn = sqlite3.connect("data/owlin.db")
        query = """
            SELECT DISTINCT ili.item_description 
            FROM invoice_line_items ili 
            JOIN invoices i ON ili.invoice_id = i.id 
            WHERE ili.item_description IS NOT NULL 
            ORDER BY ili.item_description
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['item_description'].tolist() if not df.empty else []
    except Exception as e:
        print(f"Error fetching available products: {e}")
        return []

def get_historical_data(item_name: str) -> List[Dict[str, Any]]:
    """Get historical price data for a specific item."""
    try:
        conn = sqlite3.connect("data/owlin.db")
        query = """
            SELECT 
                strftime('%Y-%m-%d', i.invoice_date) as date,
                AVG(ili.unit_price) as avg_price,
                COUNT(*) as transactions
            FROM invoice_line_items ili
            JOIN invoices i ON ili.invoice_id = i.id
            WHERE ili.item_description = ? AND ili.unit_price IS NOT NULL
            GROUP BY strftime('%Y-%m', i.invoice_date)
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn, params=[item_name])
        conn.close()
        
        if df.empty:
            return []
        
        # Convert to the format expected by frontend
        historical_data = []
        for _, row in df.iterrows():
            historical_data.append({
                "x": row["date"],
                "y": round(float(row["avg_price"]), 2)
            })
        
        return historical_data
    except Exception as e:
        print(f"Error fetching historical data for {item_name}: {e}")
        return []

@router.get("/available")
async def get_products() -> Dict[str, Any]:
    """Get list of available products for forecasting."""
    try:
        products = get_available_products()
        return {
            "products": products,
            "count": len(products)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch products: {str(e)}")

@router.get("/forecast/{item_name}")
async def get_product_forecast(item_name: str, months_ahead: int = 12) -> Dict[str, Any]:
    """
    Get price forecast for a specific product/item using real forecasting algorithm.
    
    Args:
        item_name: Name of the product/item to forecast
        months_ahead: Number of months to forecast (default: 12)
    
    Returns:
        Dictionary containing historic and forecast data with confidence bands
    """
    try:
        # Get real forecast data using the forecasting algorithm
        forecast_df = forecast_item_price(item_name, months_ahead)
        
        # Get historical data from database
        historical_data = get_historical_data(item_name)
        
        if forecast_df.empty:
            return {
                "item_name": item_name,
                "historic": historical_data,
                "forecast": [],
                "confidence": "low",
                "volatility": "unknown",
                "data_points": len(historical_data),
                "message": "No forecast data available - insufficient historical data"
            }
        
        # Convert forecast data to the format expected by the frontend
        forecast_data = []
        for _, row in forecast_df.iterrows():
            forecast_point = {
                "x": row["date"],
                "y": round(float(row["prediction"]), 2),
                "upper": round(float(row["upper"]), 2),
                "lower": round(float(row["lower"]), 2)
            }
            forecast_data.append(forecast_point)
        
        # Determine confidence and volatility based on data quality
        data_points = len(historical_data)
        if data_points >= 12:
            confidence = "high"
        elif data_points >= 6:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Calculate volatility based on historical price variance
        if len(historical_data) > 1:
            prices = [point["y"] for point in historical_data]
            variance = pd.Series(prices).var()
            if variance < 0.01:
                volatility = "low"
            elif variance < 0.05:
                volatility = "moderate"
            else:
                volatility = "high"
        else:
            volatility = "moderate"
        
        return {
            "item_name": item_name,
            "historic": historical_data,
            "forecast": forecast_data,
            "confidence": confidence,
            "volatility": volatility,
            "data_points": data_points,
            "message": "Real forecast data from historical analysis"
        }
        
    except Exception as e:
        # Return error with available historical data
        historical_data = get_historical_data(item_name)
        return {
            "item_name": item_name,
            "historic": historical_data,
            "forecast": [],
            "confidence": "low",
            "volatility": "unknown",
            "data_points": len(historical_data),
            "message": f"Forecast error: {str(e)}"
        }

@router.get("/forecast-ready/{item_name}")
async def check_forecast_readiness(item_name: str) -> Dict[str, Any]:
    """
    Check if an item has sufficient data for reliable forecasting.
    
    Args:
        item_name: Name of the product/item to check
    
    Returns:
        Dictionary containing readiness status and diagnostic information
    """
    try:
        # Get historical data to assess readiness
        historical_data = get_historical_data(item_name)
        data_points = len(historical_data)
        
        if data_points >= 12:
            status = "ready"
            reason = "Sufficient data for reliable forecasting"
            recommendation = "Forecast should be accurate"
        elif data_points >= 6:
            status = "partial"
            reason = "Limited data available"
            recommendation = "Consider adding more historical data for better accuracy"
        elif data_points >= 3:
            status = "basic"
            reason = "Basic forecasting possible"
            recommendation = "Forecast will be less accurate - more data recommended"
        else:
            status = "insufficient"
            reason = "Insufficient data for forecasting"
            recommendation = "Need more invoice data for this item"
        
        return {
            "item_name": item_name,
            "ready": status in ["ready", "partial", "basic"],
            "status": status,
            "reason": reason,
            "data_points": data_points,
            "recommendation": recommendation,
            "historical_months": data_points
        }
        
    except Exception as e:
        return {
            "item_name": item_name,
            "ready": False,
            "status": "error",
            "reason": f"Error checking readiness: {str(e)}",
            "data_points": 0,
            "recommendation": "Database error occurred",
            "historical_months": 0
        } 
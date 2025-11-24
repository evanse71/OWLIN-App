# -*- coding: utf-8 -*-
"""
Forecast Engine Module

This module provides price trend prediction using Ordinary Least Squares (OLS) regression,
as specified in the System Bible Section 2.7 (lines 190-194).

Features:
- OLS regression for price trends
- 95% confidence bands
- Forecast points at 1, 3, 12 months
- R² calculation for trend quality
"""

from __future__ import annotations
import logging
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

# Optional import for OLS regression
try:
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    LinearRegression = None
    r2_score = None

LOGGER = logging.getLogger("owlin.services.forecast_engine")
LOGGER.setLevel(logging.INFO)

DB_PATH = "data/owlin.db"


@dataclass
class ForecastResult:
    """Represents forecast result for an item."""
    item_id: str
    slope: float
    intercept: float
    r_squared: float
    confidence_band_95: Tuple[float, float]  # (lower, upper)
    forecast_points: List[Dict[str, Any]]  # [{date, predicted_price, lower_bound, upper_bound}]


def _get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _ensure_tables():
    """Ensure forecast-related tables exist."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create supplier_price_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                price_ex_vat REAL NOT NULL,
                observed_at TEXT NOT NULL,
                invoice_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id)
            )
        """)
        
        # Create forecast_points table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forecast_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                forecast_date TEXT NOT NULL,
                predicted_price REAL NOT NULL,
                lower_bound REAL NOT NULL,
                upper_bound REAL NOT NULL,
                confidence REAL DEFAULT 0.95,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(item_id, forecast_date)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_item_id ON supplier_price_history(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_observed_at ON supplier_price_history(observed_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_forecast_points_item_id ON forecast_points(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_forecast_points_date ON forecast_points(forecast_date)")
        
        conn.commit()
        LOGGER.debug("Forecast tables ensured")
        
    except Exception as e:
        LOGGER.error(f"Error ensuring forecast tables: {e}")
        conn.rollback()
    finally:
        conn.close()


def add_price_observation(item_id: str, price_ex_vat: float, invoice_id: Optional[str] = None) -> bool:
    """
    Add a price observation to the history.
    
    Args:
        item_id: Item ID
        price_ex_vat: Price excluding VAT
        invoice_id: Optional invoice ID
    
    Returns:
        True if successful
    """
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO supplier_price_history (item_id, price_ex_vat, observed_at, invoice_id)
            VALUES (?, ?, ?, ?)
        """, (item_id, price_ex_vat, datetime.now().isoformat(), invoice_id))
        
        conn.commit()
        LOGGER.debug(f"Price observation added: item={item_id}, price={price_ex_vat:.2f}")
        return True
        
    except Exception as e:
        LOGGER.error(f"Error adding price observation: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def fit_trend(item_id: str) -> Optional[ForecastResult]:
    """
    Fit OLS regression trend for an item's price history.
    
    Args:
        item_id: Item ID
    
    Returns:
        ForecastResult with slope, intercept, R², and confidence band
    """
    if not SKLEARN_AVAILABLE:
        LOGGER.warning("scikit-learn not available. Install with: pip install scikit-learn")
        return None
    
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get price history (last 12 months)
        cutoff_date = (datetime.now() - timedelta(days=365)).isoformat()
        
        cursor.execute("""
            SELECT price_ex_vat, observed_at
            FROM supplier_price_history
            WHERE item_id = ? AND observed_at >= ?
            ORDER BY observed_at ASC
        """, (item_id, cutoff_date))
        
        rows = cursor.fetchall()
        
        if len(rows) < 3:
            LOGGER.debug(f"Insufficient data for trend fitting: item={item_id}, points={len(rows)}")
            return None
        
        # Prepare data for regression
        prices = []
        dates = []
        
        for price, obs_date in rows:
            try:
                price_val = float(price)
                date_obj = datetime.fromisoformat(obs_date.replace('Z', '+00:00'))
                # Convert to days since first observation
                dates.append((date_obj - datetime.fromisoformat(rows[0][1].replace('Z', '+00:00'))).days)
                prices.append(price_val)
            except (ValueError, TypeError) as e:
                LOGGER.warning(f"Error parsing price history data: {e}")
                continue
        
        if len(prices) < 3:
            LOGGER.debug(f"Insufficient valid data for trend fitting: item={item_id}")
            return None
        
        # Convert to numpy arrays
        X = np.array(dates).reshape(-1, 1)
        y = np.array(prices)
        
        # Fit OLS regression
        model = LinearRegression()
        model.fit(X, y)
        
        # Calculate predictions
        y_pred = model.predict(X)
        
        # Calculate R²
        r_squared = r2_score(y, y_pred)
        
        # Calculate 95% confidence band
        residuals = y - y_pred
        std_error = np.std(residuals)
        confidence_interval = 1.96 * std_error  # 95% confidence
        
        lower_bound = np.min(y) - confidence_interval
        upper_bound = np.max(y) + confidence_interval
        
        result = ForecastResult(
            item_id=item_id,
            slope=float(model.coef_[0]),
            intercept=float(model.intercept_),
            r_squared=float(r_squared),
            confidence_band_95=(float(lower_bound), float(upper_bound)),
            forecast_points=[]
        )
        
        LOGGER.info(f"Trend fitted: item={item_id}, slope={result.slope:.4f}, R²={result.r_squared:.3f}")
        return result
        
    except Exception as e:
        LOGGER.error(f"Error fitting trend: {e}")
        return None
    finally:
        conn.close()


def predict_band(item_id: str, months: List[int] = [1, 3, 12]) -> List[Dict[str, Any]]:
    """
    Predict price with confidence bands for specified months ahead.
    
    Args:
        item_id: Item ID
        months: List of months ahead to forecast (default: [1, 3, 12])
    
    Returns:
        List of forecast points with date, predicted_price, lower_bound, upper_bound
    """
    if not SKLEARN_AVAILABLE:
        return []
    
    # Fit trend first
    trend = fit_trend(item_id)
    if not trend:
        return []
    
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get most recent observation date
        cursor.execute("""
            SELECT MAX(observed_at)
            FROM supplier_price_history
            WHERE item_id = ?
        """, (item_id,))
        
        row = cursor.fetchone()
        if not row or not row[0]:
            return []
        
        base_date = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
        
        # Get base days (days since first observation)
        cursor.execute("""
            SELECT MIN(observed_at)
            FROM supplier_price_history
            WHERE item_id = ?
        """, (item_id,))
        
        first_row = cursor.fetchone()
        if not first_row or not first_row[0]:
            return []
        
        first_date = datetime.fromisoformat(first_row[0].replace('Z', '+00:00'))
        base_days = (base_date - first_date).days
        
        forecast_points = []
        
        for months_ahead in months:
            # Calculate forecast date
            forecast_date = base_date + timedelta(days=months_ahead * 30)
            
            # Calculate days ahead from first observation
            days_ahead = base_days + (months_ahead * 30)
            
            # Predict price
            predicted_price = trend.slope * days_ahead + trend.intercept
            
            # Calculate confidence bounds
            # Use standard error from historical data
            cursor.execute("""
                SELECT price_ex_vat
                FROM supplier_price_history
                WHERE item_id = ?
                ORDER BY observed_at DESC
                LIMIT 10
            """, (item_id,))
            
            recent_prices = [float(row[0]) for row in cursor.fetchall() if row[0]]
            
            if recent_prices:
                price_std = np.std(recent_prices)
                confidence_interval = 1.96 * price_std
                
                lower_bound = predicted_price - confidence_interval
                upper_bound = predicted_price + confidence_interval
            else:
                # Fallback to trend confidence band
                lower_bound, upper_bound = trend.confidence_band_95
            
            forecast_point = {
                "date": forecast_date.isoformat(),
                "predicted_price": float(predicted_price),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "confidence": 0.95,
                "months_ahead": months_ahead
            }
            
            forecast_points.append(forecast_point)
            
            # Save to database
            cursor.execute("""
                INSERT OR REPLACE INTO forecast_points 
                (item_id, forecast_date, predicted_price, lower_bound, upper_bound, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                item_id,
                forecast_date.isoformat(),
                predicted_price,
                lower_bound,
                upper_bound,
                0.95
            ))
        
        conn.commit()
        LOGGER.info(f"Forecast generated: item={item_id}, points={len(forecast_points)}")
        return forecast_points
        
    except Exception as e:
        LOGGER.error(f"Error predicting band: {e}")
        conn.rollback()
        return []
    finally:
        conn.close()


def update_forecast_points() -> int:
    """
    Batch update forecast points for all items with sufficient history.
    
    Returns:
        Number of items updated
    """
    _ensure_tables()
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all items with at least 3 price observations
        cursor.execute("""
            SELECT item_id, COUNT(*) as count
            FROM supplier_price_history
            GROUP BY item_id
            HAVING count >= 3
        """)
        
        items = cursor.fetchall()
        updated_count = 0
        
        for item_id, _ in items:
            try:
                forecast_points = predict_band(item_id, [1, 3, 12])
                if forecast_points:
                    updated_count += 1
            except Exception as e:
                LOGGER.warning(f"Error updating forecast for item {item_id}: {e}")
                continue
        
        LOGGER.info(f"Forecast points updated for {updated_count} items")
        return updated_count
        
    except Exception as e:
        LOGGER.error(f"Error updating forecast points: {e}")
        return 0
    finally:
        conn.close()


def get_forecast_for_item(item_id: str) -> Optional[Dict[str, Any]]:
    """
    Get forecast data for an item.
    
    Args:
        item_id: Item ID
    
    Returns:
        Dictionary with trend data and forecast points
    """
    trend = fit_trend(item_id)
    if not trend:
        return None
    
    forecast_points = predict_band(item_id, [1, 3, 12])
    
    return {
        "item_id": item_id,
        "trend": {
            "slope": trend.slope,
            "intercept": trend.intercept,
            "r_squared": trend.r_squared,
            "confidence_band_95": {
                "lower": trend.confidence_band_95[0],
                "upper": trend.confidence_band_95[1]
            }
        },
        "forecast_points": forecast_points
    }


"""
Forecast Service

Comprehensive forecasting pipeline with model selection, backtesting, and confidence intervals.
Implements deterministic algorithm with explainable model selection.
"""

import os
import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import uuid4
import math

# Set deterministic seed
np.random.seed(1337)

from contracts import ForecastPoint, ForecastSeries, ForecastQuality, ForecastScenario
from services import permissions

DB_PATH = os.path.join("data", "owlin.db")

def get_conn() -> sqlite3.Connection:
    """Get database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def _get_historical_prices(item_id: int, supplier_id: Optional[int] = None, venue_id: Optional[int] = None) -> pd.DataFrame:
    """Get historical prices for an item."""
    conn = get_conn()
    
    # Build query based on available filters
    query = """
        SELECT date, unit_price, quantity, total_amount
        FROM item_price_history 
        WHERE item_id = ?
    """
    params = [item_id]
    
    if supplier_id:
        query += " AND supplier_id = ?"
        params.append(supplier_id)
    
    if venue_id:
        query += " AND venue_id = ?"
        params.append(venue_id)
    
    query += " ORDER BY date ASC"
    
    try:
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
    except Exception:
        df = pd.DataFrame()
    
    conn.close()
    return df

def _preprocess_series(df: pd.DataFrame) -> pd.Series:
    """Preprocess price series with outlier removal and aggregation."""
    if df.empty:
        return pd.Series(dtype=float)
    
    # Aggregate to monthly (median to reduce outliers)
    df['month'] = df['date'].dt.to_period('M')
    monthly = df.groupby('month')['unit_price'].median().sort_index()
    
    # Convert period to timestamp
    monthly.index = monthly.index.astype(str).map(pd.to_datetime)
    
    # Outlier removal using MAD (Median Absolute Deviation)
    if len(monthly) > 3:
        median = monthly.median()
        mad = np.median(np.abs(monthly - median))
        if mad > 0:
            # Cap at 3.5 MAD
            lower_bound = median - 3.5 * mad
            upper_bound = median + 3.5 * mad
            monthly = monthly.clip(lower=lower_bound, upper=upper_bound)
    
    # Forward fill missing months
    if len(monthly) > 0:
        full_range = pd.date_range(monthly.index.min(), monthly.index.max(), freq='MS')
        monthly = monthly.reindex(full_range).fillna(method='ffill')
    
    return monthly

def _naive_forecast(series: pd.Series, horizon: int) -> Tuple[List[float], float]:
    """Naive forecast: last observed value."""
    if series.empty:
        return [0.0] * horizon, 0.0
    
    last_value = series.iloc[-1]
    forecast = [last_value] * horizon
    
    # Estimate std from historical variance
    std = series.std() if len(series) > 1 else 0.0
    
    return forecast, std

def _seasonal_naive_forecast(series: pd.Series, horizon: int) -> Tuple[List[float], float]:
    """Seasonal naive forecast: repeat last year's month."""
    if len(series) < 24:  # Need at least 2 years
        return _naive_forecast(series, horizon)
    
    forecast = []
    for i in range(horizon):
        # Get the same month from last year
        target_month = series.index[-1] + pd.DateOffset(months=i+1)
        last_year_month = target_month - pd.DateOffset(years=1)
        
        if last_year_month in series.index:
            forecast.append(series[last_year_month])
        else:
            # Fallback to naive
            forecast.append(series.iloc[-1])
    
    std = series.std() if len(series) > 1 else 0.0
    return forecast, std

def _ewma_forecast(series: pd.Series, horizon: int, alpha: float = 0.3) -> Tuple[List[float], float]:
    """Exponential Weighted Moving Average forecast."""
    if series.empty:
        return [0.0] * horizon, 0.0
    
    # Calculate EWMA
    ewma_values = series.ewm(alpha=alpha).mean()
    last_ewma = ewma_values.iloc[-1]
    
    # Simple forecast: continue the trend
    forecast = [last_ewma] * horizon
    
    # Estimate std from residuals
    residuals = series - ewma_values
    std = residuals.std() if len(residuals) > 1 else 0.0
    
    return forecast, std

def _holt_winters_forecast(series: pd.Series, horizon: int) -> Tuple[List[float], float]:
    """Holt-Winters forecast (simplified implementation)."""
    if len(series) < 12:
        return _ewma_forecast(series, horizon)
    
    # Simple implementation: trend + seasonal
    # For now, use EWMA as fallback
    return _ewma_forecast(series, horizon, alpha=0.2)

def _calculate_metrics(actual: List[float], predicted: List[float]) -> Dict[str, float]:
    """Calculate forecast accuracy metrics."""
    if not actual or not predicted:
        return {'smape': float('inf'), 'mape': float('inf'), 'wape': float('inf'), 'bias_pct': 0.0}
    
    min_len = min(len(actual), len(predicted))
    actual = actual[:min_len]
    predicted = predicted[:min_len]
    
    # SMAPE
    smape_numerator = sum(abs(a - p) for a, p in zip(actual, predicted))
    smape_denominator = sum(abs(a) + abs(p) for a, p in zip(actual, predicted))
    smape = (2 * smape_numerator / smape_denominator) if smape_denominator > 0 else float('inf')
    
    # MAPE
    mape_errors = [abs(a - p) / (abs(a) + 1e-8) for a, p in zip(actual, predicted)]
    mape = np.mean(mape_errors) * 100
    
    # WAPE
    wape_numerator = sum(abs(a - p) for a, p in zip(actual, predicted))
    wape_denominator = sum(abs(a) for a in actual)
    wape = (wape_numerator / wape_denominator) if wape_denominator > 0 else float('inf')
    
    # Bias
    mean_actual = np.mean(actual) if actual else 0
    bias_pct = ((np.mean(predicted) - mean_actual) / mean_actual * 100) if mean_actual > 0 else 0
    
    return {
        'smape': smape,
        'mape': mape,
        'wape': wape,
        'bias_pct': bias_pct
    }

def _rolling_backtest(series: pd.Series, model_func, model_params: Dict = None) -> Dict[str, float]:
    """Perform rolling origin backtest."""
    if len(series) < 12:
        return {'smape': float('inf'), 'mape': float('inf'), 'wape': float('inf'), 'bias_pct': 0.0}
    
    # 5-fold rolling origin
    fold_metrics = []
    min_train_size = 6
    test_size = 1
    
    for i in range(5):
        if len(series) < min_train_size + test_size + i:
            break
        
        train_end = len(series) - test_size - i
        if train_end < min_train_size:
            break
        
        train_series = series.iloc[:train_end]
        test_actual = series.iloc[train_end:train_end + test_size].tolist()
        
        # Generate forecast
        if model_params:
            forecast, _ = model_func(train_series, test_size, **model_params)
        else:
            forecast, _ = model_func(train_series, test_size)
        
        # Calculate metrics for this fold
        metrics = _calculate_metrics(test_actual, forecast[:len(test_actual)])
        fold_metrics.append(metrics)
    
    if not fold_metrics:
        return {'smape': float('inf'), 'mape': float('inf'), 'wape': float('inf'), 'bias_pct': 0.0}
    
    # Average across folds
    avg_metrics = {}
    for key in ['smape', 'mape', 'wape', 'bias_pct']:
        avg_metrics[key] = np.mean([m[key] for m in fold_metrics])
    
    return avg_metrics

def _select_best_model(series: pd.Series) -> Tuple[str, Dict[str, float], Dict]:
    """Select best model based on backtesting."""
    models = {
        'naive': (_naive_forecast, {}),
        'seasonal_naive': (_seasonal_naive_forecast, {}),
        'ewma_0.1': (_ewma_forecast, {'alpha': 0.1}),
        'ewma_0.2': (_ewma_forecast, {'alpha': 0.2}),
        'ewma_0.3': (_ewma_forecast, {'alpha': 0.3}),
        'ewma_0.5': (_ewma_forecast, {'alpha': 0.5}),
        'holt_winters': (_holt_winters_forecast, {})
    }
    
    best_model = 'naive'
    best_metrics = {'smape': float('inf')}
    all_metrics = {}
    
    # Test each model
    for model_name, (model_func, params) in models.items():
        metrics = _rolling_backtest(series, model_func, params)
        all_metrics[model_name] = metrics
        
        if metrics['smape'] < best_metrics['smape']:
            best_metrics = metrics
            best_model = model_name
    
    # Acceptance rule: must beat best baseline by >= 3% SMAPE
    baseline_models = ['naive', 'seasonal_naive']
    baseline_smape = min(all_metrics.get(m, {}).get('smape', float('inf')) for m in baseline_models)
    
    if best_metrics['smape'] > baseline_smape - 0.03:
        # Fallback to best baseline
        best_baseline = min(baseline_models, key=lambda m: all_metrics.get(m, {}).get('smape', float('inf')))
        best_model = best_baseline
        best_metrics = all_metrics[best_baseline]
    
    return best_model, best_metrics, all_metrics

def _apply_scenario(series: pd.Series, scenario: ForecastScenario) -> pd.Series:
    """Apply scenario adjustments to the series."""
    if series.empty:
        return series
    
    adjusted_series = series.copy()
    
    # Apply shock to last known price
    if scenario.shock_pct != 0:
        last_price = adjusted_series.iloc[-1]
        shock_factor = 1 + (scenario.shock_pct / 100)
        adjusted_series.iloc[-1] = last_price * shock_factor
    
    return adjusted_series

def _generate_forecast_points(forecast_values: List[float], std: float, start_date: datetime, scenario: ForecastScenario = None) -> List[ForecastPoint]:
    """Generate forecast points with confidence intervals."""
    points = []
    
    for i, yhat in enumerate(forecast_values):
        # Calculate date
        forecast_date = start_date + pd.DateOffset(months=i+1)
        
        # Apply inflation drift if specified
        if scenario and scenario.inflation_annual_pct != 0:
            monthly_rate = (1 + scenario.inflation_annual_pct / 100) ** (1/12) - 1
            inflation_factor = (1 + monthly_rate) ** (i + 1)
            yhat = yhat * inflation_factor
        
        # Ensure non-negative
        yhat = max(0, yhat)
        
        # Calculate confidence intervals
        yhat_lower = max(0, yhat - 1.28 * std)  # 80% CI
        yhat_upper = yhat + 1.28 * std  # 80% CI
        
        points.append(ForecastPoint(
            t=forecast_date.strftime('%Y-%m-%d'),
            yhat=round(yhat, 2),
            yhat_lower=round(yhat_lower, 2),
            yhat_upper=round(yhat_upper, 2)
        ))
    
    return points

def compute_forecast(item_id: int, horizon_months: int = 12, supplier_id: Optional[int] = None, 
                    venue_id: Optional[int] = None, scenario: ForecastScenario = None) -> ForecastSeries:
    """Compute forecast for an item."""
    # Get historical data
    df = _get_historical_prices(item_id, supplier_id, venue_id)
    series = _preprocess_series(df)
    
    if len(series) < 12:
        # Insufficient history - return empty forecast
        return ForecastSeries(
            item_id=item_id,
            supplier_id=supplier_id,
            venue_id=venue_id,
            horizon_months=horizon_months,
            granularity="month",
            model="insufficient_history",
            version=1,
            points=[],
            explain={"reason": "Insufficient historical data (need 12+ months)"}
        )
    
    # Apply scenario adjustments
    if scenario:
        series = _apply_scenario(series, scenario)
    
    # Select best model
    best_model, metrics, all_metrics = _select_best_model(series)
    
    # Generate forecast
    if best_model == 'naive':
        forecast_values, std = _naive_forecast(series, horizon_months)
    elif best_model == 'seasonal_naive':
        forecast_values, std = _seasonal_naive_forecast(series, horizon_months)
    elif best_model.startswith('ewma_'):
        alpha = float(best_model.split('_')[1])
        forecast_values, std = _ewma_forecast(series, horizon_months, alpha)
    elif best_model == 'holt_winters':
        forecast_values, std = _holt_winters_forecast(series, horizon_months)
    else:
        forecast_values, std = _naive_forecast(series, horizon_months)
    
    # Generate forecast points
    start_date = series.index[-1]
    points = _generate_forecast_points(forecast_values, std, start_date, scenario)
    
    # Create explain metadata
    explain = {
        "model": best_model,
        "metrics": metrics,
        "all_metrics": all_metrics,
        "history_length": len(series),
        "last_known_price": float(series.iloc[-1]),
        "scenario_applied": scenario.dict() if scenario else None,
        "acceptance_reason": "Model selected" if metrics['smape'] <= min(all_metrics.get(m, {}).get('smape', float('inf')) for m in ['naive', 'seasonal_naive']) - 0.03 else "Baseline chosen for reliability"
    }
    
    return ForecastSeries(
        item_id=item_id,
        supplier_id=supplier_id,
        venue_id=venue_id,
        horizon_months=horizon_months,
        granularity="month",
        model=best_model,
        version=1,
        points=points,
        explain=explain
    )

def save_forecast(forecast: ForecastSeries) -> None:
    """Save forecast to database."""
    conn = get_conn()
    cursor = conn.cursor()
    
    forecast_id = str(uuid4())
    
    cursor.execute("""
        INSERT OR REPLACE INTO forecasts (id, item_id, supplier_id, venue_id, model, horizon_months, 
                                        granularity, version, series_json, explain_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        forecast_id,
        forecast.item_id,
        forecast.supplier_id,
        forecast.venue_id,
        forecast.model,
        forecast.horizon_months,
        forecast.granularity,
        forecast.version,
        json.dumps([p.dict() for p in forecast.points]),
        json.dumps(forecast.explain)
    ))
    
    # Save metrics
    if 'metrics' in forecast.explain:
        metrics = forecast.explain['metrics']
        cursor.execute("""
            INSERT OR REPLACE INTO forecast_metrics (id, item_id, model, window_days, smape, mape, wape, bias_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            forecast.item_id,
            forecast.model,
            180,  # 6 months window
            metrics.get('smape', 0.0),
            metrics.get('mape', 0.0),
            metrics.get('wape', 0.0),
            metrics.get('bias_pct', 0.0)
        ))
    
    conn.commit()
    conn.close()

def get_forecast_summary(limit: int = 50, offset: int = 0, search: str = None, 
                        supplier_id: Optional[int] = None, venue_id: Optional[int] = None) -> Dict[str, Any]:
    """Get forecast summary for items."""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Get items with forecasts
    query = """
        SELECT DISTINCT f.item_id, f.model, f.horizon_months, f.series_json, f.explain_json
        FROM forecasts f
        WHERE 1=1
    """
    params = []
    
    if supplier_id:
        query += " AND f.supplier_id = ?"
        params.append(supplier_id)
    
    if venue_id:
        query += " AND f.venue_id = ?"
        params.append(venue_id)
    
    query += " ORDER BY f.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    items = []
    for row in rows:
        item_id, model, horizon, series_json, explain_json = row
        
        try:
            series_data = json.loads(series_json)
            explain_data = json.loads(explain_json)
            
            # Get latest price and forecasts
            latest_price = explain_data.get('last_known_price', 0.0)
            
            # Get 1m, 3m, 12m forecasts
            forecast_1m = series_data[0]['yhat'] if len(series_data) > 0 else latest_price
            forecast_3m = series_data[2]['yhat'] if len(series_data) > 2 else latest_price
            forecast_12m = series_data[11]['yhat'] if len(series_data) > 11 else latest_price
            
            # Calculate trend
            trend = "up" if forecast_3m > latest_price else "down" if forecast_3m < latest_price else "flat"
            
            items.append({
                'item_id': item_id,
                'name': f"Item {item_id}",  # Would need items table lookup
                'latest_price': latest_price,
                'trend': trend,
                'forecast_1m': forecast_1m,
                'forecast_3m': forecast_3m,
                'forecast_12m': forecast_12m,
                'model': model
            })
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
    
    conn.close()
    
    return {'items': items}

def get_forecast_quality(item_id: int) -> Optional[ForecastQuality]:
    """Get quality metrics for an item's best model."""
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT model, window_days, smape, mape, wape, bias_pct
        FROM forecast_metrics 
        WHERE item_id = ? 
        ORDER BY smape ASC 
        LIMIT 1
    """, (item_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        model, window_days, smape, mape, wape, bias_pct = row
        return ForecastQuality(
            item_id=item_id,
            model=model,
            window_days=window_days,
            smape=smape,
            mape=mape,
            wape=wape,
            bias_pct=bias_pct
        )
    
    return None 
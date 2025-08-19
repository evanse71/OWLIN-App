// Forecast TypeScript interfaces

export interface ForecastPoint {
  t: string;                 // ISO date (month start)
  yhat: number;
  yhat_lower: number;
  yhat_upper: number;
}

export interface ForecastSeries {
  item_id: number;
  supplier_id?: number;
  venue_id?: number;
  horizon_months: number;
  granularity: "month";
  model: string;
  version: number;
  points: ForecastPoint[];
  explain: Record<string, any>;   // includes residual sd, params, scenario info
}

export interface ForecastQuality {
  item_id: number;
  model: string;
  window_days: number;
  smape: number;
  mape: number;
  wape: number;
  bias_pct: number;
}

export interface ForecastSummary {
  items: Array<{
    item_id: number;
    name: string;
    latest_price: number;
    trend: string;
    forecast_1m: number;
    forecast_3m: number;
    forecast_12m: number;
  }>;
}

export interface ForecastScenario {
  inflation_annual_pct: number;        // 0..10%
  shock_pct: number;                   // apply to last known price (+/-)
  weight_by_venue: boolean;
  alt_supplier_id?: number;
}

export interface ForecastItem {
  item_id: number;
  name: string;
  latest_price: number;
  trend: string;
  forecast_1m: number;
  forecast_3m: number;
  forecast_12m: number;
} 
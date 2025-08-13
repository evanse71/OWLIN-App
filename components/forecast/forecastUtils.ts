// forecastUtils.ts
// Utility functions for forecast panels and trend graphs

export type ConfidenceLevel = 'low' | 'medium' | 'high';
export type VolatilityLevel = 'low' | 'moderate' | 'high';

export function getConfidenceBadge(level: ConfidenceLevel): { label: string; color: string } {
  switch (level) {
    case 'high':
      return { label: 'High Confidence', color: 'bg-green-100 text-green-800' };
    case 'medium':
      return { label: 'Medium Confidence', color: 'bg-yellow-100 text-yellow-800' };
    case 'low':
    default:
      return { label: 'Low Confidence', color: 'bg-red-100 text-red-800' };
  }
}

export function getVolatilityBadge(level: VolatilityLevel): { label: string; color: string } {
  switch (level) {
    case 'low':
      return { label: 'Low Volatility', color: 'bg-green-50 text-green-700' };
    case 'moderate':
      return { label: 'Moderate Volatility', color: 'bg-yellow-50 text-yellow-700' };
    case 'high':
    default:
      return { label: 'High Volatility', color: 'bg-red-50 text-red-700' };
  }
}

export function generateInsightMessage(confidence: ConfidenceLevel, volatility: VolatilityLevel): string {
  if (confidence === 'high' && volatility === 'low') {
    return 'Forecast is highly reliable with stable price trends.';
  }
  if (confidence === 'high' && volatility === 'moderate') {
    return 'Forecast is reliable, but some price fluctuation is expected.';
  }
  if (confidence === 'medium' && volatility === 'moderate') {
    return 'Forecast is moderately reliable; monitor for price swings.';
  }
  if (confidence === 'low' || volatility === 'high') {
    return 'Forecast is uncertain due to high price volatility.';
  }
  return 'Forecast reliability and volatility are within normal range.';
}

export function formatCurrency(value: number): string {
  return value.toLocaleString('en-GB', { style: 'currency', currency: 'GBP' });
} 
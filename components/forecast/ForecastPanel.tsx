import React from 'react';
import UniversalTrendGraph from './UniversalTrendGraph';
import { getConfidenceBadge, getVolatilityBadge, generateInsightMessage, formatCurrency, ConfidenceLevel, VolatilityLevel } from './forecastUtils';

export interface ForecastPanelProps {
  productName: string;
  historic?: { x: string; y: number }[];
  forecast?: { x: string; y: number; upper?: number; lower?: number }[];
  confidence?: ConfidenceLevel;
  volatility?: VolatilityLevel;
  dataPoints?: number;
}

const ForecastPanel: React.FC<ForecastPanelProps> = ({
  productName,
  historic = [],
  forecast = [],
  confidence = 'medium',
  volatility = 'moderate',
  dataPoints = 0,
}) => {
  const hasData = historic.length > 0 && forecast.length > 0;
  const confidenceBadge = getConfidenceBadge(confidence);
  const volatilityBadge = getVolatilityBadge(volatility);
  const insight = generateInsightMessage(confidence, volatility);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-8 transition-colors">
      <div className="flex items-center mb-2">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mr-4">{productName}</h2>
        <span className={`ml-auto px-3 py-1 rounded-full text-xs font-medium ${confidenceBadge.color} mr-2`}>{confidenceBadge.label}</span>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${volatilityBadge.color}`}>{volatilityBadge.label}</span>
      </div>
      {hasData ? (
        <>
          <div className="mb-2">
            <UniversalTrendGraph
              historic={historic}
              forecast={forecast}
              xLabel="Date"
              yLabel="Price (£)"
              lineLabel="Unit Price"
              color="#1C2D45"
              height={320}
              fadeIn
              theme={typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'}
              showDots={false}
              confidence={confidence}
              volatility={volatility}
              data_points={dataPoints}
            />
          </div>
          <div className="text-gray-700 dark:text-gray-300 text-sm mt-2">
            <span className="font-medium">Insight:</span> {insight}
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center h-48 text-gray-400 dark:text-gray-500">
          <svg className="w-12 h-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-base font-medium">No forecast data available</div>
        </div>
      )}
    </div>
  );
};

export default ForecastPanel; 
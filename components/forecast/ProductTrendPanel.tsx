import React, { useState } from 'react';
import UniversalTrendGraph from './UniversalTrendGraph';
import { getConfidenceBadge, getVolatilityBadge, generateInsightMessage, ConfidenceLevel, VolatilityLevel } from './forecastUtils';

export interface ProductTrendPanelProps {
  productName: string;
  historic?: { x: string; y: number }[];
  forecast?: { x: string; y: number; upper?: number; lower?: number }[];
  confidence?: ConfidenceLevel;
  volatility?: VolatilityLevel;
  dataPoints?: number;
}

const ProductTrendPanel: React.FC<ProductTrendPanelProps> = ({
  productName,
  historic = [],
  forecast = [],
  confidence = 'medium',
  volatility = 'moderate',
  dataPoints = 0,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasData = historic.length > 0 && forecast.length > 0;
  const confidenceBadge = getConfidenceBadge(confidence);
  const volatilityBadge = getVolatilityBadge(volatility);
  const insight = generateInsightMessage(confidence, volatility);

  // Get current price (last historic value)
  const currentPrice = historic.length > 0 ? historic[historic.length - 1].y : 0;

  // Create mini sparkline data (last 5 points)
  const miniSparkline = historic.slice(-5);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 mb-4 transition-all duration-200 hover:shadow-md">
      {/* Header - Always visible */}
      <div 
        className="p-6 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {productName}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Current: £{currentPrice.toFixed(2)}
              </p>
            </div>
            
            {/* Mini sparkline */}
            {hasData && miniSparkline.length > 0 && (
              <div className="w-20 h-8 bg-gray-50 dark:bg-gray-700 rounded p-1">
                <svg width="100%" height="100%" viewBox="0 0 80 30">
                  <polyline
                    fill="none"
                    stroke="#1C2D45"
                    strokeWidth="1.5"
                    points={miniSparkline.map((point, index) => {
                      const x = (index / (miniSparkline.length - 1)) * 70 + 5;
                      const y = 25 - ((point.y - Math.min(...miniSparkline.map(p => p.y))) / 
                                   (Math.max(...miniSparkline.map(p => p.y)) - Math.min(...miniSparkline.map(p => p.y)))) * 20;
                      return `${x},${y}`;
                    }).join(' ')}
                  />
                </svg>
              </div>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {/* Badges */}
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${confidenceBadge.color}`}>
              {confidenceBadge.label}
            </span>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${volatilityBadge.color}`}>
              {volatilityBadge.label}
            </span>
            
            {/* Expand/collapse icon */}
            <div className={`transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-gray-100 dark:border-gray-700 p-6">
          {hasData ? (
            <>
              <div className="mb-4">
                <UniversalTrendGraph
                  historic={historic}
                  forecast={forecast}
                  xLabel="Date"
                  yLabel="Price (£)"
                  lineLabel="Unit Price"
                  color="#1C2D45"
                  height={280}
                  fadeIn
                  theme={typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'}
                  showDots={false}
                  confidence={confidence}
                  volatility={volatility}
                  data_points={dataPoints}
                />
              </div>
              <div className="text-gray-700 dark:text-gray-300 text-sm">
                <span className="font-medium">Insight:</span> {insight}
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-32 text-gray-400 dark:text-gray-500">
              <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="text-sm font-medium">No forecast data available</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ProductTrendPanel; 
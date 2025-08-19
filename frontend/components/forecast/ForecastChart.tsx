import React from 'react';
import { ForecastSeries } from '../../types/forecast';

interface ForecastChartProps {
  forecast: ForecastSeries;
}

const ForecastChart: React.FC<ForecastChartProps> = ({ forecast }) => {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { month: 'short', year: '2-digit' });
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      minimumFractionDigits: 2
    }).format(price);
  };

  // Calculate chart dimensions and scales
  const chartWidth = 600;
  const chartHeight = 300;
  const padding = 40;

  const prices = forecast.points.map(p => p.yhat);
  const minPrice = Math.min(...prices, ...forecast.points.map(p => p.yhat_lower));
  const maxPrice = Math.max(...prices, ...forecast.points.map(p => p.yhat_upper));
  const priceRange = maxPrice - minPrice;

  const xScale = (index: number) => {
    const availableWidth = chartWidth - 2 * padding;
    return padding + (index / (forecast.points.length - 1)) * availableWidth;
  };

  const yScale = (price: number) => {
    const availableHeight = chartHeight - 2 * padding;
    return chartHeight - padding - ((price - minPrice) / priceRange) * availableHeight;
  };

  // Generate SVG path for confidence intervals
  const generateConfidencePath = () => {
    if (forecast.points.length < 2) return '';
    
    const upperPoints = forecast.points.map((point, index) => 
      `${xScale(index)},${yScale(point.yhat_upper)}`
    ).join(' ');
    
    const lowerPoints = forecast.points.slice().reverse().map((point, index) => 
      `${xScale(forecast.points.length - 1 - index)},${yScale(point.yhat_lower)}`
    ).join(' ');
    
    return `M ${upperPoints} L ${lowerPoints} Z`;
  };

  // Generate SVG path for forecast line
  const generateForecastPath = () => {
    if (forecast.points.length < 2) return '';
    
    const points = forecast.points.map((point, index) => 
      `${xScale(index)},${yScale(point.yhat)}`
    ).join(' ');
    
    return `M ${points}`;
  };

  return (
    <div className="bg-white rounded-[12px] p-6 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Price Forecast</h3>
          <p className="text-sm text-gray-600">
            {forecast.horizon_months}-month horizon • {forecast.model} model
          </p>
        </div>
        
        <div className="text-right">
          <div className="text-sm text-gray-600">Model Version</div>
          <div className="text-lg font-semibold text-gray-900">v{forecast.version}</div>
        </div>
      </div>

      <div className="relative">
        <svg
          width={chartWidth}
          height={chartHeight}
          className="w-full h-auto"
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        >
          {/* Grid lines */}
          <defs>
            <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#F3F4F6" strokeWidth="1"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Confidence interval fill */}
          <path
            d={generateConfidencePath()}
            fill="rgba(37, 99, 235, 0.1)"
            stroke="none"
          />

          {/* Forecast line */}
          <path
            d={generateForecastPath()}
            stroke="#2563EB"
            strokeWidth="2"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data points */}
          {forecast.points.map((point, index) => (
            <circle
              key={index}
              cx={xScale(index)}
              cy={yScale(point.yhat)}
              r="4"
              fill="#2563EB"
              stroke="white"
              strokeWidth="2"
            />
          ))}

          {/* Y-axis labels */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const price = minPrice + ratio * priceRange;
            return (
              <g key={ratio}>
                <line
                  x1={padding - 5}
                  y1={yScale(price)}
                  x2={padding}
                  y2={yScale(price)}
                  stroke="#9CA3AF"
                  strokeWidth="1"
                />
                <text
                  x={padding - 10}
                  y={yScale(price) + 4}
                  textAnchor="end"
                  fontSize="12"
                  fill="#6B7280"
                >
                  {formatPrice(price)}
                </text>
              </g>
            );
          })}

          {/* X-axis labels */}
          {forecast.points.map((point, index) => {
            if (index % Math.max(1, Math.floor(forecast.points.length / 6)) === 0) {
              return (
                <g key={index}>
                  <line
                    x1={xScale(index)}
                    y1={chartHeight - padding}
                    x2={xScale(index)}
                    y2={chartHeight - padding + 5}
                    stroke="#9CA3AF"
                    strokeWidth="1"
                  />
                  <text
                    x={xScale(index)}
                    y={chartHeight - padding + 20}
                    textAnchor="middle"
                    fontSize="12"
                    fill="#6B7280"
                  >
                    {formatDate(point.t)}
                  </text>
                </g>
              );
            }
            return null;
          })}
        </svg>

        {/* Legend */}
        <div className="flex justify-center mt-4 space-x-6">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-[#2563EB] rounded-full"></div>
            <span className="text-sm text-gray-600">Forecast</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-blue-100 rounded"></div>
            <span className="text-sm text-gray-600">80% Confidence</span>
          </div>
        </div>
      </div>

      {/* Model explanation */}
      {forecast.explain && (
        <div className="mt-4 p-3 bg-gray-50 rounded-[8px]">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Model Details</h4>
          <div className="text-xs text-gray-600 space-y-1">
            {forecast.explain.residual_sd && (
              <div>Residual SD: {forecast.explain.residual_sd.toFixed(2)}</div>
            )}
            {forecast.explain.params && (
              <div>Parameters: {JSON.stringify(forecast.explain.params)}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ForecastChart; 
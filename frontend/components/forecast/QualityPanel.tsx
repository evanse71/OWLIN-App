import React from 'react';
import { ForecastQuality } from '../../types/forecast';

interface QualityPanelProps {
  quality: ForecastQuality | null;
}

const QualityPanel: React.FC<QualityPanelProps> = ({ quality }) => {
  const getQualityColor = (metric: string, value: number) => {
    switch (metric) {
      case 'smape':
      case 'mape':
      case 'wape':
        // Lower is better for error metrics
        if (value < 10) return 'text-green-600';
        if (value < 20) return 'text-yellow-600';
        return 'text-red-600';
      case 'bias_pct':
        // Closer to 0 is better for bias
        if (Math.abs(value) < 5) return 'text-green-600';
        if (Math.abs(value) < 10) return 'text-yellow-600';
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getQualityBadge = (metric: string, value: number) => {
    switch (metric) {
      case 'smape':
      case 'mape':
      case 'wape':
        if (value < 10) return { text: 'Excellent', color: 'bg-green-100 text-green-800' };
        if (value < 20) return { text: 'Good', color: 'bg-yellow-100 text-yellow-800' };
        return { text: 'Poor', color: 'bg-red-100 text-red-800' };
      case 'bias_pct':
        if (Math.abs(value) < 5) return { text: 'Unbiased', color: 'bg-green-100 text-green-800' };
        if (Math.abs(value) < 10) return { text: 'Slight Bias', color: 'bg-yellow-100 text-yellow-800' };
        return { text: 'Biased', color: 'bg-red-100 text-red-800' };
      default:
        return { text: 'Unknown', color: 'bg-gray-100 text-gray-800' };
    }
  };

  if (!quality) {
    return (
      <div className="bg-white rounded-[12px] p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Forecast Quality</h3>
        <div className="text-center py-8 text-gray-500">
          <svg className="mx-auto h-8 w-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-sm">No quality metrics available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-[12px] p-6 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Forecast Quality</h3>
        <div className="text-sm text-gray-600">
          {quality.window_days}-day window
        </div>
      </div>

      <div className="space-y-4">
        {/* Model Info */}
        <div className="p-3 bg-gray-50 rounded-[8px]">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-900">Model</span>
            <span className="text-sm text-gray-600">{quality.model}</span>
          </div>
        </div>

        {/* SMAPE */}
        <div className="border border-gray-200 rounded-[8px] p-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-900">SMAPE</span>
            <span className={`text-lg font-semibold ${getQualityColor('smape', quality.smape)}`}>
              {quality.smape.toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-600">Symmetric Mean Absolute Percentage Error</span>
            <span className={`px-2 py-1 text-xs rounded-full ${getQualityBadge('smape', quality.smape).color}`}>
              {getQualityBadge('smape', quality.smape).text}
            </span>
          </div>
        </div>

        {/* MAPE */}
        <div className="border border-gray-200 rounded-[8px] p-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-900">MAPE</span>
            <span className={`text-lg font-semibold ${getQualityColor('mape', quality.mape)}`}>
              {quality.mape.toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-600">Mean Absolute Percentage Error</span>
            <span className={`px-2 py-1 text-xs rounded-full ${getQualityBadge('mape', quality.mape).color}`}>
              {getQualityBadge('mape', quality.mape).text}
            </span>
          </div>
        </div>

        {/* WAPE */}
        <div className="border border-gray-200 rounded-[8px] p-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-900">WAPE</span>
            <span className={`text-lg font-semibold ${getQualityColor('wape', quality.wape)}`}>
              {quality.wape.toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-600">Weighted Absolute Percentage Error</span>
            <span className={`px-2 py-1 text-xs rounded-full ${getQualityBadge('wape', quality.wape).color}`}>
              {getQualityBadge('wape', quality.wape).text}
            </span>
          </div>
        </div>

        {/* Bias */}
        <div className="border border-gray-200 rounded-[8px] p-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-900">Bias</span>
            <span className={`text-lg font-semibold ${getQualityColor('bias_pct', quality.bias_pct)}`}>
              {quality.bias_pct > 0 ? '+' : ''}{quality.bias_pct.toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-600">Forecast bias percentage</span>
            <span className={`px-2 py-1 text-xs rounded-full ${getQualityBadge('bias_pct', quality.bias_pct).color}`}>
              {getQualityBadge('bias_pct', quality.bias_pct).text}
            </span>
          </div>
        </div>

        {/* Overall Quality Score */}
        <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-[8px] border border-blue-200">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Overall Quality</h4>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Model Performance</span>
            </div>
            <div className="text-right">
              <div className="text-lg font-semibold text-blue-600">
                {((100 - (quality.smape + quality.mape + quality.wape) / 3) * 0.7 + 
                  (100 - Math.abs(quality.bias_pct)) * 0.3).toFixed(0)}%
              </div>
              <div className="text-xs text-gray-600">Quality Score</div>
            </div>
          </div>
        </div>

        {/* Quality Legend */}
        <div className="mt-4 p-3 bg-gray-50 rounded-[8px]">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Quality Guide</h4>
          <div className="text-xs text-gray-600 space-y-1">
            <div className="flex justify-between">
              <span>SMAPE/MAPE/WAPE:</span>
              <span>&lt;10% Excellent, &lt;20% Good, &gt;20% Poor</span>
            </div>
            <div className="flex justify-between">
              <span>Bias:</span>
              <span>&lt;5% Unbiased, &lt;10% Slight, &gt;10% Biased</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QualityPanel; 
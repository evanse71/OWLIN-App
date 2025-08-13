import React from 'react';

interface SupplierMetrics {
  name: string;
  mismatchPercentage: number;
  lateDeliveryRate: number;
  priceVolatility: number;
  totalInvoices: number;
  averageAmount: number;
  lastInvoiceDate: string;
  riskLevel: 'low' | 'medium' | 'high';
}

interface SupplierInsightsProps {
  supplierName: string;
  isVisible: boolean;
  onClose: () => void;
}

const SupplierInsights: React.FC<SupplierInsightsProps> = ({
  supplierName,
  isVisible,
  onClose,
}) => {
  // Mock supplier metrics - in real app, this would come from API
  const mockMetrics: SupplierMetrics = {
    name: supplierName,
    mismatchPercentage: 12.5,
    lateDeliveryRate: 8.3,
    priceVolatility: 15.2,
    totalInvoices: 45,
    averageAmount: 1250.75,
    lastInvoiceDate: '2024-01-15',
    riskLevel: 'medium',
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30';
      case 'medium': return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30';
      case 'high': return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30';
      default: return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30';
    }
  };

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return '✅';
      case 'medium': return '⚠️';
      case 'high': return '🚨';
      default: return '❓';
    }
  };

  if (!isVisible) return null;

  return (
    <div className="absolute z-50 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          Supplier Insights
        </h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Supplier Name */}
      <div className="mb-3">
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {mockMetrics.name}
        </div>
        <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(mockMetrics.riskLevel)}`}>
          <span className="mr-1">{getRiskIcon(mockMetrics.riskLevel)}</span>
          {mockMetrics.riskLevel.charAt(0).toUpperCase() + mockMetrics.riskLevel.slice(1)} Risk
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
          <div className="text-lg font-bold text-red-600 dark:text-red-400">
            {mockMetrics.mismatchPercentage}%
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400">
            Price Mismatch
          </div>
        </div>
        <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
          <div className="text-lg font-bold text-orange-600 dark:text-orange-400">
            {mockMetrics.lateDeliveryRate}%
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400">
            Late Deliveries
          </div>
        </div>
        <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
          <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
            {mockMetrics.priceVolatility}%
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400">
            Price Volatility
          </div>
        </div>
        <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
          <div className="text-lg font-bold text-green-600 dark:text-green-400">
            {mockMetrics.totalInvoices}
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400">
            Total Invoices
          </div>
        </div>
      </div>

      {/* Additional Info */}
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Average Amount:</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            £{mockMetrics.averageAmount.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Last Invoice:</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {mockMetrics.lastInvoiceDate}
          </span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-4 space-y-2">
        <button className="w-full px-3 py-2 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">
          📊 View Full Report
        </button>
        {mockMetrics.riskLevel === 'high' && (
          <button className="w-full px-3 py-2 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors">
            🚨 Escalate Supplier
          </button>
        )}
      </div>
    </div>
  );
};

export default SupplierInsights; 